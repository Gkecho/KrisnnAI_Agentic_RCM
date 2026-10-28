"""Appointments arriving as HL7 messages and CSV files in a drop folder go through the same trigger as OpenEMR bookings (synthetic)."""

from __future__ import annotations

from datetime import date

from krisnai.live.intake import DropFolder, parse_csv, parse_hl7
from krisnai.live.trigger import Trigger

TODAY = date(2026, 10, 22)


def _in1(set_id: int, company: str, name: str, group: str, begin: str, end: str, relation: str, member: str) -> str:
    f = [""] * 37  # IN1-n sits at index n
    f[0], f[1], f[2], f[3], f[4], f[8] = "IN1", str(set_id), "PLAN", company, name, group
    f[12], f[13], f[16], f[17], f[18], f[36] = begin, end, "Hlseven^Pat", relation, "19850304", member
    return "|".join(f)


def hl7(trigger: str = "S12", appt: str = "9001", day: str = "20261105", with_ins: bool = True) -> str:
    sch = [""] * 12
    sch[0], sch[1], sch[2], sch[11] = "SCH", appt, appt, f"^^^{day}103000"
    segs = [
        "MSH|^~" + chr(92) + f"&|PMSYS|CLINIC|KRISNAI|KRISNAI|20261022090000||SIU^{trigger}|MSG{appt}|P|2.5",
        "|".join(sch),
        "PID|1||SYNHL7001^^^CLINIC||Hlseven^Pat||19850304|F",
    ]
    if with_ins:
        segs += [
            _in1(1, "SYNAETNA", "SYNAETNA Demo Payer", "GRP1", "20260101", "20271231", "SEL", "H-9001"),
            _in1(2, "SYNBLUE", "SYNBLUE Demo Payer", "GRP2", "20260101", "", "SEL", "H-9001B"),
        ]
    return chr(13).join(segs)


def _trigger(folder, tmp_path) -> Trigger:  # noqa: ANN001
    return Trigger(DropFolder(folder), tmp_path / "t", as_of=TODAY, log=lambda *_: None)


def test_the_hl7_message_is_read_into_an_appointment_with_two_policies():
    m = parse_hl7(hl7())
    assert m["appt_id"] == "9001" and m["visit"] == "2026-11-05" and m["time"] == "10:30:00" and not m["cancelled"]
    assert (m["last"], m["first"], m["dob"]) == ("Hlseven", "Pat", "1985-03-04")
    assert [(p.order, p.payer_code, p.member, p.relationship) for p in m["policies"]] == [
        (1, "SYNAETNA", "H-9001", "self"),
        (2, "SYNBLUE", "H-9001B", "self"),
    ]
    assert parse_hl7("not hl7") is None and parse_hl7(hl7(trigger="S15"))["cancelled"]


def test_an_hl7_booking_fires_once_and_sends_a_270_per_policy(tmp_path):
    folder = tmp_path / "drop"
    folder.mkdir()
    with _trigger(folder, tmp_path) as t:
        assert t.tick() == []  # a first start ignores what is already there
        (folder / "a.hl7").write_text(hl7(), encoding="utf-8")
        got = t.tick()
        assert len(got) == 1 and [c["order"] for c in got[0]["checks"]] == ["primary", "secondary"]
        assert got[0]["member"] == "SYNHL7001" and got[0]["clearance"]["cleared"]
        assert t.tick() == []  # the same file does not fire twice
        assert (folder / "a.hl7").exists()  # the folder is only read


def test_a_rescheduled_message_is_a_new_version_and_a_cancel_is_skipped(tmp_path):
    folder = tmp_path / "drop"
    folder.mkdir()
    with _trigger(folder, tmp_path) as t:
        t.tick()
        (folder / "a.hl7").write_text(hl7(), encoding="utf-8")
        assert len(t.tick()) == 1
        (folder / "b.hl7").write_text(hl7(trigger="S13", day="20261110"), encoding="utf-8")  # later file, same appointment id
        again = t.tick()
        assert len(again) == 1 and again[0]["appointment"]["pc_eventDate"] == "2026-11-10"
        (folder / "c.hl7").write_text(hl7(trigger="S15", day="20261110"), encoding="utf-8")
        assert t.tick() == []


def test_a_csv_drop_file_with_a_child_on_a_parents_policy(tmp_path):
    folder = tmp_path / "drop"
    folder.mkdir()
    head = "appointment_id,patient_id,first_name,last_name,dob,visit_date,visit_time,status,policy_order,payer_code,payer_name,member_id,plan,group_number,relationship,holder_last,holder_first,holder_dob,policy_begin,policy_end,copay\n"
    row = "C-1,SYNCSV01,Kid,Csv,2015-06-01,2026-11-06,09:15,booked,1,SYNAETNA,SYNAETNA Demo Payer,P-77,PPO,G1,child,Parent,Pat,1980-02-02,2026-01-01,2027-12-31,30\n"
    (folder / "appointments.csv").write_text(head + row, encoding="utf-8")
    rows = parse_csv(folder / "appointments.csv")
    assert rows[0]["policies"][0].copay is not None and rows[0]["time"] == "09:15:00"
    srv = DropFolder(tmp_path / "empty")
    srv.folder.mkdir()
    with _trigger(srv.folder, tmp_path) as t:
        t.tick()
        (srv.folder / "appointments.csv").write_text(head + row, encoding="utf-8")
        res = t.tick()[0]
    c = res["checks"][0]
    assert "HL*4*3*23*0" in c["x12_270"] and c["decoded"]["dependent"] == "Kid Csv (child)" and res["clearance"]["copay_due"] == "30.00"


def test_a_policy_that_has_ended_is_ignored_and_no_insurance_is_an_exception(tmp_path):
    folder = tmp_path / "drop"
    folder.mkdir()
    with _trigger(folder, tmp_path) as t:
        t.tick()
        (folder / "a.hl7").write_text(hl7(with_ins=False), encoding="utf-8")
        res = t.tick()[0]
    assert res["checks"] == [] and res["clearance"]["top_gap"] == "no_eligibility_check"


# ------------------------------------------------------------------------------ database view and manual upload


def test_a_database_view_is_read_with_a_select_only_and_fires_like_any_other_source(tmp_path):
    import pytest
    from sqlalchemy import create_engine, text

    from krisnai.live.intake import COLUMNS, DatabaseView

    url = f"sqlite:///{tmp_path / 'pm.sqlite'}"
    eng = create_engine(url)
    cols = ", ".join(f"{c} TEXT" for c in COLUMNS)
    with eng.begin() as c:
        c.execute(text(f"CREATE TABLE appt ({cols})"))
        c.execute(text("CREATE VIEW v_krisnai_appointments AS SELECT * FROM appt"))
    with pytest.raises(ValueError):
        DatabaseView(url, "v; DROP TABLE appt")  # only a plain view name is accepted
    with _trigger_for(DatabaseView(url, "v_krisnai_appointments"), tmp_path) as t:
        assert t.tick() == []
        with eng.begin() as c:
            c.execute(text("INSERT INTO appt (appointment_id, patient_id, first_name, last_name, dob, visit_date, visit_time, status, policy_order, payer_code, payer_name, member_id, relationship) VALUES ('D-1','SYNDB01','Dee','Bee','1990-05-05','2026-11-09','08:00','booked','1','SYNAETNA','SYNAETNA Demo Payer','DB-1','self')"))
        got = t.tick()
    assert len(got) == 1 and got[0]["member"] == "SYNDB01" and got[0]["clearance"]["cleared"]
    with eng.connect() as c:  # nothing was changed in the practice's data
        assert c.execute(text("SELECT count(*) FROM appt")).scalar() == 1


def _trigger_for(source, tmp_path) -> Trigger:  # noqa: ANN001
    return Trigger(source, tmp_path / "t2", as_of=TODAY, log=lambda *_: None)


def test_manual_upload_checks_the_file_and_only_a_clean_one_reaches_the_folder(tmp_path):
    from krisnai.live.intake import upload

    head = "appointment_id,patient_id,first_name,last_name,dob,visit_date\n"
    bad = tmp_path / "bad.csv"
    bad.write_text(head + "U-1,SYNUP01,A,B,1990-01-01,soon\n", encoding="utf-8")
    nocols = tmp_path / "nocols.csv"
    nocols.write_text("a,b\n1,2\n", encoding="utf-8")
    good = tmp_path / "good.csv"
    good.write_text(head + "U-2,SYNUP02,A,B,1990-01-01,2026-11-12\n", encoding="utf-8")
    drop = tmp_path / "drop"
    dest, problems = upload(bad, drop)
    assert dest is None and "not a date" in problems[0] and not drop.exists()
    assert upload(nocols, drop)[1] == ["missing column(s): appointment_id, patient_id, first_name, last_name, dob, visit_date"]
    dest, problems = upload(good, drop)
    assert problems == [] and dest.exists() and good.exists()  # copied, original untouched
    hl, bad_hl = tmp_path / "m.hl7", tmp_path / "x.hl7"
    hl.write_text(hl7(), encoding="utf-8")
    bad_hl.write_text("nothing useful", encoding="utf-8")
    assert upload(hl, drop)[1] == [] and upload(bad_hl, drop)[0] is None
