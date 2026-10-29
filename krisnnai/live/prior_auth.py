# ruff: noqa: E501
"""Prior authorization mock (A2, Permit Clerk): does this visit need an authorization, and if so ask the payer (a mock one).

Steps, all plain code (CLAUDE.md rule 6), nothing sent to a real payer (rule 3):
  1. need()      read the Knowledge Book's `prior_auth` rule for this payer, CPT and visit date: required / not required / unknown.
                 No planned procedure, or no rule, is "unknown", never "not required".
  2. on file     an authorization number already carried by the source is taken as on file; no request is made.
  3. write_278   the request (X12 278, 005010X217 shape) to the mock payer; decode_278 reads the answer.
  4. mock payer  scripted, deterministic answers: certified (A1) with an authorization number, validity and units; pended (A4) when the
                 clinical documents are missing; not certified (A3) for a scripted denial; a rejection (AAA) when the member is unknown.
  5. close the loop: a certified answer is recorded in the payer sim (`grant_auth`), so a later claim for that service is not denied
                 with CARC 197. The same request twice gives the same authorization number (idempotent).
  6. suggest     what scheduling should do (keep, hold, or contact the patient). It is a suggestion; nothing is changed in the EMR.

ILLUSTRATIVE: segment positions in the 278 (UM, HCR, HSD, DTP, MSG) follow general knowledge of the standard and must be confirmed with the
clearinghouse's companion guide. Rules and answers are synthetic and are not any real payer's policy. Demo data is synthetic.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

from krisnnai.ingest.x12 import X12Error, read_transactions
from krisnnai.knowledge.demo import network_book
from krisnnai.synthea.x12out import BILLING_NPI, CLINIC, SENDER, _envelope, _seg

REQUIRED, NOT_REQUIRED, UNKNOWN = "required", "not_required", "unknown"
CERTIFIED, PENDED, NOT_CERTIFIED, REJECTED, ON_FILE = "certified", "pended", "not_certified", "rejected", "on_file"
HCR_ACTION = {"A1": CERTIFIED, "A4": PENDED, "A3": NOT_CERTIFIED}
SUGGESTION = {
    CERTIFIED: "keep the appointment: authorization is in place",
    ON_FILE: "keep the appointment: an authorization number is already on file (the window and units were not checked)",
    NOT_REQUIRED: "keep the appointment: no authorization needed",
    UNKNOWN: "front desk to confirm whether this service needs an authorization before the visit",
    PENDED: "hold: send the missing documents, then follow up with the payer before the visit",
    NOT_CERTIFIED: "contact the patient and the provider: authorization was not approved (appeal or reschedule is a person's decision)",
    REJECTED: "fix the request (member or service details) and send it again",
}
_book = None


def book():  # noqa: ANN201
    global _book  # noqa: PLW0603
    if _book is None:
        _book = network_book()
    return _book


def need(payer: str, cpt: str, visit: date, as_of: date) -> dict:
    """Required / not required / unknown, with the rule that decided it."""
    if not cpt:
        return {"status": UNKNOWN, "why": "no planned procedure (CPT) on this booking, so the rule cannot be applied"}
    found = book().lookup(payer, "prior_auth", cpt, {"service_date": visit}, as_of)
    if not found.ok:
        return {"status": UNKNOWN, "why": found.problem.message if found.problem else "no rule found"}
    content = found.rule.content
    return {
        "status": REQUIRED if content.get("required") else NOT_REQUIRED, "rule": found.rule.rule_id, "version": found.rule.version,
        "valid_days": content.get("valid_days"), "why": f"rule {found.rule.rule_id} v{found.rule.version}",
    }  # fmt: skip


# ------------------------------------------------------------------------------------------------------------ the 278 request
def write_278(payer_id: str, payer_name: str, member: str, last: str, first: str, dob: str, cpt: str, units: int, dx: str, dos: date,
              ref: str, ctrl: int, when: date) -> str:  # fmt: skip
    body = [
        _seg("BHT", "0007", "13", ref, when.strftime("%Y%m%d"), "1200"),
        _seg("HL", 1, "", "20", 1),
        _seg("NM1", "X3", "2", payer_name, "", "", "", "", "PI", payer_id),
        _seg("HL", 2, 1, "21", 1),
        _seg("NM1", "1P", "2", CLINIC, "", "", "", "", "XX", BILLING_NPI),
        _seg("HL", 3, 2, "22", 1),
        _seg("NM1", "IL", "1", last, first, "", "", "", "MI", member),
        _seg("DMG", "D8", dob or "19700101"),
        _seg("HL", 4, 3, "EV", 1),
        _seg("TRN", "1", ref, SENDER.ljust(10, "0")[:10]),
        _seg("UM", "HS", "I", "1"),  # health services review, initial request
        _seg("HI", f"ABK:{dx}") if dx else "",
        _seg("DTP", "472", "D8", dos.strftime("%Y%m%d")),
        _seg("HL", 5, 4, "SS", 0),
        _seg("SV1", f"HC:{cpt}", "", "UN", units),
    ]
    return _envelope("HI", "005010X217", "278", "005010X217", [s for s in body if s], ctrl, SENDER, payer_id, when)


def parse_278_request(text: str) -> dict:
    out = {"payer": "", "member": "", "ref": "", "cpt": "", "units": 1, "dx": "", "dos": None}
    for tx in read_transactions(text):
        if tx.st01 != "278":
            raise X12Error(f"expected a 278, got {tx.st01}")
        for s in tx.segments:
            if s.id == "NM1" and s[1] == "X3":
                out["payer"] = s[9]
            elif s.id == "NM1" and s[1] == "IL":
                out["member"] = s[9]
            elif s.id == "TRN":
                out["ref"] = s[2]
            elif s.id == "SV1":
                out["cpt"], out["units"] = s[1].split(":")[-1], int(s[4] or 1)
            elif s.id == "HI":
                out["dx"] = s[1].split(":")[-1]
            elif s.id == "DTP" and s[1] == "472":
                d = s[3]
                out["dos"] = date(int(d[:4]), int(d[4:6]), int(d[6:8]))
    return out


# ----------------------------------------------------------------------------------------------------- the mock payer's answer
def auth_number(payer: str, member: str, cpt: str, visit: date) -> str:
    """Stable for the same request: asking twice never creates a second authorization."""
    return "SYNAUTH" + hashlib.sha1(f"{payer}|{member}|{cpt}|{visit}".encode()).hexdigest()[:8].upper()


def write_278_response(req: dict, payer_name: str, action: str, units: int, ctrl: int, when: date, valid_days: int, note: str = "", bad_member: bool = False) -> str:
    body = [
        _seg("BHT", "0007", "11", f"SYN278R{ctrl}", when.strftime("%Y%m%d"), "1200"),
        _seg("HL", 1, "", "20", 1),
        _seg("NM1", "X3", "2", payer_name, "", "", "", "", "PI", req["payer"]),
        _seg("HL", 2, 1, "21", 1),
        _seg("NM1", "1P", "2", CLINIC, "", "", "", "", "XX", BILLING_NPI),
        _seg("HL", 3, 2, "22", 1),
        _seg("NM1", "IL", "1", "", "", "", "", "", "MI", req["member"]),
    ]
    if bad_member:
        body.append(_seg("AAA", "Y", "", "75", "C"))  # patient not found
    else:
        number = auth_number(req["payer"], req["member"], req["cpt"], req["dos"])
        body += [_seg("HL", 4, 3, "EV", 1), _seg("TRN", "2", req["ref"], SENDER.ljust(10, "0")[:10]), _seg("HCR", action, number)]
        if action in ("A1", "A6"):
            end = req["dos"] + timedelta(days=valid_days)
            body += [_seg("DTP", "472", "RD8", f"{req['dos']:%Y%m%d}-{end:%Y%m%d}"), _seg("HSD", "VS", units)]
        if note:
            body.append(_seg("MSG", note))
    return _envelope("HI", "005010X217", "278", "005010X217", body, ctrl, req["payer"], SENDER, when)


def decode_278(text: str) -> dict:
    """The answer in plain fields. An unknown action code is reported as such, for a person."""
    out = {"outcome": "", "action": "", "auth_number": "", "valid_from": "", "valid_to": "", "units": None, "message": "", "rejected": False}
    for tx in read_transactions(text):
        for s in tx.segments:
            if s.id == "AAA":
                out.update(outcome=REJECTED, rejected=True, message="the payer could not find this member (AAA 75)")
            elif s.id == "HCR":
                out["action"], out["auth_number"] = s[1], s[2]
                out["outcome"] = HCR_ACTION.get(s[1], "unknown_action")
                if out["outcome"] == "unknown_action":
                    out["message"] = f"unrecognised review action {s[1]}: a person must read the answer"
            elif s.id == "DTP" and s[1] == "472" and s[2] == "RD8":
                a, b = s[3].split("-")
                out["valid_from"], out["valid_to"] = f"{a[:4]}-{a[4:6]}-{a[6:]}", f"{b[:4]}-{b[4:6]}-{b[6:]}"
            elif s.id == "HSD":
                out["units"] = int(s[2])
            elif s.id == "MSG":
                out["message"] = s[1]
    if not out["outcome"]:
        raise X12Error("278 answer has neither an HCR review action nor an AAA rejection")
    return out


class MockAuthPayer:
    """Deterministic answers for the demo. `deny` = {(member, cpt): reason}; a member the payer sim does not know is rejected."""

    def __init__(self, deny: dict[tuple[str, str], str] | None = None):
        self.deny = deny or {}
        self._ctrl = 880000

    def answer(self, req_text: str, payer_name: str, known_member: bool, docs: bool, valid_days: int, when: date) -> str:
        req = parse_278_request(req_text)
        self._ctrl += 1
        if not known_member:
            return write_278_response(req, payer_name, "", 0, self._ctrl, when, valid_days, bad_member=True)
        reason = self.deny.get((req["member"], req["cpt"]))
        if reason:
            return write_278_response(req, payer_name, "A3", 0, self._ctrl, when, valid_days, note=reason)
        if not docs:
            return write_278_response(req, payer_name, "A4", 0, self._ctrl, when, valid_days, note="clinical notes and the order are needed before a decision")
        return write_278_response(req, payer_name, "A1", req["units"], self._ctrl, when, valid_days)
