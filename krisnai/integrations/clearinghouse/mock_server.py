"""A local stand-in for a clearinghouse: X12 in, X12 out, bearer-token protected. Not a payer, not a real service.

    POST /v1/eligibility   270 -> 271
    POST /v1/claim-status  276 -> 277
    POST /v1/claims        837 -> {"999": ..., "277CA": ..., "results": [...]}
    GET  /v1/health

Bodies are plain X12 text. The token comes from the environment (KRISNAI_MOCK_CH_TOKEN) or the caller.
"""

from __future__ import annotations

import os
from datetime import date

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from krisnai.integrations.clearinghouse.mock_world import (
    MockWorld,
    parse_inbound_270,
    parse_inbound_276,
)
from krisnai.integrations.clearinghouse.x12_out import write_277
from krisnai.ingest.x12 import X12Error

DEFAULT_TOKEN_ENV = "KRISNAI_MOCK_CH_TOKEN"


def create_app(world: MockWorld, token: str | None = None, today: date | None = None) -> FastAPI:
    token = token or os.environ.get(DEFAULT_TOKEN_ENV, "")
    if not token:
        raise ValueError(f"set {DEFAULT_TOKEN_ENV} (or pass a token): the mock service is never open")
    app = FastAPI(title="KrisnAI mock clearinghouse", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.log = []  # (endpoint, ok, detail) for tests and the Stage 1 report

    def _auth(authorization: str | None) -> None:
        if authorization != f"Bearer {token}":
            raise HTTPException(status_code=401, detail="bad or missing bearer token")

    def _when() -> date:
        return today or date.today()

    @app.get("/v1/health")
    async def health() -> dict:
        return {"ok": True, "service": "krisnai-mock-clearinghouse", "claims": len(world.extract.claims)}

    @app.post("/v1/eligibility", response_class=PlainTextResponse)
    async def eligibility(request: Request, authorization: str | None = Header(default=None)) -> str:
        _auth(authorization)
        text = (await request.body()).decode("utf-8", "ignore")
        try:
            subs = parse_inbound_270(text)
        except X12Error as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        s = subs[0]
        ans = world.eligibility(s["payer_id"], s["member"], s["dos"], s["dependent"])
        app.state.log.append(("eligibility", ans.found, s["ref"]))
        if not ans.found:
            return world.write_271_not_found(s["payer_id"], s["payer_name"], s["member"], s["ref"], _when())
        return world.write_271(s["payer_id"], s["payer_name"], s["member"], s["last"], s["first"], s["dos"],
                               s["ref"], ans, _when(), s["dependent"])  # fmt: skip

    @app.post("/v1/claim-status", response_class=PlainTextResponse)
    async def claim_status(request: Request, authorization: str | None = Header(default=None)) -> str:
        _auth(authorization)
        text = (await request.body()).decode("utf-8", "ignore")
        try:
            subs = parse_inbound_276(text)
        except X12Error as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        s = subs[0]
        category, code, paid, payer_no, claim = world.claim_state(s["claim"])
        app.state.log.append(("claim-status", category, s["claim"]))
        return write_277(
            s["payer_id"], claim.payer_name if claim else "", s["claim"], s["member"], category, code,
            claim.billed if claim else 0, paid, payer_no or s["payer_claim_no"], claim.dos if claim else None,
            world.next_ctrl(), _when(),
        )  # fmt: skip

    @app.post("/v1/claims")
    async def claims(request: Request, authorization: str | None = Header(default=None)) -> JSONResponse:
        _auth(authorization)
        text = (await request.body()).decode("utf-8", "ignore")
        try:
            c999, c277, results = world.accept_claims(text, _when())
        except X12Error as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        app.state.log.append(("claims", all(r["ok"] for r in results), ",".join(r["claim"] for r in results)))
        return JSONResponse({"999": c999, "277CA": c277, "results": results})

    return app
