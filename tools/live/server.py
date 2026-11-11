"""KrisnnAI live: a running practice, seven live agents, and you at the inbox.

Start:  python tools/live/setup_db.py   (once)      then      python tools/live/server.py      then open http://127.0.0.1:8766
Local only. Everything is synthetic; nothing is sent to any payer, clearinghouse or EHR.
"""
import asyncio
import datetime as dt
import io
import json
import re
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse

from agents_live import AGENTS, NAMES, Ctx
from claim_log_export import build_workbook
from common import DB, raw_connect
from sim import ACTIONS, Clock, Sim, START

HERE = Path(__file__).resolve().parent
app = FastAPI(title="KrisnnAI live")
S = dict(clock=None, sim=None, ctx=None, agents=[], clients=set(), loop=None, pending=[], lock=threading.Lock(), plans={}, ro=None, started=False, status="starting")


def publish(item):
    with S["lock"]:
        S["pending"].append(item)
        del S["pending"][:-4000]


def build_world():
    """(Re)creates the clock, the simulator and the seven agents on the current krisnnai_live database."""
    old_sim, old_agents = S["sim"], S["agents"]
    if old_sim:
        old_sim.stop_flag.set()
        S["clock"].pause()
        for a in old_agents:
            a.stop_flag.set()
        time.sleep(1.5)
        for a in old_agents + [old_sim]:
            try:
                a.db.close()
            except Exception:
                pass
    if S["ro"]:
        try:
            S["ro"].close()
        except Exception:
            pass
    S["clock"] = Clock(START, rate=1440.0)
    S["ctx"] = Ctx(S["clock"], publish)
    S["sim"] = Sim(S["clock"], publish)
    S["agents"] = [A(S["ctx"]) for A in AGENTS]
    S["ro"] = raw_connect("krisnnai_live")
    S["ro"].autocommit = True
    S["ro_lock"] = threading.Lock()
    S["plans"] = {}
    S["ctx"].traces.update(recover_traces())
    S["sim"].start()
    for a in S["agents"]:
        a.start()
    S["status"] = "ready"


def recover_traces():
    """After a restart (not a reset) the database still holds the earlier decisions. Their traces are in the saved log files; each is re-attached only if it still
    matches its database row (same id, agent, decision type and entity), so a trace from a world that was since reset is never attached to the wrong decision."""
    from agents_live import LOGS
    cand = {}
    for f in sorted(LOGS.glob("live-*.jsonl"))[-8:]:
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                tr = json.loads(line)
                cand[tr["id"]] = tr
            except Exception:
                pass
    if not cand:
        return {}
    cur = S["ro"].cursor()
    cur.execute("select agent_decision_id, agent_code, decision_type, entity_id from agent_decision where agent_decision_id = any(%s)", [list(cand)])
    ok = {}
    for did, agent, dtype, eid in cur.fetchall():
        tr = cand[did]
        if tr["agent"] == agent and tr["decision_type"] == dtype and tr["entity_id"] == eid:
            ok[did] = tr
    cur.close()
    return ok


def ro(sql, params=None):
    with S["ro_lock"]:
        import psycopg2.extras
        cur = S["ro"].cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()] if cur.description else []
        cur.close()
        return rows


def js(v):
    from common import jsonable
    return jsonable(v)


def clean(rows):
    return [{k: js(v) for k, v in r.items()} for r in rows]


async def broadcaster():
    while True:
        await asyncio.sleep(0.4)
        with S["lock"]:
            batch, S["pending"] = S["pending"], []
        clock = S["clock"]
        world = [b for b in batch if b.get("type") == "world"]
        agent = [b for b in batch if b.get("type") == "agent"]
        errs = [b for b in batch if b.get("type") == "error"]
        msg = dict(type="batch", sim=clock.now().isoformat(timespec="seconds"), paused=clock.paused, rate=clock.rate, world=world[-40:], world_n=len(world), agent=agent[-40:], agent_n=len(agent),
                   errors=[e["msg"][-400:] for e in errs[-3:]])
        data = json.dumps(msg, default=str)
        for q in list(S["clients"]):
            q.put_nowait(data)


@app.on_event("startup")
async def startup():
    S["loop"] = asyncio.get_running_loop()
    threading.Thread(target=build_world, daemon=True).start()
    asyncio.create_task(broadcaster())


@app.get("/", response_class=HTMLResponse)
def index():
    return (HERE / "live.html").read_text(encoding="utf-8")


@app.get("/api/state")
def state():
    if S["status"] != "ready":
        return dict(status=S["status"])
    c, sim = S["clock"], S["sim"]
    return dict(counters=dict(sim.counters), status="paused" if c.paused else "running", sim=c.now().isoformat(timespec="seconds"), rate=c.rate, mirror_enforce=sim.rules["mirror_enforce"], pending_events=len(sim.heap),
                agents={a.code: dict(name=NAMES[a.code], **a.stats) for a in S["agents"]}, actions=ACTIONS)


@app.post("/api/start")
def start():
    S["clock"].resume()
    return dict(ok=True)


@app.post("/api/pause")
def pause():
    S["clock"].pause()
    return dict(ok=True)


@app.post("/api/rate")
def rate(body: dict):
    S["clock"].set_rate(max(60.0, float(body.get("rate", 3600))))
    return dict(ok=True)


@app.post("/api/reset")
def reset():
    S["status"] = "resetting"
    S["clock"].pause()
    import subprocess
    import sys
    build = S

    def go():
        old = [S["sim"]] + S["agents"]
        for a in S["agents"]:
            a.stop_flag.set()
        S["sim"].stop_flag.set()
        time.sleep(1.5)
        for a in old:
            try:
                a.db.close()
            except Exception:
                pass
        try:
            S["ro"].close()
        except Exception:
            pass
        sys.path.insert(0, str(HERE))
        import setup_db
        setup_db.reset_live()
        S["sim"], S["agents"] = None, []
        build_world()
    threading.Thread(target=go, daemon=True).start()
    return dict(ok=True)


@app.get("/api/inbox")
def inbox(role: str):
    rows = S["sim"].inbox(role)
    return dict(role=role, tasks=[dict(clean([r])[0], actions=ACTIONS.get(r["task_type"], [])) for r in rows])


@app.get("/api/inbox_counts")
def inbox_counts():
    rows = ro("select owner_role, count(*) as n from agent_task where task_status = 'open' group by 1")
    return {r["owner_role"]: r["n"] for r in rows}


@app.post("/api/task/{task_id}/act")
def act(task_id: int, body: dict):
    r = S["sim"].act(task_id, body.get("action", ""))
    if not r.get("ok"):
        raise HTTPException(400, r.get("msg", "failed"))
    return r


@app.post("/api/chaos")
def chaos(body: dict):
    return dict(ok=True, msg=S["sim"].chaos(body.get("kind", "")))


@app.get("/api/metrics")
def metrics():
    cs = ro("select claim_status, count(*) as n from claim group by 1")
    val = ro("select value_stage, coalesce(sum(amount),0) as amt from agent_value group by 1")
    per = ro("select agent_code, count(*) as decisions from agent_decision group by 1")
    mir = ro("""select count(*) filter (where d.outcome = 'hold') as holds, count(*) filter (where d.outcome = 'hold' and exists (select 1 from denial x where x.claim_id = d.claim_id)) as held_denied
                from agent_decision d where d.agent_code = 'A5'""")[0]
    miss = ro("""select count(*) as n from denial x join claim c on c.claim_id = x.claim_id where c.source = 'live'
                 and not exists (select 1 from agent_decision d where d.agent_code = 'A5' and d.claim_id = x.claim_id and d.outcome = 'hold')""")[0]["n"]
    tasks = ro("select count(*) filter (where task_status = 'open') as open, count(*) filter (where task_status = 'done') as done, count(*) filter (where contact_channel = 'staff bot') as bot from agent_task")[0]
    df = ro("select count(*) filter (where check_result = 'pass') as answered, count(*) filter (where check_result = 'fail') as outbound from agent_decision_details where rule_code = 'DATA-FIRST'")[0]
    appr = ro("select count(*) as n from agent_approval")[0]["n"]
    wbk = {r["target_system"]: r["n"] for r in ro("select target_system, count(*) as n from agent_writeback group by 1")}
    world = ro("select (select count(*) from encounter where source = 'live') as visits, (select count(*) from claim where source = 'live') as claims, (select count(*) from denial where source = 'live') as denials")[0]
    return dict(claims={r["claim_status"]: r["n"] for r in cs}, value={r["value_stage"]: float(r["amt"]) for r in val}, decisions={r["agent_code"]: r["decisions"] for r in per},
                data_first=dict(answered=df["answered"], outbound=df["outbound"]), approvals=appr, writebacks=wbk, mirror=dict(holds=mir["holds"], held_denied=mir["held_denied"], missed=miss), tasks=tasks, world=world)


@app.get("/api/claim/{claim_id}")
def claim(claim_id: int):
    c = ro("select c.claim_number, c.claim_status, c.total_charge, p.payer_name from claim c join payer p using (payer_id) where c.claim_id = %s", [claim_id])
    if not c:
        raise HTTPException(404, "unknown claim")
    ev = [dict(date=js(r["event_ts"] or r["event_date"]), who="history", text=f"{r['event_type'].replace('_', ' ')} ({r['status_after']})" + (f": {r['rejection_reason']}" if r["rejection_reason"] else ""))
          for r in ro("select event_type, event_date, event_ts, status_after, rejection_reason from claim_status_history where claim_id = %s order by claim_status_history_id", [claim_id])]
    for r in ro("select decided_at, agent_code, reason_summary, agent_decision_id from agent_decision where claim_id = %s order by 1", [claim_id]):
        ev.append(dict(date=js(r["decided_at"]), who=f"{r['agent_code']} {NAMES.get(r['agent_code'], '')}", text=r["reason_summary"], trace=r["agent_decision_id"]))
    for r in ro("select t.completed_date, t.title, t.contact_channel from agent_task t where t.claim_id = %s and t.task_status = 'done'", [claim_id]):
        ev.append(dict(date=js(r["completed_date"]), who="person" if r["contact_channel"] != "staff bot" else "staff bot", text=f"finished: {r['title']}"))
    ev.sort(key=lambda e: e["date"] or "")
    return dict(claim=c[0]["claim_number"], status=c[0]["claim_status"], payer=c[0]["payer_name"], amount=float(c[0]["total_charge"]), events=ev)


# ------------------------------------------------------------------ traces
def plan_info(sql, params):
    """What Postgres itself says the statement touches, from EXPLAIN (VERBOSE): relations and output columns."""
    if sql in S["plans"]:
        return S["plans"][sql]
    info = dict(tables=[], columns=[], error=None)
    try:
        with S["ro_lock"]:
            cur = S["ro"].cursor()
            cur.execute("EXPLAIN (VERBOSE, FORMAT JSON) " + sql, params)
            plan = cur.fetchone()[0]
            cur.close()
        nodes, alias, cols = [], {}, set()

        def walk(n):
            if "Relation Name" in n:
                alias[n.get("Alias", n["Relation Name"])] = n["Relation Name"]
                nodes.append(n["Relation Name"])
            for o in n.get("Output", []) or []:
                for m in re.finditer(r"\b([a-z_][a-z_0-9]*)\.([a-z_][a-z_0-9]*)\b", o):
                    cols.add((m.group(1), m.group(2)))
            for k in ("Filter", "Index Cond", "Recheck Cond", "Join Filter", "Hash Cond", "Merge Cond"):
                for m in re.finditer(r"\b([a-z_][a-z_0-9]*)\.([a-z_][a-z_0-9]*)\b", str(n.get(k, ""))):
                    cols.add((m.group(1), m.group(2)))
            for ch in n.get("Plans", []) or []:
                walk(ch)
        walk(plan[0]["Plan"])
        info["tables"] = sorted(set(nodes))
        info["columns"] = sorted({f"{alias[a]}.{c}" for a, c in cols if a in alias})
    except Exception as ex:
        info["error"] = str(ex)[:160]
    S["plans"][sql] = info
    return info


@app.get("/api/trace/{tid}")
def trace(tid: int):
    tr = S["ctx"].traces.get(tid)
    if not tr:
        raise HTTPException(404, "no trace for that decision")
    out = dict(tr)
    reads = []
    for rd in tr["reads"]:
        p = plan_info(rd["sql"], rd["params"])
        reads.append(dict(rd, plan_tables=p["tables"], plan_columns=p["columns"], plan_error=p["error"]))
    out["reads"] = reads
    out["tables_read"] = sorted({t for r in reads for t in r["plan_tables"]})
    out["columns_read"] = sorted({c for r in reads for c in r["plan_columns"]})
    out["log_file"] = S["ctx"].logf.name
    return out


@app.post("/api/trace/{tid}/run/{i}")
def rerun(tid: int, i: int):
    tr = S["ctx"].traces.get(tid)
    if not tr or i >= len(tr["reads"]):
        raise HTTPException(404, "no such read")
    rd = tr["reads"][i]
    t0 = time.perf_counter()
    rows = ro(rd["sql"], rd["params"])
    return dict(rows=clean(rows[:6]), n=len(rows), ms=round((time.perf_counter() - t0) * 1000, 2), note="re-run now: data may have moved on since the agent looked")


FILTER_SQL = dict(payers="select payer_id as id, payer_name as name from payer order by 2",
                  providers="select provider_id as id, provider_name as name from provider where practice_id is not null order by 2",
                  facilities="select facility_id as id, facility_name as name from facility order by 2",
                  specialties="select specialty_id as id, specialty_name as name from specialty order by 2",
                  practices="select practice_id as id, practice_name as name from practice order by 2")


@app.get("/api/filters")
def filters_list():
    return {k: ro(sql) for k, sql in FILTER_SQL.items()}


def _period(start, end):
    sim = S["clock"].now().date()
    s = dt.date.fromisoformat(start) if start else sim - dt.timedelta(days=45)
    e = dt.date.fromisoformat(end) if end else sim + dt.timedelta(days=60)
    return s, e


def _flt(payer, provider, practice, facility, specialty):
    return dict(payer=payer, provider=provider, practice=practice, facility=facility, specialty=specialty)


@app.get("/api/export_preview")
def export_preview(basis: str = "service", start: str = "", end: str = "", touched: int = 1, payer: str = "", provider: str = "", practice: str = "", facility: str = "", specialty: str = ""):
    from claim_log_export import scope_sql
    s, e = _period(start, end)
    scope, sp = scope_sql(basis, s, e, bool(touched), _flt(payer, provider, practice, facility, specialty))
    n = ro(f"select count(*) as n from claim c where {scope}", sp)[0]["n"]
    return dict(claims=n, start=s.isoformat(), end=e.isoformat())


@app.get("/api/export")
def export(basis: str = "service", start: str = "", end: str = "", touched: int = 1, payer: str = "", provider: str = "", practice: str = "", facility: str = "", specialty: str = ""):
    s, e = _period(start, end)
    data, info = build_workbook(ro, S["ctx"].traces, basis, s, e, bool(touched), plan=plan_info, label="live simulation (krisnnai_live, local Postgres)", filters=_flt(payer, provider, practice, facility, specialty))
    name = f"krisnnai-claim-log-{basis}-{s}-to-{e}.xlsx"
    return StreamingResponse(io.BytesIO(data), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="{name}"', "X-Export-Info": json.dumps(info)})


@app.get("/api/performance")
def performance(dim: str = "payer", basis: str = "service", start: str = "", end: str = "", touched: int = 1, payer: str = "", provider: str = "", practice: str = "", facility: str = "", specialty: str = ""):
    from claim_log_export import performance_view
    s, e = _period(start, end)
    r = performance_view(ro, basis, s, e, bool(touched), _flt(payer, provider, practice, facility, specialty), dim)
    r["rows"] = [[(float(v) if hasattr(v, "as_tuple") else v) for v in row] for row in r["rows"]]
    return r


@app.get("/flow", response_class=HTMLResponse)
def flow():
    return (HERE / "static" / "agent-bot-workflow.html").read_text(encoding="utf-8")


@app.get("/api/claim_lookup")
def claim_lookup(q: str):
    r = ro("select claim_id, claim_number from claim where claim_number ilike %s order by claim_id desc limit 8", [f"%{q.strip()}%"])
    return r


@app.get("/api/stream")
async def stream():
    q: asyncio.Queue = asyncio.Queue()
    S["clients"].add(q)

    async def gen():
        try:
            while True:
                yield dict(data=await q.get())
        finally:
            S["clients"].discard(q)
    return EventSourceResponse(gen())


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8766, log_level="warning")
