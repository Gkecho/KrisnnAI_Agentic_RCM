"""Query Admin: a small local web app (standard library only) for the analytics query registry.

Run from the repo root:   python tools/analytics/query_admin.py          (http://127.0.0.1:8780/)

Local use only: it binds to 127.0.0.1, checks the Host header, and requires a custom header on every POST (so a
web page in another tab cannot drive it). There is no login: the "actor" name is typed in the page.
It never returns or logs the database password. "Publish to site data" writes out/fin/fin_data.js and nothing else.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "synthea"))

import qreg  # noqa: E402
import qsafe  # noqa: E402
import qsvc  # noqa: E402

HOST, PORT = "127.0.0.1", 8780
UI = pathlib.Path(__file__).resolve().parent / "admin_ui" / "index.html"
EXPECTED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
MAX_BODY = 200_000


class App:
    """All endpoint logic, independent of HTTP so it can be tested directly."""

    def __init__(self, service: qsvc.Service) -> None:
        self.svc = service
        self.reg = service.registry

    def get(self, path: str, q: dict[str, str]) -> Any:
        r = self.reg
        if path == "/api/tree":
            return {"tree": r.tree(), "approval_mode": r.approval_mode, "levels": list(qreg.LEVELS)}
        if path == "/api/queries":
            node = int(q["node"])
            return {"node": r.node(node), "path": r.path(node), "queries": r.effective_list(node)}
        if path == "/api/query":
            return self.query_detail(q["query_id"], int(q["node"]))
        if path == "/api/impact":
            return r.impact(q["query_id"], int(q["node"]))
        if path == "/api/audit":
            return {"audit": r.audit_log(int(q.get("limit", 100)), q.get("query_id")), "chain_ok": r.audit_chain_ok()}
        raise KeyError(path)

    def query_detail(self, query_id: str, node_id: int) -> dict[str, Any]:
        r = self.reg
        hist = r.history(query_id, node_id)
        open_v = next((h for h in hist if h["status"] in qreg.OPEN_STATUSES), None)
        eff = r.resolve_at(query_id, node_id)
        sp = r.spec_row(query_id)
        return {
            "spec": sp,
            "node": r.node(node_id),
            "effective": {
                "sql": eff.sql,
                "level": eff.level,
                "from_node": eff.node_name,
                "from_node_id": eff.node_id,
                "version": eff.version,
                "inherited": eff.node_id != node_id,
            },
            "open_version": open_v,
            "history": hist,
            "impact": r.impact(query_id, node_id),
            "approval_mode": r.approval_mode,
        }

    def post(self, path: str, b: dict[str, Any]) -> Any:
        r, actor = self.reg, str(b.get("actor") or "admin").strip()[:40] or "admin"
        if path == "/api/draft":
            vid = r.save_draft(b["query_id"], int(b["node_id"]), b["sql"], actor, str(b.get("note", ""))[:300])
            return {"version_id": vid}
        if path == "/api/test":
            return self.svc.test_run(int(b["version_id"]), actor, self._tenant(int(b.get("node_id", 0))))
        if path in ("/api/submit", "/api/approve", "/api/publish", "/api/discard"):
            fn = {
                "/api/submit": r.submit,
                "/api/approve": r.approve,
                "/api/publish": r.publish,
                "/api/discard": r.discard_draft,
            }[path]
            fn(int(b["version_id"]), actor)
            return {"ok": True}
        if path == "/api/reject":
            r.reject(int(b["version_id"]), actor, str(b.get("note", ""))[:300])
            return {"ok": True}
        if path == "/api/rollback":
            v = r.rollback(b["query_id"], int(b["node_id"]), int(b["to_version"]), actor, str(b.get("note", ""))[:300])
            return {"version": v}
        if path == "/api/retire":
            r.retire_override(b["query_id"], int(b["node_id"]), actor)
            return {"ok": True}
        if path == "/api/mode":
            r.set_approval_mode(str(b["mode"]), actor)
            return {"approval_mode": r.approval_mode}
        if path == "/api/publish_site":
            return self.svc.publish_site(actor)  # the output path is fixed in code; the request cannot choose it
        raise KeyError(path)

    def _tenant(self, node_id: int) -> int:
        """Tenant for reads = the customer key on the selected node's path (numeric), else tenant 1."""
        try:
            for n in self.reg.path(node_id):
                if n["level"] == "customer" and str(n["key"]).isdigit():
                    return int(n["key"])
        except KeyError:
            pass
        return 1


def make_handler(app: App) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "KrisnnAIQueryAdmin"

        def log_message(self, fmt: str, *args: Any) -> None:  # method + path only: no bodies, nothing sensitive
            sys.stderr.write(f"{self.command} {urlparse(self.path).path} -> {args[1] if len(args) > 1 else ''}\n")

        def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(code)
            self.send_header(
                "Content-Type", ctype + ("; charset=utf-8" if ctype.startswith(("text", "application/json")) else "")
            )
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'",
            )
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj: Any) -> None:
            self._send(code, json.dumps(obj, default=qsvc.jsonable).encode("utf-8"))

        def _host_ok(self) -> bool:
            return (self.headers.get("Host") or "") in EXPECTED_HOSTS

        def do_GET(self) -> None:  # noqa: N802
            if not self._host_ok():
                return self._json(HTTPStatus.FORBIDDEN, {"error": "bad Host header"})
            u = urlparse(self.path)
            if u.path in ("/", "/index.html"):
                return self._send(200, UI.read_bytes(), "text/html")
            if not u.path.startswith("/api/"):
                return self._json(404, {"error": "not found"})
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            try:
                self._json(200, app.get(u.path, q))
            except KeyError as e:
                self._json(404, {"error": f"not found: {e.args[0] if e.args else ''}"})
            except Exception as exc:  # noqa: BLE001
                self._json(400, {"error": qsvc.safe_error(exc)})

        def do_POST(self) -> None:  # noqa: N802
            if not self._host_ok():
                return self._json(HTTPStatus.FORBIDDEN, {"error": "bad Host header"})
            if self.headers.get("X-Admin-Request") != "1" or "application/json" not in (
                self.headers.get("Content-Type") or ""
            ):
                return self._json(HTTPStatus.FORBIDDEN, {"error": "missing admin request headers"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if n > MAX_BODY:
                    return self._json(413, {"error": "body too large"})
                body = json.loads(self.rfile.read(n) or b"{}")
                self._json(200, app.post(urlparse(self.path).path, body))
            except (qsafe.SqlRejected, qsafe.ResultRejected, qreg.WorkflowError) as exc:
                self._json(400, {"error": str(exc)})
            except KeyError as e:
                self._json(404, {"error": f"not found: {e.args[0] if e.args else ''}"})
            except Exception as exc:  # noqa: BLE001
                self._json(400, {"error": qsvc.safe_error(exc)})

    return Handler


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="KrisnnAI Query Admin (local, 127.0.0.1 only)")
    ap.add_argument("--registry", default=None, help="registry sqlite file (default var/analytics_registry.sqlite)")
    args = ap.parse_args(argv)
    reg = qreg.open_default(args.registry)
    app = App(qsvc.Service(reg))
    srv = ThreadingHTTPServer(
        (HOST, PORT), make_handler(app)
    )  # fails loudly if the port is taken; never kills anything
    print(f"Query Admin on http://{HOST}:{PORT}/  (registry: {reg.db_path})  Ctrl+C to stop")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        reg.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
