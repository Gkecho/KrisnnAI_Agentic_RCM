"""A small FHIR R4 REST client: capability check, paged search, incremental pull, transaction bundles.

Read-only toward any server by default. Writing (seeding) is allowed only to a local server: the same local-only guard
as the clearinghouse client, so this never pushes synthetic data to someone else's EMR.
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx

from krisnai.integrations.clearinghouse.client import check_endpoint

JSON = "application/fhir+json"


class FhirClient:
    def __init__(self, base_url: str, http: httpx.Client | None = None, token: str | None = None, timeout: float = 60):
        check_endpoint(base_url)
        self.base_url = base_url.rstrip("/")
        self._http = http or httpx.Client(base_url=self.base_url, timeout=timeout)
        self._http.headers.update({"Accept": JSON})
        if token:
            self._http.headers["Authorization"] = f"Bearer {token}"

    def close(self) -> None:
        self._http.close()

    def capability(self) -> dict:
        return self._http.get("/metadata").raise_for_status().json()

    def supports(self, resource_type: str) -> bool:
        cap = self.capability()
        return any(r.get("type") == resource_type for rest in cap.get("rest", []) for r in rest.get("resource", []))

    def search(self, resource_type: str, params: dict | None = None, page_size: int = 100) -> Iterator[dict]:
        """Every resource of a type, following the bundle's `next` links. `_lastUpdated=gt<date>` gives an
        incremental pull."""
        q = {"_count": page_size, **(params or {})}
        r = self._http.get(f"/{resource_type}", params=q).raise_for_status().json()
        while True:
            for entry in r.get("entry", []):
                res = entry.get("resource")
                if res and res.get("resourceType") == resource_type:
                    yield res
            nxt = next((link["url"] for link in r.get("link", []) if link.get("relation") == "next"), None)
            if not nxt:
                return
            r = self._http.get(nxt).raise_for_status().json()

    def transaction(self, entries: list[dict]) -> dict:
        """POST a transaction bundle of PUT entries. Local servers only (the base URL was checked at construction)."""
        bundle = {
            "resourceType": "Bundle", "type": "transaction",
            "entry": [
                {"resource": res, "request": {"method": "PUT", "url": f"{res['resourceType']}/{res['id']}"}}
                for res in entries
            ],
        }  # fmt: skip
        return self._http.post("/", json=bundle, headers={"Content-Type": JSON}).raise_for_status().json()
