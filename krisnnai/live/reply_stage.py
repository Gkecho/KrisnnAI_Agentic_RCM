# ruff: noqa: E501
"""S8: the stream stages that come AFTER a claim is adjudicated (cfg.replies), as a mixin so `stream.py` changes stay small.

reply_pending -> replied -> (adjudicated again | settled | patient_balance | review)

Every step saves state before the next one (`_advance`), every file written has a fixed name and fixed content and every event has
a fixed key, so a run killed at any point repeats no reply and loses no claim. See `responder.py` for the decisions themselves.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal

from krisnnai.ingest.x12 import read_transactions
from krisnnai.live.payer_replies import ReplyAnswer, ReplySim, truth_csv, truth_row
from krisnnai.live.responder import SEND_DELAY, Plan, ReplyPolicy, Responder, read_remit
from krisnnai.synthea import x12out

LABEL = {"corrected_claim": "corrected claim", "appeal": "appeal", "dispute": "dispute", "records": "records"}


class RepliesMixin:
    # ---- helpers
    def _init_replies(self) -> None:
        self.reply_policy = ReplyPolicy(per_day=dict(self.state.get("reply_per_day", {})))
        self.responder: Responder | None = None  # tests may set a Responder with another book

    def _resp(self, e: dict) -> Responder:
        return self.responder or Responder(self.payer_for(e).book)

    def _sent_text(self, e: dict) -> str:
        return (self.out / "claims" / e.get("file", f"{e['claim']}.837")).read_text("utf-8")

    def _reply_ctx(self, e: dict, notified: date | None = None) -> dict:
        from krisnnai.ingest import p837

        rec = p837.parse(read_transactions(self._sent_text(e))[0], "live")[0]
        lines = [(ln.cpt, int(ln.units), Decimal(str(ln.charge))) for ln in rec.lines]
        return {"claim_id": e["claim"], "payer_id": e.get("payer_id", ""), "member": e["member"], "dos": rec.service_date.isoformat(), "cpt": lines[0][0], "cpts": [x[0] for x in lines],
                "lines": lines, "active_271": e.get("active"), "notified": notified.isoformat() if notified else e.get("remit_date")}  # fmt: skip

    def _find(self, name: str) -> str | None:
        for d in ("inbox", "archive"):
            for p in sorted((self.out / d).rglob(name)):
                return p.read_text("utf-8")
        return None

    def _pcn(self, e: dict) -> str:
        """The payer claim number from the first remit, when there was one (it goes into REF*F8 on a replacement claim)."""
        t = self._find(f"835_{e['claim']}.835")
        v = read_remit(t, e["claim"]) if t else None
        return v.payer_claim_no if v and v.payer_claim_no else ""

    def _rev(self, e: dict, day: date, key: str, step: str, outcome: str, detail: str, plan: dict | None = None, who: str = "") -> None:
        new = key not in self.seen_events
        self._event(key, day, step, "Reply bot", "responder", e.get("claim") or "", outcome, detail)
        if new:
            row = {"agent_id": "s8_responder", "agent_version": "1", "tenant_id": 1, "mode": "demo-live", "event_key": key, "day": day.isoformat(), "claim": e.get("claim"),
                   "action_type": (plan or {}).get("kind", step), "action_payload": plan, "rules_fired": [(plan or {}).get("finding"), (plan or {}).get("deadline")],
                   "autonomy": "L3 named simulated approval" if (who or "").startswith("person:") else ("L4 demo capped policy" if who else "L2 prepared for a person"),
                   "approver": who or None, "result": outcome, "detail": detail}  # fmt: skip
            with (self.out / "decision_records.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, default=str) + "\n")

    def _bump(self) -> int:
        self.state["ctrl835"] += 1
        return self.state["ctrl835"]

    def _reject_kind(self, claim_id: str) -> str:
        """Which data-entry error (if any) this claim is sent with: seeded on (seed, claim id), so a restart chooses the same."""
        if self.cfg.reject_rate <= 0:
            return ""
        h = int(hashlib.sha256(f"{self.cfg.seed}:reject:{claim_id}".encode()).hexdigest(), 16)
        if (h % 10_000) >= int(self.cfg.reject_rate * 10_000):
            return ""
        return ("payer_id", "diagnosis")[(h // 10_000) % 2]

    # ---- the tick
    def _replies_tick(self, day: date, client) -> None:  # noqa: ANN001
        if not self.cfg.replies:
            return
        for eid in sorted(self.state["enc"]):
            e = self.state["enc"][eid]
            if e["stage"] == "rejected" and e.get("reject_reason") and not e.get("rounds"):
                plan = self._resp(e).plan_after_rejection(self._reply_ctx(e), e["reject_reason"], day, 1)
                self._take_plan(eid, e, day, plan)
            if e["stage"] == "adjudicated":
                self._r_adjudicated(eid, e, day)
            if e["stage"] == "reply_pending":
                self._r_send(eid, e, day, client)
            if e["stage"] == "replied" and day >= date.fromisoformat(e["rounds"][-1]["answer_on"]):
                self._r_answer(eid, e, day)

    def _r_adjudicated(self, eid: str, e: dict, day: date) -> None:
        cid = e["claim"]
        if cid in self.state["issued"]:
            text = self._find(f"835_{cid}.835")
            view = read_remit(text, cid) if text else None
            if view is None:
                return
            e.setdefault("remits", {})[cid] = {"paid": str(view.paid), "pr": str(view.patient_resp)}
            ctx = self._reply_ctx(e, date.fromisoformat(e["remit_date"]))
            plan = self._resp(e).plan_after_remit(ctx, view, day, len(e.get("rounds", [])) + 1, e.get("rounds", []), self.payer_for(e).fees)
            self._take_plan(eid, e, day, plan)
        elif not e.get("records_sent") and (day - date.fromisoformat(e["billed_on"])).days >= 2 and self.payer_for(e).status(cid, day)[5]:
            plan = self._resp(e).plan_records(self._reply_ctx(e), day, len(e.get("rounds", [])) + 1)
            self._take_plan(eid, e, day, plan)

    def _take_plan(self, eid: str, e: dict, day: date, plan: Plan) -> None:
        n = plan.round
        d = plan.to_dict()
        if plan.finding:
            f = plan.finding
            self._rev(e, day, f"{eid}:r{n}:recog", "8 reply: recognized", "contradiction",
                      f"the payer contradicted its own published rule or answer: {f['ground']} ({f['rule_id']} v{f['version']}); appealing on that ground", d)  # fmt: skip
        if plan.kind == "settled":
            pr = sum((Decimal(r["pr"]) for r in e.get("remits", {}).values()), Decimal(0))
            if pr > 0:
                e["patient_balance"] = str(pr)
                self._rev(e, day, f"{eid}:r{n}:final", "8 reply: patient balance", "patient_balance", f"paid by the payer; patient responsibility {pr} stays as a patient balance (a remit is not cash)", d)
                self._advance(e, "patient_balance")
            else:
                self._rev(e, day, f"{eid}:r{n}:final", "8 reply: settled", "settled", "paid; nothing left to ask the payer for (a remit is not cash)", d)
                self._advance(e, "settled")
            return
        if plan.kind == "review":
            e["review"] = {"reason": plan.reason, "owner": plan.owner, "carc": plan.carc, "round": n}
            self._rev(e, day, f"{eid}:r{n}:review", "8 reply: review", "needs a person", f"{plan.reason}; owner {plan.owner or 'billing'}; nothing sent and nothing written off", d)
            self._advance(e, "review")
            return
        delay = 0 if plan.trigger == "rejection" else SEND_DELAY[plan.kind]
        d["send_on"] = (day + timedelta(days=delay)).isoformat()
        e["next"] = d
        self._rev(e, day, f"{eid}:r{n}:plan", "8 reply: plan", plan.kind, f"{plan.reason}; approval {plan.approval}; to be sent {d['send_on']}", d, plan.approval)
        self._advance(e, "reply_pending")

    def _r_send(self, eid: str, e: dict, day: date, client) -> None:  # noqa: ANN001
        nx = e["next"]
        n, kind = nx["round"], nx["kind"]
        if day < date.fromisoformat(nx["send_on"]):
            return
        resp = self._resp(e)
        ctx = self._reply_ctx(e, date.fromisoformat(e["remit_date"]) if e.get("remit_date") else None)
        if kind in ("corrected_claim", "appeal"):  # the deadline is checked again on the day it would go out
            dl, why = resp.check_deadline(kind, {**ctx, "notified": ctx.get("notified") or day.isoformat()}, day)
            if why:
                e.pop("next", None)
                self._take_plan(eid, e, day, resp.review_plan(n, why, nx.get("carc", ""), None, dl))
                return
        if not self.reply_policy.can_send(day):
            self._rev(e, day, f"{eid}:r{n}:cap", "8 reply: deferred", "daily cap", f"the daily cap of {self.reply_policy.daily_cap} replies is reached; {kind} waits for the next day", nx, nx["approval"])
            return
        payer = self.payer_for(e)
        sim = ReplySim(self.cfg.seed, payer.fees)
        (self.out / "replies").mkdir(exist_ok=True)
        cid = e["claim"]
        plan = Plan(**nx)
        if kind == "corrected_claim":
            note = "" if plan.trigger == "rejection" else ("INSURANCE DETAILS UPDATED (SIMULATED RE-VERIFICATION)" if plan.evidence.get("fields") == "insurance details" else "ADDITIONAL INFORMATION ADDED (SIMULATED)")
            dx = [e["coding"]["dx"][0][0].replace(".", "")]
            text = Responder.corrected_837(self._sent_text(e), payer_claim_no=self._pcn(e), note=note, payer_id=e.get("payer_id", ""), dx_codes=dx)
            fname = f"{cid}.c{n}.837"
            self._write(fname, text, "claims")
            self._write(f"837_{cid}.c{n}.837", text)
            got = client.submit_claim(text)
            self._write(f"999_{cid}_c{n}.999", got["999"])
            self._write(f"277CA_{cid}_c{n}.277ca", got["277CA"])
            bad = [r for r in got["results"] if not r["ok"]]
            e.pop("next", None)
            e["file"] = fname
            if bad:
                self._take_plan(eid, e, day, resp.review_plan(n, f"the corrected claim was rejected again by the clearinghouse: {bad[0]['reason']}", nx.get("carc", "")))
                return
            self.reply_policy.took(day)
            self._rev(e, day, f"{eid}:r{n}:send", "8 reply: corrected claim", "sent", f"replacement 837 (CLM05-3 = 7) through the mock clearinghouse; codes unchanged; {plan.reason}; approval {plan.approval}; deadline {plan.deadline and plan.deadline['rule']}", nx, plan.approval)  # fmt: skip
            if plan.trigger == "rejection":
                self.world.release(cid)
                c = [x for x in self.world.accepted if x.claim_id == cid][-1]
                d = payer.adjudicate(c, day)
                e["remit_date"], e["adjudicated_on"] = d.remit_date.isoformat(), day.isoformat()
                self._event(f"{eid}:payer", day, "6 payer", "Payer sim", "mock", cid, "received", f"corrected claim received; remit expected {d.remit_date}")
                e.setdefault("rounds", []).append({"round": n, "plan": nx, "sent_on": day.isoformat(), "answer_on": day.isoformat(), "answer": None, "answered": True})
                self._advance(e, "adjudicated")
                return
            ans = sim.answer(payer.cases[cid], kind, n, carc=plan.carc, info_fixed=True)
        else:
            d0 = payer.cases[cid]
            if kind == "appeal":
                packet = {"claim": cid, "carc": plan.carc, "ground": plan.finding, "deadline": plan.deadline, "attachments": plan.evidence.get("attachments"), "approval": plan.approval, "sent_on": day.isoformat()}
                (self.out / "replies" / f"{cid}_r{n}_appeal.json").write_text(json.dumps(packet, indent=1, sort_keys=True), encoding="utf-8")
                (self.out / "replies" / f"{cid}_r{n}_appeal.txt").write_text(Responder.appeal_letter(ctx, plan), encoding="utf-8")
            elif kind == "dispute":
                (self.out / "replies" / f"{cid}_r{n}_dispute.txt").write_text(Responder.dispute_letter(ctx, plan), encoding="utf-8")
            else:
                (self.out / "replies" / f"{cid}_r{n}_records.json").write_text(json.dumps({"claim": cid, "attachments": plan.evidence.get("attachments"), "approval": plan.approval}, indent=1), encoding="utf-8")
            self.reply_policy.took(day)
            ans = sim.answer(d0, kind, n, carc=plan.carc, cites_rule=plan.finding is not None, fee_evidence=kind == "dispute",
                             shortfall_allowed=Decimal(plan.evidence.get("shortfall_allowed", "0")))  # fmt: skip
            why = (plan.finding or {}).get("ground") or (f"deadline {plan.deadline['rule']}" if plan.deadline else "") or "; ".join(plan.evidence.get("attachments", []))
            self._rev(e, day, f"{eid}:r{n}:send", f"8 reply: {LABEL[kind]}", "sent", f"{plan.reason}; handed to the payer simulator (simulated, not a real payer); approval {plan.approval}; evidence: {why}", nx, plan.approval)
            e.pop("next", None)
        e.setdefault("rounds", []).append({"round": n, "plan": nx, "sent_on": day.isoformat(), "answer_on": (day + timedelta(days=ans.answer_days)).isoformat(), "answer": ans.to_dict(), "answered": False})
        self._advance(e, "replied")

    def _r_answer(self, eid: str, e: dict, day: date) -> None:
        rnd = e["rounds"][-1]
        ans = ReplyAnswer(**rnd["answer"])
        n, cid = ans.round, e["claim"]
        payer = self.payer_for(e)
        d0 = payer.cases[cid]
        sim = ReplySim(self.cfg.seed, payer.fees)
        if ans.kind == "records":
            c = d0.claim
            self._write(f"277CA_{cid}_records.277ca", x12out.write_277ca(c.payer, [c], self._bump(), day))
            rnd["answered"], e["records_sent"] = True, True
            self._rev(e, day, f"{eid}:r{n}:answer", "8 reply: answer", ans.outcome, f"{ans.reason} (277CA acknowledgement; payment date unchanged)", rnd["plan"])
            self._advance(e, "adjudicated")
            return
        text = x12out.write_835(d0.claim.payer, day, [sim.remit_claim(d0, ans)], self._bump())
        self._write(f"835_{ans.reply_id}.835", text)
        rnd["answered"] = True
        view = read_remit(text, ans.reply_id)
        assert view is not None
        e.setdefault("remits", {})[ans.reply_id] = {"paid": str(view.paid), "pr": str(view.patient_resp)}
        self._rev(e, day, f"{eid}:r{n}:answer", "8 reply: answer", ans.outcome, f"{ans.reason}; second remit {ans.reply_id}: paid {view.paid} (a remit is not cash)", rnd["plan"])
        resp = self._resp(e)
        if ans.kind == "dispute":
            plan = Plan("settled", n + 1, "dispute accepted in full", "") if ans.outcome == "accepted_full" else resp.review_plan(n + 1, f"underpayment dispute {ans.outcome.replace('_', ' ')}: the rest of the shortfall needs a person", "45")
        else:
            plan = resp.plan_after_remit(self._reply_ctx(e, day), view, day, n + 1, e["rounds"], payer.fees, check_underpay=False)
        self._take_plan(eid, e, day, plan)

    # ---- the end of the run
    def _reply_rows(self) -> list[dict]:
        rows = []
        for e in self.state["enc"].values():
            for r in e.get("rounds", []):
                if r.get("answered") and r.get("answer") and r["answer"]["kind"] != "records":
                    rows.append(truth_row(r["answer"], r["sent_on"], r["answer_on"], r["plan"]["approval"]))
        return rows

    def _replies_finish(self) -> dict:
        (self.out / "truth_replies.csv").write_text(truth_csv(self._reply_rows()), encoding="utf-8")
        review = [{"encounter": k, "claim": e.get("claim"), **e["review"]} for k, e in sorted(self.state["enc"].items()) if e["stage"] == "review"]
        (self.out / "review_queue.jsonl").write_text("".join(json.dumps(p) + "\n" for p in review), encoding="utf-8")
        sent: dict[str, int] = {}
        outcomes: dict[str, int] = {}
        for e in self.state["enc"].values():
            for r in e.get("rounds", []):
                sent[r["plan"]["kind"]] = sent.get(r["plan"]["kind"], 0) + 1
                if r.get("answer"):
                    k = r["answer"]["kind"] + ":" + r["answer"]["outcome"]
                    outcomes[k] = outcomes.get(k, 0) + 1
        billed = [e for e in self.state["enc"].values() if e.get("billed_on")]
        done = [e for e in billed if e["stage"] in ("settled", "patient_balance")]
        return {"sent": sent, "answers": outcomes, "settled": len(done), "in_review": len(review), "claims": len(billed), "daily_cap": self.reply_policy.daily_cap}
