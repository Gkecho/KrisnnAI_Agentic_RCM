"""Stage 1, portal bot hard cases: MFA, CAPTCHA, script-drawn pages, locked account, maintenance, session expiry.

In every case the bot stops, says why, requests nothing more, and leaks no credential. It never tries to solve or
bypass a challenge and never retries a locked account.
"""

from __future__ import annotations

import json
from dataclasses import asdict

import pytest

from krisnnai.integrations.portal.bots import claim_status_bot
from tests.test_portal import PASSWORD, USER, driver_for, world  # noqa: F401  (world is a fixture)

CLAIMS = ["REJ1", "PAID1", "DEN1"]

# mode -> (reason handed over, requests the bot made before stopping, requests the mock rate-limits and counted)
HANDOFF = {
    "mfa": ("mfa", 2, 1),  # login form, password post (lands on the code page)
    "captcha": ("captcha", 1, 0),  # login form only: the bot does not even post the password
    "js_only": ("js_required", 2, 2),  # login form, password post, then the redirect to an empty shell
    "locked": ("account_locked", 2, 1),  # one sign-in attempt, never a second
    "maintenance": ("maintenance", 1, 0),
}


@pytest.mark.parametrize("mode", sorted(HANDOFF))
def test_a_challenge_stops_the_run_and_is_handed_to_a_person(world, tmp_path, mode):  # noqa: F811
    reason, requests, posts = HANDOFF[mode]
    d, app = driver_for(world, mode=mode)
    res = claim_status_bot(d, USER, PASSWORD, CLAIMS, tmp_path / "ev", log_path=tmp_path / "log.jsonl")
    assert [r.outcome for r in res] == ["needs_human"] + ["not_attempted"] * (len(CLAIMS) - 1)
    assert res[0].handoff == reason and reason in res[0].detail
    assert d.requests == requests
    assert len(app.state.requests) == posts  # the mock counts sign-in posts and claim pages
    assert bool(app.state.sessions) == (mode == "js_only")  # only the script-drawn page is behind a real sign-in
    blob = json.dumps([asdict(r) for r in res]) + (tmp_path / "log.jsonl").read_text()
    assert PASSWORD not in blob and USER not in blob
    assert not list((tmp_path / "ev").glob("*"))  # no challenge page is kept as claim evidence


def test_an_account_locked_page_is_not_mistaken_for_a_wrong_password(world, tmp_path):  # noqa: F811
    d, _ = driver_for(world, mode="locked")
    res = claim_status_bot(d, USER, PASSWORD, ["REJ1"], tmp_path)
    assert res[0].outcome == "needs_human" and res[0].outcome != "login_failed"


def test_one_session_expiry_is_recovered_with_a_fresh_login(world, tmp_path):  # noqa: F811
    d, app = driver_for(world, expire_after=3)
    res = claim_status_bot(d, USER, PASSWORD, CLAIMS, tmp_path)
    assert [r.outcome for r in res] == ["read"] * 3
    assert [r.status for r in res][1] == "Finalized: paid"
    assert app.state.logins >= 2  # at least one fresh login was needed


def test_a_session_that_keeps_expiring_is_handed_to_a_person(world, tmp_path):  # noqa: F811
    d, _ = driver_for(world, expire_after=1)
    res = claim_status_bot(d, USER, PASSWORD, CLAIMS, tmp_path)
    assert res[0].outcome == "needs_human" and res[0].handoff == "session_expired"
    assert [r.outcome for r in res[1:]] == ["not_attempted"] * 2


def test_re_login_is_capped_so_a_dropping_portal_cannot_lock_the_account(world, tmp_path):  # noqa: F811
    d, app = driver_for(world, expire_after=2)
    res = claim_status_bot(d, USER, PASSWORD, [f"X{i}" for i in range(30)], tmp_path)
    assert any(r.handoff == "session_expired" for r in res)
    assert app.state.logins <= 6  # the first login plus at most five more


def test_an_expiry_in_the_middle_does_not_repeat_earlier_claims(world, tmp_path):  # noqa: F811
    d, _ = driver_for(world, expire_after=3)
    res = claim_status_bot(d, USER, PASSWORD, ["REJ1", "PAID1"], tmp_path)
    assert [r.claim for r in res] == ["REJ1", "PAID1"]


def test_the_normal_portal_is_unchanged(world, tmp_path):  # noqa: F811
    d, _ = driver_for(world)
    res = claim_status_bot(d, USER, PASSWORD, CLAIMS, tmp_path)
    assert [r.outcome for r in res] == ["read"] * 3 and all(not r.handoff for r in res)


def test_the_mock_rejects_an_unknown_mode(world):  # noqa: F811
    with pytest.raises(ValueError):
        driver_for(world, mode="telepathy")
