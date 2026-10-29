"""Seed a local FHIR server from the practice's CSV feeds, and pull the feeds back out of a FHIR server.

`pull` is the integration: it reads Appointment, Encounter and DocumentReference (plus the Patient, Practitioner and
Organization they point at) and writes `appointments.csv`, `visits.csv` and `notes.csv` into an inbox folder, where the
daily loader treats them like any other feed.
"""

from __future__ import annotations

import csv
from pathlib import Path

from krisnnai.integrations.fhir import mapper
from krisnnai.integrations.fhir.client import FhirClient

CHUNK = 100


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def seed(client: FhirClient, feed_dir: Path) -> dict[str, int]:
    """Load the folder's appointments.csv, visits.csv and notes.csv into the server as FHIR resources."""
    resources = mapper.resources_from_feeds(
        _rows(feed_dir / "appointments.csv"), _rows(feed_dir / "visits.csv"), _rows(feed_dir / "notes.csv")
    )
    counts: dict[str, int] = {}
    for i in range(0, len(resources), CHUNK):
        batch = resources[i:i + CHUNK]
        client.transaction(batch)
        for r in batch:
            counts[r["resourceType"]] = counts.get(r["resourceType"], 0) + 1
    return counts


def pull(client: FhirClient, out_dir: Path, since: str | None = None) -> dict[str, int]:
    """Write the three feeds from the server. `since` (YYYY-MM-DD) pulls only resources updated after it."""
    out_dir.mkdir(parents=True, exist_ok=True)
    params = {"_lastUpdated": f"gt{since}"} if since else {}
    d = mapper.Directory(
        client.search("Patient"), client.search("Practitioner"), client.search("Organization")
    )  # references are small and always pulled in full
    appts = mapper.appointments_to_rows(client.search("Appointment", params), d)
    enc_resources = list(client.search("Encounter", params))
    visits = mapper.encounters_to_rows(enc_resources, d)
    by_id = {e["id"]: (e.get("identifier") or [{}])[0].get("value", "") for e in client.search("Encounter")}
    notes = mapper.notes_to_rows(client.search("DocumentReference", params), by_id)
    mapper.write_csv(out_dir / "appointments.csv", mapper.APPT_COLUMNS, appts)
    mapper.write_csv(out_dir / "visits.csv", mapper.VISIT_COLUMNS, visits)
    mapper.write_csv(out_dir / "notes.csv", mapper.NOTE_COLUMNS, notes)
    return {"appointments": len(appts), "visits": len(visits), "notes": len(notes)}
