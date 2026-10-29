"""Seed the local OpenEMR through its REST API, and pull it back through FHIR into the three feeds.

Why two APIs: OpenEMR's FHIR API cannot create Appointments or Encounters (search and read only), so writes go through its
standard REST API, and FHIR is the way back out. OpenEMR's FHIR resources do not carry everything our feeds hold, so the
fields it cannot carry ride in free-text fields that it does expose, encoded as `krisnnai:key=value;key=value`:
    appointment   pc_title          (the REST read returns it; the FHIR Appointment does not)
    encounter     reason            (FHIR Encounter.reasonCode.text)
    note          document content  (FHIR DocumentReference -> Binary)
Everything here is synthetic. Patients are created as `Synthetic <member id>` with the member id in OpenEMR's external id
(`pubpid`), which FHIR returns as the patient's identifier. Idempotent: what already exists (found by those keys) is skipped.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from pathlib import Path

import httpx

from krisnnai.integrations.fhir import mapper
from krisnnai.integrations.fhir.client import FhirClient, _Bearer
from krisnnai.integrations.fhir.sync import _rows
from krisnnai.integrations.openemr.auth import OpenEmrAuth
from krisnnai.integrations.openemr.docker import FHIR_PATH, HTTPS_URL

PREFIX = "krisnnai:"
NPI_SYSTEM = mapper.NPI
FACILITY_ID = "3"  # the clinic OpenEMR creates at install
OFFICE_VISIT = "5"  # calendar / encounter category "Office Visit"
DOC_CATEGORY = "Medical Record"  # the document category path OpenEMR's REST upload accepts
DEFAULT_LIMIT = 50


def encode(**fields: str) -> str:
    """`krisnnai:a=1;b=2`. Values may not contain ';' or '='; commas in lists are written as '|'."""
    for k, v in fields.items():
        if ";" in str(v) or "=" in str(v):
            raise ValueError(f"{k} cannot be stored in an OpenEMR text field: {v!r}")
    return PREFIX + ";".join(f"{k}={v}" for k, v in fields.items())


def decode(text: str | None) -> dict[str, str] | None:
    if not text or not text.startswith(PREFIX):
        return None
    out = {}
    for part in text[len(PREFIX):].split(";"):
        k, _, v = part.partition("=")
        out[k] = v
    return out


def _synthetic_person(member: str) -> dict:
    h = int(hashlib.sha256(member.encode()).hexdigest(), 16)
    return {"DOB": (date(1950, 1, 1) + timedelta(days=h % 22000)).isoformat(), "sex": "Female" if h % 2 else "Male"}


class _Server:
    """The REST and FHIR clients for one OpenEMR, both with the same bearer token."""

    def __init__(self, auth: OpenEmrAuth, base: str = HTTPS_URL, rest: httpx.Client | None = None,
                 fhir: FhirClient | None = None):  # fmt: skip
        if rest is None:
            rest = httpx.Client(base_url=f"{base}/apis/default/api", verify=False, timeout=60,  # noqa: S501
                                auth=_Bearer(auth.token))  # fmt: skip
        self.rest = rest
        self.fhir = fhir or FhirClient(base + FHIR_PATH, token_provider=auth.token, verify=False)

    def rest_json(self, method: str, path: str, **kw) -> dict | list:
        r = self.rest.request(method, path, **kw)
        r.raise_for_status()
        return r.json()

    def rest_rows(self, path: str) -> list[dict]:
        """A list endpoint's rows. OpenEMR answers 404, not an empty list, when a list endpoint has no rows yet."""
        try:
            d = self.rest_json("GET", path)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise
        return d["data"] if isinstance(d, dict) else d


# ----------------------------------------------------------------------------------------------------------- seed


def select_feeds(feed_dir: Path, limit: int | None) -> tuple[list[dict], list[dict], list[dict]]:
    """Appointment, visit and note rows for the first `limit` patients (in appointment order)."""
    appts, visits, notes = (_rows(feed_dir / f"{n}.csv") for n in ("appointments", "visits", "notes"))
    if limit:
        keep: list[str] = []
        for r in [*appts, *visits]:
            if r["patient_ref"] not in keep and len(keep) < limit:
                keep.append(r["patient_ref"])
        appts = [r for r in appts if r["patient_ref"] in keep]
        visits = [r for r in visits if r["patient_ref"] in keep]
    have = {v["visit_id"] for v in visits}
    return appts, visits, [n for n in notes if n["visit_id"] in have]


def seed(server: _Server, feed_dir: Path, limit: int | None = DEFAULT_LIMIT) -> dict[str, dict[str, int]]:
    """Create what is missing. Returns {kind: {"created": n, "existing": n}}."""
    appts, visits, notes = select_feeds(feed_dir, limit)
    out = {k: {"created": 0, "existing": 0} for k in ("patients", "practitioners", "appointments", "encounters", "notes")}

    # patients, keyed by the member id in pubpid
    patients = {p["pubpid"]: p for p in server.rest_rows("/patient") if p.get("pubpid")}
    for member in sorted({r["patient_ref"] for r in [*appts, *visits]}):
        if member in patients:
            out["patients"]["existing"] += 1
            continue
        body = {"fname": "Synthetic", "lname": member, "pubpid": member, "street": "100 Synthetic Way", "city": "Testville",
                "state": "TX", "postal_code": "75001", "country_code": "US", **_synthetic_person(member)}  # fmt: skip
        data = server.rest_json("POST", "/patient", json=body)["data"]
        patients[member] = {"pid": data["pid"], "uuid": data["uuid"], "pubpid": member}
        out["patients"]["created"] += 1

    # practitioners, keyed by NPI (created through FHIR, which OpenEMR allows for Practitioner)
    uuid_by_npi = {}
    for p in server.fhir.search("Practitioner", page_size=None):
        for ident in p.get("identifier", []):
            if ident.get("system") == NPI_SYSTEM:
                uuid_by_npi[ident["value"]] = p["id"]
    user_id = {u["uuid"]: u["id"] for u in server.rest_rows("/practitioner")}
    for npi in sorted({r["provider_npi"] for r in [*appts, *visits]}):
        if npi in uuid_by_npi:
            out["practitioners"]["existing"] += 1
            continue
        body = {"resourceType": "Practitioner", "identifier": [{"system": NPI_SYSTEM, "value": npi}],
                "name": [{"use": "official", "family": f"Provider{npi}", "given": ["Synthetic"]}],
                "telecom": [{"system": "phone", "value": "5550000000", "use": "work"}], "active": True}  # fmt: skip
        r = server.fhir._http.post("/Practitioner", json=body, headers={"Content-Type": "application/fhir+json"})
        r.raise_for_status()
        made = r.json()
        uuid_by_npi[npi], user_id[made["uuid"]] = made["uuid"], str(made["id"])
        out["practitioners"]["created"] += 1

    # appointments (REST), keyed by the appointment id inside pc_title
    have = {(decode(a.get("pc_title")) or {}).get("appt") for a in server.rest_rows("/appointment")}
    for a in appts:
        if a["appointment_id"] in have:
            out["appointments"]["existing"] += 1
            continue
        title = encode(appt=a["appointment_id"], cpt=a["cpt"], payer=a["payer_id"], booked=a["booked_on"],
                       status=a.get("status") or "booked")  # fmt: skip
        server.rest_json("POST", f"/patient/{patients[a['patient_ref']]['pid']}/appointment", json={
            "pc_catid": OFFICE_VISIT, "pc_title": title, "pc_hometext": "Synthetic appointment", "pc_duration": "1800",
            "pc_apptstatus": "-",
            "pc_eventDate": a["appt_date"], "pc_startTime": "09:00", "pc_facility": FACILITY_ID,
            "pc_billing_location": FACILITY_ID, "pc_aid": user_id[uuid_by_npi[a["provider_npi"]]],
        })  # fmt: skip
        out["appointments"]["created"] += 1

    # encounters (REST, patient addressed by uuid), keyed by the visit id inside the reason
    have_enc = {(decode(rc.get("text")) or {}).get("visit")
                for e in server.fhir.search("Encounter", page_size=None) for rc in e.get("reasonCode", [])}  # fmt: skip
    for v in visits:
        if v["visit_id"] in have_enc:
            out["encounters"]["existing"] += 1
            continue
        when = f"{v['dos']} 09:00:00"
        server.rest_json("POST", f"/patient/{patients[v['patient_ref']]['uuid']}/encounter", json={
            "pc_catid": OFFICE_VISIT, "class_code": "AMB", "sensitivity": "normal", "date": when, "onset_date": when,
            "reason": encode(visit=v["visit_id"], cpt=v["cpt"], units=v.get("units") or "1", payer=v["payer_id"]),
            "facility_id": FACILITY_ID, "billing_facility": FACILITY_ID,
            "provider_id": user_id[uuid_by_npi[v["provider_npi"]]], "referral_source": "",
        })  # fmt: skip
        out["encounters"]["created"] += 1

    # notes (REST document upload), keyed by the file name
    have_doc = {c.get("attachment", {}).get("title") for d in server.fhir.search("DocumentReference", page_size=None) for c in d.get("content", [])}
    patient_of = {v["visit_id"]: v["patient_ref"] for v in visits}
    for n in notes:
        name = f"note_{n['visit_id']}.txt"
        if name in have_doc:
            out["notes"]["existing"] += 1
            continue
        content = encode(visit=n["visit_id"], note_date=n["note_date"], signed=n.get("signed_date", ""),
                         minutes=n.get("minutes", ""), elements=n.get("elements", "").replace(",", "|"))  # fmt: skip
        server.rest_json("POST", f"/patient/{patients[patient_of[n['visit_id']]]['pid']}/document",
                         params={"path": DOC_CATEGORY}, files={"document": (name, content.encode(), "text/plain")})  # fmt: skip
        out["notes"]["created"] += 1
    return out


# ------------------------------------------------------------------------------------------------------------ pull


def _ref_uuid(ref: dict | None) -> str:
    return ((ref or {}).get("reference") or "").split("/")[-1]


def pull(server: _Server, out_dir: Path) -> dict[str, int]:
    """Write appointments.csv, visits.csv and notes.csv from OpenEMR's FHIR API (appointment titles via REST)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    member_of = {}
    for p in server.fhir.search("Patient", page_size=None):
        for ident in p.get("identifier", []):
            member_of[p["id"]] = ident.get("value", "")
    npi_of = {}
    for p in server.fhir.search("Practitioner", page_size=None):
        for ident in p.get("identifier", []):
            if ident.get("system") == NPI_SYSTEM:
                npi_of[p["id"]] = ident["value"]
    title_of = {a["pc_uuid"]: a.get("pc_title") for a in server.rest_rows("/appointment")}

    def actor(res: dict, kind: str) -> str:
        for p in res.get("participant", []):
            ref = (p.get("actor") or p.get("individual") or {}).get("reference", "")
            if ref.startswith(kind + "/"):
                return ref.split("/")[-1]
        return ""

    appts, visits, notes = [], [], []
    for a in server.fhir.search("Appointment", page_size=None):
        k = decode(title_of.get(a["id"]))
        if k is None:
            continue  # not one of ours
        appts.append({"appointment_id": k["appt"], "payer_id": k["payer"], "provider_npi": npi_of.get(actor(a, "Practitioner"), ""),
                      "patient_ref": member_of.get(actor(a, "Patient"), ""), "appt_date": a["start"][:10],
                      "booked_on": k["booked"], "cpt": k["cpt"], "status": k["status"]})  # fmt: skip
    for e in server.fhir.search("Encounter", page_size=None):
        k = decode(next((rc.get("text") for rc in e.get("reasonCode", []) if decode(rc.get("text"))), None))
        if k is None:
            continue
        visits.append({"visit_id": k["visit"], "payer_id": k["payer"], "provider_npi": npi_of.get(actor(e, "Practitioner"), ""),
                       "patient_ref": member_of.get(_ref_uuid(e.get("subject")), ""), "dos": e["period"]["start"][:10],
                       "cpt": k["cpt"], "units": k["units"]})  # fmt: skip
    for d in server.fhir.search("DocumentReference", page_size=None):
        for c in d.get("content", []):
            att = c.get("attachment", {})
            if not str(att.get("title", "")).startswith("note_") or not att.get("url"):
                continue
            r = server.fhir._http.get(att["url"], headers={"Accept": "*/*"})
            r.raise_for_status()
            k = decode(r.text.strip())
            if k is not None:
                notes.append({"visit_id": k["visit"], "note_date": k["note_date"], "signed_date": k["signed"],
                              "minutes": k["minutes"], "elements": k["elements"].replace("|", ",")})  # fmt: skip
    for rows, key in ((appts, "appointment_id"), (visits, "visit_id"), (notes, "visit_id")):
        rows.sort(key=lambda r: r[key])
    mapper.write_csv(out_dir / "appointments.csv", mapper.APPT_COLUMNS, appts)
    mapper.write_csv(out_dir / "visits.csv", mapper.VISIT_COLUMNS, visits)
    mapper.write_csv(out_dir / "notes.csv", mapper.NOTE_COLUMNS, notes)
    return {"appointments": len(appts), "visits": len(visits), "notes": len(notes)}
