"""M12a tests: Synthea CSV -> billable bundles -> simulated payer files + ground truth -> existing agents."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

import krisnai.model as m
from krisnai import cli
from krisnai.ingest.loader import ingest_path
from krisnai.match.engine import run_matching
from krisnai.model import tenant_session
from krisnai.synthea import build, runner
from krisnai.synthea.bundles import build_bundles
from krisnai.synthea.reader import find_csv_dir, read_dir
from krisnai.synthea.simulate import simulate
from tests.fixtures import synthea_mini
from tests.test_ingest import SALT, make_engine

AS_OF = date(2026, 6, 30)


@pytest.fixture(scope="module")
def mini(tmp_path_factory):
    return synthea_mini.write(tmp_path_factory.mktemp("synthea"))


@pytest.fixture(scope="module")
def built(mini, tmp_path_factory):
    out = tmp_path_factory.mktemp("built")
    return out, build(mini, out, AS_OF, seed=7)


def digest(folder: Path) -> dict[str, str]:
    return {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir())}


# ------------------------------------------------------------------------------------- reader + bundles


def test_reader_accepts_the_run_folder_or_its_csv_folder_and_rejects_anything_else(mini, tmp_path):
    assert find_csv_dir(mini) == mini / "csv" and find_csv_dir(mini / "csv") == mini / "csv"
    with pytest.raises(FileNotFoundError):
        find_csv_dir(tmp_path)
    data = read_dir(mini)
    assert len(data.claims) == 400 and len(data.patients) == 60 and len(data.payers) == 4


def test_bundles_bill_only_covered_professional_visits_and_count_what_they_skip(mini):
    bundles, report = build_bundles(read_dir(mini), AS_OF)
    assert report["claims_read"] == 400
    assert report["skipped_no_coverage"] > 0 and report["skipped_not_professional"] > 0  # NO_INSURANCE, inpatient / home
    assert report["bundles"] == len(bundles) > 100
    assert all(b.cpts and b.dx for b in bundles)
    assert report["dx_fallback"] > 0 and report["procedure_codes_unmapped"] > 0  # the stand-in crosswalk gaps are visible
    assert [b.dos for b in bundles] == sorted(b.dos for b in bundles)
    assert len({b.claim_id for b in bundles}) == len(bundles)
    assert not any("NO_INSURANCE" in b.payer.name for b in bundles)


def test_claims_dated_after_as_of_are_not_billed(mini):
    bundles, report = build_bundles(read_dir(mini), date(2025, 9, 1))
    assert report["skipped_after_as_of"] > 0 and max(b.dos for b in bundles) <= date(2025, 9, 1)


# ------------------------------------------------------------------------------------- payer simulator


def test_simulation_is_deterministic_and_changes_with_the_seed(mini):
    bundles, _ = build_bundles(read_dir(mini), AS_OF)
    first = [(c.claim_id, c.scenario, c.remit_date, c.carc) for c in simulate(bundles, AS_OF, 7)[0]]
    again = [(c.claim_id, c.scenario, c.remit_date, c.carc) for c in simulate(bundles, AS_OF, 7)[0]]
    other = [(c.claim_id, c.scenario, c.remit_date, c.carc) for c in simulate(bundles, AS_OF, 8)[0]]
    assert first == again and first != other


def test_every_planted_problem_is_in_the_ground_truth_and_the_money_balances(built):
    out, report = built
    truth = list(csv.DictReader((out / "ground_truth.csv").open()))
    kinds = Counter(t["issue_type"] for t in truth)
    scen = report["claims_by_scenario"]
    assert kinds["denial"] == scen.get("denial", 0) > 0
    assert kinds["underpayment"] == scen.get("underpayment", 0) > 0
    assert kinds["rejection"] == scen.get("rejection", 0) > 0
    assert kinds["timely_filing"] == scen.get("timely_filing", 0)
    assert kinds["unbilled_visit"] == report["unbilled_visits"] > 0
    assert report["files"]["837"] > 0 and report["files"]["835"] > 0
    assert all(Decimal(t["expected_amount"]) > 0 for t in truth)


def test_a_claim_is_never_answered_before_it_is_sent_or_after_as_of(mini):
    bundles, _ = build_bundles(read_dir(mini), AS_OF)
    claims, _ = simulate(bundles, AS_OF, 7)
    assert claims and all(c.submitted <= AS_OF for c in claims)
    for c in claims:
        if c.remit_date is not None:
            assert c.submitted < c.remit_date <= AS_OF
            assert c.paid + c.pr + sum((a for ln in c.lines for g, _, a in ln.cas if g == "CO"), Decimal("0")) == c.billed
        else:
            assert c.scenario in ("open", "rejection")
    # the simulator never plants a problem on a claim that has no answer to be wrong about
    assert Counter(c.scenario for c in claims if c.scenario in ("denial", "underpayment") and c.remit_date is None) == {}


# ------------------------------------------------------------------------------------- through the product


def test_built_files_load_with_the_existing_ingest_and_match_to_the_ground_truth(built, tmp_path):
    out, report = built
    engine = make_engine(tmp_path / "db.sqlite")
    results = ingest_path(engine, 1, out, SALT)
    assert results and all(r.status == "loaded" for r in results), [r for r in results if r.status != "loaded"][:3]
    run_matching(engine, 1)
    with tenant_session(engine, 1) as s:
        n_claims = s.scalar(select(func.count()).select_from(m.Claim))
        n_remits = s.scalar(select(func.count()).select_from(m.Remit))
    assert n_claims == report["claims_billed"]
    assert n_remits > 0
    again = ingest_path(engine, 1, out, SALT)  # idempotent
    assert all(r.status == "skipped" for r in again)


def test_the_wave_one_agents_run_on_a_synthea_book_in_shadow(built, tmp_path, capsys):
    out, report = built
    engine = make_engine(tmp_path / "wave.sqlite")
    ingest_path(engine, 1, out, SALT)
    run_matching(engine, 1)
    url = str(engine.url)
    for argv in (
        ["a8", "seed"], ["a8", "replay"], ["a5", "seed"], ["a5", "replay"], ["a6", "seed"], ["a6", "replay"],
        ["a7", "sweep", "--from", "2026-03-01", "--to", "2026-06-30"], ["a7", "replay"],
        ["a14", "sweep", "--from", "2026-06-30", "--to", "2026-06-30"], ["a14", "replay"],
    ):  # fmt: skip
        assert cli.main(["--db-url", url, *argv, "--tenant", "1"]) == 0, argv
    capsys.readouterr()
    assert cli.main(["--db-url", url, "tower", "--tenant", "1", "--as-of", "2026-06-30", "--json",
                     "--backtest-weeks", "0"]) == 0  # fmt: skip
    tower = json.loads(capsys.readouterr().out)
    assert tower["backlog"]["items"] > 0
    with tenant_session(engine, 1) as s:
        agents = set(s.scalars(select(m.DecisionRecord.agent_id)))
        executed = s.scalar(select(func.count()).select_from(m.DecisionRecord)
                            .where(m.DecisionRecord.outcome == "executed"))  # fmt: skip
    assert agents == {"a8_denial", "a5_prevention", "a6_submission", "a7_ar", "a14_tower"}
    assert executed == 0


# ------------------------------------------------------------------------------------- CLI + runner


def test_cli_build_writes_the_files_and_prints_a_report(mini, tmp_path, capsys):
    out = tmp_path / "cli"
    assert cli.main(["synthea", "build", "--in", str(mini), "--out", str(out), "--as-of", "2026-06-30"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["claims_billed"] > 0 and (out / "ground_truth.csv").exists()
    assert digest(out) == digest(built_again(mini, tmp_path / "again"))


def built_again(mini, out):
    build(mini, out, AS_OF, seed=7)
    return out


def test_runner_plan_names_the_exact_steps_and_runs_nothing(tmp_path):
    p = runner.plan(tmp_path / "out", tmp_path / "cache", population=50, seed=3, state="Massachusetts")
    assert p.download[0] == "curl" and p.jar.name == "synthea-with-dependencies.jar"
    assert p.docker[:3] == ["docker", "run", "--rm"] and "-p" in p.docker and "50" in p.docker
    assert "--exporter.fhir.export=false" in p.docker and p.docker[-1] == "Massachusetts"
    assert not (tmp_path / "out").exists() and not (tmp_path / "cache").exists()


def test_cli_run_without_yes_only_prints_the_plan(tmp_path, capsys):
    argv = ["synthea", "run", "--out", str(tmp_path / "o"), "--cache", str(tmp_path / "c")]
    assert cli.main(argv) == 0
    assert "nothing run" in capsys.readouterr().out and not (tmp_path / "o").exists()


def test_several_encounters_for_one_patient_on_one_day_become_one_claim(tmp_path):
    root = synthea_mini.write(tmp_path / "s", n_claims=300, seed=3, n_patients=6)  # few patients: many same-day visits
    bundles, report = build_bundles(read_dir(root), AS_OF)
    assert report["merged_same_day"] > 0
    keys = [(b.patient.ref, b.dos, b.payer.payer_id) for b in bundles]
    assert len(keys) == len(set(keys))
    assert all(len({c for c, _ in b.cpts}) == len(b.cpts) for b in bundles)  # no repeated CPT on a claim


def test_old_visits_outside_the_lookback_window_are_not_billed(mini):
    _, report = build_bundles(read_dir(mini), AS_OF, lookback_days=90)
    assert report["skipped_before_window"] > 0
