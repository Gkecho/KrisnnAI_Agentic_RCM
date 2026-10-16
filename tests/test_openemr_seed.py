"""OpenEMR seed (REST) and pull (FHIR) against a fake OpenEMR: counts, idempotency, the round trip, what is ignored."""

from __future__ import annotations

import csv
import re
import uuid
from pathlib import Path

import httpx
import pytest

from krisnai.integrations.fhir import mapper
from krisnai.integrations.fhir.client import FhirClient
from krisnai.integrations.openemr import seed as oeseed

BASE = "https://localhost:9300/apis/default"

APPTS = [
    {"appointment_id": "AP1", "payer_id": "PAYA", "provider_npi": "1888888800", "patient_ref": "MEM001",
     "appt_date": "2026-05-04", "booked_on": "2026-04-28", "cpt": "99213", "status": "booked"},
    {"appointment_id": "AP2", "payer_id": "PAYB", "provider_npi": "1888888801", "patient_ref": "MEM002",
     "appt_date": "2026-05-05", "booked_on": "2026-04-20", "cpt": "45378", "status": "booked"},
    {"appointment_id": "AP3", "payer_id": "PAYA", "provider_npi": "1888888800", "patient_ref": "MEM003",
     "appt_date": "2026-05-06", "booked_on": "2026-04-30", "cpt": "99214", "status": "booked"},
]
VISITS = [
    {"visit_id": "V1", "payer_id": "PAYA", "provider_npi": "1888888800", "patient_ref": "MEM001", "dos": "2026-05-04",
     "cpt": "99213", "units": "1"},
    {"visit_id": "V2", "payer_id": "PAYB", "provider_npi": "1888888801", "patient_ref": "MEM002", "dos": "2026-05-05",
     "cpt": "45378", "units": "2"},
]
NOTES = [
    {"visit_id": "V1", "note_date": "2026-05-04", "signed_date": "2026-05-05", "minutes": "", "elements": "assessment,plan"},
    {"visit_id": "V2", "note_date": "2026-05-05", "signed_date": "", "minutes": "", "elements": "assessment"},
]


class FakeOpenEmr:
    """Just enough of OpenEMR's REST and FHIR APIs, with its limits: FHIR Appointment has no comment, Binary needs a read."""

    def __init__(self):
        self.patients, self.users, self.appts, self.encs, self.docs = [], [], [], [], []
        self.calls: list[tuple[str, str]] = []
        self.count_params: list[str] = []  # every _count the client sent on a FHIR search

    def _bundle(self, resources: list[dict]) -> httpx.Response:
        # real OpenEMR: ignores paging. A `_count` returns exactly that many rows and no `next` link.
        count = self._request.url.params.get("_count")
        if count:
            self.count_params.append(count)
            resources = resources[: int(count)]
        return httpx.Response(200, json={"resourceType": "Bundle", "entry": [{"resource": r} for r in resources]})

    def _patient_of(self, key: str) -> dict:
        return next(p for p in self.patients if key in (str(p["pid"]), p["uuid"]))

    def __call__(self, request: httpx.Request) -> httpx.Response:  # noqa: C901
        self._request = request
        path, method = request.url.path.removeprefix("/apis/default"), request.method
        self.calls.append((method, path))
        if path.startswith("/api/"):
            return self._rest(method, path.removeprefix("/api"), request)
        return self._fhir(method, path.removeprefix("/fhir"), request)

    def _rest(self, method: str, path: str, request: httpx.Request) -> httpx.Response:
        import json

        if (method, path) == ("GET", "/patient"):
            return httpx.Response(200, json={"data": self.patients})
        if (method, path) == ("POST", "/patient"):
            b = json.loads(request.content)
            p = {"pid": len(self.patients) + 1, "uuid": str(uuid.uuid4()), "pubpid": b["pubpid"]}
            self.patients.append(p)
            return httpx.Response(201, json={"data": {"pid": p["pid"], "uuid": p["uuid"]}})
        if (method, path) == ("GET", "/practitioner"):
            return httpx.Response(200, json={"data": [{"id": u["id"], "uuid": u["uuid"]} for u in self.users]})
        if (method, path) == ("GET", "/appointment"):
            if not self.appts:  # real OpenEMR: 404 when there is nothing yet
                return httpx.Response(404, json={"error": "no appointments"})
            return httpx.Response(200, json={"data": [{"pc_uuid": a["uuid"], "pc_title": a["title"]} for a in self.appts]})
        m = re.fullmatch(r"/patient/([^/]+)/(appointment|encounter|document)", path)
        if method == "POST" and m:
            p, kind = self._patient_of(m.group(1)), m.group(2)
            if kind == "appointment":
                b = json.loads(request.content)
                assert "krisnai:appt=" in b["pc_title"] and b["pc_aid"]
                if "pc_hometext" not in b:  # OpenEMR requires it
                    return httpx.Response(400, json={"pc_hometext": {"Required::NON_EXISTENT_KEY": "must be provided"}})
                self.appts.append({"uuid": str(uuid.uuid4()), "title": b["pc_title"], "date": b["pc_eventDate"], "patient": p,
                                   "aid": b["pc_aid"]})  # fmt: skip
                return httpx.Response(200, json={"id": len(self.appts)})
            if kind == "encounter":
                assert m.group(1) == p["uuid"], "encounters are addressed by patient uuid"
                b = json.loads(request.content)
                self.encs.append({"uuid": str(uuid.uuid4()), "reason": b["reason"], "date": b["date"], "patient": p,
                                  "provider": b["provider_id"]})  # fmt: skip
                return httpx.Response(201, json={"data": {"eid": len(self.encs)}})
            assert request.url.params["path"] == "Medical Record"
            text = request.content.decode()
            name = re.search(r'filename="([^"]+)"', text).group(1)
            body = text.split("\r\n\r\n", 1)[1].rsplit("\r\n--", 1)[0]
            self.docs.append({"uuid": str(uuid.uuid4()), "name": name, "content": body, "patient": p})
            return httpx.Response(200, json=True)
        return httpx.Response(404, json={"error": f"{method} {path}"})

    def _fhir(self, method: str, path: str, request: httpx.Request) -> httpx.Response:
        import json

        user_of = {u["uuid"]: u for u in self.users}
        if (method, path) == ("POST", "/Practitioner"):
            b = json.loads(request.content)
            u = {"id": 100 + len(self.users), "uuid": str(uuid.uuid4()), "npi": b["identifier"][0]["value"]}
            self.users.append(u)
            return httpx.Response(201, json={"id": u["id"], "uuid": u["uuid"]})
        if path == "/Practitioner":
            return self._bundle([{"resourceType": "Practitioner", "id": u["uuid"],
                                  "identifier": [{"system": mapper.NPI, "value": u["npi"]}]} for u in self.users])  # fmt: skip
        if path == "/Patient":
            return self._bundle([{"resourceType": "Patient", "id": p["uuid"], "identifier": [{"value": p["pubpid"]}]}
                                 for p in self.patients])  # fmt: skip
        if path == "/Appointment":  # no comment, no CPT, no payer: only timing, status and participants
            user = lambda a: next(u for u in self.users if str(u["id"]) == str(a["aid"]))  # noqa: E731
            return self._bundle([{"resourceType": "Appointment", "id": a["uuid"], "status": "proposed",
                                  "start": f"{a['date']}T09:00:00+00:00", "participant": [
                                      {"actor": {"reference": f"Patient/{a['patient']['uuid']}"}},
                                      {"actor": {"reference": f"Practitioner/{user(a)['uuid']}"}}]} for a in self.appts])  # fmt: skip
        if path == "/Encounter":
            return self._bundle([{"resourceType": "Encounter", "id": e["uuid"], "subject": {"reference": f"Patient/{e['patient']['uuid']}"},
                                  "participant": [{"individual": {"reference": f"Practitioner/{next(u for u in self.users if str(u['id']) == str(e['provider']))['uuid']}"}}],
                                  "period": {"start": e["date"].replace(" ", "T") + "+00:00"},
                                  "reasonCode": [{"text": e["reason"]}]} for e in self.encs])  # fmt: skip
        if path == "/DocumentReference":
            return self._bundle([{"resourceType": "DocumentReference", "id": d["uuid"], "content": [{"attachment": {
                "title": d["name"], "url": f"{BASE}/fhir/Binary/{d['uuid']}"}}]} for d in self.docs])  # fmt: skip
        m = re.fullmatch(r"/Binary/(.+)", path)
        if m:
            return httpx.Response(200, text=next(d["content"] for d in self.docs if d["uuid"] == m.group(1)))
        return httpx.Response(404, json={"error": f"{method} {path}"})


def _write(path: Path, columns: list[str], rows: list[dict]) -> None:
    mapper.write_csv(path, columns, rows)


@pytest.fixture()
def feeds(tmp_path) -> Path:
    d = tmp_path / "feeds"
    d.mkdir()
    _write(d / "appointments.csv", mapper.APPT_COLUMNS, APPTS)
    _write(d / "visits.csv", mapper.VISIT_COLUMNS, VISITS)
    _write(d / "notes.csv", mapper.NOTE_COLUMNS, NOTES)
    return d


def make_server(fake: FakeOpenEmr) -> oeseed._Server:
    transport = httpx.MockTransport(fake)
    rest = httpx.Client(transport=transport, base_url=f"{BASE}/api")
    fhir = FhirClient(f"{BASE}/fhir", http=httpx.Client(transport=transport, base_url=f"{BASE}/fhir"))
    return oeseed._Server(auth=None, rest=rest, fhir=fhir)  # type: ignore[arg-type]


def read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_seed_creates_everything_through_rest_and_a_second_run_creates_nothing(feeds):
    fake = FakeOpenEmr()
    server = make_server(fake)
    first = oeseed.seed(server, feeds, limit=None)
    assert first["patients"] == {"created": 3, "existing": 0}
    assert first["practitioners"]["created"] == 2
    assert first["appointments"]["created"] == 3 and first["encounters"]["created"] == 2 and first["notes"]["created"] == 2
    second = oeseed.seed(server, feeds, limit=None)
    assert all(v["created"] == 0 for v in second.values()) and second["appointments"]["existing"] == 3
    assert len(fake.patients) == 3 and len(fake.appts) == 3 and len(fake.encs) == 2 and len(fake.docs) == 2


def test_appointments_and_encounters_are_never_written_over_fhir(feeds):
    fake = FakeOpenEmr()
    oeseed.seed(make_server(fake), feeds, limit=None)
    posts = [p for m, p in fake.calls if m == "POST"]
    fhir_posts = {p for p in posts if p.startswith("/fhir")}
    assert fhir_posts == {"/fhir/Practitioner"}  # the only resource of ours OpenEMR lets FHIR create
    assert any(p.endswith("/appointment") for p in posts) and any(p.endswith("/encounter") for p in posts)  # REST


def test_the_round_trip_returns_the_same_rows(feeds, tmp_path):
    fake = FakeOpenEmr()
    server = make_server(fake)
    oeseed.seed(server, feeds, limit=None)
    out = tmp_path / "pulled"
    counts = oeseed.pull(server, out)
    assert counts == {"appointments": 3, "visits": 2, "notes": 2}
    assert read(out / "appointments.csv") == sorted(APPTS, key=lambda r: r["appointment_id"])
    assert read(out / "visits.csv") == sorted(VISITS, key=lambda r: r["visit_id"])
    assert read(out / "notes.csv") == sorted(NOTES, key=lambda r: r["visit_id"])


def test_the_limit_keeps_only_the_first_patients_and_their_visits_and_notes(feeds):
    fake = FakeOpenEmr()
    out = oeseed.seed(make_server(fake), feeds, limit=1)
    assert out["patients"]["created"] == 1 and out["appointments"]["created"] == 1
    assert out["encounters"]["created"] == 1 and out["notes"]["created"] == 1


def test_records_that_are_not_ours_are_ignored_on_pull(feeds, tmp_path):
    fake = FakeOpenEmr()
    server = make_server(fake)
    oeseed.seed(server, feeds, limit=None)
    fake.appts.append({"uuid": str(uuid.uuid4()), "title": "walk-in", "date": "2026-05-09", "patient": fake.patients[0],
                       "aid": fake.users[0]["id"]})  # fmt: skip
    fake.docs.append({"uuid": str(uuid.uuid4()), "name": "scan.pdf", "content": "binary", "patient": fake.patients[0]})
    counts = oeseed.pull(server, tmp_path / "p")
    assert counts == {"appointments": 3, "visits": 2, "notes": 2}


def test_the_text_encoding_round_trips_and_rejects_separators():
    text = oeseed.encode(appt="AP1", cpt="99213", elements="a|b")
    assert oeseed.decode(text) == {"appt": "AP1", "cpt": "99213", "elements": "a|b"}
    assert oeseed.decode("walk-in") is None and oeseed.decode(None) is None
    with pytest.raises(ValueError):
        oeseed.encode(payer="A;B")


def test_synthetic_patients_have_no_real_identity(feeds):
    fake = FakeOpenEmr()
    oeseed.seed(make_server(fake), feeds, limit=None)
    assert {p["pubpid"] for p in fake.patients} == {"MEM001", "MEM002", "MEM003"}
    person = oeseed._synthetic_person("MEM001")
    assert person == oeseed._synthetic_person("MEM001") and person["sex"] in ("Female", "Male")


def test_openemr_calls_never_send_count_because_openemr_truncates_at_it(feeds, tmp_path):
    fake = FakeOpenEmr()
    server = make_server(fake)
    oeseed.seed(server, feeds, limit=None)
    oeseed.seed(server, feeds, limit=None)  # a rerun must find everything it created
    oeseed.pull(server, tmp_path / "p")
    assert fake.count_params == []
    assert len(fake.encs) == 2 and len(fake.docs) == 2 and len(fake.appts) == 3
