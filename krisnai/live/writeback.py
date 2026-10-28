# ruff: noqa: E501
"""Write-back to the EMR: a note (a message in the EMR's inbox, assigned to the front desk) with the eligibility result.

Rules this adapter keeps (CLAUDE.md, rule 2):
  * It is OFF by default. Nothing is sent unless the adapter is switched on AND a named person has approved that one note.
  * It writes one kind of thing only: a message/task. It cannot write insurance, demographics or an appointment, and it has no
    method that tries to: OpenEMR's API has no appointment-status update either, so the front desk applies the status from the
    dashboard (a person), or a screen-automation bot would, once a client allows one.
  * A note is sent once. Proposals and sends are both logged with who approved and when.

The trigger only PROPOSES notes (shadow). `approve()` is the one place a send can happen. Demo data is synthetic.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

NOTE_KIND = "eligibility_note"
ALLOWED = {NOTE_KIND}  # nothing else can be written


class WriteBackError(Exception):
    """A write that is switched off, not approved, not allowed, or already done."""


def build_note(res: dict) -> dict:
    """The note text for one trigger result: what was checked, the answers in plain words, and what the front desk should do."""
    a, cl = res["appointment"], res["clearance"]
    when = "booking" if res["kind"] == "booking" else res["kind"].replace("recheck-", "re-check ")
    title = f"KrisnAI: eligibility {'cleared' if cl['cleared'] else 'needs attention'} for {a['pc_eventDate']} visit ({when})"
    lines = [
        f"Visit {a['pc_eventDate']} {a['pc_startTime']}. Checked as of {res['as_of']} ({when}). Source: payer 271 answers (simulated in the demo)."
    ]
    if not res["checks"]:
        lines.append("No insurance is on file for this patient, so no eligibility check was sent.")
    for c in res["checks"]:
        d = c["decoded"]
        if d["found"]:
            lines.append(
                f"- {c['order']} {c['payer']} member {c['member']}: {'ACTIVE' if d['active'] else 'NOT ACTIVE'}, copay {d['copay']}, coinsurance {d['coinsurance']}, deductible left {d['deductible_remaining']}, other payer: {d['other_payer'] or 'none'}"
            )
        else:
            lines.append(f"- {c['order']} {c['payer']} member {c['member']}: {d['why']}")
    if cl["cleared"]:
        lines.append(f"Result: cleared. Copay due at the visit: {cl['copay_due'] or 'not reported'}.")
    else:
        lines += [
            f"Needs attention: {g['detail']}" + (f" ({g['order']} {g['payer']})" if g["payer"] else "")
            for g in cl["gaps"]
        ]
        lines.append(f"Suggested task for the front desk: {cl['action']}.")
    au = res.get("prior_auth")
    if au:
        lines.append(f"Prior authorization ({au['cpt'] or 'no procedure on the booking'}, {au['payer']}): {au['outcome'].replace('_', ' ')}. {au['note']}. Suggestion: {au['suggestion']}.")
    lines.append(
        "KrisnAI note: it is sent to the EMR only after a named person approves it. No insurance or appointment data was changed."
    )
    return {
        "kind": NOTE_KIND,
        "event_id": res["event_id"],
        "run": res["kind"],
        "pid": a["pid"],
        "title": title[:250],
        "body": "\n".join(lines),
    }


class WriteBack:
    def __init__(self, server, work: Path, enabled: bool = False, assign_to: str = "admin"):  # noqa: ANN001
        self.server, self.work, self.enabled, self.assign_to = server, work, enabled, assign_to
        self.file = work / "writeback.json"  # {key: {"proposal":..., "state": proposed|sent, ...}}
        self.log_file = work / "writeback.jsonl"
        self.items: dict[str, dict] = json.loads(self.file.read_text(encoding="utf-8")) if self.file.exists() else {}

    @staticmethod
    def key(note: dict) -> str:
        return f"{note['event_id']}|{note['run']}"

    def _save(self, what: str, key: str, **extra) -> None:  # noqa: ANN003
        self.work.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self.items, indent=1), encoding="utf-8")
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "what": what, "key": key, **extra})
                + "\n"
            )

    def propose(self, res: dict) -> dict:
        """Record the note that would be written. Never sends. Proposing twice for the same event and run keeps the first."""
        note = build_note(res)
        key = self.key(note)
        if key not in self.items:
            self.items[key] = {"proposal": note, "state": "proposed", "mode": "shadow"}
            self._save("proposed", key)
        return {"key": key, "state": self.items[key]["state"], "title": note["title"]}

    def pending(self) -> dict[str, dict]:
        return {k: v for k, v in self.items.items() if v["state"] == "proposed"}

    def approve(self, key: str, approver: str, kind: str = NOTE_KIND) -> dict:
        """Send one proposed note. Needs the adapter switched on and the name of the person who approved it."""
        if kind not in ALLOWED:
            raise WriteBackError(f"{kind!r} cannot be written back: only notes and tasks are allowed")
        if not self.enabled:
            raise WriteBackError("write-back is switched off (it is off by default)")
        if not approver.strip():
            raise WriteBackError("a named approver is required")
        item = self.items.get(key)
        if item is None:
            raise WriteBackError(f"no proposal {key!r}")
        if item["state"] == "sent":
            raise WriteBackError(f"{key!r} was already sent")
        n = item["proposal"]
        body = {
            "body": n["body"],
            "to": self.assign_to,
            "from": "krisnai",
            "groupname": "Default",
            "title": n["title"],
            "message_status": "New",
        }
        out = self.server.rest_json("POST", f"/patient/{n['pid']}/message", json=body)
        item.update(
            state="sent",
            approver=approver.strip(),
            sent_at=datetime.now().isoformat(timespec="seconds"),
            emr_response=str(out)[:200],
        )
        self._save("sent", key, approver=approver.strip())
        return item
