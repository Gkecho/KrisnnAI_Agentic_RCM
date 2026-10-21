# ruff: noqa: E501
"""Read a professional claim file (837P) and lay it out as the boxes of a CMS-1500 form, so a person can see the form and the EDI side by side.

The form is built FROM the EDI, never from internal state: what is shown is exactly what the claim file says. Each field also
records which EDI line it came from (`seg`, an index into `lines`), so a screen can highlight the matching line when a box is touched.
Demo labels only: names, ids and amounts are synthetic.
"""

from __future__ import annotations

from krisnai.ingest.x12 import read_transactions

NOTE = {  # what each kind of line is, in plain words
    "BHT": "Start of the claim message", "NM1*41": "Who is sending the claim (submitter)", "NM1*40": "Who receives it (the clearinghouse or payer)",
    "NM1*85": "Billing provider: the clinic (form box 33)", "N3": "Street address", "N4": "City, state, ZIP", "REF*EI": "Clinic's tax ID (form box 25)",
    "HL": "A level marker in the claim", "SBR": "How the insurance is held (the patient is the subscriber)", "NM1*IL": "The patient and member ID (boxes 1a and 2)",
    "DMG": "Birth date and sex (box 3)", "NM1*PR": "The insurer (the payer)", "CLM": "The claim: number, total charge, place of service (boxes 28 and 24B)",
    "HI": "The diagnoses (box 21)", "NM1*82": "Rendering provider who saw the patient (box 24J)", "PRV": "Provider's specialty code", "LX": "Service line number",
    "SV1": "A service line: code, modifier, charge, units, diagnosis pointer (box 24D to 24G)", "DTP": "Date of service (box 24A)", "PER": "Billing contact",
    "REF": "A reference number such as an authorization (box 23)",
}  # fmt: skip


def _comp(seg, i: int, j: int) -> str:  # noqa: ANN001
    parts = seg[i].split(seg.sub)
    return parts[j - 1] if j - 1 < len(parts) else ""


def _date(d: str) -> str:
    return f"{d[4:6]}/{d[6:8]}/{d[:4]}" if len(d) == 8 and d.isdigit() else d


def claim_form(x12: str) -> dict:
    """{'lines': [{'text','id','note'}], 'form': {...boxes with seg indexes...}} for the first claim in the file."""
    tx = read_transactions(x12)[0]
    segs = list(tx.segments)
    lines = []
    for s in segs:
        key = f"{s.id}*{s[1]}" if f"{s.id}*{s[1]}" in NOTE else s.id
        lines.append({"text": "*".join(s.els), "id": s.id, "note": NOTE.get(key, "")})
    form: dict = {"dx": [], "lines": [], "auth": None}

    sv_idx = -1
    ctx = ""  # which party the address lines that follow belong to
    for i, s in enumerate(segs):
        if s.id == "NM1":
            ctx = s[1]
        if s.id == "NM1" and s[1] == "PR":
            form["payer"] = {"name": s[3], "id": s[9], "seg": i}
        elif s.id == "NM1" and s[1] == "IL":
            form["patient"] = {"last": s[3], "first": s[4], "member": s[9], "seg": i}
        elif s.id == "DMG" and "patient" in form:
            form["patient"].update(dob=_date(s[2]), sex=s[3], dmg_seg=i)
        elif s.id == "NM1" and s[1] == "85":
            form["billing"] = {"name": s[3], "npi": s[9], "seg": i}
        elif s.id == "N3" and ctx in ("IL", "85", "PR"):
            form[{"IL": "patient", "85": "billing", "PR": "payer"}[ctx]]["address"] = s[1]
        elif s.id == "N4" and ctx in ("IL", "85", "PR"):
            form[{"IL": "patient", "85": "billing", "PR": "payer"}[ctx]].update(city=s[1], state=s[2], zip=s[3])
        elif s.id == "REF" and s[1] in ("EI", "EIN"):
            form["tax_id"] = {"value": s[2], "seg": i}
        elif s.id == "REF" and s[1] in ("G1", "9F"):
            form["auth"] = {"value": s[2], "seg": i}
        elif s.id == "NM1" and s[1] == "82":
            form["rendering"] = {"name": f"{s[4]} {s[3]}".strip(), "npi": s[9], "seg": i}
        elif s.id == "CLM":
            form["claim"] = {"id": s[1], "total": s[2], "pos": _comp(s, 5, 1), "frequency": _comp(s, 5, 3), "seg": i}
        elif s.id == "HI":
            for el in s.els[1:]:
                q, _, code = el.partition(s.sub)
                form["dx"].append({"code": code, "qualifier": q, "seg": i})
        elif s.id == "SV1":
            bits = s[1].split(s.sub)  # HC:99213:LT
            form["lines"].append({"cpt": bits[1] if len(bits) > 1 else "", "mods": bits[2:], "charge": s[2], "unit": s[3], "units": s[4], "pointer": s[7], "seg": i, "date": "", "date_seg": None})
            sv_idx = len(form["lines"]) - 1
        elif s.id == "DTP" and s[1] == "472" and sv_idx >= 0 and not form["lines"][sv_idx]["date"]:
            form["lines"][sv_idx].update(date=_date(s[3]), date_seg=i)
    for i, d in enumerate(form["dx"]):
        d["letter"] = chr(ord("A") + i)
    return {"lines": lines, "form": form}
