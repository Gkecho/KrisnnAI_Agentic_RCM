"""The booking trigger: a new appointment in the EMR reads the insurance, sends a 270 per payer and gets each 271 back (synthetic, local)."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from krisnnai.live.payer import PayerSim
from krisnnai.live.trigger import AppointmentWatcher, Trigger, explain, show
from krisnnai.live.writeback import WriteBack, WriteBackError

TODAY = date(2026, 10, 22)


class FakeFhir:
    """The two FHIR searches the insurance reader uses."""

    def __init__(self, server: FakeServer) -> None:
        self.server = server

    def search(self, resource: str, params: dict | None = None, page_size: int | None = None):  # noqa: ANN201
        if resource == "Organization":
            return [
                {"id": f"org-{code}", "name": f"{code} Demo Payer", "identifier": [{"value": code}]}
                for code in self.server.payers
            ]
        return [
            {"id": r["uuid"], "payor": [{"reference": f"Organization/org-{r['_payer']}"}]}
            for rows in self.server.policies.values()
            for r in rows
        ]


class FakeServer:
    """Stands in for the EMR's REST API: only GETs, like the real watcher and reader use."""

    def __init__(self) -> None:
        self.appts: list[dict] = []
        self.patients: list[dict] = []
        self.policies: dict[str, list[dict]] = {}
        self.payers: set[str] = set()
        self.calls: list[str] = []
        self.fhir = FakeFhir(self)

    def rest_rows(self, path: str) -> list[dict]:
        self.calls.append(path)
        if path.endswith("/insurance"):
            return list(self.policies.get(path.split("/")[2], []))
        return list(self.appts if path == "/appointment" else self.patients)

    def book(
        self, eid: int, member: str, day: str = "2026-10-25", title: str = "Office Visit", status: str = "-"
    ) -> None:
        self.patients.append({"pid": eid, "pubpid": member, "uuid": f"u{eid}"})
        self.appts.append({"pc_eid": str(eid), "pid": str(eid), "fname": "Synthetic", "lname": member, "DOB": "1980-01-02",
                           "pc_eventDate": day, "pc_startTime": "09:00:00", "pc_apptstatus": status, "pc_title": title})  # fmt: skip

    def insure(
        self,
        eid: int,
        order: str,
        payer: str,
        member: str,
        copay: str = "25",
        begin: str = "2026-01-01",
        end: str = "2027-12-31",
    ) -> None:
        self.payers.add(payer)
        rows = self.policies.setdefault(f"u{eid}", [])
        rows.append({"uuid": f"pol-{eid}-{len(rows)}", "_payer": payer, "type": order, "policy_number": member, "plan_name": f"{payer} PPO",
                     "group_number": "G1", "subscriber_relationship": "self", "subscriber_lname": f"L{member}", "subscriber_fname": "Pat",
                     "subscriber_DOB": "1980-01-02", "date": begin, "date_end": end, "copay": copay})  # fmt: skip


def _trigger(server: FakeServer, tmp_path, assume: bool = False, today: date = TODAY) -> Trigger:  # noqa: ANN001
    return Trigger(server, tmp_path / "t", as_of=today, log=lambda *_: None, assume_missing=assume)


def test_existing_bookings_do_not_fire_and_a_new_one_does(tmp_path):
    srv = FakeServer()
    srv.book(1, "SYNOLD001")
    with _trigger(srv, tmp_path, assume=True) as t:
        assert t.tick() == []  # the first start marks what is already there as seen
        srv.book(2, "SYNNEW002")
        got = t.tick()
        assert [g["member"] for g in got] == ["SYNNEW002"]
        d = got[0]["decoded"]
        assert d["found"] and d["active"] and d["visit_date"] == "2026-10-25"
        assert "270" in got[0]["x12_270"] and got[0]["x12_271"].startswith("ISA")
        assert got[0]["assumed"]  # no insurance and no payer: the assumption is reported
        assert t.tick() == []  # the same booking does not fire twice


def test_a_restart_does_not_replay_and_a_moved_appointment_fires_again(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path, assume=True) as t:
        srv.book(5, "SYNMOVE05")
        assert len(t.tick()) == 1
    with _trigger(srv, tmp_path, assume=True) as t2:  # new process, same state file
        assert t2.tick() == []
        srv.appts[0]["pc_eventDate"] = "2026-11-02"  # rescheduled in the EMR
        again = t2.tick()
        assert len(again) == 1 and again[0]["decoded"]["visit_date"] == "2026-11-02"


def test_cancelled_bookings_are_skipped_and_the_watcher_only_reads(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path, assume=True) as t:
        srv.book(7, "SYNCANC07", status="x")
        assert t.tick() == []
        assert t.tick() == []  # and it is remembered, not re-examined
    assert all(
        c.startswith("/patient") or c == "/appointment" for c in srv.calls
    )  # only GET list paths exist on the fake


def test_a_member_the_payer_marks_inactive_or_unknown_is_reported(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(8, "SYNLAPSE8", title="krisnnai:appt=A8;payer=SYNAETNA")
        t.payers["SYNAETNA"].enrol("SYNLAPSE8", active=False)
        res = t.tick()[0]
        assert res["decoded"]["found"] and res["decoded"]["active"] is False
        assert res["payer"] == "SYNAETNA"
        assert (
            res["clearance"]["top_gap"] == "coverage_inactive"
            and res["clearance"]["action"] == "a1_coverage_exception_review"
        )
        srv.book(9, "SYNGHOST9", title="krisnnai:appt=A9;payer=OTHERPAYER")
        res2 = t.tick()[
            0
        ]  # a payer the demo has not met yet is created, and the unknown member is enrolled and reported
        assert res2["payer"] == "OTHERPAYER" and res2["decoded"]["found"] is True
        assert any("enrolled" in a for a in res2["assumed"])


def test_files_and_explanation_are_written(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path, assume=True) as t:
        t.tick()
        srv.book(3, "SYNFILE03")
        res = t.tick()[0]
    folder = tmp_path / "t" / "TRG000003"
    assert (folder / "270.x12").exists() and (folder / "271.x12").exists() and (folder / "result.json").exists()
    assert (tmp_path / "t" / "inbox" / "271_TRG000003.x12").exists()
    assert any("ACTIVE" in x["note"] for x in explain(res["x12_271"]))
    assert all(x["note"] for x in explain(res["x12_270"]) if x["text"].startswith(("NM1*PR", "DTP*291", "EQ")))


def test_watcher_state_file_survives(tmp_path):
    srv = FakeServer()
    srv.book(1, "SYNA1")
    w = AppointmentWatcher(srv, tmp_path / "s.json")
    assert w.baseline() == 1
    assert AppointmentWatcher(srv, tmp_path / "s.json").poll() == []


# --------------------------------------------------------------------------------- insurance read, copay, several payers
def test_no_insurance_is_an_exception_not_an_assumed_payer(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(11, "SYNNOINS11")
        res = t.tick()[0]
    assert res["checks"] == [] and res["x12_270"] == "" and res["decoded"]["found"] is False
    assert res["clearance"]["action"] == "a1_eligibility_check_task" and res["clearance"]["owner"] == "front_desk"
    assert "no insurance on file" in res["clearance"]["gaps"][0]["detail"]
    assert (tmp_path / "t" / "TRG000011" / "result.json").exists()


def test_the_insurance_record_supplies_payer_member_and_copay(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(12, "SYNREC012")
        srv.insure(12, "primary", "SYNAETNA", "POL-12345", copay="30")
        res = t.tick()[0]
    d = res["decoded"]
    assert res["payer"] == "SYNAETNA" and d["member"] == "POL-12345"  # the policy number, not the chart number
    assert d["copay"] == "30.00" and res["clearance"]["copay_due"] == "30.00" and res["clearance"]["cleared"]
    assert "NM1*IL*1*LPOL-12345*Pat" in res["x12_270"]  # the policyholder on the record is the subscriber of the 270


def test_a_policy_not_in_force_on_the_visit_date_is_ignored(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(13, "SYNOLDPOL13", day="2026-10-25")
        srv.insure(13, "primary", "SYNAETNA", "OLD-1", end="2026-06-30")
        srv.insure(13, "primary", "SYNBLUE", "NEW-1", begin="2026-07-01")
        res = t.tick()[0]
    assert [c["payer"] for c in res["checks"]] == ["SYNBLUE"]


def test_two_payers_get_two_270s_and_the_secondary_naming_the_primary_is_not_a_problem(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(14, "SYNTWO014")
        srv.insure(
            14, "secondary", "SYNBLUE", "B-14", copay="10"
        )  # entered second on purpose: the order must follow the type
        srv.insure(14, "primary", "SYNAETNA", "A-14", copay="25")
        res = t.tick()[0]
    assert [c["order"] for c in res["checks"]] == ["primary", "secondary"]
    assert "A-14" in res["checks"][0]["x12_270"] and "B-14" in res["checks"][1]["x12_270"]
    assert (
        res["checks"][1]["decoded"]["other_payer"] == "SYNAETNA Demo Payer"
    )  # the secondary's 271 says the other plan pays first
    assert res["checks"][0]["decoded"]["other_payer"] is None
    assert res["clearance"]["cleared"] and res["clearance"]["copay_due"] == "25.00"
    folder = tmp_path / "t" / "TRG000014"
    assert (folder / "270_2.x12").exists() and (folder / "271_2.x12").exists()


def test_a_primary_that_says_another_plan_is_primary_goes_to_the_front_desk(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(15, "SYNCOB015")
        srv.insure(15, "primary", "SYNAETNA", "A-15")
        t.payers.setdefault("SYNAETNA", PayerSim("SYNAETNA", "SYNAETNA Demo Payer")).cob["A-15"] = "SOME OTHER PLAN"
        res = t.tick()[0]
    assert res["clearance"]["top_gap"] == "cob_other_payer" and res["clearance"]["action"] == "a1_cob_review"


def test_a_lapsed_secondary_is_reported_with_which_payer(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(16, "SYNLAPSE16")
        srv.insure(16, "primary", "SYNAETNA", "A-16")
        srv.insure(16, "secondary", "SYNBLUE", "B-16")
        t.tick()  # first booking check enrols both; now the secondary lapses and the next check (a re-check) sees it
        t.payers["SYNBLUE"].enrol("B-16", active=False)
        t.advance(date(2026, 10, 24))
        res = t.tick()[0]
    gap = res["clearance"]["gaps"][0]
    assert gap["kind"] == "coverage_inactive" and gap["payer"] == "SYNBLUE" and gap["order"] == "secondary"


# ------------------------------------------------------------------------------------------------------- re-checks
def test_rechecks_run_three_days_and_one_day_before_the_visit_once_each(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(20, "SYNRECHK20", day=(TODAY + timedelta(days=10)).isoformat())
        srv.insure(20, "primary", "SYNAETNA", "A-20")
        assert [r["kind"] for r in t.tick()] == ["booking"]
        assert t.tick() == []  # nothing due yet
        t.advance(TODAY + timedelta(days=7))  # 3 days before
        assert [r["kind"] for r in t.tick()] == ["recheck-3d"]
        assert t.tick() == []  # not again
        t.advance(TODAY + timedelta(days=9))  # 1 day before
        assert [r["kind"] for r in t.tick()] == ["recheck-1d"]
        t.advance(TODAY + timedelta(days=10))
        assert t.tick() == []
    assert (tmp_path / "t" / "TRG000020_recheck3d" / "result.json").exists()


def test_a_recheck_catches_coverage_that_lapsed_after_booking(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(21, "SYNLAPSE21", day=(TODAY + timedelta(days=10)).isoformat())
        srv.insure(21, "primary", "SYNAETNA", "A-21")
        assert t.tick()[0]["clearance"]["cleared"]
        t.payers["SYNAETNA"].enrol("A-21", active=False)
        t.advance(TODAY + timedelta(days=7))
        res = t.tick()[0]
    assert res["kind"] == "recheck-3d" and res["clearance"]["top_gap"] == "coverage_inactive"


def test_a_booking_inside_the_window_is_not_checked_twice_and_cancelled_or_moved_ones_drop_out(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path, assume=True) as t:
        t.tick()
        srv.book(
            22, "SYNNEAR22", day=(TODAY + timedelta(days=2)).isoformat()
        )  # 2 days out: the 3-day checkpoint is already served
        assert [r["kind"] for r in t.tick()] == ["booking"]
        t.advance(TODAY + timedelta(days=1))
        assert [r["kind"] for r in t.tick()] == ["recheck-1d"]
        srv.book(23, "SYNCANC23", day=(TODAY + timedelta(days=8)).isoformat())
        t.tick()
        srv.appts[-1]["pc_apptstatus"] = "x"  # cancelled after booking
        t.advance(TODAY + timedelta(days=5))
        assert t.tick() == [] and "23" not in t.visits


# ---------------------------------------------------------------------------------------------------------- write-back
class PostingServer(FakeServer):
    def __init__(self) -> None:
        super().__init__()
        self.posts: list[tuple[str, str, dict]] = []

    def rest_json(self, method: str, path: str, **kw):  # noqa: ANN003, ANN201
        self.posts.append((method, path, kw["json"]))
        return {"data": {"id": 1}}


def _with_note(tmp_path, enabled: bool = False):  # noqa: ANN001, ANN202
    srv = PostingServer()
    wb = WriteBack(srv, tmp_path / "wb", enabled=enabled)
    t = Trigger(srv, tmp_path / "t", as_of=TODAY, log=lambda *_: None, writeback=wb)
    return srv, wb, t


def test_the_trigger_only_proposes_a_note_and_the_adapter_is_off_by_default(tmp_path):
    srv, wb, t = _with_note(tmp_path)
    with t:
        t.tick()
        srv.book(30, "SYNWB030")
        srv.insure(30, "primary", "SYNAETNA", "A-30", copay="40")
        res = t.tick()[0]
    assert res["writeback"]["state"] == "proposed"
    assert srv.posts == []  # nothing was written to the EMR
    key = res["writeback"]["key"]
    assert (
        "copay 40.00" in wb.items[key]["proposal"]["body"]
        and "No insurance or appointment data was changed" in wb.items[key]["proposal"]["body"]
    )
    with pytest.raises(WriteBackError, match="switched off"):
        wb.approve(key, "Manager A")
    assert srv.posts == []


def test_a_note_is_sent_once_only_with_the_adapter_on_and_a_named_approver(tmp_path):
    srv, wb, t = _with_note(tmp_path, enabled=True)
    with t:
        t.tick()
        srv.book(31, "SYNWB031")
        srv.insure(31, "primary", "SYNAETNA", "A-31")
        key = t.tick()[0]["writeback"]["key"]
    with pytest.raises(WriteBackError, match="named approver"):
        wb.approve(key, "  ")
    assert srv.posts == []
    wb.approve(key, "Manager A")
    ((method, path, body),) = srv.posts
    assert method == "POST" and path == "/patient/31/message" and body["from"] == "krisnnai" and body["to"] == "admin"
    with pytest.raises(WriteBackError, match="already sent"):
        wb.approve(key, "Manager A")
    assert len(srv.posts) == 1
    log = [json.loads(x) for x in (tmp_path / "wb" / "writeback.jsonl").read_text().splitlines()]
    assert [x["what"] for x in log] == ["proposed", "sent"] and log[1]["approver"] == "Manager A"


def test_only_notes_can_be_written_and_a_missing_proposal_is_refused(tmp_path):
    srv, wb, _ = _with_note(tmp_path, enabled=True)
    for kind in ("appointment_status", "insurance", "demographics"):
        with pytest.raises(WriteBackError, match="only notes and tasks"):
            wb.approve("x", "Manager A", kind=kind)
    with pytest.raises(WriteBackError, match="no proposal"):
        wb.approve("nope|booking", "Manager A")
    assert srv.posts == []


def test_a_no_insurance_note_says_so_and_a_second_proposal_is_not_duplicated(tmp_path):
    srv, wb, t = _with_note(tmp_path)
    with t:
        t.tick()
        srv.book(32, "SYNWB032")
        res = t.tick()[0]
        again = wb.propose(res)
    assert "No insurance is on file" in wb.items[res["writeback"]["key"]]["proposal"]["body"]
    assert again["key"] == res["writeback"]["key"] and len(wb.items) == 1


# ------------------------------------------------------------------------------------ the full A1 agent (decision records)


def _agent_trigger(server: FakeServer, tmp_path) -> Trigger:  # noqa: ANN001
    from krisnnai.live.shadow_book import ShadowBook

    return Trigger(server, tmp_path / "t", as_of=TODAY, log=lambda *_: None, book=ShadowBook(tmp_path / "t"))


def test_the_full_agent_runs_on_a_clean_booking_and_writes_a_shadow_decision_record(tmp_path):
    srv = FakeServer()
    with _agent_trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(30, "SYNAGT030")
        srv.insure(30, "primary", "SYNAETNA", "A-30")
        res = t.tick()[0]
    ag = res["agent"]
    assert ag["ran"] and ag["created"] and ag["action"] == "no_action" and ag["mode"] == "shadow" and ag["level"] == "L0"
    assert "coverage_active=ok" in ag["rules"] and "no_other_primary=ok" in ag["rules"]
    assert "the decision record" in show(res)


def test_the_agent_proposes_a_cob_review_when_the_payer_names_another_primary(tmp_path):
    srv = FakeServer()
    with _agent_trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(31, "SYNAGT031")
        srv.insure(31, "primary", "SYNAETNA", "A-31")
        t.payers.setdefault("SYNAETNA", PayerSim("SYNAETNA", "SYNAETNA Demo Payer")).cob["A-31"] = "SOME OTHER PLAN"
        ag = t.tick()[0]["agent"]
    assert ag["action"] == "a1_cob_review" and "no_other_primary=FAILED" in ag["rules"] and ag["mode"] == "shadow"


def test_the_same_check_twice_gives_one_decision_record(tmp_path):
    srv = FakeServer()
    with _agent_trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(32, "SYNAGT032")
        srv.insure(32, "primary", "SYNAETNA", "A-32")
        res = t.tick()[0]
        again = t.book.record(res)
    assert again["record_id"] == res["agent"]["record_id"] and again["created"] is False


def test_no_insurance_means_the_agent_has_nothing_to_read(tmp_path):
    srv = FakeServer()
    with _agent_trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(33, "SYNAGT033")
        res = t.tick()[0]
    assert res["agent"]["ran"] is False and "no insurance" in res["agent"]["why"]


# ------------------------------------------------------------------------------------------------ the dependent loop


def _child_policy(srv: FakeServer, eid: int, relation: str = "child") -> None:
    srv.insure(eid, "primary", "SYNAETNA", f"A-{eid}")
    srv.policies[f"u{eid}"][0].update(subscriber_relationship=relation, subscriber_lname="Parent", subscriber_fname="Pat")


def test_a_child_on_a_parents_policy_is_asked_in_a_dependent_level(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(40, "SYNKID040")
        _child_policy(srv, 40)
        res = t.tick()[0]
    c = res["checks"][0]
    x270, x271 = c["x12_270"], c["x12_271"]
    assert "HL*4*3*23*0" in x270 and "NM1*03*1*SYNKID040*Synthetic" in x270 and "INS*N*19" in x270
    assert "NM1*IL*1*Parent*Pat" in x270  # the policyholder is still the subscriber
    assert "HL*4*3*23*0" in x271 and "NM1*03*1*SYNKID040*Synthetic" in x271
    assert c["decoded"]["found"] and c["decoded"]["active"] and c["decoded"]["dependent"] == "Synthetic SYNKID040 (child)"
    assert res["clearance"]["cleared"]
    assert any("dependent level (HL 23)" in n for n in res["assumed"])


def test_a_spouse_is_sent_as_relationship_01_and_a_policyholder_has_no_dependent_level(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(41, "SYNSPO041")
        _child_policy(srv, 41, "spouse")
        srv.book(42, "SYNSELF42")
        srv.insure(42, "primary", "SYNAETNA", "A-42")
        a, b = t.tick()
    assert "INS*N*01" in a["checks"][0]["x12_270"]
    assert "*23*" not in b["checks"][0]["x12_270"] and b["checks"][0]["decoded"]["dependent"] is None


def test_a_dependent_the_payer_does_not_cover_is_a_coverage_problem_even_though_the_policyholder_is_active(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(43, "SYNKID043")
        _child_policy(srv, 43)
        t.payers.setdefault("SYNAETNA", PayerSim("SYNAETNA", "SYNAETNA Demo Payer")).dependents["A-43|SYNTHETIC"] = False
        res = t.tick()[0]
    assert res["checks"][0]["decoded"]["active"] is False
    assert res["clearance"]["top_gap"] == "coverage_inactive" and res["clearance"]["action"] == "a1_coverage_exception_review"


# ------------------------------------------------------------------------------------------------ the coverage-order review


def _two(srv: FakeServer, eid: int, first: tuple[str, str], second: tuple[str, str], **rel) -> None:
    """Enter two policies: (payer, member) as primary and as secondary. rel: first_rel, second_rel, first_dob, second_dob."""
    srv.insure(eid, "primary", *first)
    srv.insure(eid, "secondary", *second)
    rows = srv.policies[f"u{eid}"]
    for row, k in zip(rows, ("first", "second"), strict=True):
        row["subscriber_relationship"] = rel.get(f"{k}_rel", "self")
        row["subscriber_DOB"] = rel.get(f"{k}_dob", "1980-01-02")


def _order_rules(res: dict) -> set[str]:
    return {f["rule"] for f in res["order_review"]}


def test_medicaid_listed_before_another_coverage_is_sent_to_cob_review(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(50, "SYNMCD050")
        _two(srv, 50, ("SYNMEDICAID", "M-50"), ("SYNAETNA", "A-50"))
        res = t.tick()[0]
    assert "medicaid_last" in _order_rules(res)
    assert res["clearance"]["top_gap"] == "cob_other_payer" and res["clearance"]["action"] == "a1_cob_review"
    assert any("coverage order to confirm" in g["detail"] for g in res["clearance"]["gaps"])


def test_the_right_order_raises_nothing(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(51, "SYNOK0051")
        _two(srv, 51, ("SYNAETNA", "A-51"), ("SYNMEDICAID", "M-51"))
        res = t.tick()[0]
    assert res["order_review"] == []


def test_own_plan_before_a_spouse_plan_is_fine_and_after_it_is_flagged(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(52, "SYNOWN052")
        _two(srv, 52, ("SYNAETNA", "A-52"), ("SYNBLUE", "B-52"), first_rel="spouse", second_rel="self")
        res = t.tick()[0]
    assert _order_rules(res) == {"own_plan_first"}


def test_birthday_rule_for_a_child_on_both_parents_plans(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(53, "SYNKID053")
        srv.book(54, "SYNKID054")
        # listed: father (born March 9) first, mother (born January 5) second -> the mother's birthday is earlier in the year
        _two(srv, 53, ("SYNAETNA", "A-53"), ("SYNBLUE", "B-53"), first_rel="child", second_rel="child", first_dob="1975-03-09", second_dob="1978-01-05")
        _two(srv, 54, ("SYNAETNA", "A-54"), ("SYNBLUE", "B-54"), first_rel="child", second_rel="child", first_dob="1978-01-05", second_dob="1975-03-09")
        wrong, right = t.tick()
    assert _order_rules(wrong) == {"birthday_rule"} and _order_rules(right) == set()


def test_medicare_first_with_a_work_plan_and_workers_comp_not_first_ask_for_confirmation(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(55, "SYNMED055")
        srv.book(56, "SYNWC0056")
        _two(srv, 55, ("SYNMEDICARE", "R-55"), ("SYNAETNA", "A-55"))
        _two(srv, 56, ("SYNAETNA", "A-56"), ("SYNWORKERSCOMP", "W-56"))
        medicare, wc = t.tick()
    assert _order_rules(medicare) == {"medicare_first"} and _order_rules(wc) == {"injury_first"}


def test_a_duplicate_policy_and_a_single_policy(tmp_path):
    srv = FakeServer()
    with _trigger(srv, tmp_path) as t:
        t.tick()
        srv.book(57, "SYNDUP057")
        srv.book(58, "SYNONE058")
        _two(srv, 57, ("SYNAETNA", "A-57"), ("SYNAETNA", "A-57"))
        srv.insure(58, "primary", "SYNMEDICAID", "M-58")
        dup, one = t.tick()
    assert "duplicate_policy" in _order_rules(dup) and one["order_review"] == []


# ------------------------------------------------------------------------------------ prior authorization (A2 mock)


def _auth_trigger(server: FakeServer, tmp_path, service: dict | None, deny: dict | None = None) -> Trigger:  # noqa: ANN001
    return Trigger(server, tmp_path / "t", as_of=TODAY, log=lambda *_: None, default_service=service, auth_deny=deny)


def _auth(tmp_path, service: dict | None, deny: dict | None = None, eid: int = 60, payer: str = "SYNAETNA") -> tuple[dict, Trigger]:  # noqa: ANN001
    srv = FakeServer()
    with _auth_trigger(srv, tmp_path, service, deny) as t:
        t.tick()
        srv.book(eid, f"SYNAUTH{eid}")
        srv.insure(eid, "primary", payer, f"A-{eid}")
        res = t.tick()[0]
    return res, t


def test_a_required_authorization_is_requested_certified_and_the_payer_sim_learns_it(tmp_path):
    res, t = _auth(tmp_path, {"cpt": "72148", "units": 1, "dx": "M5126"})
    au = res["prior_auth"]
    assert au["need"]["status"] == "required" and au["outcome"] == "certified"
    assert "UM*HS*I*1" in au["x12_278"] and "SV1*HC:72148" in au["x12_278"] and "HCR*A1*SYNAUTH" in au["x12_278_response"]
    assert au["decoded"]["valid_from"] == "2026-10-25" and au["decoded"]["units"] == 1
    assert ("A-60", "72148") in t.payers["SYNAETNA"].auths  # a later claim would not be denied with CARC 197
    folder = tmp_path / "t" / "TRG000060"
    assert (folder / "278.x12").exists() and (folder / "278_response.x12").exists()
    assert "keep the appointment" in au["suggestion"]


def test_the_same_request_gives_the_same_authorization_number(tmp_path):
    a, _ = _auth(tmp_path / "one", {"cpt": "72148"})
    b, _ = _auth(tmp_path / "two", {"cpt": "72148"})
    assert a["prior_auth"]["decoded"]["auth_number"] == b["prior_auth"]["decoded"]["auth_number"]


def test_a_service_the_rules_say_needs_no_authorization_sends_no_278_and_a_listed_service_without_a_rule_is_unknown(tmp_path):
    from krisnnai.live import prior_auth

    # SYNAETNA's rule for 70450 only starts in 2026: for a 2025 visit the rule says "not required"
    assert prior_auth.need("SYNAETNA", "70450", date(2025, 6, 2), TODAY)["status"] == "not_required"
    assert prior_auth.need("SYNAETNA", "70450", date(2026, 10, 25), TODAY)["status"] == "required"
    # the book lists only what needs authorization: a service with no rule is "unknown" (confirm), not "not required"
    res, _ = _auth(tmp_path, {"cpt": "99213"})
    au = res["prior_auth"]
    assert au["outcome"] == "unknown" and "x12_278" not in au and not (tmp_path / "t" / "TRG000060" / "278.x12").exists()


def test_no_planned_procedure_or_no_rule_is_unknown_never_not_required(tmp_path):
    none_, _ = _auth(tmp_path / "a", None)
    other, _ = _auth(tmp_path / "b", {"cpt": "72148"}, eid=61, payer="SYNNORULE")
    assert none_["prior_auth"]["outcome"] == "unknown" and "no planned procedure" in none_["prior_auth"]["note"]
    assert other["prior_auth"]["outcome"] == "unknown" and "front desk to confirm" in other["prior_auth"]["suggestion"]


def test_missing_documents_pend_and_a_scripted_denial_is_not_certified(tmp_path):
    pended, t = _auth(tmp_path / "a", {"cpt": "72148", "docs": False})
    denied, t2 = _auth(tmp_path / "b", {"cpt": "72148"}, deny={("A-60", "72148"): "not medically necessary on the information sent"})
    assert pended["prior_auth"]["outcome"] == "pended" and "HCR*A4" in pended["prior_auth"]["x12_278_response"]
    assert ("A-60", "72148") not in t.payers["SYNAETNA"].auths and "hold" in pended["prior_auth"]["suggestion"]
    assert denied["prior_auth"]["outcome"] == "not_certified" and ("A-60", "72148") not in t2.payers["SYNAETNA"].auths
    assert "not medically necessary" in denied["prior_auth"]["note"]


def test_an_authorization_number_already_on_file_means_no_request(tmp_path):
    res, _ = _auth(tmp_path, {"cpt": "72148", "auth_number": "PM-12345"})
    au = res["prior_auth"]
    assert au["outcome"] == "on_file" and au["auth_number"] == "PM-12345" and "x12_278" not in au


def test_the_278_answer_decoder_hands_an_unknown_action_to_a_person_and_the_note_carries_the_result(tmp_path):
    from krisnnai.live import prior_auth

    resp = prior_auth.write_278_response(
        {"payer": "SYNAETNA", "member": "M1", "ref": "R1", "cpt": "72148", "dos": date(2026, 10, 25)}, "P", "A9", 1, 5, TODAY, 90
    )
    dec = prior_auth.decode_278(resp)
    assert dec["outcome"] == "unknown_action" and "a person must read" in dec["message"]
    res, _ = _auth(tmp_path, {"cpt": "72148"})
    from krisnnai.live.writeback import build_note

    assert "Prior authorization (72148, SYNAETNA): certified" in build_note(res)["body"]
