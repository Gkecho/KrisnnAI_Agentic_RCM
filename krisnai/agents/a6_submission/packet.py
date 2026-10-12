"""The resubmission packet: the claim exactly as we hold it, ready for a person to review. It is not an X12 file.

A rejected claim never reached adjudication, so nothing here changes it: codes, modifiers, diagnoses, units, charges and
the frequency code are copied verbatim (rule 4). `edits` stays empty for a person to fill. Turning a packet into an 837
belongs with the real clearinghouse adapter; until then nothing is sent (rule 3).
"""

from __future__ import annotations

import krisnai.model as m


def _iso(d) -> str:
    return d.isoformat() if d else ""


def build_packet(
    claim: m.Claim,
    lines: list[m.ClaimLine],
    diagnoses: list[m.ClaimDx],
    payer_code: str,
    reason: dict,
    payer_claim_number: str | None = None,
) -> dict:
    return {
        "status": "draft_not_sent",
        "claim": claim.claim_submitter_id,
        "payer": payer_code,
        "total_charge": str(claim.total_charge),
        "place_of_service": claim.place_of_service or "",
        "frequency_code": claim.frequency_code,
        "service_date": _iso(claim.service_date),
        "payer_claim_number": payer_claim_number or claim.payer_claim_control_number or "",
        "diagnoses": [d.dx_code for d in sorted(diagnoses, key=lambda d: d.seq)],
        "lines": [
            {
                "line_number": ln.line_number,
                "cpt": ln.cpt,
                "modifiers": [x for x in (ln.modifier_1, ln.modifier_2, ln.modifier_3, ln.modifier_4) if x],
                "charge": str(ln.charge),
                "units": str(ln.units),
                "diagnosis_pointer": ln.diagnosis_pointer or "",
                "service_date": _iso(ln.service_date or claim.service_date),
            }
            for ln in sorted(lines, key=lambda ln: ln.line_number)
        ],
        "reason": reason,
        "edits": [],
    }


def unchanged(packet: dict, claim: m.Claim, lines: list[m.ClaimLine], diagnoses: list[m.ClaimDx]) -> bool:
    """True when the packet carries exactly the stored codes, modifiers, diagnoses, units, charges and frequency."""
    rebuilt = build_packet(claim, lines, diagnoses, packet["payer"], packet["reason"], packet["payer_claim_number"])
    return all(packet[k] == rebuilt[k] for k in ("frequency_code", "total_charge", "diagnoses", "lines"))
