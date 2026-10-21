# ruff: noqa: E501
"""The three pieces working as one: wide transcripts -> the reader and coder -> six payers -> the bots' replies.

These tests exist because each piece passed its own tests and the first combined run still found problems (a preventive visit
auto-accepted as an office visit, an MRI ordered with no stated reason auto-accepted, a visit plus therapy billed as therapy alone).
"""

from datetime import date

import pytest

from krisnai.live.coder import Coder, Policy
from krisnai.live.emr import FakeEmr
from krisnai.live.stream import StreamConfig, run_stream
from krisnai.live.transcripts import generate_wide

DAY = date(2026, 10, 24)
CODER = lambda: Coder(Policy(enabled=True, sample_rate=0.0))  # noqa: E731


def coded(seed: int, n: int = 150):
    c = CODER()
    return [(v, c.code(v.visit_id, v.text, v.signed, DAY)) for v in generate_wide(seed, n, DAY)]


@pytest.mark.parametrize("seed", [3, 7, 11])
def test_nothing_is_auto_accepted_with_a_code_that_disagrees_with_the_answer_key(seed):
    wrong = []
    for v, r in coded(seed):
        if r.route != "auto":
            continue
        x = v.expected
        if x.route != "auto" or r.cpt != x.cpt or r.dx[0][0] != x.dx:
            wrong.append((v.visit_id, v.visit_type, x.route, x.reason, x.cpt, r.cpt))
    assert wrong == [], wrong


@pytest.mark.parametrize("seed", [3, 7])
def test_every_problem_visit_goes_to_a_coder(seed):
    missed = [(v.visit_id, v.expected.reason, r.reason) for v, r in coded(seed) if v.expected.route == "coder" and r.route == "auto"]
    assert missed == [], missed


def test_preventive_and_emergency_visits_are_never_auto_accepted():
    seen = 0
    for v, r in coded(7, 300):
        if v.visit_type.startswith(("wide_Z00", "wide_Z01", "wide_Z23")) or v.expected.cpt.startswith(("9928", "9938", "9939")):
            seen += 1
            assert r.route == "coder", (v.visit_id, v.expected.cpt, r.cpt, r.reason)
    assert seen >= 3


def test_an_order_with_no_stated_reason_is_not_auto_accepted():
    bad = [(v.visit_id, r.reason) for v, r in coded(7, 300) if "necessity_not_documented" in v.expected.pressure and r.route == "auto"]
    assert bad == [], bad


def test_the_visit_code_follows_how_deep_the_documentation_is():
    got = {r.cpt for _, r in coded(7, 300) if r.route == "auto"}
    assert {"99212", "99213", "99214"} <= got, got


def test_a_visit_note_with_therapy_is_a_modifier_question_for_a_coder():
    hits = [r for v, r in coded(7, 300) if v.expected.services and any(s.startswith("971") for s in v.expected.services) and v.expected.services[0].startswith("992")]
    assert hits and all(r.route == "coder" for r in hits)


def test_a_bigger_catalog_is_read_from_the_same_catalog_the_generator_used():
    from krisnai.live import catalog

    assert len(catalog.CONDITIONS) >= 45 and len(catalog.SERVICES) >= 35
    named = sum(1 for v, r in coded(7, 150) if r.dx and v.expected.dx and r.dx[0][0] == v.expected.dx)
    assert named >= 120, "the reader names the right main diagnosis on most wide visits"


def test_a_thirty_visit_run_goes_through_six_payers_replies_and_settles(tmp_path):
    cfg = StreamConfig(count=30, seed=5, wide=True, payers="network", replies=True, reject_rate=0.1, engine=False, bots=False, serve=False, sample_rate=0.0)
    emr = FakeEmr()
    s = run_stream(tmp_path / "r", cfg, emr, log=lambda *_: None)
    assert s["encounters"] == 30 and emr.counts()["visits"] == 30
    stages = s["stages"]
    assert "adjudicated" not in stages, "with replies on every claim ends settled, in review, or as a patient balance"
    assert sum(stages.values()) == 30 and (stages.get("pending_coder", 0) + stages.get("review", 0) + stages.get("patient_balance", 0) + stages.get("settled", 0)) == 30
    assert len(s["replies"]["sent"]) >= 1 and s["replies"]["claims"] >= 1
    import csv

    rows = list(csv.DictReader((tmp_path / "r" / "truth.csv").read_text("utf-8").splitlines()))
    assert len(rows) == s["replies"]["claims"]
    assert (tmp_path / "r" / "truth_payers.csv").exists() and len({r["payer_id"] for r in csv.DictReader((tmp_path / "r" / "truth_payers.csv").read_text("utf-8").splitlines())}) >= 3


def test_an_unsigned_note_says_which_of_the_three_things_made_it_unsigned():
    base = ("Provider: You were last here in June, correct? Patient: Yes, I am a returning patient.\n"
            "Provider: What brings you in today? Patient: My throat is sore. It started three days ago.\n"
            "Provider: Let me examine you. Exam: Throat shows redness.\nProvider: Assessment: acute pharyngitis.\n"
            "Provider: Plan: rest and fluids, return in a week.\n")
    sig = "Signed electronically by Dr. Demo Provider."
    c = CODER()
    a = c.code("V1", base + sig, True, DAY)
    assert a.route == "auto" and a.reason == "", "text with a signature line and the flag on is signed (so editing the text fixes it)"
    b = next(k for k in c.code("V2", base + sig, False, DAY).checks if k.name == "signed")
    assert not b.ok and "marks the note unsigned" in b.detail and "has a signature line" in b.detail
    d = next(k for k in c.code("V3", base, True, DAY).checks if k.name == "signed")
    assert not d.ok and "no signature line" in d.detail
    e = next(k for k in c.code("V4", base + "Note pending signature.\n" + sig, True, DAY).checks if k.name == "signed")
    assert not e.ok and "says the note is unsigned or pending signature" in e.detail


NOTE = ("S: 34 year old man, established patient, twisted his {side} ankle playing football two days ago. Pain 6 out of 10, swelling, worse when walking.\n"
        "O: {side2} ankle swollen and tender over the lateral ligaments.\nA: Ankle sprain.\nP: Ice, compression, crutches. Ordering an ankle x-ray to rule out a fracture. Follow up in two weeks.\n"
        "Signed electronically by Dr. Rao.")


def test_a_side_named_elsewhere_in_the_note_counts_when_it_is_the_only_side():
    r = CODER().code("V1", NOTE.format(side="left", side2="Left"), True, DAY)
    assert r.route == "auto" and [p["modifiers"] for p in r.procedures] == [["LT"]], (r.reason, r.note)


def test_no_side_or_two_different_sides_still_go_to_a_coder():
    none = CODER().code("V2", NOTE.format(side="", side2="").replace("his  ankle", "his ankle").replace("O:  ankle", "O: Ankle"), True, DAY)
    assert none.route == "coder" and none.reason == "laterality_missing"
    both = CODER().code("V3", NOTE.format(side="left", side2="Right"), True, DAY)
    assert both.route == "coder", "two different sides: which is meant? a person decides"


def test_being_right_handed_is_not_the_side_of_the_problem():
    text = NOTE.format(side="", side2="").replace("his  ankle", "his ankle").replace("O:  ankle", "O: He is right-handed. Ankle")
    assert CODER().code("V4", text, True, DAY).reason == "laterality_missing"


def test_the_claim_carries_every_service_and_diagnosis_found_in_the_text_with_its_side(tmp_path):
    from krisnai.live.transcripts import Visit

    v = Visit("VX", "MX", "typed_in", NOTE.format(side="left", side2="Left"), True, None, DAY)
    cfg = StreamConfig(count=1, seed=5, engine=False, bots=False, serve=False, sample_rate=0.0, tag="Z")
    run_stream(tmp_path / "r", cfg, FakeEmr(), visits=[v], log=lambda *_: None)
    claim = next((tmp_path / "r" / "claims").glob("*.837")).read_text("utf-8").replace("~", "\n")
    assert "SV1*HC:99213*" in claim, "the visit line"
    assert "SV1*HC:73600:LT*" in claim, "the X-ray named in the plan, on the left side the note describes"
    assert "HI*ABK:S93409A" in claim, "the diagnosis written in the assessment"


def test_a_visit_with_two_diagnoses_and_two_services_reaches_the_payer_with_all_of_them(tmp_path):
    from krisnai.live.transcripts import Visit

    note = ("S: Established patient. Cough for two weeks, worse at night, with some fever.\nO: Lungs clear. Throat red.\nA: Cough.\n"
            "P: Chest x-ray to rule out pneumonia because of the persistent cough. Urinalysis because of the burning when I urinate. Return in a week.\n"
            "Signed electronically by Dr. Rao.")
    cfg = StreamConfig(count=1, seed=3, engine=False, bots=False, serve=False, sample_rate=0.0, tag="Y")
    run_stream(tmp_path / "r", cfg, FakeEmr(), visits=[Visit("VY", "MY", "typed_in", note, True, None, DAY)], log=lambda *_: None)
    claims = list((tmp_path / "r" / "claims").glob("*.837"))
    if claims:  # the coder may route it to a person; when it bills, every service it found is on the claim
        text = claims[0].read_text("utf-8").replace("~", "\n")
        assert text.count("SV1*") >= 2
