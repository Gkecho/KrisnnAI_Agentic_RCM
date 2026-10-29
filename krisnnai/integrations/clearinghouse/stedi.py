"""Stedi adapter: the same three calls as the mock clearinghouse client, over Stedi's raw X12 healthcare endpoints.

    check_eligibility(270) -> POST {base}/change/medicalnetwork/eligibility/v3/raw-x12   -> body.x12 (271 or 999)
    claim_status(276)      -> POST {base}/change/medicalnetwork/claimstatus/v2/raw-x12   -> body.x12 (277 or 999)
    submit_claim(837)      -> POST {base}/change/medicalnetwork/professionalclaims/v3/raw-x12-submission
                              -> body.x12 (277CA)

Shapes are from Stedi's published API reference (checked 2026-10-16). Because this repo already builds and parses X12,
the raw endpoints are the shortest path: nothing is translated to or from Stedi's JSON models.

Safety:
  * the API key is read from an environment variable (default STEDI_API_KEY) and never logged;
  * the client refuses non-local URLs unless KRISNNAI_ALLOW_REAL_ENDPOINTS=1 (the same guard as the mock client);
  * claim submission needs KRISNNAI_ALLOW_STEDI_SUBMIT=1 AND the caller to confirm it is a TEST-mode key, because a
    production key would send a real claim to a real payer;
  * every JSON response carries `meta.applicationMode`; a production mode on any response stops the client.
"""

from __future__ import annotations

import os
import re
import uuid

import httpx

from krisnnai.integrations.clearinghouse.client import check_endpoint

BASE = "https://healthcare.us.stedi.com/2024-04-01"
KEY_ENV = "STEDI_API_KEY"
ELIGIBILITY = "/change/medicalnetwork/eligibility/v3/raw-x12"
CLAIM_STATUS = "/change/medicalnetwork/claimstatus/v2/raw-x12"
CLAIMS = "/change/medicalnetwork/professionalclaims/v3/raw-x12-submission"
SUBMIT_ENV = "KRISNNAI_ALLOW_STEDI_SUBMIT"
PRODUCTION_ENV = "KRISNNAI_ALLOW_STEDI_PRODUCTION"


class StediError(Exception):
    """Stedi answered with an error status or a body the caller cannot use."""


class ProductionKeyRefused(StediError):
    """A response says the key is in production mode and production use was not explicitly allowed."""


class StediClient:
    def __init__(self, key_env: str = KEY_ENV, base_url: str = BASE, http: httpx.Client | None = None,
                 auth_style: str | None = None, timeout: float = 60):  # fmt: skip
        check_endpoint(base_url)
        key = os.environ.get(key_env, "")
        if not key:
            raise SystemExit(f"set the environment variable {key_env} to a Stedi TEST-mode API key")
        style = (auth_style or os.environ.get("KRISNNAI_STEDI_AUTH_STYLE", "raw")).lower()
        self.base_url = base_url.rstrip("/")
        self._http = http or httpx.Client(timeout=timeout)
        # Stedi's reference shows the bare key; the older "Key <key>" form is still accepted
        self._headers = {"Authorization": f"Key {key}" if style == "key" else key, "Content-Type": "application/json"}
        self.last_mode: str | None = None
        # Stedi's own test keys carry the "test_" prefix. Error responses to them (e.g. AAA 43) still report
        # applicationMode "production" (seen 2026-10-16), so for these keys the mode field is not a reliable signal.
        self._test_key = key.startswith("test_")

    def close(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------------------------------ plumbing
    def _post(self, path: str, x12: str, extra: dict | None = None, headers: dict | None = None) -> dict:
        r = self._http.post(self.base_url + path, json={"x12": x12, **(extra or {})},
                            headers={**self._headers, **(headers or {})})  # fmt: skip
        try:
            body = r.json()
        except ValueError:
            body = {}
        if r.status_code >= 400:
            detail = "; ".join(e.get("description", "") for e in body.get("errors", []))
            msg = body.get("message") or detail or r.text[:200]
            raise StediError(f"Stedi returned {r.status_code}: {msg}")
        mode = str((body.get("meta") or {}).get("applicationMode", "")).lower() or None
        self.last_mode = mode or self.last_mode
        if mode and mode != "test" and not self._test_key and os.environ.get(PRODUCTION_ENV) != "1":
            raise ProductionKeyRefused(
                f"the key is in {mode} mode; use a test-mode key or set {PRODUCTION_ENV}=1 deliberately"
            )
        return body

    @staticmethod
    def _x12(body: dict, what: str) -> str:
        x12 = body.get("x12")
        if not x12:
            errs = body.get("errors") or body.get("errorResponse") or body.get("status")
            raise StediError(f"{what}: Stedi returned no X12 ({errs})")
        return x12

    # ------------------------------------------------------------------- the ClearinghouseClient interface
    def check_eligibility(self, x12_270: str) -> str:
        return self._x12(self._post(ELIGIBILITY, x12_270), "eligibility")

    def claim_status(self, x12_276: str) -> str:
        return self._x12(self._post(CLAIM_STATUS, x12_276), "claim status")

    def submit_claim(self, x12_837: str, confirm_test_key: bool = False) -> dict:
        """Returns {"999": "", "277CA": <x12>, "results": [{claim, ok, reason}]} like the mock client."""
        if os.environ.get(SUBMIT_ENV) != "1":
            raise StediError(f"claim submission is off; set {SUBMIT_ENV}=1 and use a TEST-mode key")
        if not confirm_test_key:
            raise StediError("pass confirm_test_key=True only when the key is a Stedi test-mode key")
        body = self._post(CLAIMS, x12_837, headers={"Idempotency-Key": str(uuid.uuid4())})
        ok = str(body.get("status", "")).upper() == "SUCCESS" and not body.get("errors")
        reason = "accepted by the clearinghouse" if ok else "; ".join(
            e.get("description", "") for e in body.get("errors", [])
        ) or f"status {body.get('status')}"
        claims = re.findall(r"CLM\*([^*~]+)\*", x12_837) or [""]
        return {"999": "", "277CA": body.get("x12", ""),
                "results": [{"claim": c, "ok": ok, "reason": reason} for c in claims]}  # fmt: skip
