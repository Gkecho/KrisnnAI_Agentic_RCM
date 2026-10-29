"""S7: the transcript reader, the coder on a Reading, and the validated AI layer. Synthetic notes only."""

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from krisnnai.engine.models import BaaNotApproved
from krisnnai.live import catalog
from krisnnai.live.ai_reader import AiReader, FakeAi
from krisnnai.live.coder import Coder, Policy
from krisnnai.live.reader import read

FIX = Path(__file__).parent / "fixtures" / "transcripts"
DAY = date(2026, 10, 24)
ON = Policy(enabled=True, sample_rate=0.0, daily_cap=10_000)


def _cases(name: str) -> list[dict]:
    return json.loads((FIX / name).read_text(encoding="utf-8"))["cases"]


def _known(case: dict) -> bool:
    e = case["expect"]
    return all(catalog.condition_by_icd(i) for i in e["dx"]) and all(catalog.service_by_cpt(c) for c in e["services"])


def _score(name: str):
    rows = []
    for i, c in enumerate(_cases(name)):
        if not _known(c):
            continue
        r = Coder(ON).code(f"H{i}", "\n".join(c["lines"]), c["signed"], DAY)
        rows.append((c, r))
    return rows


@pytest.mark.parametrize("name,floor", [("heldout.json", 0.9), ("blind.json", 0.8)])
def test_accuracy_on_hand_written_transcripts(name, floor):
    rows = _score(name)
    assert len(rows) >= (30 if name == "heldout.json" else 15)
    n = len(rows)
    dx = sum(sorted(d[0] for d in r.dx) == sorted(c["expect"]["dx"]) for c, r in rows) / n
    sv = sum(sorted(p["cpt"] for p in r.procedures) == sorted(c["expect"]["services"]) for c, r in rows) / n
    rt = sum(r.route == c["expect"]["route"] for c, r in rows) / n
    print(f"{name}: n={n} dx={dx:.2f} services={sv:.2f} route={rt:.2f}")
    assert dx >= floor and sv >= floor and rt >= floor


@pytest.mark.parametrize("name", ["heldout.json", "blind.json"])
def test_safety_nothing_the_reader_doubts_is_auto_accepted_with_a_wrong_code(name):
    for c, r in _score(name):
        if r.route == "auto":
            assert sorted(d[0] for d in r.dx) == sorted(c["expect"]["dx"]), c["name"]
            assert sorted(p["cpt"] for p in r.procedures) == sorted(c["expect"]["services"]), c["name"]
            assert c["expect"]["route"] == "auto", c["name"]
        if r.uncertainties:
            assert r.route == "coder", c["name"]


def test_negation_and_rule_out_and_history():
    r = read("Assessment: Sore throat. No cough, no fever.\nPlan: rest.", True)
    assert [h.icd10 for h in r.diagnoses] == ["J02.9"] and not r.uncertainties
    r = read("Assessment: Low back pain. Rule out UTI.\nPlan: stretch.", True)
    assert [h.icd10 for h in r.diagnoses] == ["M54.50"] and any("uncertain" in u for u in r.uncertainties)
    r = read("Assessment: Hypertension. History of diabetes.\nPlan: x y.", True)
    assert any("history" in u for u in r.uncertainties)


def test_synonyms_typos_and_plurals():
    for phrase, icd in [("HTN", "I10"), ("DM2", "E11.9"), ("UTIs", "N39.0"), ("LBP", "M54.50"), ("bladder infection", "N39.0")]:
        assert [h.icd10 for h in read(f"A: {phrase}\nP: follow up soon", True).diagnoses] == [icd], phrase
    r = read("A: pharyngits\nP: rest well", True)
    assert [h.icd10 for h in r.diagnoses] == ["J02.9"] and any("spelling" in u for u in r.uncertainties)
    assert not read("A: hypotension\nP: fluids today", True).diagnoses


def test_time_to_units_and_laterality():
    def units(m):
        return read(f"Therapeutic exercise {m} minutes. A: LBP. P: go on.", True).services[0].units

    assert [units(m) for m in (8, 22, 23, 38, 60)] == [1, 1, 2, 3, 4]
    assert read("Therapeutic exercise 1 hour. A: LBP.", True).services[0].minutes == 60
    assert read("A: bilateral knee pain. P: ice now", True).diagnoses[0].laterality == "bilateral"
    assert read("A: right knee pain. P: ice now", True).diagnoses[0].laterality == "right"
    assert read("A: knee pain. P: ice now", True).diagnoses[0].laterality == ""


@pytest.mark.parametrize("text", [
    "S: Est patient.\nA: UTI\nP: abx, rtc 1 wk\nSigned electronically by Dr. Demo.",
    "   ASSESSMENT:   URINARY TRACT INFECTION  \n\n  PLAN:  ANTIBIOTICS\nsigned electronically by dr demo",
    "Est pt. Assessment urinary tract infection. Plan antibiotics and return. Signed electronically by Dr. Demo",
    "- A: UTI\n- P: antibiotics\n- Signed electronically by Dr. Demo",
    "Provider: Assessment: UTI. Provider: Plan: antibiotics.\nSigned electronically by Dr. Demo",
])
def test_layouts(text):
    r = read(text, True)
    assert [h.icd10 for h in r.diagnoses] == ["N39.0"] and r.plan_present and r.signed and not r.uncertainties


def test_unsigned_and_missing_pieces_route_to_a_coder():
    assert Coder(ON).code("v", "A: UTI\nP: abx today", True, DAY).reason == "unsigned"
    t = "Est patient.\nA: UTI\nSigned electronically by Dr. Demo"
    assert Coder(ON).code("v", t, True, DAY).reason == "missing_plan"


def test_the_reader_sees_catalog_entries_added_at_runtime(monkeypatch):
    new = catalog.Condition("J45.909", "Asthma, unspecified", ("asthma",), unspecified=True)
    svc = catalog.Service("94640", "Nebulizer treatment", "procedure", ("nebulizer treatment",), fee="40.00")
    monkeypatch.setattr(catalog, "CONDITIONS", [*catalog.CONDITIONS, new])
    monkeypatch.setattr(catalog, "SERVICES", [*catalog.SERVICES, svc])
    r = read("Established patient.\nA: Asthma\nP: nebulizer treatment given today, return soon", True)
    assert [h.icd10 for h in r.diagnoses] == ["J45.909"] and [s.cpt for s in r.services] == ["94640"]


# ------------------------------------------------------------------------------------------------ the AI layer
NOTE = "S: Established patient, cough for a week.\nO: Exam: lungs clear.\nA: Cough.\nP: Fluids, return in 2 weeks.\nSigned electronically by Dr. Demo Provider."


def _ai(answer):
    return AiReader(FakeAi(answer), baa_approved=True)


def test_default_ai_is_the_stub_with_no_effect():
    base = Coder(ON).code("v", NOTE, True, DAY)
    r = Coder(ON, reader="rules+ai").code("v", NOTE, True, DAY)
    assert (r.cpt, r.dx, r.route, r.reason) == (base.cpt, base.dx, base.route, base.reason) and r.ai["usable"] is False


def test_a_real_provider_is_refused_without_a_baa():
    with pytest.raises(BaaNotApproved):
        Coder(ON, reader="rules+ai", ai=AiReader(FakeAi({}))).code("v", NOTE, True, DAY)


def test_agreeing_ai_changes_nothing():
    ai = _ai({"conditions": [{"icd10": "R05.9", "evidence": "A: Cough."}], "services": []})
    r = Coder(ON, reader="rules+ai", ai=ai).code("v", NOTE, True, DAY)
    assert r.route == "auto" and not r.uncertainties and r.ai["accepted"]


def test_hallucinated_code_and_fabricated_quote_are_rejected():
    ai = _ai({"conditions": [{"icd10": "Z99.99", "evidence": "A: Cough."}, {"icd10": "I10", "evidence": "essential hypertension noted"}]})
    r = Coder(ON, reader="rules+ai", ai=ai).code("v", NOTE, True, DAY)
    assert len(r.ai["rejected"]) == 2 and not r.ai["added"]
    assert [d[0] for d in r.dx] == ["R05.9"], "the AI never changes the diagnosis list with a rejected proposal"


def test_disagreement_routes_to_a_coder_and_never_overrides_the_rules():
    ai = _ai({"conditions": [{"icd10": "I10", "evidence": "lungs clear"}]})
    r = Coder(ON, reader="rules+ai", ai=ai).code("v", NOTE, True, DAY)
    assert r.route == "coder" and r.reason in ("two_problems", "reader_uncertain") and r.ai["disagreements"]
    assert ("R05.9", "Cough, unspecified") in r.dx


def test_ai_cannot_turn_a_denied_mention_into_a_diagnosis():
    note = NOTE.replace("A: Cough.", "A: Cough. No UTI.")
    ai = _ai({"conditions": [{"icd10": "R05.9", "evidence": "A: Cough."}, {"icd10": "N39.0", "evidence": "No UTI"}]})
    r = Coder(ON, reader="rules+ai", ai=ai).code("v", note, True, DAY)
    assert [d[0] for d in r.dx] == ["R05.9"] and r.route == "coder"


def test_unknown_reader_value_is_refused():
    with pytest.raises(ValueError):
        Coder(ON, reader="magic")


def test_records_stay_plain_json():
    r = Coder(ON).code("v", NOTE, True, DAY)
    json.dumps(replace(r, checks=[]).__dict__ | {"checks": [c.__dict__ for c in r.checks]})
