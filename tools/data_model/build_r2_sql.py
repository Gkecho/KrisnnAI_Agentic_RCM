"""Builds SQL Server DDL for the R2 data dictionary received from the data modeller (docs/data_model/r2_model.json).

Usage: python tools/data_model/build_r2_sql.py        writes docs/data_model/schema_r2_sqlserver.sql and schema_r2_postgres.sql

Rules: Mandatory columns are NOT NULL; the primary key is the table's own id (id + version on versioned tables); a foreign key is created when the parent has a
single-column key and both columns have the same type. Links to versioned parents are not enforced by the database (the id alone is not unique there) and are listed in the report.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
M = json.load(open(ROOT / "docs" / "data_model" / "r2_model.json", encoding="utf-8"))
T = {t["name"]: t for t in M["tables"]}
versioned = {n for n, t in T.items() if any(c["name"] == "version" for c in t["cols"])}
q = lambda s: "[" + s + "]"
lit = lambda s: "N'" + (s or "").replace("'", "''") + "'"


def pk(t):
    return [t["cols"][0]["name"]] + (["version"] if t["name"] in versioned else [])


out = ["-- KrisnnAI R2 (SQL Server). Generated from docs/data_model/r2_model.json by tools/data_model/build_r2_sql.py. Do not edit by hand.", "SET NOCOUNT ON;", ""]
for t in M["tables"]:
    cols = [f"    {q(c['name'])} {c['type']} {'NOT NULL' if c['priority'] == 'Mandatory' or c['name'] in pk(t) else 'NULL'}" for c in t["cols"]]
    cols.append(f"    CONSTRAINT {q('PK_' + t['name'])} PRIMARY KEY ({', '.join(q(x) for x in pk(t))})")
    out += [f"CREATE TABLE {q(t['name'])} (", ",\n".join(cols), ");", "GO"]
fks, skipped = [], []
for t in M["tables"]:
    for c in t["cols"]:
        tgt = c["link"] or ("tenant" if c["name"] == "tenant_id" and t["name"] != "tenant" else "")
        if not tgt:
            continue
        p = T[tgt]
        pcol = p["cols"][0]
        ok = tgt not in versioned and pcol["type"] == c["type"] and not (tgt == t["name"] and c["name"] == pcol["name"])
        if ok:
            fks.append(f"ALTER TABLE {q(t['name'])} ADD CONSTRAINT {q('FK_' + t['name'] + '_' + c['name'])} FOREIGN KEY ({q(c['name'])}) REFERENCES {q(tgt)} ({q(pcol['name'])});")
        else:
            skipped.append((t["name"], c["name"], tgt, "versioned parent" if tgt in versioned else f"type {c['type']} vs {pcol['type']}"))
out += ["", "-- foreign keys"] + fks + ["GO", "", "-- descriptions"]
for t in M["tables"]:
    out.append(f"EXEC sp_addextendedproperty N'MS_Description', {lit(t['what'])}, N'SCHEMA', N'dbo', N'TABLE', {lit(t['name'])};")
    for c in t["cols"]:
        out.append(f"EXEC sp_addextendedproperty N'MS_Description', {lit(c['desc'])}, N'SCHEMA', N'dbo', N'TABLE', {lit(t['name'])}, N'COLUMN', {lit(c['name'])};")
out.append("GO")
(ROOT / "docs" / "data_model" / "schema_r2_sqlserver.sql").write_text("\n".join(out) + "\n", encoding="utf-8")
by = {}
for s in skipped:
    by[s[3]] = by.get(s[3], 0) + 1
print(f"{len(T)} tables, {sum(len(t['cols']) for t in T.values())} columns, {len(versioned)} versioned, {len(fks)} foreign keys created, {len(skipped)} links not enforced: {by}")
for s in skipped:
    if s[3].startswith("type"):
        print("  type mismatch:", s)


# ---------------------------------------------------------------------- PostgreSQL (the AWS RDS instance)
import re

PGTYPE = {"DATETIME2": "TIMESTAMP", "BIT": "BOOLEAN", "NVARCHAR": "VARCHAR", "TINYINT": "SMALLINT"}


def pgtype(ty):
    base = ty.split("(")[0]
    if base == "BINARY":
        return "BYTEA"
    return PGTYPE.get(base, base) + ty[len(base):]


d = lambda s: '"' + s + '"'
sq = lambda s: "'" + (s or "").replace("'", "''") + "'"
pg = ["-- KrisnnAI R2 (PostgreSQL). Generated from docs/data_model/r2_model.json by tools/data_model/build_r2_sql.py. Do not edit by hand."]
for t in M["tables"]:
    cols = [f"    {d(c['name'])} {pgtype(c['type'])} {'NOT NULL' if c['priority'] == 'Mandatory' or c['name'] in pk(t) else 'NULL'}" for c in t["cols"]]
    cols.append(f"    CONSTRAINT {d('pk_' + t['name'])} PRIMARY KEY ({', '.join(d(x) for x in pk(t))})")
    pg += [f"CREATE TABLE {d(t['name'])} (", ",\n".join(cols), ");"]
for line in fks:
    pg.append(re.sub(r"\[([^\]]+)\]", lambda m: d(m.group(1)), line))
for t in M["tables"]:
    pg.append(f"COMMENT ON TABLE {d(t['name'])} IS {sq(t['what'])};")
    for c in t["cols"]:
        pg.append(f"COMMENT ON COLUMN {d(t['name'])}.{d(c['name'])} IS {sq(c['desc'])};")
(ROOT / "docs" / "data_model" / "schema_r2_postgres.sql").write_text("\n".join(pg) + "\n", encoding="utf-8")
print("postgres schema written")
