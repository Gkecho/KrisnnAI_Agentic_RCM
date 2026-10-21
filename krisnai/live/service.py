# ruff: noqa: E501
"""A small local service so the product preview can run ONE typed-in visit through the whole workflow and show it live.

Give it a visit transcript. It runs the same chain as `krisnai live run` for that one visit: booking and eligibility, the
visit in the EMR, the transcript coder, the claim written by the EMR, the clearinghouse, the payer's decision, the engine's
agents day by day on a simulated clock, and returns the trace as it grows.

Demo only (ADR-0002), synthetic data only. It listens on this machine only, refuses requests that do not come from it, runs one
visit at a time, caps the transcript size, and uses an in-memory EMR unless it was started with `--emr openemr`.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from krisnai.live.emr import EmrPort
from krisnai.live.export import trace_run
from krisnai.live.stream import StreamConfig, run_stream
from krisnai.live.transcripts import Visit, generate

MAX_TRANSCRIPT = 20_000
PAYER_MODES = {
    "pays": {},
    "denies": {"deny_rate": 1.0},
    "breaks_rules": {"deviation_rate": 1.0},
    "pends": {"pend_rate": 1.0},
}
PAYER_LABEL = {"pays": "Pays normally", "denies": "Denies it (an ordinary denial)", "breaks_rules": "Breaks its own published rules", "pends": "Asks for records first, then pays"}
LOCAL = {"127.0.0.1", "::1", "localhost", "testclient"}
ORIGINS = ["http://127.0.0.1:8767", "http://localhost:8767"]


class RunRequest(BaseModel):
    transcript: str
    signed: bool = True
    payer: str = "pays"
    coverage_lapsed: bool = False
    emr: str = "fake"


def samples() -> list[dict]:
    """A few of the generated transcripts, one per kind, with a plain note on what each one tests."""
    note = {"missing_plan": "No plan is stated: it must go to a coder.", "two_problems": "Two unrelated problems: it must go to a coder.",
            "status_unclear": "Never says new or established: it must go to a coder.", "unsigned": "The note is not signed: it must go to a coder.",
            "thin_chronic": "A chronic follow-up documented as a minor visit: it must go to a coder."}  # fmt: skip
    out, seen = [], set()
    for v in generate(7, 50):
        key = v.expected.reason if v.expected.route == "coder" else f"clean:{v.visit_type}"
        if key in seen:
            continue
        seen.add(key)
        label = f"{v.visit_type.replace('_', ' ').capitalize()}"
        out.append({"id": v.visit_id, "label": label + (" (problem case)" if v.expected.route == "coder" else ""), "signed": v.signed, "text": v.text,
                    "note": note.get(v.expected.reason, "Complete and signed: it should be auto-accepted and billed.")})  # fmt: skip
    return out


def create_app(work_root: Path, emr_factories: dict[str, Callable[[], EmrPort]], engine: bool = True, serve_ports: bool = False) -> FastAPI:
    app = FastAPI(title="KrisnAI live demo service", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["GET", "POST"], allow_headers=["content-type"])
    runs: dict[str, dict] = {}
    lock = threading.Lock()

    @app.middleware("http")
    async def only_this_machine(request: Request, call_next):  # noqa: ANN001, ANN202
        host = request.client.host if request.client else ""
        if host not in LOCAL:
            return JSONResponse({"detail": "this demo service answers only on the machine it runs on"}, status_code=403)
        return await call_next(request)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "emr": sorted(emr_factories), "payer": [{"id": k, "label": PAYER_LABEL[k]} for k in PAYER_MODES],
                "busy": any(r["status"] == "running" for r in runs.values()), "max_transcript": MAX_TRANSCRIPT}  # fmt: skip

    @app.get("/api/samples")
    def get_samples() -> list[dict]:
        return samples()

    def _work(rid: str, req: RunRequest) -> None:
        r = runs[rid]
        try:
            h = int(hashlib.sha256(req.transcript.encode()).hexdigest(), 16)
            cfg = StreamConfig(count=1, seed=h % 1000, start=date(2026, 10, 21), per_day=1, engine=engine, bots=engine, serve=serve_ports,
                               early_stop=True, tag=rid, inactive_rate=1.0 if req.coverage_lapsed else 0.0, settle_days=3, **PAYER_MODES[req.payer])  # fmt: skip
            visit = Visit(f"V{rid}", f"M{rid}", "typed_in", req.transcript, req.signed, None, date(2026, 10, 24))
            run_stream(r["out"], cfg, emr_factories[req.emr](), visits=[visit], log=lambda *_: None)
            r["status"] = "done"
        except Exception as e:  # noqa: BLE001
            r["status"], r["error"] = "error", f"{type(e).__name__}: {e}"[:300]

    @app.post("/api/run")
    def start(req: RunRequest) -> dict:
        if not req.transcript.strip():
            raise HTTPException(400, "give it a transcript")
        if len(req.transcript) > MAX_TRANSCRIPT:
            raise HTTPException(413, f"a transcript can be at most {MAX_TRANSCRIPT} characters")
        if req.payer not in PAYER_MODES:
            raise HTTPException(400, f"payer must be one of {sorted(PAYER_MODES)}")
        if req.emr not in emr_factories:
            raise HTTPException(400, f"emr must be one of {sorted(emr_factories)}")
        with lock:
            if any(r["status"] == "running" for r in runs.values()):
                raise HTTPException(409, "a visit is already running; wait for it to finish")
            rid = hashlib.sha256(f"{time.time()}{len(runs)}".encode()).hexdigest()[:6].upper()
            (work_root / "runs").mkdir(parents=True, exist_ok=True)
            runs[rid] = {"status": "running", "out": work_root / "runs" / rid, "started": time.time(), "error": ""}
            threading.Thread(target=_work, args=(rid, req), daemon=True).start()
        return {"id": rid}

    @app.get("/api/run/{rid}")
    def status(rid: str) -> dict:
        r = runs.get(rid)
        if r is None:
            raise HTTPException(404, "no such run")
        out = r["out"]
        data = trace_run(out) if (out / "state.json").exists() else {"claims": [], "events": [], "day": None, "ledger": None}
        return {"id": rid, "status": r["status"], "error": r["error"], "seconds": round(time.time() - r["started"], 1), **data}

    return app
