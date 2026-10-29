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

from krisnnai.integrations.clearinghouse.mock_world import MockWorld

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


MODES = {"normal", "mfa", "captcha", "js_only", "locked", "maintenance"}


def create_app(world: MockWorld, user: str, password: str, layout: int = 1, max_per_minute: int = 120,
               mode: str = "normal", expire_after: int | None = None) -> FastAPI:  # fmt: skip
    """`mode` models the things a bot must hand to a person: mfa (a code page after the password), captcha (a box on
    the sign-in page), js_only (a shell page whose content a script would draw), locked (account locked page),
    maintenance (503). `expire_after=n` ends every session after n page views, to test re-login."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {sorted(MODES)}")
    if not user or not password:
        raise ValueError("the mock portal needs a user and password from the caller; it has no default account")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.sessions = set()
    app.state.requests = []  # (path, time) for rate limiting and for tests
    app.state.layout = layout
    app.state.logins = 0  # sessions ever opened
    app.state.views = {}  # session id -> authenticated page views, for expire_after

    def _limited() -> bool:
        now = time.time()
        recent = [t for t in app.state.requests[-max_per_minute * 2:] if now - t < 60]
        app.state.requests.append(now)
        return len(recent) >= max_per_minute

    def _authed(request: Request) -> bool:
        sid = request.cookies.get("sid")
        if sid not in app.state.sessions:
            return False
        app.state.views[sid] = app.state.views.get(sid, 0) + 1
        if expire_after is not None and app.state.views[sid] > expire_after:
            app.state.sessions.discard(sid)
            return False
        return True

    def _maintenance() -> HTMLResponse | None:
        if mode == "maintenance":
            return HTMLResponse(_page("Down for maintenance", "<p id='maintenance'>Back soon</p>"), status_code=503)
        return None

    def _layout(request: Request) -> dict:
        return IDS_V2 if request.query_params.get("layout", str(app.state.layout)) == "2" else IDS_V1

    @app.get("/login", response_class=HTMLResponse)
    async def login_form():
        down = _maintenance()
        if down is not None:
            return down
        challenge = "<div id='captcha-box'>Select all the traffic lights</div>" if mode == "captcha" else ""
        return _page("Provider portal sign in",
                     "<form method='post' action='/login'><input id='username' name='username'>"
                     "<input id='password' name='password' type='password'>" + challenge +
                     "<button id='login-submit' type='submit'>Sign in</button></form>")  # fmt: skip

    @app.post("/login")
    async def login(request: Request):
        down = _maintenance()
        if down is not None:
            return down
        form = parse_qs((await request.body()).decode("utf-8", "ignore"))  # no multipart dependency needed
        username = (form.get("username") or [""])[0]
        password_in = (form.get("password") or [""])[0]
        if _limited():
            return HTMLResponse(_page("Slow down", "<p id='rate-limit'>Too many requests</p>"), status_code=429)
        if not (secrets.compare_digest(username, user) and secrets.compare_digest(password_in, password)):
            return HTMLResponse(_page("Sign in failed", "<p id='login-error'>Invalid credentials</p>"), status_code=401)
        if mode == "locked":
            return HTMLResponse(_page("Account locked", "<p id='account-locked'>Contact your administrator</p>"),
                                status_code=403)  # fmt: skip
        if mode == "mfa":  # no session until a code is entered; the bot never enters one
            return RedirectResponse("/mfa", status_code=303)
        sid = secrets.token_hex(16)
        app.state.sessions.add(sid)
        app.state.logins += 1
        resp = RedirectResponse("/claims", status_code=303)
        resp.set_cookie("sid", sid, httponly=True)
        return resp

    @app.get("/mfa", response_class=HTMLResponse)
    async def mfa() -> str:
        return _page("Verify it is you", "<form method='post' action='/mfa'><input id='mfa-code' name='code'>"
                     "<button id='mfa-submit'>Verify</button></form>")  # fmt: skip

    @app.get("/claims", response_class=HTMLResponse)
    async def search(request: Request, claim_id: str = ""):
        down = _maintenance()
        if down is not None:
            return down
        if _limited():
            return HTMLResponse(_page("Slow down", "<p id='rate-limit'>Too many requests</p>"), status_code=429)
        if not _authed(request):
            return RedirectResponse("/login", status_code=303)
        if mode == "js_only":
            return _page("Claims", "<div id='app'></div><noscript id='js-required'>Turn on JavaScript</noscript>"
                         "<script>/* the claim search is drawn here */</script>")  # fmt: skip
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
        hook = getattr(world, "portal_reason", None)  # a world that tracks live payer state supplies its own reason
        live = hook(claim_id, category) if hook else None
        if live is not None:
            reason = live[0]
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
        hook = getattr(world, "portal_reason", None)
        live = hook(claim_id, category) if hook else None
        if live is not None:
            asked = live[1]
        text = "Please send the medical records for the date of service within 30 days." if asked else "No request."
        return _page("Records request", f"<p id='request-text'>{escape(text)}</p>"
                     f"<p id='request-open'>{'yes' if asked else 'no'}</p>")  # fmt: skip

    return app
