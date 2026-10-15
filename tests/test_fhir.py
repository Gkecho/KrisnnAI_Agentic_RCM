"""Stage 1, FHIR: seed and pull through a fake FHIR server, mapping fidelity, paging, incremental pull, loader round trip."""

from __future__ import annotations

import csv
import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy import func, select

import krisnai.model as m
from krisnai.ingest.loader import ingest_file
from krisnai.integrations.clearinghouse.client import EndpointRefused
from krisnai.integrations.fhir import mapper
from krisnai.integrations.fhir.client import FhirClient
from krisnai.integrations.fhir.sync import pull, seed
from krisnai.model import tenant_session
from tests.test_ingest import SALT, make_engine

APPTS = [
    {"appointment_id": "AP1", "payer_id": "PAYA", "provider_npi": "1888888800", "patient_ref": "MEM001",
     "appt_date": "2026-05-04", "booked_on": "2026-04-28", "cpt": "99213", "status": "booked"},
    {"appointment_id": "AP2", "payer_id": "PAYB", "provider_npi": "1888888801", "patient_ref": "MEM002",
     "appt_date": "2026-05-05", "booked_on": "2026-04-20", "cpt": "45378", "status": "booked"},
    {"appointment_id": "AP3", "payer_id": "PAYA", "provider_npi": "1888888800", "patient_ref": "MEM003",
     "appt_date": "2026-05-06", "booked_on": "2026-04-30", "cpt": "99214", "status": "booked"},
]
VISITS = [
    {"visit_id": "V1", "payer_id": "PAYA", "provider_npi": "1888888800", "patient_ref": "MEM001",
     "dos": "2026-05-04", "cpt": "99213", "units": "1"},
    {"visit_id": "V2", "payer_id": "PAYB", "provider_npi": "1888888801", "patient_ref": "MEM002",
     "dos": "2026-05-05", "cpt": "45378", "units": "2"},
]
NOTES = [
    {"visit_id": "V1", "note_date": "2026-05-04", "signed_date": "2026-05-05", "minutes": "",
     "elements": "assessment,plan"},
    {"visit_id": "V2", "note_date": "2026-05-05", "signed_date": "", "minutes": "", "elements": "assessment"},
]


class FakeFhir:
    """Just enough of a FHIR R4 REST server: capability, transaction PUTs, paged search with _count and _lastUpdated."""

    def __init__(self):
        self.store: dict[tuple[str, str], dict] = {}
        self.day = "2026-06-01"
        self.requests = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests += 1
        url = urlparse(str(request.url))
        if url.path == "/metadata":
            types = sorted({t for t, _ in self.store})
            return httpx.Response(200, json={"resourceType": "CapabilityStatement",
                                             "rest": [{"resource": [{"type": t} for t in types]}]})
        if request.method == "POST" and url.path in ("", "/"):
            for e in json.loads(request.content)["entry"]:
                res = e["resource"]
                res["meta"] = {"lastUpdated": f"{self.day}T00:00:00Z"}
                self.store[(res["resourceType"], res["id"])] = res
            return httpx.Response(200, json={"resourceType": "Bundle", "type": "transaction-response"})
        rtype = url.path.strip("/")
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        items = [r for (t, _), r in sorted(self.store.items()) if t == rtype]
        if "_lastUpdated" in q:
            cut = q["_lastUpdated"].removeprefix("gt")
            items = [r for r in items if r["meta"]["lastUpdated"][:10] > cut]
        size, page = int(q.get("_count", 100)), int(q.get("_page", 0))
        chunk = items[page * size:(page + 1) * size]
        bundle = {"resourceType": "Bundle", "type": "searchset", "entry": [{"resource": r} for r in chunk], "link": []}
        if (page + 1) * size < len(items):
            nq = {**q, "_page": page + 1}
            query = "&".join(f"{k}={v}" for k, v in nq.items())
            bundle["link"].append({"relation": "next", "url": f"http://localhost:8080/{rtype}?{query}"})
        return httpx.Response(200, json=bundle)


@pytest.fixture()
def server():
    fake = FakeFhir()
    http = httpx.Client(base_url="http://localhost:8080", transport=httpx.MockTransport(fake.handler))
    return fake, FhirClient("http://localhost:8080", http=http)


def write_feed(dir_, name, columns, rows):
    dir_.mkdir(parents=True, exist_ok=True)
    mapper.write_csv(dir_ / name, columns, rows)


def read(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def seed_all(client, src, appts=APPTS, visits=VISITS, notes=NOTES):
    write_feed(src, "appointments.csv", mapper.APPT_COLUMNS, appts)
    write_feed(src, "visits.csv", mapper.VISIT_COLUMNS, visits)
    write_feed(src, "notes.csv", mapper.NOTE_COLUMNS, notes)
    return seed(client, src)


def test_seed_then_pull_returns_the_same_feeds(server, tmp_path):
    fake, client = server
    counts = seed_all(client, tmp_path / "src")
    assert counts["Appointment"] == 3 and counts["Encounter"] == 2 and counts["DocumentReference"] == 2
    assert counts["Patient"] == 3 and counts["Practitioner"] == 2 and counts["Organization"] == 2
    got = pull(client, tmp_path / "out")
    assert got == {"appointments": 3, "visits": 2, "notes": 2}
    for name, rows in (("appointments.csv", APPTS), ("visits.csv", VISITS), ("notes.csv", NOTES)):
        assert read(tmp_path / "out" / name) == [{k: str(v) for k, v in r.items()} for r in rows]


def test_paging_follows_next_links(server):
    fake, client = server
    for i in range(7):
        fake.store[("Patient", f"p{i}")] = {"resourceType": "Patient", "id": f"p{i}"}
    assert len(list(client.search("Patient", page_size=3))) == 7
    assert fake.requests == 3


def test_incremental_pull_returns_only_what_changed_since(server, tmp_path):
    fake, client = server
    seed_all(client, tmp_path / "src", APPTS[:2], VISITS, NOTES)
    fake.day = "2026-06-10"
    seed_all(client, tmp_path / "src2", APPTS[2:], [], [])
    got = pull(client, tmp_path / "delta", since="2026-06-05")
    assert got["appointments"] == 1 and got["visits"] == 0
    assert [r["appointment_id"] for r in read(tmp_path / "delta" / "appointments.csv")] == ["AP3"]


def test_a_note_whose_encounter_was_not_sent_is_not_sent():
    res = mapper.resources_from_feeds(APPTS, VISITS, [*NOTES, {**NOTES[0], "visit_id": "V99"}])
    assert [r["id"] for r in res if r["resourceType"] == "DocumentReference"] == ["dr-V1", "dr-V2"]


def test_the_pulled_feeds_load_through_the_normal_loader(server, tmp_path):
    fake, client = server
    seed_all(client, tmp_path / "src")
    pull(client, tmp_path / "out")
    eng = make_engine(tmp_path / "db.sqlite")
    for name in ("visits.csv", "appointments.csv", "notes.csv"):
        assert ingest_file(eng, 1, tmp_path / "out" / name, SALT).status == "loaded", name
    with tenant_session(eng, 1) as s:
        assert s.scalar(select(func.count()).select_from(m.Visit)) == 2
        assert s.scalar(select(func.count()).select_from(m.Appointment)) == 3
        assert s.scalar(select(func.count()).select_from(m.VisitNote)) == 2


def test_the_client_refuses_a_remote_server_unless_enabled(monkeypatch):
    monkeypatch.delenv("KRISNAI_ALLOW_REAL_ENDPOINTS", raising=False)
    with pytest.raises(EndpointRefused):
        FhirClient("https://fhir.example-emr.com/r4")


def test_capability_check_names_the_resources_the_server_supports(server, tmp_path):
    fake, client = server
    seed_all(client, tmp_path / "s", APPTS[:1], [], [])
    assert client.supports("Appointment") and not client.supports("Claim")
