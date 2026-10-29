"""Stage 1 runner: build a book, bring it to a chosen day, let the bots act against the mock services, show what changed.

    book (Synthea) -> database at day D -> mock clearinghouse + mock portal on localhost -> bots
       eligibility bot (A1's flagged appointments)   270 -> 271      files into the inbox
       status bot (A7's open claims)                  276 -> 277      files into the inbox
       resubmission bot (A6's returned claims)        replacement 837 -> 999 + 277CA
       portal bot (the same open claims)              login -> search -> read status, reason, evidence
    -> the same agents two days later, with and without the bot's files (a control database)
    -> optional: the same feeds through a FHIR server

Everything is local and mock. The report says so on its first line.
"""

from __future__ import annotations

import json
import shutil
import socket
import threading
import time
from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
from pathlib import Path

import httpx
import uvicorn
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.integrations.clearinghouse.bots import (
    BotReport,
    eligibility_bot,
    latest_decisions,
    resubmission_bot,
    status_bot,
)
from krisnnai.integrations.clearinghouse.claim_store import PmExtract, load_extract
from krisnnai.integrations.clearinghouse.client import ClearinghouseClient
from krisnnai.integrations.clearinghouse.mock_server import create_app as create_clearinghouse
from krisnnai.integrations.clearinghouse.mock_world import MockWorld
from krisnnai.integrations.clearinghouse.scenario import pick_bot_day
from krisnnai.integrations.portal.bots import claim_status_bot
from krisnnai.integrations.portal.driver import HttpDriver
from krisnnai.integrations.portal.mock_portal import create_app as create_portal
from krisnnai.model import Base
from krisnnai.ops import run_period
from krisnnai.synthea import build

SALT = "stage1-salt"
CH_TOKEN = "stage1-local-token"  # a throwaway value for a service that only listens on 127.0.0.1
PORTAL_USER, PORTAL_PASSWORD = "stage1-bot", "stage1-local-only"


class _Server:
    def __init__(self, app, port: int):
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.url = f"http://127.0.0.1:{port}"

    def __enter__(self):
        self.thread.start()
        for _ in range(100):
            if self.server.started:
                return self
            time.sleep(0.1)
        raise RuntimeError("local mock server did not start")

    def __exit__(self, *exc):
        self.server.should_exit = True
        self.thread.join(timeout=10)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _engine(path: Path):
    eng = create_engine(f"sqlite:///{path}")

    @event.listens_for(eng, "connect")
    def _fk(conn, _rec):  # noqa: ANN001
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(m.Tenant(name="stage1", patient_salt_key="STAGE1_SALT"))
        s.commit()
    return eng


@dataclass
class Stage1Result:
    root: Path
    day: date
    report: Path
    summary: dict


def _a1_gaps(engine, appts: list[str]) -> dict[str, set[str]]:
    latest = latest_decisions(engine, 1, "a1_clearance", "appt")
    return {a: {g["kind"] for g in latest.get(a, ("", {}))[1].get("gaps", [])} for a in appts}


def run_stage1(out_dir: Path, synthea_dir: Path, as_of: date, seed: int = 7, with_fhir: bool = False,
               limit: int = 25, log=print) -> Stage1Result:  # fmt: skip
    if not synthea_dir.exists():
        raise SystemExit(f"{synthea_dir} does not exist; generate Synthea output first (krisnnai synthea run --yes)")
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True)
    book = out_dir / "book"
    log("1/6 building the book ...")
    build(synthea_dir, book, as_of, seed=seed, documentation=True, eligibility=True)
    extract: PmExtract = load_extract(book)
    day, planted = pick_bot_day(extract, book)
    log(f"    bot day {day}: {len(planted)} appointments with a planted check defect and a visit on {day + timedelta(days=3)}")

    log("2/6 bringing the database to the bot day (all fifteen agents, shadow mode) ...")
    base_db = out_dir / "base.sqlite"
    eng = _engine(base_db)
    inbox = out_dir / "inbox_base"
    shutil.copytree(book, inbox, ignore=shutil.ignore_patterns("*truth*"))
    rep = run_period(eng, 1, SALT, day, inbox=inbox, archive=out_dir / "archive_base", mode="backfill",
                     start=day - timedelta(days=150), step_days=28)  # fmt: skip
    if rep.status != "ok":
        raise SystemExit("the base run did not finish ok: " + "; ".join(rep.reasons))
    eng.dispose()
    shutil.copy(base_db, out_dir / "bot.sqlite")  # the control continues from the same state
    bot_eng, ctl_eng = _engine_existing(out_dir / "bot.sqlite"), _engine_existing(base_db)

    check_gaps = {"no_eligibility_check", "stale_check"}
    # what A1 flagged on the bot day for visits exactly three days out: these reach their 24 h checkpoint inside the
    # follow-up run, so they are the appointments where the bot's answer can be seen to matter
    visit_day = (day + timedelta(days=3)).isoformat()
    flagged_gaps = _a1_gaps(eng2 := _engine_existing(out_dir / "bot.sqlite"), sorted(extract.appointments))
    eng2.dispose()
    targets = sorted(a for a, kinds in flagged_gaps.items()
                     if kinds & check_gaps and extract.appointments[a]["appt_date"] == visit_day)  # fmt: skip

    log("3/6 running the bots against the mock clearinghouse and the mock portal ...")
    world = MockWorld(extract, truth_dir=book, today=day)
    ch_app = create_clearinghouse(world, token=CH_TOKEN, today=day)
    portal_app = create_portal(world, PORTAL_USER, PORTAL_PASSWORD)
    bot_out, log_path = out_dir / "bot_out", out_dir / "bot_log.jsonl"
    reports: dict[str, BotReport] = {}
    with _Server(ch_app, _free_port()) as ch, _Server(portal_app, _free_port()) as portal:
        client = ClearinghouseClient(ch.url, CH_TOKEN)
        client.health()
        reports["eligibility"] = eligibility_bot(bot_eng, 1, extract, client, bot_out, day, limit, log_path)
        reports["status"] = status_bot(bot_eng, 1, extract, client, bot_out, day, limit, log_path)
        reports["resubmission"] = resubmission_bot(bot_eng, 1, extract, client, bot_out, day, limit, log_path)
        client.close()
        open_claims = sorted(latest_decisions(bot_eng, 1, "a7_ar", "claim"))[:limit]
        driver = HttpDriver(portal.url)
        portal_results = claim_status_bot(driver, PORTAL_USER, PORTAL_PASSWORD, open_claims,
                                          out_dir / "evidence", log_path)  # fmt: skip
        driver.close()
        # the same bot against a redesigned portal: it must stop at the first page it does not understand
        redesigned = _Server(create_portal(world, PORTAL_USER, PORTAL_PASSWORD, layout=2), _free_port())
        with redesigned as rd:
            d2 = HttpDriver(rd.url)
            changed = claim_status_bot(d2, PORTAL_USER, PORTAL_PASSWORD, open_claims[:5], out_dir / "evidence_changed")
            changed_requests = d2.requests
            d2.close()

    log("4/6 the agents two days later, with the bot's files and without (control) ...")
    after = day + timedelta(days=2)
    run_period(bot_eng, 1, SALT, after, inbox=bot_out, archive=out_dir / "archive_bot", mode="daily",
               allow_failed=True)  # fmt: skip
    run_period(ctl_eng, 1, SALT, after, mode="daily")
    answered = {e.subject for e in reports["eligibility"].events if e.outcome != "skipped"}
    checked = sorted(set(targets) & answered)
    bot_gaps, ctl_gaps = _a1_gaps(bot_eng, checked), _a1_gaps(ctl_eng, checked)
    summary = {
        "day": day.isoformat(), "planted_appointments": len(planted), "flagged_for_visit_in_3_days": len(targets),
        "checked": len(checked),
        "control_still_missing": sum(1 for a in checked if ctl_gaps[a] & check_gaps),
        "bot_still_missing": sum(1 for a in checked if bot_gaps[a] & check_gaps),
        "bots": {k: v.counts() for k, v in reports.items()},
        "portal": {r.outcome: sum(1 for x in portal_results if x.outcome == r.outcome) for r in portal_results},
        "portal_changed": [r.outcome for r in changed], "portal_changed_requests": changed_requests,
        "fhir": None,
    }  # fmt: skip

    if with_fhir:
        log("5/6 FHIR: starting the local server (first start pulls about 2 GB of images) ...")
        summary["fhir"] = _fhir_round_trip(book, out_dir)
    else:
        log("5/6 FHIR skipped (run with --with-fhir; needs Docker and the images)")

    log("6/6 writing the report ...")
    path = _write_report(out_dir, summary, reports, portal_results, changed, extract, bot_out)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    for e in (bot_eng, ctl_eng):
        e.dispose()
    return Stage1Result(out_dir, day, path, summary)


def _engine_existing(path: Path):
    eng = create_engine(f"sqlite:///{path}")

    @event.listens_for(eng, "connect")
    def _fk(conn, _rec):  # noqa: ANN001
        conn.execute("PRAGMA foreign_keys=ON")

    return eng


def _fhir_round_trip(book: Path, out_dir: Path) -> dict:
    from krisnnai.integrations.fhir import docker
    from krisnnai.integrations.fhir.client import FhirClient
    from krisnnai.integrations.fhir.sync import pull, seed

    url = docker.up(out_dir / "fhir")
    client = FhirClient(url)
    seeded = seed(client, book)
    pulled = pull(client, out_dir / "fhir_pull")
    import csv

    def count(p: Path) -> int:
        with p.open(encoding="utf-8") as f:
            return max(sum(1 for _ in csv.reader(f)) - 1, 0)

    src = {k: count(book / f"{k}.csv") for k in ("appointments", "visits", "notes")}
    client.close()
    return {"server": url, "seeded": seeded, "pulled": pulled, "source_rows": src, "equal": pulled == src}


# ---------------------------------------------------------------------------------------------------- report


def _table(head: list[str], rows: list[list]) -> str:
    th = "".join(f"<th>{escape(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{th}</tr>{body}</table>"


def _sample(path: Path, n: int = 12) -> str:
    if not path.exists():
        return ""
    segs = path.read_text(encoding="ascii", errors="ignore").replace("\n", "").split("~")
    return escape("~\n".join(segs[:n]) + "~ ...")


def _write_report(out_dir, summary, reports, portal_results, changed, extract, bot_out) -> Path:
    s = summary
    parts = [
        "<h1>KrisnnAI Stage 1: integrations running against local mock services</h1>",
        '<div class="banner"><b>Mock endpoints, not a real payer or EMR.</b> Everything below ran on this PC against '
        "services written for the test. It shows the bots can do the work end to end; it does not show how a real "
        "clearinghouse, payer or portal behaves.</div>",
        f"<p>Bot day {s['day']} (a historical book; visits are three days after it).</p>",
        "<h2>1. Eligibility bot (270 to 271)</h2>",
        f"<p>On the bot day A1 flagged {s['flagged_for_visit_in_3_days']} appointments (visit in three days) as "
        f"having no or a stale eligibility check. The bot checked {s['checked']} of them. Two days later, at A1's 24 h "
        f"checkpoint, the check gap was still open on <b>{s['control_still_missing']}</b> without the bot and on "
        f"<b>{s['bot_still_missing']}</b> with it.</p>",
        _table(["outcome", "count"], sorted(s["bots"]["eligibility"].items())),
    ]
    sample = next(iter(sorted(bot_out.glob("271_*.x12"))), None)
    if sample:
        parts += [f"<h3>Example 271 returned ({sample.name})</h3><pre>{_sample(sample)}</pre>"]
    parts += [
        "<h2>2. Claim status bot (276 to 277)</h2>",
        _table(["status read", "count"], sorted(s["bots"]["status"].items())),
        "<h2>3. Resubmission bot (replacement 837 to 999 and 277CA)</h2>",
        _table(["outcome", "count"], sorted(s["bots"]["resubmission"].items())) if s["bots"]["resubmission"]
        else "<p>No claim was in a returned state at the bot day.</p>",
        "<p class=\"mut\">The mock accepts any replacement of a claim it returned: this shows the transport and the "
        "loop, not whether a correction is right.</p>",
        "<h2>4. Portal bot</h2>",
        _table(["claim", "outcome", "status", "reason", "paid", "records requested"],
               [[r.claim, r.outcome, r.status, r.reason, r.paid, "" if r.records_requested is None else r.records_requested]
                for r in portal_results]),  # fmt: skip
        f"<p>Against a redesigned portal the same bot stopped at the first page it did not recognise: "
        f"{escape(', '.join(s['portal_changed']))} after {s['portal_changed_requests']} requests, and touched nothing else.</p>",
        "<h2>5. FHIR</h2>",
    ]
    if s["fhir"]:
        f = s["fhir"]
        parts += [f"<p>Server {escape(f['server'])}. Seeded {f['seeded']}; pulled {f['pulled']}; source rows "
                  f"{f['source_rows']}. Round trip equal: <b>{f['equal']}</b>.</p>"]  # fmt: skip
    else:
        parts += ['<p class="mut">Not run in this pass (needs Docker and the FHIR server images).</p>']
    parts += [
        "<h2>What this does not show</h2><ul><li>Real authentication, real payer rules, real portal quirks, CAPTCHA or "
        "MFA (the bot would stop and hand over).</li><li>Whether the correction on a resubmitted claim is right.</li>"
        "<li>Any saving in staff time: that needs a measured baseline and a control group.</li></ul>",
    ]
    css = ("body{font:15px/1.5 system-ui,Segoe UI,sans-serif;margin:0 auto;max-width:1000px;padding:16px}"
           "table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #ddd;padding:4px 8px;text-align:left}"
           ".banner{background:#fff7e0;color:#8a5a00;padding:8px 12px;border-radius:6px}pre{background:#f4f4f4;"
           "padding:8px;overflow:auto}.mut{color:#666}")  # fmt: skip
    html = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' "
            "content='width=device-width,initial-scale=1'><title>KrisnnAI Stage 1</title>"
            f"<style>{css}</style></head><body>{''.join(parts)}</body></html>")  # fmt: skip
    path = out_dir / "stage1_report.html"
    path.write_text(html, encoding="utf-8", newline="\n")
    return path


def reachable(url: str) -> bool:
    try:
        return httpx.get(url, timeout=3).status_code < 500
    except httpx.HTTPError:
        return False
