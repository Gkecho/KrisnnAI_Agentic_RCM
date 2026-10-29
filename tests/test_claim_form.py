# ruff: noqa: E501
"""The CMS-1500 view: the form is read back from the 837P claim file, so it shows exactly what the file says."""

from pathlib import Path

from krisnnai.live.claim_form import claim_form
from krisnnai.live.emr import FakeEmr
from krisnnai.live.stream import StreamConfig, run_stream
from krisnnai.live.transcripts import Visit

FIXTURE = Path(__file__).parent / "fixtures" / "openemr_837p_synthetic.x12"


def test_the_form_is_read_from_a_real_openemr_claim_file():
    d = claim_form(FIXTURE.read_text(encoding="utf-8"))
    f, lines = d["form"], d["lines"]
    assert f["claim"]["id"] == "51-1635" and f["claim"]["total"] == "110.00" and f["claim"]["pos"] == "11"
    assert [x["code"] for x in f["dx"]] == ["J029"] and f["dx"][0]["letter"] == "A"
    assert f["lines"][0]["cpt"] == "99213" and f["lines"][0]["date"] == "10/24/2026" and f["lines"][0]["pointer"] == "1"
    assert f["patient"]["member"] and f["payer"]["id"] == "SYNAETNA" and f["billing"]["npi"] == "1999999984"
    assert f["tax_id"]["value"] == "123456789" and f["rendering"]["npi"] == "1234567893"
    assert lines[f["dx"][0]["seg"]]["text"].startswith("HI*"), "a field points at the EDI line it came from"
    assert lines[f["lines"][0]["seg"]]["text"].startswith("SV1*HC:99213") and lines[f["claim"]["seg"]]["id"] == "CLM"


def test_every_line_of_the_file_has_a_plain_word_explanation_where_one_exists():
    d = claim_form(FIXTURE.read_text(encoding="utf-8"))
    notes = {x["id"]: x["note"] for x in d["lines"]}
    assert notes["HI"] and notes["SV1"] and notes["CLM"] and notes["DMG"]


def test_a_claim_with_two_services_and_a_side_shows_both_lines_and_the_modifier(tmp_path):
    note = ("S: 34 year old man, established patient, twisted his left ankle two days ago. Pain 6 out of 10, swelling, worse when walking.\n"
            "O: Left ankle swollen and tender over the lateral ligaments.\nA: Ankle sprain.\nP: Ice, compression. Ordering an ankle x-ray to rule out a fracture. Follow up in two weeks.\n"
            "Signed electronically by Dr. Rao.")
    cfg = StreamConfig(count=1, seed=5, engine=False, bots=False, serve=False, sample_rate=0.0, tag="F")
    run_stream(tmp_path / "r", cfg, FakeEmr(), visits=[Visit("VF", "MF", "typed_in", note, True, None, __import__("datetime").date(2026, 10, 24))], log=lambda *_: None)
    d = claim_form(next((tmp_path / "r" / "claims").glob("*.837")).read_text("utf-8"))
    ls = d["form"]["lines"]
    assert [(x["cpt"], x["mods"]) for x in ls] == [("99213", []), ("73600", ["LT"])]
    assert float(d["form"]["claim"]["total"]) == sum(float(x["charge"]) for x in ls), "the form total is the sum of its lines"
    assert all(x["date"] for x in ls) and d["form"]["dx"][0]["code"] == "S93409A"
