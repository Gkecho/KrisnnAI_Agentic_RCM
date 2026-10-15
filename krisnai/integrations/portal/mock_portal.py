"""A small mock payer portal: login, claim search, claim detail with status and pend reason, a records-request page.

Plain server-rendered HTML with stable element ids, so a bot can be written the way real portal automation is: log in,
find the claim, read the status, capture evidence. `?layout=2` (or `layout=2` on the app) renames the ids on the claim
page to model a portal redesign, which is how the bot's stop-on-change behaviour is tested.

Data comes from the same mock world as the mock clearinghouse. Credentials come from the caller (a bot gets them from
environment variables); there is no default account.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from html import escape

from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from krisnai.integrations.clearinghouse.mock_world import MockWorld

STATUS_TEXT = {
    "A1": "Received", "A2": "Accepted for processing", "A3": "Returned: missing or invalid information",
    "A4": "Returned: unprocessable", "P1": "Pending: in review", "F1": "Finalized: paid", "F2": "Finalized: denied",
    "E1": "Claim not found",
}  # fmt: skip

IDS_V1 = {"title": "claim-title", "status": "claim-status", "reason": "pend-reason", "paid": "paid-amount"}
IDS_V2 = {"title": "claim-heading", "status": "current-state", "reason": "reason-text", "paid": "amount-paid"}


def _page(title: str, body: str) -> str:
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{escape(title)}</title></head>"
            f"<body><h1>{escape(title)}</h1>{body}</body></html>")  # fmt: skip


def create_app(world: MockWorld, user: str, password: str, layout: int = 1, max_per_minute: int = 120) -> FastAPI:
    if not user or not password:
        raise ValueError("the mock portal needs a user and password from the caller; it has no default account")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.sessions = set()
    app.state.requests = []  # (path, time) for rate limiting and for tests
    app.state.layout = layout

    def _limited() -> bool:
        now = time.time()
        recent = [t for t in app.state.requests[-max_per_minute * 2:] if now - t < 60]
        app.state.requests.append(now)
        return len(recent) >= max_per_minute

    def _authed(request: Request) -> bool:
        return request.cookies.get("sid") in app.state.sessions

    def _layout(request: Request) -> dict:
        return IDS_V2 if request.query_params.get("layout", str(app.state.layout)) == "2" else IDS_V1

    @app.get("/login", response_class=HTMLResponse)
    async def login_form() -> str:
        return _page("Provider portal sign in",
                     "<form method='post' action='/login'><input id='username' name='username'>"
                     "<input id='password' name='password' type='password'>"
                     "<button id='login-submit' type='submit'>Sign in</button></form>")  # fmt: skip

    @app.post("/login")
    async def login(request: Request):
        form = parse_qs((await request.body()).decode("utf-8", "ignore"))  # no multipart dependency needed
        username = (form.get("username") or [""])[0]
        password_in = (form.get("password") or [""])[0]
        if _limited():
            return HTMLResponse(_page("Slow down", "<p id='rate-limit'>Too many requests</p>"), status_code=429)
        if not (secrets.compare_digest(username, user) and secrets.compare_digest(password_in, password)):
            return HTMLResponse(_page("Sign in failed", "<p id='login-error'>Invalid credentials</p>"), status_code=401)
        sid = secrets.token_hex(16)
        app.state.sessions.add(sid)
        resp = RedirectResponse("/claims", status_code=303)
        resp.set_cookie("sid", sid, httponly=True)
        return resp

    @app.get("/claims", response_class=HTMLResponse)
    async def search(request: Request, claim_id: str = ""):
        if _limited():
            return HTMLResponse(_page("Slow down", "<p id='rate-limit'>Too many requests</p>"), status_code=429)
        if not _authed(request):
            return RedirectResponse("/login", status_code=303)
        rows = ""
        if claim_id:
            claim = world.extract.claims.get(claim_id)
            if claim is not None:
                rows = (f"<tr><td><a id='open-{escape(claim_id)}' href='/claims/{escape(claim_id)}'>"
                        f"{escape(claim_id)}</a></td><td>{escape(claim.payer_id)}</td></tr>")  # fmt: skip
        return _page("Claims", "<form method='get' action='/claims'><input id='claim-search' name='claim_id'>"
                     "<button id='search-submit'>Search</button></form>"
                     f"<table id='results'>{rows}</table>")  # fmt: skip

    @app.get("/claims/{claim_id}", response_class=HTMLResponse)
    async def detail(request: Request, claim_id: str):
        if _limited():
            return HTMLResponse(_page("Slow down", "<p id='rate-limit'>Too many requests</p>"), status_code=429)
        if not _authed(request):
            return RedirectResponse("/login", status_code=303)
        ids = _layout(request)
        category, code, paid, payer_no, claim = world.claim_state(claim_id)
        if claim is None:
            return HTMLResponse(_page("Not found", f"<p id='{ids['status']}'>Claim not found</p>"), status_code=404)
        reason = "In normal processing"
        if category == "A3":
            reason = f"Returned (code {code}): correct the claim and resubmit"
        elif category == "F2":
            reason = "Denied: see remittance advice"
        elif category == "P1" and int(hashlib.sha256(claim_id.encode()).hexdigest(), 16) % 3 == 0:
            reason = "Records requested: medical records for the date of service"
        body = (f"<h2 id='{ids['title']}'>Claim {escape(claim_id)}</h2>"
                f"<p>Payer claim number: <span id='payer-claim-no'>{escape(payer_no)}</span></p>"
                f"<p>Status: <span id='{ids['status']}'>{escape(STATUS_TEXT.get(category, category))}</span></p>"
                f"<p>Reason: <span id='{ids['reason']}'>{escape(reason)}</span></p>"
                f"<p>Paid: <span id='{ids['paid']}'>{paid:.2f}</span></p>"
                f"<p><a id='records-request' href='/claims/{escape(claim_id)}/records'>Records request</a></p>")  # fmt: skip
        return _page(f"Claim {claim_id}", body)

    @app.get("/claims/{claim_id}/records", response_class=HTMLResponse)
    async def records(request: Request, claim_id: str):
        if not _authed(request):
            return RedirectResponse("/login", status_code=303)
        category, _, _, _, claim = world.claim_state(claim_id)
        asked = category == "P1" and int(hashlib.sha256(claim_id.encode()).hexdigest(), 16) % 3 == 0
        text = "Please send the medical records for the date of service within 30 days." if asked else "No request."
        return _page("Records request", f"<p id='request-text'>{escape(text)}</p>"
                     f"<p id='request-open'>{'yes' if asked else 'no'}</p>")  # fmt: skip

    return app
