"""Persist Replay results into the agent_* tables of krisnnai_r2.

What goes in: the final-state rows a Replay run produced (the engine keeps them in `Replay.S.rows[table]`; rows are updated in place as tasks
complete, findings resolve and forecasts get their actuals, so the end state is what is written) and, optionally, the decision traces
(`Replay.traces`). See docs/replay_r2_mapping.md for the field-by-field mapping.

What it does
- translate(): pure. Engine tables and columns -> R2 agent_* tables and columns, allowed values, typed links, salted hashes. No database.
- assign_ids(): pure. Gives new R2 keys and skips rows that are already there (natural keys), so a rerun adds nothing.
- persist(): the only part that touches the database. Writes ONLY agent_* tables, tenant-filtered, source = 'replay'.
- reset(): deletes only this tenant's rows with this source from the agent_* tables.

Rules kept: money is Decimal; every decision keeps its rule checks (hard rule 5); reruns are idempotent (7); every statement filters tenant_id (8);
dates stay dates (10). The connection is never committed here; the CLI commits, tests roll back.

CLI
    python tools/replay/r2_persist.py --input run.json            # write (reruns add nothing)
    python tools/replay/r2_persist.py --input run.json --reset    # delete this tenant's 'replay' rows from agent_*, then write
    python tools/replay/r2_persist.py --reset-only                # just delete
    python tools/replay/r2_persist.py --input run.json --dry-run  # translate and count, write nothing
`run.json` is produced by dump_results(); from Python call persist_run(conn, replay) directly.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys
from collections import defaultdict
from decimal import Decimal

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "synthea"))
import r2load  # noqa: E402  (connect(), Loader, TBL, h)

DB = "krisnnai_r2"
SOURCE = "replay"
TENANT = 1
D = Decimal

# Insert order (parents first). Delete order is the reverse.
TABLES = ["agent_run", "agent_decision", "agent_decision_check", "agent_finding", "agent_task", "agent_approval", "agent_writeback", "agent_value", "agent_forecast"]
ENGINE_TABLE = {"agent_decision_check": "agent_decision_details"}      # the engine's name for the check table
RENAME = {                                                              # engine column -> R2 column, per R2 table
    "agent_task": {"assigned_to": "assigned_to_staff_id"},
    "agent_approval": {"approved_by": "approved_by_staff_id"},
}
PK = {t: t + "_id" for t in TABLES}
FK = {                                                                  # column -> parent table (ids are remapped to new R2 keys)
    "agent_decision": {"agent_run_id": "agent_run", "supersedes_decision_id": "agent_decision"},
    "agent_decision_check": {"agent_decision_id": "agent_decision"},
    "agent_finding": {"agent_run_id": "agent_run", "agent_decision_id": "agent_decision", "previous_agent_finding_id": "agent_finding"},
    "agent_task": {"agent_decision_id": "agent_decision", "agent_finding_id": "agent_finding", "previous_agent_task_id": "agent_task"},
    "agent_approval": {"agent_decision_id": "agent_decision", "agent_task_id": "agent_task"},
    "agent_writeback": {"agent_decision_id": "agent_decision", "agent_approval_id": "agent_approval", "previous_agent_writeback_id": "agent_writeback"},
    "agent_value": {"agent_finding_id": "agent_finding", "agent_decision_id": "agent_decision"},
    "agent_forecast": {"previous_agent_forecast_id": "agent_forecast"},
    "agent_run": {},
}
PREV = {"agent_finding": "previous_agent_finding_id", "agent_task": "previous_agent_task_id", "agent_writeback": "previous_agent_writeback_id", "agent_forecast": "previous_agent_forecast_id"}

# typed links to real R2 tables: column -> (table, key column). Checked against the database before writing.
LINKS = {"practice_id": "practice", "patient_id": "patient", "payer_id": "payer", "provider_id": "provider", "specialty_id": "specialty", "appointment_id": "appointment",
         "encounter_id": "encounter", "bill_id": "bill", "claim_id": "claim", "denial_id": "denial", "authorization_id": "authorization", "cpt_code_id": "cpt_code",
         "ledger_entry_id": "ledger_entry", "assigned_to_staff_id": "staff", "approved_by_staff_id": "staff"}
ENTITY_LINK = {"claim": "claim_id", "denial": "denial_id", "appointment": "appointment_id", "encounter": "encounter_id", "bill": "bill_id", "authorization": "authorization_id",
               "patient": "patient_id", "payer": "payer_id", "provider": "provider_id", "cpt_code": "cpt_code_id"}

# ------------------------------------------------------------------ value maps (engine value -> R2 allowed value)
OUTCOME = {"flag": "flag", "route": "flag", "hold": "hold", "clear": "proceed", "release": "proceed", "match": "proceed", "suggest": "propose_change", "proposed": "propose_change",
           "proceed": "proceed", "propose_change": "propose_change", "no_action": "no_action", "needs_human": "needs_human"}
HUMAN_OUTCOME = {"accepted": "accepted", "edited": "changed", "changed": "changed", "rejected": "rejected", "ignored": "ignored"}
FINDING_STATUS = {"open": "open", "resolved": "fixed", "confirmed": "accepted", "unconfirmed": "dismissed", "accepted": "accepted", "fixed": "fixed", "dismissed": "dismissed", "expired": "expired"}
TASK_STATUS = {"open": "open", "done": "done", "returned": "done", "in_progress": "in_progress", "cancelled": "cancelled", "blocked": "blocked"}
TASK_OUTCOME = {"resolved": "done", "returned": "returned", "done": "done"}        # 'returned' has no R2 code: see the mapping doc
PRIORITY = {"hi": "high", "md": "normal", "lo": "low", "high": "high", "normal": "normal", "low": "low"}
RUN_STATUS = {"ok": "succeeded"}
APPROVAL_TYPE = {"code_change": "code_change", "resubmit": "send_to_payer", "appeal_send": "send_to_payer", "dispute_send": "send_to_payer", "rule_activation": "setting_change"}
SEND_STATUS = {"suppressed": "not_sent_shadow"}
TARGET = {"PM": "pm", "portal": "payer_portal"}
WB_TYPE = {"task_note": "note", "appeal_submit": "appeal_packet", "dispute_submit": "appeal_packet"}
FORECAST_TYPE = {"weekly_cash": "cash_week"}
ENTITY_TYPE = {"claim_detail": "claim_line", "payer_cpt": "cpt_code", "payer_rule": "payer", "ar": "ar_snapshot"}
VALUE_STAGE = {"detected": "detected", "confirmed": "recovered", "pending": "recovered"}   # engine 'pending' = cash seen, remit not posted: recovered + is_estimate

ALLOWED_CHECK = {("agent_run", "run_mode"): {"shadow", "assisted", "live"},
                 ("agent_decision", "outcome"): {"proceed", "hold", "flag", "propose_change", "no_action", "needs_human"},
                 ("agent_decision", "human_outcome"): {"accepted", "changed", "rejected", "ignored"},
                 ("agent_finding", "finding_status"): {"open", "accepted", "fixed", "dismissed", "expired"},
                 ("agent_task", "task_status"): {"open", "in_progress", "done", "cancelled", "blocked"},
                 ("agent_approval", "approval_status"): {"approved", "rejected", "expired"},
                 ("agent_writeback", "send_status"): {"not_sent_shadow", "queued", "sent", "acknowledged", "failed"},
                 ("agent_decision_check", "check_result"): {"pass", "fail", "warn", "skipped", "unknown"}}
# reason_summary and summary are scanned at write time (R2: "a value that fails is refused")
PHI = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9,}\b|[\w.+-]+@[\w-]+\.[\w.]+|\b(19|20)\d{2}-\d{2}-\d{2}\b.*\bDOB\b|\bDOB\b|\bMRN\b|\bSSN\b", re.I)


class PersistError(Exception):
    pass


# ------------------------------------------------------------------ helpers
def _hash(v, kind, text):
    if v is None:
        return "\\x" + r2load.hashlib.sha256(f"{r2load.SALT}|{kind}|{text}".encode()).hexdigest()
    if isinstance(v, (bytes, bytearray, memoryview)):
        return "\\x" + bytes(v).hex()
    return v


def _dec(v):
    if v is None or isinstance(v, Decimal):
        return v
    if isinstance(v, float):
        raise PersistError("money must be Decimal, got float")
    return D(str(v))


def _cols(table):
    return [c["name"] for c in r2load.TBL[table]["cols"]]


def _engine_rows(results, table):
    rows = results.get("rows", results)
    got = rows.get(table)
    if got is None and table in ENGINE_TABLE:
        got = rows.get(ENGINE_TABLE[table])
    return list(got or [])


def _scan(table, row, col):
    v = row.get(col)
    if v and PHI.search(str(v)):
        raise PersistError(f"{table}.{col} looks like it holds an identifier and is refused: {str(v)[:60]!r}")


def _norm(v):
    if v is None:
        return ""
    if isinstance(v, (dt.datetime, dt.date, Decimal)):
        return str(v)
    return v


# ------------------------------------------------------------------ 1. translate (pure)
def translate(results, tenant_id=TENANT, source=SOURCE, loaded_at=None, load_batch_id=None, traces=None):
    """Engine rows -> {R2 table: [row dicts with R2 columns]}. Ids are still the engine's local ids. Rows are sorted by local id.

    `results` is {"rows": {engine table: [rows]}, "traces": {local decision id: trace}} (or just the rows dict).
    """
    loaded_at = (loaded_at or dt.datetime.now()).replace(microsecond=0)
    traces = traces if traces is not None else (results.get("traces") if isinstance(results.get("rows"), dict) else None) or {}
    out = {}
    dec_pk = "agent_decision_id"
    # lookups the child tables need from the decision row
    dec_rows = {r[dec_pk]: r for r in _engine_rows(results, "agent_decision")}
    fnd_status0 = {r["agent_finding_id"]: r.get("finding_status") for r in _engine_rows(results, "agent_finding")}
    for t in TABLES:
        cols = set(_cols(t))
        rows = []
        for n, src in enumerate(sorted(_engine_rows(results, t), key=lambda r: (r.get(PK[t]) is None, r.get(PK[t]) or 0)), 1):
            ren = RENAME.get(t, {})
            r = {ren.get(k, k): v for k, v in src.items()}
            r = {k: v for k, v in r.items() if k in cols}
            r.setdefault(PK[t], n)
            r["tenant_id"] = tenant_id
            r["source"] = source
            r["loaded_at"] = loaded_at
            if r.get(PK[t]) is None:
                r[PK[t]] = n
            _row_rules(t, r, src, dec_rows, traces, fnd_status0, load_batch_id)
            for c in cols:                                  # every R2 column present, so rows share one COPY column list
                r.setdefault(c, None)
            for c in ("is_current",):
                if c in cols and r.get(c) is None:
                    r[c] = True
            if "version" in cols and r.get("version") is None:
                r["version"] = 1
            for c in ("amount_at_stake", "amount_at_risk", "amount_recovered", "amount", "signed_amount", "incremental_amount", "amount_approved", "expected_amount", "low_amount",
                      "high_amount", "actual_amount", "value_difference", "predicted_allowed_amount", "predicted_patient_responsibility", "confidence", "predicted_probability", "probability",
                      "attribution_share", "interval_level", "cost_amount"):
                if c in cols:
                    r[c] = _dec(r.get(c))
            rows.append(r)
        out[t] = rows
    _chain_flags(out)
    return out


def _row_rules(t, r, src, dec_rows, traces, fnd_status0, load_batch_id):
    if t == "agent_run":
        r["run_status"] = RUN_STATUS.get(r.get("run_status"), r.get("run_status"))
        r["trigger_type"] = (r.get("trigger_type") or "schedule").lower()
        cv = r.get("code_version")
        if load_batch_id is not None:                       # the agent tables have no load_batch_id column: the lineage rides in code_version
            r["code_version"] = f"{cv or 'replay'}|lb{load_batch_id}"[:30]
        if r.get("ended_at") is None:
            r["ended_at"] = r.get("started_at")
    elif t == "agent_decision":
        o = r.get("outcome")
        r["outcome"] = OUTCOME.get(o, "needs_human")
        if r.get("human_outcome") is not None:
            r["human_outcome"] = HUMAN_OUTCOME.get(r["human_outcome"], "ignored")
        et = r.get("entity_type")
        if et == "payer_rule":                              # A9's proposed rule is a payer_rule row (not an agent_* table): point at the payer instead
            r["entity_id"] = r.get("payer_id") or r["entity_id"]
        r["entity_type"] = ENTITY_TYPE.get(et, et)
        r["input_hash"] = _hash(r.get("input_hash"), "input", f"{r.get('agent_code')}{et}{src.get('entity_id')}{r.get('decided_at')}")
        _scan(t, r, "reason_summary")
        _typed(t, r)
    elif t == "agent_decision_check":
        d = dec_rows.get(src.get("agent_decision_id"), {})
        tr = traces.get(src.get("agent_decision_id")) or {}
        r["payer_rule_id"] = None                           # payer_rule rows are not written by this layer
        if tr.get("tables_read"):
            r["evidence_ref"] = ("reads:" + ",".join(tr["tables_read"]))[:100]
        if src.get("rule_source") == "learned" and src.get("payer_rule_id") is not None:
            r["evidence_ref"] = (r.get("evidence_ref") or "")[:80] + f" learned_rule#{src['payer_rule_id']}"[:20]
            r["evidence_ref"] = r["evidence_ref"][:100]
        if d.get("entity_type") and not r.get("input_table"):
            r["input_table"] = ENTITY_TYPE.get(d["entity_type"], d["entity_type"])
        for c in ("observed_value", "expected_value"):
            if r.get(c) is not None:
                r[c] = str(r[c])[:100]
    elif t == "agent_finding":
        st0 = r.get("finding_status")
        r["finding_status"] = FINDING_STATUS.get(st0, "open")
        et = r.get("entity_type")
        if et == "payer_rule":
            r["entity_id"] = r.get("payer_id") or r["entity_id"]
        r["entity_type"] = ENTITY_TYPE.get(et, et)
        r["finding_hash"] = _hash(r.get("finding_hash"), "finding", f"{r.get('agent_code')}{et}{src.get('entity_id')}{r.get('finding_type')}")
        if r.get("resolution") == "recovered":
            r["resolution"] = "fixed"
        _scan(t, r, "summary")
        _typed(t, r)
    elif t == "agent_task":
        r["task_status"] = TASK_STATUS.get(r.get("task_status"), "open")
        if r.get("outcome") is not None:
            r["outcome"] = TASK_OUTCOME.get(r["outcome"], r["outcome"])
        r["priority"] = PRIORITY.get(r.get("priority"), r.get("priority"))
        et = r.get("entity_type")
        r["entity_type"] = ENTITY_TYPE.get(et, et)
        if et == "payer_rule":
            r["entity_id"] = r.get("payer_id") or r["entity_id"]
        _scan(t, r, "title")
        _typed(t, r)
    elif t == "agent_approval":
        r["approval_type"] = APPROVAL_TYPE.get(r.get("approval_type"), r.get("approval_type"))
        et = r.get("entity_type")
        r["entity_type"] = ENTITY_TYPE.get(et, et)
        if r["approval_status"] == "approved" and r.get("approved_by_staff_id") is None:
            raise PersistError("an approved agent_approval needs approved_by_staff_id (R2 CHECK)")
        if r["approval_status"] != "approved":
            r["approved_by_staff_id"] = None
    elif t == "agent_writeback":
        r["target_system"] = TARGET.get(r.get("target_system"), r.get("target_system"))
        r["writeback_type"] = WB_TYPE.get(r.get("writeback_type"), r.get("writeback_type"))
        r["send_status"] = SEND_STATUS.get(r.get("send_status"), r.get("send_status"))
        r["payload_hash"] = _hash(r.get("payload_hash"), "payload", src.get("agent_decision_id"))
        et = r.get("entity_type")
        r["entity_type"] = ENTITY_TYPE.get(et, et)
    elif t == "agent_value":
        stage0 = r.get("value_stage")
        r["value_stage"] = VALUE_STAGE.get(stage0, stage0)
        amt = _dec(r.get("amount"))
        if amt is not None and amt < 0:
            raise PersistError("agent_value.amount is never negative (reversals are separate rows)")
        r["signed_amount"] = amt
        if stage0 == "pending":
            r["is_estimate"] = True
            r["ledger_entry_id"] = None
        else:
            r["ledger_entry_id"] = src.get("transaction_id") if stage0 == "confirmed" else None
            r["is_estimate"] = bool(r.get("is_estimate"))
        et = r.get("entity_type")
        r["entity_type"] = ENTITY_TYPE.get(et, et)
        _typed(t, r)
    elif t == "agent_forecast":
        r["forecast_type"] = FORECAST_TYPE.get(r.get("forecast_type"), r.get("forecast_type"))
    for (tt, col), ok in ALLOWED_CHECK.items():
        if tt == t and r.get(col) is not None and r[col] not in ok:
            raise PersistError(f"{t}.{col}={r[col]!r} is not an allowed value {sorted(ok)}")


def _typed(t, r):
    """entity_type and the typed link must agree (R2 CHECK): fill the typed column, refuse a disagreement."""
    col = ENTITY_LINK.get(r.get("entity_type"))
    if not col or col not in r:
        return
    if r.get(col) is None:
        r[col] = r["entity_id"]
    elif r[col] != r["entity_id"]:
        raise PersistError(f"{t}: entity {r['entity_type']}#{r['entity_id']} disagrees with {col}={r[col]}")


def _chain_flags(out):
    """is_current false on every version that has a successor; A5-style verification fields on the decision."""
    for t, prev in PREV.items():
        has_next = {r[prev] for r in out[t] if r.get(prev) is not None}
        for r in out[t]:
            r["is_current"] = r[PK[t]] not in has_next
    sup = {r["supersedes_decision_id"] for r in out["agent_decision"] if r.get("supersedes_decision_id") is not None}
    for r in out["agent_decision"]:
        r["is_current"] = r["agent_decision_id"] not in sup
    # decision record: verification condition and result, taken from how the finding was scored when the payer answered
    fnd = {}
    for f in out["agent_finding"]:
        fnd.setdefault(f["agent_decision_id"], f)
    for d in out["agent_decision"]:
        f = fnd.get(d["agent_decision_id"])
        if f and d["agent_code"] == "A5" and f["finding_type"] == "predicted_denial":
            d["recheck_condition"] = "payer_answer_received"
            d["recheck_result"] = {"fixed": "n/a", "accepted": "confirmed", "dismissed": "not_confirmed"}.get(f["finding_status"], "pending")


# ------------------------------------------------------------------ 2. natural keys and ids (pure)
def natural_key(t, r):
    """Idempotency key per hard rule 7: (tenant, event, agent, action). Parents are already remapped to R2 keys."""
    k = {
        "agent_run": ("agent_code", "run_mode", "started_at"),
        "agent_decision": ("agent_code", "decision_type", "entity_type", "entity_id", "decided_at"),
        "agent_decision_check": ("agent_decision_id", "check_seq"),
        "agent_finding": ("agent_code", "finding_type", "entity_type", "entity_id", "found_date", "version"),
        "agent_task": ("agent_code", "task_type", "entity_type", "entity_id", "created_date", "version"),
        "agent_approval": ("agent_decision_id", "approval_type", "approval_date"),
        "agent_writeback": ("agent_decision_id", "writeback_type", "attempt_no", "version"),
        "agent_value": ("agent_code", "value_stage", "value_kind", "entity_type", "entity_id", "value_date", "amount"),
        "agent_forecast": ("forecast_type", "as_of_date", "payer_id", "target_start_date", "version"),
    }[t]
    return tuple(_norm(r.get(c)) for c in k)


def assign_ids(rows, existing=None, next_id=None):
    """-> (new_rows, idmap, stats). `existing[t]` = {(key, occurrence): id} for rows already in the database; `next_id[t]` = first free key.

    A row whose key is already there maps to the existing id and is not written again. Identical keys inside one batch
    get an occurrence number (A4 can raise two decisions on one encounter on one day), so the n-th stays the n-th on a rerun.
    """
    existing = existing or {}
    next_id = dict(next_id or {})
    idmap = {t: {} for t in TABLES}
    new = {t: [] for t in TABLES}
    stats = {t: {"in": 0, "new": 0, "existing": 0} for t in TABLES}
    for t in TABLES:
        seen = defaultdict(int)
        have = existing.get(t, {})
        for r in rows.get(t, []):
            local = r[PK[t]]
            for col, parent in FK[t].items():
                v = r.get(col)
                if v is not None:
                    if v not in idmap[parent]:
                        raise PersistError(f"{t}.{col}={v} points at a {parent} that is not in the batch")
                    r[col] = idmap[parent][v]
            key = natural_key(t, r)
            seen[key] += 1
            stats[t]["in"] += 1
            kk = (key, seen[key])
            if kk in have:
                idmap[t][local] = have[kk]
                stats[t]["existing"] += 1
                continue
            nid = next_id.get(t, 1)
            next_id[t] = nid + 1
            idmap[t][local] = nid
            r[PK[t]] = nid
            new[t].append(r)
            stats[t]["new"] += 1
    # successors written in this batch point at ids that now exist; fix is_current for chains that reach into existing rows is not needed (insert-only)
    return new, idmap, stats


# ------------------------------------------------------------------ 3. database
def assert_r2(conn):
    cur = conn.cursor()
    cur.execute("select current_database()")
    db = cur.fetchone()[0]
    if db != DB:
        raise PersistError(f"refusing to write to database {db!r}: only {DB!r} is allowed")


def latest_load_batch(conn, tenant_id=TENANT):
    cur = conn.cursor()
    cur.execute("select max(load_batch_id) from load_batch where tenant_id = %s", (tenant_id,))
    return cur.fetchone()[0]


def reset(conn, tenant_id=TENANT, source=SOURCE):
    """Deletes this tenant's rows with this source from the agent_* tables. Returns rows deleted per table."""
    assert_r2(conn)
    cur = conn.cursor()
    out = {}
    for t in reversed(TABLES):
        assert t.startswith("agent_")
        cur.execute(f'DELETE FROM "{t}" WHERE tenant_id = %s AND source = %s', (tenant_id, source))
        out[t] = cur.rowcount
    return out


def _existing(cur, t, tenant_id, source):
    cols = {"agent_run": ("agent_code", "run_mode", "started_at"),
            "agent_decision": ("agent_code", "decision_type", "entity_type", "entity_id", "decided_at"),
            "agent_decision_check": ("agent_decision_id", "check_seq"),
            "agent_finding": ("agent_code", "finding_type", "entity_type", "entity_id", "found_date", "version"),
            "agent_task": ("agent_code", "task_type", "entity_type", "entity_id", "created_date", "version"),
            "agent_approval": ("agent_decision_id", "approval_type", "approval_date"),
            "agent_writeback": ("agent_decision_id", "writeback_type", "attempt_no", "version"),
            "agent_value": ("agent_code", "value_stage", "value_kind", "entity_type", "entity_id", "value_date", "amount"),
            "agent_forecast": ("forecast_type", "as_of_date", "payer_id", "target_start_date", "version")}[t]
    cur.execute(f'SELECT "{PK[t]}", ' + ",".join(f'"{c}"' for c in cols) + f' FROM "{t}" WHERE tenant_id = %s AND source = %s ORDER BY "{PK[t]}"', (tenant_id, source))
    seen, out = defaultdict(int), {}
    for row in cur.fetchall():
        key = tuple(_norm(v) for v in row[1:])
        seen[key] += 1
        out[(key, seen[key])] = row[0]
    return out


def check_links(cur, rows, tenant_id):
    """Every typed link must resolve to a real R2 row of this tenant. Returns {column: [missing ids]}."""
    want = defaultdict(set)
    for t in TABLES:
        for r in rows.get(t, []):
            for c, tbl in LINKS.items():
                if r.get(c) is not None:
                    want[c].add(r[c])
    missing = {}
    for c, ids in want.items():
        tbl = LINKS[c]
        cur.execute(f'SELECT "{tbl}_id" FROM "{tbl}" WHERE tenant_id = %s AND "{tbl}_id" = ANY(%s)', (tenant_id, sorted(ids)))
        gone = ids - {x[0] for x in cur.fetchall()}
        if gone:
            missing[c] = sorted(gone)[:10]
    return missing


def persist(conn, results, tenant_id=TENANT, source=SOURCE, reset_first=False, dry_run=False, verify_links=True, loaded_at=None, load_batch_id=None):
    """Writes the results into the agent_* tables on `conn` (no commit). Returns {"deleted": {...}, "written": {...}, "existing": {...}, "load_batch_id": n}."""
    assert_r2(conn)
    cur = conn.cursor()
    if load_batch_id is None:
        load_batch_id = latest_load_batch(conn, tenant_id)
    rows = translate(results, tenant_id, source, loaded_at, load_batch_id)
    report = {"deleted": {}, "written": {}, "existing": {}, "load_batch_id": load_batch_id, "dropped_columns": _dropped(results)}
    if reset_first and not dry_run:
        report["deleted"] = reset(conn, tenant_id, source)
    if verify_links:
        miss = check_links(cur, rows, tenant_id)
        if miss:
            raise PersistError(f"typed links that are not in R2 for tenant {tenant_id}: {miss}")
    existing = {t: _existing(cur, t, tenant_id, source) for t in TABLES} if not dry_run else {}
    base = {}
    for t in TABLES:
        cur.execute(f'SELECT coalesce(max("{PK[t]}"), 0) + 1 FROM "{t}"')
        base[t] = cur.fetchone()[0]
    new, _, stats = assign_ids(rows, existing, base)
    report["existing"] = {t: s["existing"] for t, s in stats.items()}
    if dry_run:
        report["written"] = {t: len(v) for t, v in new.items()}
        return report
    loader = r2load.Loader(conn)
    for t in TABLES:
        assert t.startswith("agent_")
        for r in new[t]:
            for c, v in list(r.items()):
                if isinstance(v, (bytes, bytearray)):
                    r[c] = "\\x" + bytes(v).hex()
        report["written"][t] = _copy(loader, t, new[t], tenant_id, source)
    return report


def _copy(loader, t, rows, tenant_id, source):
    if not rows:
        return 0
    cols = _cols(t)
    t_ = r2load.TBL[t]
    for r in rows:
        r["tenant_id"], r["source"] = tenant_id, source      # our rows carry every column, so the Loader's synthea defaults never apply
    return loader.rows(t, [{c: r.get(c) for c in cols} for r in rows])


def _dropped(results):
    out = {}
    for t in TABLES:
        cols = set(_cols(t)) | set(RENAME.get(t, {})) | set(RENAME.get(t, {}).values())
        extra = set()
        for r in _engine_rows(results, t):
            extra |= {k for k in r if k not in cols}
        if extra:
            out[t] = sorted(extra)
    return out


def persist_run(conn, replay, **kw):
    """Convenience for a finished tools.replay.engine.Replay: pass the object, get the same report as persist()."""
    return persist(conn, from_engine(replay), **kw)


def from_engine(replay):
    """Takes what a Replay holds after run(): final rows per table and the decision traces."""
    return {"rows": {t: list(replay.S.rows[ENGINE_TABLE.get(t, t)]) for t in TABLES}, "traces": dict(getattr(replay, "traces", {}))}


# ------------------------------------------------------------------ JSON round trip for the CLI
def _enc(o):
    if isinstance(o, Decimal):
        return {"$n": str(o)}
    if isinstance(o, dt.datetime):
        return {"$t": o.isoformat()}
    if isinstance(o, dt.date):
        return {"$d": o.isoformat()}
    if isinstance(o, (bytes, bytearray)):
        return {"$b": bytes(o).hex()}
    raise TypeError(type(o))


def _dec_hook(o):
    if "$n" in o:
        return D(o["$n"])
    if "$t" in o:
        return dt.datetime.fromisoformat(o["$t"])
    if "$d" in o:
        return dt.date.fromisoformat(o["$d"])
    if "$b" in o:
        return bytes.fromhex(o["$b"])
    return o


def dump_results(results, path):
    pathlib.Path(path).write_text(json.dumps(results, default=_enc), encoding="utf-8")


def load_results(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"), object_hook=_dec_hook, parse_int=int)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--input", help="results JSON written by dump_results()")
    ap.add_argument("--reset", action="store_true", help="delete this tenant's rows with this source from agent_* first")
    ap.add_argument("--reset-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tenant", type=int, default=TENANT)
    ap.add_argument("--source", default=SOURCE)
    ap.add_argument("--skip-link-check", action="store_true")
    a = ap.parse_args(argv)
    conn = r2load.connect()                                # asserts krisnnai_r2
    try:
        if a.reset_only:
            print("deleted", reset(conn, a.tenant, a.source))
        else:
            if not a.input:
                ap.error("--input is required unless --reset-only")
            rep = persist(conn, load_results(a.input), a.tenant, a.source, reset_first=a.reset, dry_run=a.dry_run, verify_links=not a.skip_link_check)
            for k, v in rep.items():
                print(k, v)
        if a.dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
