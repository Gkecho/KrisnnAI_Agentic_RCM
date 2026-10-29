"""FHIR R4 resources <-> the practice's CSV feeds, so the loader and the agents do not change.

    Patient       identifier urn:krisnnai:member-id            member id
    Practitioner  identifier http://hl7.org/fhir/sid/us-npi   NPI
    Organization  identifier urn:krisnnai:payer-id             payer id
    Appointment   -> appointments.csv      (serviceType = CPT, created = booked on, start = visit day)
    Encounter     -> visits.csv            (type = CPT, extension units, extension payer)
    DocumentReference -> notes.csv         (context.encounter, extension elements and signed date)

Names are not carried (synthetic practice: nothing but the member id identifies a person).
"""

from __future__ import annotations

import base64
import csv
import io
from collections.abc import Iterable

MEMBER = "urn:krisnnai:member-id"
NPI = "http://hl7.org/fhir/sid/us-npi"
PAYER = "urn:krisnnai:payer-id"
CPT = "http://www.ama-assn.org/go/cpt"
X_UNITS = "urn:krisnnai:units"
X_PAYER = "urn:krisnnai:payer"
X_ELEMENTS = "urn:krisnnai:elements"
X_SIGNED = "urn:krisnnai:signed-date"

APPT_COLUMNS = ["appointment_id", "payer_id", "provider_npi", "patient_ref", "appt_date", "booked_on", "cpt", "status"]
VISIT_COLUMNS = ["visit_id", "payer_id", "provider_npi", "patient_ref", "dos", "cpt", "units"]
NOTE_COLUMNS = ["visit_id", "note_date", "signed_date", "minutes", "elements"]


def _slug(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-." else "-" for c in value)[:60]


def patient_id(member: str) -> str:
    return "pt-" + _slug(member)


def practitioner_id(npi: str) -> str:
    return "pr-" + _slug(npi)


def organization_id(payer: str) -> str:
    return "org-" + _slug(payer)


# --------------------------------------------------------------------------------------------------- to FHIR


def patient(member: str) -> dict:
    return {"resourceType": "Patient", "id": patient_id(member),
            "identifier": [{"system": MEMBER, "value": member}], "active": True}  # fmt: skip


def practitioner(npi: str) -> dict:
    return {"resourceType": "Practitioner", "id": practitioner_id(npi), "identifier": [{"system": NPI, "value": npi}]}


def organization(payer: str) -> dict:
    return {"resourceType": "Organization", "id": organization_id(payer),
            "identifier": [{"system": PAYER, "value": payer}], "name": payer}  # fmt: skip


def appointment(row: dict) -> dict:
    return {
        "resourceType": "Appointment", "id": "ap-" + _slug(row["appointment_id"]),
        "identifier": [{"value": row["appointment_id"]}],
        "status": row.get("status") or "booked",
        "serviceType": [{"coding": [{"system": CPT, "code": row["cpt"]}]}],
        "start": f"{row['appt_date']}T09:00:00Z", "end": f"{row['appt_date']}T09:30:00Z",
        "created": row["booked_on"],
        "extension": [{"url": X_PAYER, "valueReference": {"reference": f"Organization/{organization_id(row['payer_id'])}"}}],
        "participant": [
            {"actor": {"reference": f"Patient/{patient_id(row['patient_ref'])}"}, "status": "accepted"},
            {"actor": {"reference": f"Practitioner/{practitioner_id(row['provider_npi'])}"}, "status": "accepted"},
        ],
    }  # fmt: skip


def encounter(row: dict) -> dict:
    return {
        "resourceType": "Encounter", "id": "en-" + _slug(row["visit_id"]),
        "identifier": [{"value": row["visit_id"]}], "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
        "type": [{"coding": [{"system": CPT, "code": row["cpt"]}]}],
        "subject": {"reference": f"Patient/{patient_id(row['patient_ref'])}"},
        "participant": [{"individual": {"reference": f"Practitioner/{practitioner_id(row['provider_npi'])}"}}],
        "period": {"start": f"{row['dos']}T09:00:00Z"},
        "extension": [
            {"url": X_UNITS, "valueInteger": int(float(row.get("units") or 1))},
            {"url": X_PAYER, "valueReference": {"reference": f"Organization/{organization_id(row['payer_id'])}"}},
        ],
    }  # fmt: skip


def document_reference(row: dict) -> dict:
    ext = [{"url": X_ELEMENTS, "valueString": row.get("elements", "")}]
    if row.get("signed_date"):
        ext.append({"url": X_SIGNED, "valueDate": row["signed_date"]})
    return {
        "resourceType": "DocumentReference", "id": "dr-" + _slug(row["visit_id"]), "status": "current",
        "type": {"text": "Progress note"}, "date": f"{row['note_date']}T12:00:00Z",
        "context": {"encounter": [{"reference": f"Encounter/en-{_slug(row['visit_id'])}"}]},
        "content": [{"attachment": {"contentType": "text/plain",
                                    "data": base64.b64encode(row.get("elements", "").encode()).decode() or "AA=="}}],
        "description": row.get("elements", ""), "extension": ext,
    }  # fmt: skip


def resources_from_feeds(appointments: Iterable[dict], visits: Iterable[dict], notes: Iterable[dict]) -> list[dict]:
    """All resources for a set of feed rows, referenced resources first (patients, practitioners, payers)."""
    appointments, visits, notes = list(appointments), list(visits), list(notes)
    members = {r["patient_ref"] for r in [*appointments, *visits]}
    npis = {r["provider_npi"] for r in [*appointments, *visits]}
    payers = {r["payer_id"] for r in [*appointments, *visits]}
    out = [patient(x) for x in sorted(members)] + [practitioner(x) for x in sorted(npis)]
    out += [organization(x) for x in sorted(payers)]
    out += [appointment(r) for r in appointments] + [encounter(r) for r in visits]
    # the note's visit must exist (a note can only describe an encounter we sent)
    have = {r["visit_id"] for r in visits}
    out += [document_reference(r) for r in notes if r["visit_id"] in have]
    return out


# ------------------------------------------------------------------------------------------------- from FHIR


def _ident(res: dict, system: str) -> str:
    return next((i.get("value", "") for i in res.get("identifier", []) if i.get("system") == system), "")


def _ref_id(ref: dict | None) -> str:
    return (ref or {}).get("reference", "").split("/")[-1]


def _ext(res: dict, url: str):
    for e in res.get("extension", []):
        if e.get("url") == url:
            return e
    return {}


def _cpt(res_codeable: list[dict]) -> str:
    for cc in res_codeable or []:
        for c in cc.get("coding", []):
            if c.get("system") == CPT:
                return c.get("code", "")
    return ""


class Directory:
    """Resolves resource ids to the identifiers our feeds use."""

    def __init__(self, patients: Iterable[dict], practitioners: Iterable[dict], organizations: Iterable[dict]):
        self.member = {p["id"]: _ident(p, MEMBER) for p in patients}
        self.npi = {p["id"]: _ident(p, NPI) for p in practitioners}
        self.payer = {o["id"]: _ident(o, PAYER) for o in organizations}


def appointments_to_rows(resources: Iterable[dict], d: Directory) -> list[dict]:
    rows = []
    for a in resources:
        patient_ref = prov = ""
        for part in a.get("participant", []):
            ref = _ref_id(part.get("actor"))
            if ref in d.member:
                patient_ref = d.member[ref]
            elif ref in d.npi:
                prov = d.npi[ref]
        rows.append({
            "appointment_id": (a.get("identifier") or [{}])[0].get("value", ""),
            "payer_id": d.payer.get(_ref_id(_ext(a, X_PAYER).get("valueReference")), ""),
            "provider_npi": prov, "patient_ref": patient_ref, "appt_date": (a.get("start") or "")[:10],
            "booked_on": (a.get("created") or "")[:10], "cpt": _cpt(a.get("serviceType", [])),
            "status": a.get("status", "booked"),
        })  # fmt: skip
    return sorted(rows, key=lambda r: r["appointment_id"])


def encounters_to_rows(resources: Iterable[dict], d: Directory) -> list[dict]:
    rows = []
    for e in resources:
        prov = next((d.npi.get(_ref_id(p.get("individual")), "") for p in e.get("participant", [])), "")
        rows.append({
            "visit_id": (e.get("identifier") or [{}])[0].get("value", ""),
            "payer_id": d.payer.get(_ref_id(_ext(e, X_PAYER).get("valueReference")), ""),
            "provider_npi": prov, "patient_ref": d.member.get(_ref_id(e.get("subject")), ""),
            "dos": (e.get("period", {}).get("start") or "")[:10], "cpt": _cpt(e.get("type", [])),
            "units": _ext(e, X_UNITS).get("valueInteger", 1),
        })  # fmt: skip
    return sorted(rows, key=lambda r: r["visit_id"])


def notes_to_rows(resources: Iterable[dict], encounters_by_id: dict[str, str]) -> list[dict]:
    """`encounters_by_id`: Encounter resource id -> the visit id (the encounter's identifier)."""
    rows = []
    for dr in resources:
        enc = _ref_id((dr.get("context", {}).get("encounter") or [{}])[0])
        visit = encounters_by_id.get(enc, "")
        if not visit:
            continue
        rows.append({
            "visit_id": visit, "note_date": (dr.get("date") or "")[:10],
            "signed_date": _ext(dr, X_SIGNED).get("valueDate", ""), "minutes": "",
            "elements": _ext(dr, X_ELEMENTS).get("valueString", dr.get("description", "")),
        })  # fmt: skip
    return sorted(rows, key=lambda r: r["visit_id"])


def write_csv(path, columns: list[str], rows: list[dict]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in columns})
    path.write_text(buf.getvalue(), encoding="utf-8", newline="")

