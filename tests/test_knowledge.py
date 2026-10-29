# ruff: noqa: E501
"""Payer Knowledge Book v1: effective-date lookup, deadlines by route, and refusing to guess."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from krisnnai.knowledge import Book, BookError, Rule, Source, deadline
from krisnnai.knowledge.demo import DEMO, KNOWN_SINCE, PAYER, demo_book

NOW = date(2026, 10, 21)  # the simulation clock, passed in: the book never reads the computer's date


@pytest.fixture()
def book() -> Book:
    return demo_book()


def _cov(book, service_date, service="97110", as_of=NOW, **kw):
    return book.lookup(PAYER, "coverage", service, {"service_date": service_date}, as_of, **kw)


def test_a_2025_service_gets_the_2025_rule_and_a_2026_service_the_2026_rule(book):
    assert _cov(book, date(2025, 12, 15)).rule.content["visit_limit"] == 20
    assert _cov(book, date(2026, 1, 15)).rule.content["visit_limit"] == 12


def test_the_boundary_day_belongs_to_the_right_version(book):
    assert _cov(book, date(2025, 12, 31)).rule.version == 1
    assert _cov(book, date(2026, 1, 1)).rule.version == 2


def test_evaluating_in_2026_does_not_pull_a_2025_service_onto_a_2026_rule(book):
    f = _cov(book, date(2025, 12, 15), as_of=date(2026, 10, 21))
    assert f.rule.version == 1 and f.rule.effective_to == date(2025, 12, 31)


def test_prior_auth_was_not_required_in_2025_but_is_in_2026(book):
    pa = lambda d: book.lookup(PAYER, "prior_auth", "97110", {"service_date": d}, NOW).rule.content["required"]  # noqa: E731
    assert pa(date(2025, 12, 15)) is False and pa(date(2026, 1, 15)) is True


def test_the_appeal_deadline_changes_when_the_notification_date_changes(book):
    d = lambda n: deadline(book, "appeal", PAYER, "97110", {"denial_notification_date": n}, NOW)  # noqa: E731
    before, after = d(date(2025, 12, 30)), d(date(2026, 1, 2))
    assert before.deadline.window_days == 180 and after.deadline.window_days == 120
    assert before.deadline.due == date(2025, 12, 30) + timedelta(days=180)
    assert after.deadline.due == date(2026, 5, 2)


def test_an_old_service_with_a_recent_denial_is_judged_on_the_denial_date_not_the_service_date(book):
    r = deadline(book, "appeal", PAYER, "97110",
                 {"service_date": date(2025, 12, 5), "denial_notification_date": date(2026, 9, 1)}, NOW)
    assert r.ok and not r.deadline.expired and r.deadline.due == date(2026, 12, 30) and r.deadline.days_left == 70


def test_an_old_denial_is_reported_expired_not_silently_appealed(book):
    r = deadline(book, "appeal", PAYER, "97110", {"denial_notification_date": date(2025, 12, 1)}, NOW)
    assert r.deadline.expired and r.deadline.due == date(2026, 5, 30) and r.deadline.days_left < 0


def test_appeal_and_corrected_claim_are_separate_routes_with_separate_clocks(book):
    dates = {"service_date": date(2025, 12, 5), "denial_notification_date": date(2026, 1, 20)}
    a = deadline(book, "appeal", PAYER, "99213", dates, NOW).deadline
    c = deadline(book, "corrected_claim", PAYER, "99213", dates, NOW).deadline
    assert (a.start, c.start) == (date(2026, 1, 20), date(2025, 12, 5)) and a.due != c.due and c.window_days == 365


def test_a_missing_event_date_is_a_request_not_a_guess(book):
    r = deadline(book, "appeal", PAYER, "97110", {"service_date": date(2025, 12, 5)}, NOW)
    assert not r.ok and r.problem.kind == "missing_date" and "denial_notification_date" in r.problem.ask


def test_no_rule_names_an_owner_and_what_to_add(book):
    f = book.lookup(PAYER, "coverage", "70553", {"service_date": date(2025, 12, 5)}, NOW)
    assert not f.ok and f.problem.kind == "no_rule" and f.problem.owner == "payer_rules_owner" and "70553" in f.problem.ask
    assert book.lookup("SYNNOBODY", "coverage", "97110", {"service_date": date(2025, 12, 5)}, NOW).problem.kind == "no_rule"
    assert _cov(book, date(2024, 6, 1)).problem.kind == "no_rule", "before the first rule took effect"


def test_a_fact_marked_unknown_blocks_the_deadline(book):
    r = deadline(book, "appeal", "SYNHUMANA", "97110", {"denial_notification_date": date(2026, 2, 1)}, NOW)
    assert not r.ok and r.problem.kind == "unknown_fact" and "window_days" in r.problem.message


def test_overlapping_rules_of_equal_scope_are_a_conflict(book):
    book.add(Rule(rule_id="cov-97110-other", version=1, payer=PAYER, family="coverage", service="97110",
                  date_basis="service_date", effective_from=date(2025, 6, 1), source=DEMO, content={"covered": False},
                  active_from=KNOWN_SINCE))
    f = _cov(book, date(2025, 12, 15))
    assert not f.ok and f.problem.kind == "conflict" and set(f.problem.context["rules"]) == {"cov-97110", "cov-97110-other"}


def test_a_plan_specific_rule_wins_when_the_plan_is_known_and_blocks_a_guess_when_it_is_not(book):
    book.add(Rule(rule_id="cov-97110-gold", version=1, payer=PAYER, plan="GOLD", family="coverage", service="97110",
                  date_basis="service_date", effective_from=date(2025, 1, 1), source=DEMO,
                  content={"covered": True, "visit_limit": 30}, active_from=KNOWN_SINCE))
    assert _cov(book, date(2025, 12, 15), plan="GOLD").rule.content["visit_limit"] == 30
    assert _cov(book, date(2025, 12, 15), plan="BASIC").rule.content["visit_limit"] == 20
    unsure = _cov(book, date(2025, 12, 15))
    assert not unsure.ok and unsure.problem.kind == "unknown_fact" and "plan" in unsure.problem.ask


def test_the_book_answers_as_it_knew_things_on_the_evaluation_date(book):
    book.add(Rule(rule_id="cov-70553", version=1, payer=PAYER, family="coverage", service="70553", date_basis="service_date",
                  effective_from=date(2025, 1, 1), source=DEMO, content={"covered": True}, active_from=date(2026, 3, 1)))
    d = {"service_date": date(2025, 12, 5)}
    assert book.lookup(PAYER, "coverage", "70553", d, date(2026, 2, 1)).problem.kind == "no_rule"
    assert book.lookup(PAYER, "coverage", "70553", d, date(2026, 3, 2)).ok


def test_versions_are_kept_numbered_and_retirement_is_point_in_time(book):
    assert [r.version for r in book.history("cov-97110")] == [1, 2]
    with pytest.raises(BookError, match="next version is 3"):
        book.add(Rule(rule_id="cov-97110", version=5, payer=PAYER, family="coverage", service="97110", source=DEMO,
                      date_basis="service_date", effective_from=date(2027, 1, 1), content={}, active_from=NOW))
    book.retire("cov-97110", 2, date(2026, 6, 1))
    assert _cov(book, date(2026, 2, 1), as_of=date(2026, 5, 1)).ok
    assert _cov(book, date(2026, 2, 1), as_of=date(2026, 7, 1)).problem.kind == "no_rule"


def test_business_days_skip_weekends_say_so_and_inclusivity_matters():
    b = Book()
    mk = lambda inc: Rule(rule_id=f"x{inc}", version=1, payer="P", family="denial_appeal", date_basis="denial_notification_date",  # noqa: E731
                          effective_from=date(2025, 1, 1), source=Source("demo", "t"), active_from=KNOWN_SINCE,
                          content={"window_days": 5, "day_count": "business", "inclusive": inc})
    b.add(mk(False))
    r = deadline(b, "appeal", "P", "*", {"denial_notification_date": date(2026, 3, 6)}, NOW)  # a Friday
    assert r.deadline.due == date(2026, 3, 13) and "no holiday calendar" in r.deadline.note
    b2 = Book()
    b2.add(mk(True))
    r2 = deadline(b2, "appeal", "P", "*", {"denial_notification_date": date(2026, 3, 6)}, NOW)
    assert r2.deadline.due == date(2026, 3, 12)


def test_bad_records_are_refused():
    with pytest.raises(BookError):
        Book().add(Rule(rule_id="a", version=1, payer="P", family="nonsense", date_basis="service_date", source=DEMO,
                        effective_from=date(2025, 1, 1), content={}, active_from=NOW))
    with pytest.raises(BookError):
        Book().add(Rule(rule_id="a", version=1, payer="P", family="coverage", date_basis="whenever", source=DEMO,
                        effective_from=date(2025, 1, 1), content={}, active_from=NOW))


def test_the_book_round_trips_through_json_and_every_demo_rule_is_labelled_demo(book, tmp_path):
    p = tmp_path / "book.json"
    book.save(p)
    assert Book.load(p).rules == book.rules
    assert {r.source.kind for r in book.rules} == {"demo"} and all("not official" in r.source.title for r in book.rules)


def test_the_book_never_reads_the_computer_clock():
    for f in (Path(__file__).resolve().parents[1] / "krisnnai" / "knowledge").glob("*.py"):
        assert "today()" not in f.read_text(encoding="utf-8") and "now()" not in f.read_text(encoding="utf-8"), f.name


def test_a_plan_rule_that_is_not_in_force_on_the_date_does_not_block_the_general_rule(book):
    book.add(Rule(rule_id="cov-97110-gold", version=1, payer=PAYER, plan="GOLD", family="coverage", service="97110",
                  date_basis="service_date", effective_from=date(2024, 1, 1), effective_to=date(2024, 12, 31), source=DEMO,
                  content={"covered": True}, active_from=KNOWN_SINCE))
    assert _cov(book, date(2025, 12, 15)).rule.version == 1, "the GOLD rule ended in 2024, so the plan does not matter"
