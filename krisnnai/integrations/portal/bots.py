"""Portal bots: log in, look a claim up, read what the portal says, keep the page as evidence, log out of the story.

Rules the bots follow:
  * credentials come from environment variables the caller names; they are never logged or written anywhere
  * every page is checked for the elements the bot expects; a mismatch stops the whole run, nothing else is clicked
  * a bot reads and records; it submits nothing, changes nothing, and never answers a request on the practice's behalf
  * evidence (the page as received) is saved per claim
  * MFA, CAPTCHA, script-drawn pages, a locked account, maintenance and a second session expiry stop the run and are
    handed to a person (outcome `needs_human`); the bot never tries to solve, bypass or retry them
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from krisnnai.integrations.portal.driver import HttpDriver, ScreenChanged

LOGIN_IDS = ["username", "password", "login-submit"]
SEARCH_IDS = ["claim-search", "search-submit", "results"]
DETAIL_IDS = ["claim-title", "claim-status", "pend-reason", "paid-amount"]
RECORDS_IDS = ["request-text", "request-open"]
HANDOFF_IDS = {"maintenance": "maintenance", "account-locked": "account_locked", "mfa-code": "mfa",
               "captcha-box": "captcha", "js-required": "js_required"}  # element id -> reason


MAX_RELOGINS = 5


class NeedsHuman(Exception):
    """The portal asks for something only a person should do. The run stops; nothing else is requested."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class PortalResult:
    claim: str
    outcome: str  # read | not_found | login_failed | screen_changed | not_attempted | rate_limited | needs_human
    status: str = ""
    reason: str = ""
    paid: str = ""
    records_requested: bool | None = None
    evidence: list[str] = field(default_factory=list)
    detail: str = ""
    handoff: str = ""  # why a person is needed, when outcome is needs_human


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def credentials_from_env(user_env: str, pass_env: str) -> tuple[str, str]:
    user, password = os.environ.get(user_env, ""), os.environ.get(pass_env, "")
    if not user or not password:
        raise SystemExit(f"set the environment variables {user_env} and {pass_env} for this portal")
    return user, password


def _check(page) -> None:  # noqa: ANN001
    """Raise NeedsHuman if the page is one of the things a person must handle."""
    if page.status == 503:
        raise NeedsHuman("maintenance")
    ids = page.ids()
    for ident, reason in HANDOFF_IDS.items():
        if ident in ids:
            raise NeedsHuman(reason)
    if "app" in ids and not ids & set(SEARCH_IDS):  # an empty shell that a script would fill in
        raise NeedsHuman("js_required")


def _login(driver: HttpDriver, user: str, password: str) -> tuple[bool, str]:
    page = driver.get("/login")
    _check(page)
    page.require("login", LOGIN_IDS)
    after = driver.post("/login", {"username": user, "password": password})
    if after.status == 429:
        return False, "rate_limited"
    _check(after)  # before the 401/403 test: a locked account answers 403 and must not be retried
    if after.status in (401, 403) or "login-error" in after.ids():
        return False, "login_failed"
    after.require("claim search", SEARCH_IDS)
    return True, ""


class _Session:
    def __init__(self, driver: HttpDriver, user: str, password: str):
        self.driver, self.user, self.password, self.relogins = driver, user, password, 0

    def fetch(self, path: str, params: dict | None = None):  # noqa: ANN201
        """GET a page. A bounce to sign in gets one fresh login for that page; a bounce right after it, or more than
        MAX_RELOGINS in a run, is handed to a person."""
        page = self.driver.get(path, params)
        if page.status == 429:
            return page
        if {"username", "login-submit"} <= page.ids():
            if self.relogins >= MAX_RELOGINS:  # a cap, so a portal that keeps dropping us cannot lock the account
                raise NeedsHuman("session_expired")
            self.relogins += 1
            ok, _ = _login(self.driver, self.user, self.password)
            if not ok:
                raise NeedsHuman("session_expired")
            page = self.driver.get(path, params)
            if page.status == 429:
                return page
            if {"username", "login-submit"} <= page.ids():  # a fresh login was bounced straight away
                raise NeedsHuman("session_expired")
        _check(page)
        return page


def claim_status_bot(driver: HttpDriver, user: str, password: str, claim_ids: list[str], evidence_dir: Path,
                     log_path: Path | None = None, read_records_request: bool = True) -> list[PortalResult]:  # fmt: skip
    results: list[PortalResult] = []
    evidence_dir.mkdir(parents=True, exist_ok=True)

    def record(r: PortalResult) -> None:
        results.append(r)
        if log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"bot": "portal_status", **asdict(r)}, sort_keys=True) + "\n")

    try:
        ok, why = _login(driver, user, password)
    except NeedsHuman as e:
        for c in claim_ids:
            record(PortalResult(c, "needs_human" if c == claim_ids[0] else "not_attempted",
                                detail=f"needs a person: {e.reason}", handoff=e.reason if c == claim_ids[0] else ""))  # fmt: skip
        return results
    except ScreenChanged as e:
        for c in claim_ids:
            record(PortalResult(c, "not_attempted" if c != claim_ids[0] else "screen_changed", detail=str(e)))
        return results
    if not ok:
        for c in claim_ids:
            record(PortalResult(c, why if c == claim_ids[0] else "not_attempted", detail="stopped at sign in"))
        return results

    session = _Session(driver, user, password)
    stopped = ""
    for claim in claim_ids:
        if stopped:
            record(PortalResult(claim, "not_attempted", detail=stopped))
            continue
        try:
            found = session.fetch("/claims", {"claim_id": claim})
            if found.status == 429:
                stopped = "portal rate limit reached; stopped"
                record(PortalResult(claim, "rate_limited", detail=stopped))
                continue
            found.require("claim search", SEARCH_IDS)
            link = found.link(f"open-{claim}")
            if not link:
                record(PortalResult(claim, "not_found", detail="no row for this claim"))
                continue
            page = session.fetch(link)
            if page.status == 404:
                record(PortalResult(claim, "not_found", detail="detail page says not found"))
                continue
            page.require("claim detail", DETAIL_IDS)
            ev = evidence_dir / f"{_safe(claim)}_detail.html"
            ev.write_text(page.html, encoding="utf-8", newline="")
            res = PortalResult(claim, "read", page.text("claim-status"), page.text("pend-reason"),
                               page.text("paid-amount"), None, [ev.name])  # fmt: skip
            if read_records_request and "records" in res.reason.lower():
                rec = session.fetch(page.link("records-request"))
                rec.require("records request", RECORDS_IDS)
                ev2 = evidence_dir / f"{_safe(claim)}_records_request.html"
                ev2.write_text(rec.html, encoding="utf-8", newline="")
                res.records_requested = rec.text("request-open").lower() == "yes"
                res.evidence.append(ev2.name)
            record(res)
        except NeedsHuman as e:
            stopped = f"stopped: needs a person ({e.reason})"
            record(PortalResult(claim, "needs_human", detail=f"needs a person: {e.reason}", handoff=e.reason))
        except ScreenChanged as e:
            stopped = f"stopped: {e}"
            record(PortalResult(claim, "screen_changed", detail=str(e)))
    return results
