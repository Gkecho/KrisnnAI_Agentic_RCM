"""Start the local SQL Server and load the canonical schema:  python tools/data_model/db_up.py [--reset]

First run creates .env.db (git-ignored) with a generated SA password. --reset drops and recreates the krisnnai_canonical database.
The database holds the schema only (no rows); it is for inspecting how the tables are designed. Synthetic data only.
"""
import os, re, secrets, string, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
ENV = os.path.join(REPO, ".env.db")
COMPOSE = os.path.join(REPO, "docker-compose.db.yml")
SCHEMA = os.path.join(REPO, "docs", "data_model", "schema_sqlserver.sql")
DB, CTR = "krisnnai_canonical", "krisnnai-db"
SQLCMD = "/opt/mssql-tools18/bin/sqlcmd"
ENVV = dict(os.environ, MSYS_NO_PATHCONV="1")


def run(args, check=True):
    r = subprocess.run(args, capture_output=True, text=True, env=ENVV)
    if check and r.returncode:
        sys.exit(f"FAILED: {' '.join(args[:4])}...\n{r.stdout[-800:]}{r.stderr[-800:]}")
    return r


def sql(query=None, file=None, db="master"):
    cmd = f'{SQLCMD} -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -d {db} -b '
    cmd += f'-Q "{query}"' if query else f"-i {file}"
    return run(["docker", "exec", CTR, "bash", "-c", cmd + " -h -1 -W"], check=False)


if not os.path.exists(ENV):
    pw = "Kr!" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20)) + "9a"
    open(ENV, "w").write(f"MSSQL_SA_PASSWORD={pw}\n")
    print("created .env.db with a generated SA password (git-ignored)")
reset = "--reset" in sys.argv

print("starting container ...", flush=True)
run(["docker", "compose", "-f", COMPOSE, "--env-file", ENV, "up", "-d"])
for i in range(40):
    st = run(["docker", "inspect", "-f", "{{.State.Health.Status}}", CTR], check=False).stdout.strip()
    if st == "healthy":
        break
    time.sleep(5)
else:
    sys.exit(f"container not healthy (status: {st}); check: docker logs {CTR}")
print("SQL Server is healthy")

if reset:
    sql(f"IF DB_ID('{DB}') IS NOT NULL BEGIN ALTER DATABASE {DB} SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE {DB}; END")
have = sql(f"SELECT COUNT(*) FROM sys.tables", db=DB)
if have.returncode == 0 and have.stdout.strip().split()[0:1] not in (["0"], []):
    print(f"database {DB} already has tables; use --reset to rebuild it")
else:
    sql(f"IF DB_ID('{DB}') IS NULL CREATE DATABASE {DB}")
    run(["docker", "cp", SCHEMA, f"{CTR}:/tmp/schema.sql"])
    r = sql(file="/tmp/schema.sql", db=DB)
    if r.returncode:
        sys.exit("schema load failed:\n" + r.stdout[-1500:] + r.stderr[-500:])
    print("schema loaded")
q = ("SELECT (SELECT COUNT(*) FROM sys.tables), (SELECT COUNT(*) FROM sys.columns c JOIN sys.tables t ON t.object_id=c.object_id), "
     "(SELECT COUNT(*) FROM sys.foreign_keys), (SELECT COUNT(*) FROM sys.extended_properties WHERE name='MS_Description')")
print("tables, columns, foreign keys, descriptions:", " ".join(sql(q, db=DB).stdout.split()))
print(f"connect: server 127.0.0.1,14330, user sa, database {DB}, password in .env.db")
