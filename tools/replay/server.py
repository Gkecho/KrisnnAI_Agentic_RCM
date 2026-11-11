"""KrisnnAI replay server: a Run button over the loaded history, with a live feed of what the agents do.

Start:  python tools/replay/server.py        then open http://127.0.0.1:8765
Local only (127.0.0.1). Reads the history from the canonical Postgres and writes agent rows there while it runs.
KRISNNAI_REPLAY_DB=krisnnai_r2 reads R2 through the canon_compat views instead (run tools/replay/r2_compat.py once); KRISNNAI_REPLAY_PORT overrides the port (default 8765).
Writing agent rows to R2 is not enabled yet: a Run on R2 stops with an error message.
"""
import asyncio
import json
import os
import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

from engine import Replay, AGENT_TABLES, NAMES
from world import World, connect_replay, is_r2

HERE = Path(__file__).resolve().parent
app = FastAPI(title="KrisnnAI replay")
state = dict(world=None, replay=None, thread=None, last=None, status="loading", clients=set(), loop=None, db="")


def broadcast(p):
    if p.get("type") == "day":
        state["last"] = p
    if p.get("type") == "status":
        state["status"] = p["status"]
    for q in list(state["clients"]):
        state["loop"].call_soon_threadsafe(q.put_nowait, p)


@app.on_event("startup")
async def startup():
    state["loop"] = asyncio.get_running_loop()

    def load():
        state["world"] = World(log=lambda m: None)
        state["db"] = state["world"].db
        state["status"] = "idle"
        broadcast(dict(type="status", status="idle"))
    threading.Thread(target=load, daemon=True).start()


@app.get("/", response_class=HTMLResponse)
def index():
    return (HERE / "ui.html").read_text(encoding="utf-8")


@app.get("/api/state")
def get_state():
    r = state["replay"]
    return dict(status=state["status"], db=state["db"], last=state["last"], names=NAMES, tables=AGENT_TABLES)


@app.post("/api/run")
def run(body: dict):
    if state["world"] is None:
        raise HTTPException(409, "still reading the history from the database")
    if state["thread"] and state["thread"].is_alive():
        raise HTTPException(409, "a replay is already running")
    speed = float(body.get("speed", 1))
    state["last"] = None
    r = Replay(state["world"], publish=broadcast)
    state["replay"] = r
    def go():
        try:
            r.run(speed)
        except Exception as ex:                      # report it in the UI instead of hanging on "preparing"
            broadcast(dict(type="error", msg=f"replay failed: {ex}"))
            broadcast(dict(type="status", status="idle"))
    state["thread"] = threading.Thread(target=go, daemon=True)
    state["thread"].start()
    return dict(ok=True)


@app.post("/api/pause")
def pause():
    r = state["replay"]
    if r:
        r.pause_flag.set()
    return dict(ok=True)


@app.post("/api/resume")
def resume():
    r = state["replay"]
    if r:
        r.pause_flag.clear()
    return dict(ok=True)


@app.post("/api/stop")
def stop():
    r = state["replay"]
    if r:
        r.pause_flag.clear()
        r.stop_flag.set()
    return dict(ok=True)


@app.post("/api/speed")
def speed(body: dict):
    r = state["replay"]
    if r:
        r.speed = max(.1, float(body.get("speed", 1)))
    return dict(ok=True)


@app.get("/api/dbcounts")
def dbcounts():
    conn, db = connect_replay()
    cur = conn.cursor()
    out = {}
    for n in AGENT_TABLES:
        try:
            cur.execute(f'SELECT count(*) FROM {"public." if is_r2() else ""}"{n}"')     # R2: search_path is canon_compat (views only), so read the real tables by schema
            out[n] = cur.fetchone()[0]
        except Exception:                                                                   # R2 has no agent_decision_details (it is agent_decision_check)
            conn.rollback()
            out[n] = None
    conn.close()
    return dict(db=db, counts=out)


@app.get("/api/claim/{claim_id}")
def claim(claim_id: int):
    W, r = state["world"], state["replay"]
    if W is None or claim_id not in W.claim:
        raise HTTPException(404, "unknown claim")
    c = W.claim[claim_id]
    ev = [dict(date=x["event_date"].isoformat(), who="history", text=f"{x['event_type'].replace('_', ' ')} ({x['status_after']})" + (f": {x['rejection_reason']}" if x["rejection_reason"] else ""))
          for x in W.hist[claim_id]]
    ev.append(dict(date=c["submitted_date"].isoformat(), who="history", text=f"claim {c['claim_number']} submitted, ${float(c['total_charge']):,.2f}"))
    for d in W.den_by_claim.get(claim_id, []):
        ev.append(dict(date=d["denial_date"].isoformat(), who="history", text=f"denied CARC {W.carc[d['adjustment_reason_id']]['carc_code']} ${float(d['denied_amount']):,.2f}"))
    if r:
        for n in ("agent_decision", "agent_finding"):
            for x in r.S.rows[n]:
                if x["claim_id"] == claim_id:
                    ev.append(dict(date=(x["decided_at"].date() if n == "agent_decision" else x["found_date"]).isoformat(), who=f"{x['agent_code']} {NAMES[x['agent_code']]}",
                                   text=(x["reason_summary"] if n == "agent_decision" else x["summary"]) or n))
    ev.sort(key=lambda e: e["date"])
    return dict(claim=c["claim_number"], payer=W.payer[c["payer_id"]]["payer_name"], events=ev)


@app.get("/api/trace/{tid}")
def get_trace(tid: int):
    r = state["replay"]
    tr = r.traces.get(tid) if r else None
    if not tr:
        raise HTTPException(404, "no trace for that decision")
    return dict(tr, log_file=r.logf.name if r.logf else None)


@app.post("/api/trace/{tid}/run/{i}")
def run_read(tid: int, i: int):
    """Re-runs one logged read against the database (read-only, the engine's own SQL) so it can be compared with what the agent saw."""
    r = state["replay"]
    tr = r.traces.get(tid) if r else None
    if not tr or i >= len(tr["reads"]):
        raise HTTPException(404, "no such read")
    rd = tr["reads"][i]
    if not rd.get("runnable", True):
        raise HTTPException(400, "this read is computed inside the engine and has no single SQL statement")
    conn, db = connect_replay()
    try:
        conn.set_session(readonly=True)
        cur = conn.cursor()
        cur.execute("SET statement_timeout = 8000")
        cur.execute(rd["sql"], rd["params"])
        cols = [c[0] for c in cur.description]
        rows = [[(float(v) if hasattr(v, "as_tuple") else v.isoformat() if hasattr(v, "isoformat") else v) for v in row] for row in cur.fetchmany(25)]
    finally:
        conn.close()
    return dict(db=db, columns=cols, rows=rows)


def _export_fetch():
    import psycopg2.extras
    conn, db = connect_replay()
    conn.set_session(readonly=True)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def fetch(sql, params=None):
        cur.execute(sql, params)
        return [dict(x) for x in cur.fetchall()]
    return conn, fetch


@app.get("/api/export")
def export(basis: str = "service", start: str = "2025-11-01", end: str = "2026-11-02", touched: int = 1, payer: str = "", provider: str = "", practice: str = "", facility: str = "", specialty: str = ""):
    import datetime as dt
    import io
    import sys
    from fastapi.responses import StreamingResponse
    sys.path.insert(0, str(HERE.parent / "live"))
    from claim_log_export import build_workbook
    if is_r2():
        raise HTTPException(501, "the claim-log export reads canonical tables the canon_compat layer does not cover; not available on R2 yet")
    r = state["replay"]
    conn, fetch = _export_fetch()
    try:
        data, info = build_workbook(fetch, r.traces if r else {}, basis, dt.date.fromisoformat(start), dt.date.fromisoformat(end), bool(touched), label="history replay (krisnnai_canonical on AWS RDS, Singapore)", filters=dict(payer=payer, provider=provider, practice=practice, facility=facility, specialty=specialty))
    finally:
        conn.close()
    return StreamingResponse(io.BytesIO(data), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="krisnnai-claim-log-replay-{basis}-{start}-to-{end}.xlsx"'})


@app.get("/api/filters")
def filters_list():
    conn, fetch = _export_fetch()
    try:
        return dict(payers=fetch("select payer_id as id, payer_name as name from payer order by 2"),
                    providers=fetch("select provider_id as id, provider_name as name from provider where practice_id is not null order by 2"),
                    facilities=fetch("select facility_id as id, facility_name as name from facility order by 2"),
                    specialties=fetch("select specialty_id as id, specialty_name as name from specialty order by 2"),
                    practices=fetch("select practice_id as id, practice_name as name from practice order by 2"))
    finally:
        conn.close()


@app.get("/api/stream")
async def stream():
    q: asyncio.Queue = asyncio.Queue()
    state["clients"].add(q)

    async def gen():
        try:
            yield dict(data=json.dumps(dict(type="status", status=state["status"], db=state["db"])))
            if state["last"]:
                yield dict(data=json.dumps(state["last"], default=str))
            while True:
                p = await q.get()
                yield dict(data=json.dumps(p, default=str))
        finally:
            state["clients"].discard(q)
    return EventSourceResponse(gen())


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("KRISNNAI_REPLAY_PORT", "8765")), log_level="warning")
