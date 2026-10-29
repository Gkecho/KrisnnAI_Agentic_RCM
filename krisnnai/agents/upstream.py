"""Which upstream agents had already flagged a claim's work before the claim was billed.

Decision records of the front-end agents are matched to claims by the same keys the rest of the repo uses: the claim id
(A4, A5), the visit (A3), the appointment (A1, A2) through (payer, patient, date of service, CPT), and the rendering
provider and payer (A13) through the visit extract. A flag counts only when its decision was known on or before the
day the claim itself became known. Key matching, not proof of cause.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.engine import NO_ACTION
from krisnnai.model import tenant_session

UPSTREAM = {"a1_clearance": "A1", "a2_authorization": "A2", "a3_documentation": "A3", "a4_coding": "A4",
            "a5_prevention": "A5", "a13_credentialing": "A13"}  # fmt: skip


def upstream_flags(engine: Engine, tenant_id: int, as_of: date | None = None) -> dict[str, set[str]]:
    """claim submitter id -> the upstream agents that flagged it before it was billed (events known by `as_of`)."""
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at.date() for e in s.scalars(select(m.Event))
                 if as_of is None or e.known_at.date() <= as_of}  # fmt: skip
        payer_code = {p.id: p.payer_id_code for p in s.scalars(select(m.Payer))}
        npi = {p.id: p.npi for p in s.scalars(select(m.Provider))}
        claims: dict[tuple, list[tuple[str, date]]] = defaultdict(list)  # (payer, patient, dos) -> [(sid, known)]
        sids: dict[str, date] = {}
        lines: dict[int, set[str]] = defaultdict(set)
        for cid, cpt in s.execute(select(m.ClaimLine.claim_id, m.ClaimLine.cpt)):
            lines[cid].add(cpt)
        cpts_of: dict[str, set[str]] = {}
        for c in s.scalars(select(m.Claim)):
            when = known.get(c.event_id)
            if when is None:
                continue
            sids[c.claim_submitter_id] = when
            cpts_of[c.claim_submitter_id] = lines.get(c.id, set())
            claims[(c.payer_id, c.patient_ref_id, c.service_date)].append((c.claim_submitter_id, when))
        visit_key: dict[str, tuple] = {}
        by_provider: dict[tuple[str, str], list[tuple]] = defaultdict(list)
        for v in s.scalars(select(m.Visit)):
            key = (v.payer_id, v.patient_ref_id, v.service_date, v.cpt)
            visit_key[v.visit_ref] = key
            by_provider[(npi[v.provider_id], payer_code[v.payer_id])].append(key)
        appt_key = {
            a.appt_ref: (a.payer_id, a.patient_ref_id, a.appt_date, a.cpt) for a in s.scalars(select(m.Appointment))
        }

        flags: dict[str, dict[str, date]] = defaultdict(dict)

        def flag(agent: str, sid: str, when: date) -> None:
            if agent not in flags[sid] or when < flags[sid][agent]:
                flags[sid][agent] = when

        def flag_key(agent: str, key: tuple, when: date) -> None:
            payer_id, patient, dos, cpt = key
            for sid, _ in claims.get((payer_id, patient, dos), []):
                if cpt in cpts_of.get(sid, set()):
                    flag(agent, sid, when)

        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id.in_(UPSTREAM))):
            if rec.action_type == NO_ACTION or rec.event_id not in known:
                continue
            p, when, agent = json.loads(rec.action_payload), known[rec.event_id], UPSTREAM[rec.agent_id]
            if rec.agent_id in ("a5_prevention", "a4_coding"):
                if p.get("claim"):
                    flag(agent, p["claim"], when)
            elif rec.agent_id == "a3_documentation":
                if p.get("visit") in visit_key:
                    flag_key(agent, visit_key[p["visit"]], when)
            elif rec.agent_id in ("a1_clearance", "a2_authorization"):
                if p.get("appt") in appt_key:
                    flag_key(agent, appt_key[p["appt"]], when)
            elif rec.agent_id == "a13_credentialing" and "|" in p.get("key", ""):  # npi|payer (not a screening)
                npi_code, payer_code_ = p["key"].split("|", 1)
                for key in by_provider.get((npi_code, payer_code_), []):
                    flag_key(agent, key, when)
    return {
        sid: {a for a, when in by_agent.items() if when <= sids.get(sid, date.max)}
        for sid, by_agent in flags.items()
        if any(when <= sids.get(sid, date.max) for when in by_agent.values())
    }  # fmt: skip
