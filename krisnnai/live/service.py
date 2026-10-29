# ruff: noqa: E501
"""A small local service so the product preview can run ONE typed-in visit through the whole workflow and show it live.

Give it a visit transcript. It runs the same chain as `krisnnai live run` for that one visit: booking and eligibility, the
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
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from krisnnai.live.emr import EmrPort
from krisnnai.live.export import trace_run
from krisnnai.live.stream import StreamConfig, run_stream
from krisnnai.live.transcripts import Visit, generate

MAX_TRANSCRIPT = 20_000
MAX_BATCH = 25
MAX_BATCH_CHARS = 200_000
_NONE = {"pend_rate": 0.0, "deny_rate": 0.0, "deviation_rate": 0.0}  # every mode sets all three: "pays" must really pay
PAYER_MODES = {
    "random": {},  # nothing forced: each visit gets its own payer (by market share) and its outcome from what the claim contains
    "pays": dict(_NONE),
    "denies": {**_NONE, "deny_rate": 1.0},
    "breaks_rules": {**_NONE, "deviation_rate": 1.0},
    "pends": {**_NONE, "pend_rate": 1.0},
}
PAYER_LABEL = {"random": "Random (recommended)", "pays": "Pays normally", "denies": "Denies it (an ordinary denial)", "breaks_rules": "Breaks its own published rules", "pends": "Asks for records first, then pays"}
LOCAL = {"127.0.0.1", "::1", "localhost", "testclient"}
ORIGINS = ["http://127.0.0.1:8767", "http://localhost:8767"]


class BatchItem(BaseModel):
    transcript: str
    signed: bool = True
    lapsed: bool = False
    label: str = ""


class BatchRequest(BaseModel):
    items: list[BatchItem]
    payer: str = "random"
    emr: str = "fake"


class RunRequest(BaseModel):
    transcript: str
    signed: bool = True
    payer: str = "random"
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
    app = FastAPI(title="KrisnnAI live demo service", docs_url=None, redoc_url=None, openapi_url=None)
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
                "busy": any(r["status"] == "running" for r in runs.values()), "max_transcript": MAX_TRANSCRIPT, "max_batch": MAX_BATCH}  # fmt: skip

    @app.get("/api/wide")
    def get_wide(n: int = 25, seed: int = 7) -> list[dict]:
        """Varied visits from the wide generator (the whole catalog, many kinds of problem), labelled with what each one tests."""
        from krisnnai.live.catalog import condition_by_icd
        from krisnnai.live.transcripts import generate_wide

        out = []
        for v in generate_wide(seed, max(1, min(n, MAX_BATCH)), date(2026, 10, 24)):
            x = v.expected
            c = condition_by_icd(x.dx)
            tests = list(x.problems) + list(x.pressure) + (["coverage lapsed"] if x.lapsed else []) + (["other insurance first"] if x.other_primary else [])
            out.append({"label": (c.name if c else x.dx) + (f" [{', '.join(t.replace('_', ' ') for t in tests[:3])}]" if tests else ""),
                        "text": v.text, "signed": v.signed, "lapsed": bool(x.lapsed), "tests": tests})  # fmt: skip
        return out

    @app.get("/api/samples")
    def get_samples() -> list[dict]:
        return samples()

    def _work(rid: str, visits: list[Visit], payer: str, emr: str, lapsed_ids: tuple[int, ...], all_lapsed: bool) -> None:
        r = runs[rid]
        try:
            h = int(hashlib.sha256("".join(v.text for v in visits).encode()).hexdigest(), 16)
            cfg = StreamConfig(count=len(visits), seed=h % 1000, start=date(2026, 10, 21), per_day=5, engine=engine, bots=engine, serve=serve_ports,
                               early_stop=True, sample_rate=0.0, tag=rid, inactive_rate=1.0 if all_lapsed else 0.0, lapsed_ids=lapsed_ids, settle_days=3, payers="network", replies=True, reject_rate=0.05, **PAYER_MODES[payer])  # fmt: skip
            run_stream(r["out"], cfg, emr_factories[emr](), visits=visits, log=lambda *_: None)
            r["status"] = "done"
        except Exception as e:  # noqa: BLE001
            r["status"], r["error"] = "error", f"{type(e).__name__}: {e}"[:300]

    def _launch(visits: list[Visit], payer: str, emr: str, lapsed_ids: tuple[int, ...] = (), all_lapsed: bool = False) -> dict:
        if payer not in PAYER_MODES:
            raise HTTPException(400, f"payer must be one of {sorted(PAYER_MODES)}")
        if emr not in emr_factories:
            raise HTTPException(400, f"emr must be one of {sorted(emr_factories)}")
        with lock:
            if any(r["status"] == "running" for r in runs.values()):
                raise HTTPException(409, "a run is already going; wait for it to finish")
            rid = hashlib.sha256(f"{time.time()}{len(runs)}".encode()).hexdigest()[:6].upper()
            (work_root / "runs").mkdir(parents=True, exist_ok=True)
            runs[rid] = {"status": "running", "out": work_root / "runs" / rid, "started": time.time(), "error": ""}
            vs = [Visit(f"V{rid}{n}", f"M{rid}{n}", "typed_in", v.text, v.signed, None, date(2026, 10, 24) + timedelta(days=(n - 1) // 5)) for n, v in enumerate(visits, start=1)]
            threading.Thread(target=_work, args=(rid, vs, payer, emr, lapsed_ids, all_lapsed), daemon=True).start()
        return {"id": rid, "visits": len(visits)}

    @app.post("/api/run")
    def start(req: RunRequest) -> dict:
        if not req.transcript.strip():
            raise HTTPException(400, "give it a transcript")
        if len(req.transcript) > MAX_TRANSCRIPT:
            raise HTTPException(413, f"a transcript can be at most {MAX_TRANSCRIPT} characters")
        return _launch([Visit("v", "m", "typed_in", req.transcript, req.signed)], req.payer, req.emr, all_lapsed=req.coverage_lapsed)

    @app.post("/api/batch")
    def start_batch(req: BatchRequest) -> dict:
        if not req.items:
            raise HTTPException(400, "give it at least one transcript")
        if len(req.items) > MAX_BATCH:
            raise HTTPException(400, f"at most {MAX_BATCH} visits in one batch")
        total = 0
        for n, it in enumerate(req.items, start=1):
            if not it.transcript.strip():
                raise HTTPException(400, f"visit {n} is empty")
            if len(it.transcript) > MAX_TRANSCRIPT:
                raise HTTPException(413, f"visit {n} is longer than {MAX_TRANSCRIPT} characters")
            total += len(it.transcript)
        if total > MAX_BATCH_CHARS:
            raise HTTPException(413, f"a batch can hold at most {MAX_BATCH_CHARS} characters in all")
        visits = [Visit("v", "m", "typed_in", it.transcript, it.signed) for it in req.items]
        return _launch(visits, req.payer, req.emr, lapsed_ids=tuple(n for n, it in enumerate(req.items, start=1) if it.lapsed))

    @app.get("/api/run/{rid}")
    def status(rid: str) -> dict:
        r = runs.get(rid)
        if r is None:
            raise HTTPException(404, "no such run")
        out = r["out"]
        state = r["status"]  # read first: if it says done, the run had already finished writing when the trace below is read
        data = r.get("last") or {"claims": [], "events": [], "day": None, "ledger": None}
        if (out / "state.json").exists():
            for attempt in range(8):  # the run replaces its state file as it goes; on Windows a read at that instant is refused, so try again
                try:
                    data = r["last"] = trace_run(out)
                    break
                except (OSError, ValueError):
                    if state != "running" and attempt == 7:
                        raise
                    time.sleep(0.05 * (attempt + 1))
        return {"id": rid, "status": state, "error": r["error"], "seconds": round(time.time() - r["started"], 1), **data}

    return app
