"""Load stage 1 for the Synthea data into krisnnai_r2 (AWS RDS): reference data, practice, facilities, providers, guarantors, patients and coverage.

Usage: python tools/synthea/load_ref_people.py --reset     (empties every table in krisnnai_r2 first; refuses to run on any other database)
Later stages (encounters, bills, claims, ledger) read work/idmaps.pkl written here.
"""
import collections
import datetime as dt
import sys

from psycopg2.extras import execute_values

sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())
from crosswalk import ENC, PROC, ICD, FEE, POS  # noqa: E402
from r2load import Loader, connect, reader, date, h, NOW, END, TBL  # noqa: E402

START = dt.date(2019, 1, 1)
LIVE_END = dt.date(2026, 10, 31)
PAYER = {  # Synthea name -> (code, type, filing days, appeal days, plan type, plan name)
    "Medicare": ("MEDICARE", "medicare", 365, 120, "Medicare Part B", "Medicare Part B"), "Medicaid": ("MEDICAID", "medicaid", 365, 90, "Medicaid managed care", "Medicaid managed care"),
    "Dual Eligible": ("DUAL", "medicaid", 365, 90, "Dual eligible", "Medicare and Medicaid dual eligible"), "Humana": ("HUMANA", "commercial", 180, 180, "PPO", "Humana PPO"),
    "Blue Cross Blue Shield": ("BCBS", "commercial", 180, 180, "PPO", "Blue Cross Blue Shield PPO"), "UnitedHealthcare": ("UHC", "commercial", 90, 180, "PPO", "UnitedHealthcare PPO"),
    "Aetna": ("AETNA", "commercial", 180, 180, "PPO", "Aetna PPO"), "Cigna Health": ("CIGNA", "commercial", 180, 180, "PPO", "Cigna PPO"), "Anthem": ("ANTHEM", "commercial", 180, 180, "PPO", "Anthem PPO"),
    "NO_INSURANCE": ("SELF", "self_pay", 365, 0, None, None)}


# a period ends the day before the next one for the same patient and order starts (Synthea ends a year on the day the next begins)
FIX_OVERLAP = """UPDATE coverage c SET termination_date = n.nxt - 1 FROM (SELECT coverage_id, lead(effective_date) OVER (PARTITION BY patient_id, coverage_order ORDER BY effective_date, coverage_id) AS nxt FROM coverage) n
                 WHERE c.coverage_id = n.coverage_id AND n.nxt IS NOT NULL AND (c.termination_date IS NULL OR c.termination_date >= n.nxt)"""


def main(reset):
    conn = connect()
    cur = conn.cursor()
    if reset:
        cur.execute("select string_agg(format('%I', tablename), ',') from pg_tables where schemaname='public'")
        cur.execute(f"TRUNCATE {cur.fetchone()[0]} CASCADE")
        conn.commit()
    else:
        cur.execute('select count(*) from "patient"')
        assert cur.fetchone()[0] == 0, "krisnnai_r2 already has patients; run with --reset"
    L = Loader(conn)
    M = L.maps
    out = collections.OrderedDict()

    def put(table, rows):
        out[table] = out.get(table, 0) + L.rows(table, rows)

    # ---- tenant, feed and batch point at each other, so the three bootstrap rows go in with foreign-key checks off for this one transaction
    cur.execute("SET session_replication_role = replica")
    put("tenant", [dict(tenant_id=1, tenant_code="SYNTHEA", tenant_name="Synthea Texas (synthetic)", tenant_status="active", baa_signed_date=START, salt_key_ref="synthetic-no-real-phi")])
    put("data_feed", [dict(data_feed_id=1, table_name="(all)", feed_name="synthea-csv", source_system="synthea", feed_status="active", fallback_level=0)])
    put("load_batch", [dict(load_batch_id=1, data_feed_id=1, started_at=NOW, batch_status="complete")])
    cur.execute("SET session_replication_role = DEFAULT")
    conn.commit()

    # ---- what the encounters use: organizations, providers, patients, first and last visit
    orgs, provs, seen = set(), set(), {}
    for r in reader("encounters.csv"):
        orgs.add(r["ORGANIZATION"])
        provs.add(r["PROVIDER"])
        d = date(r["START"])
        lo, hi = seen.get(r["PATIENT"], (d, d))
        seen[r["PATIENT"]] = (min(lo, d), max(hi, d))
    print(f"encounters use {len(orgs)} organizations, {len(provs)} providers, {len(seen)} patients")

    # ---- reference data
    put("practice", [dict(practice_id=1, practice_number="SYN-TX", practice_name="Synthea Texas Network (synthetic)", go_live_date=START)])
    M["practice"] = 1
    specs = sorted({r["SPECIALITY"] for r in reader("providers.csv") if r["Id"] in provs})
    M["specialty"] = {}
    rows = []
    for s in specs:
        M["specialty"][s] = L.key("specialty")
        rows.append(dict(specialty_id=M["specialty"][s], specialty_code=s[:20], specialty_name=s.title(), is_primary_care=s in ("GENERAL PRACTICE", "FAMILY PRACTICE", "PEDIATRICS", "INTERNAL MEDICINE")))
    put("specialty", rows)
    M["pos"] = {}
    rows = []
    for cls, (code, name, setting, fac, tele) in POS.items():
        if code not in M["pos"]:
            M["pos"][code] = L.key("place_of_service")
            rows.append(dict(place_of_service_id=M["pos"][code], pos_code=code, pos_name=name, setting=setting, is_facility=fac, is_telehealth=tele, effective_from=START, effective_to=END))
    put("place_of_service", rows)
    M["payer"], M["payer_plan"], rows, prow = {}, {}, [], []
    for r in reader("payers.csv"):
        code, typ, filing, appeal, ptype, pname = PAYER[r["NAME"]]
        M["payer"][r["Id"]] = pid = L.key("payer")
        M["payer"][code] = pid
        M.setdefault("payer_info", {})[r["Id"]] = PAYER[r["NAME"]]
        rows.append(dict(payer_id=pid, payer_code=code, payer_name=r["NAME"], payer_type=typ, filing_days=filing, corrected_claim_days=filing, appeal_days=appeal))
        if pname:
            M["payer_plan"][pid] = L.key("payer_plan")
            prow.append(dict(payer_plan_id=M["payer_plan"][pid], payer_id=pid, plan_code="STD", plan_name=pname, plan_type=ptype, effective_from=START, effective_to=END))
    put("payer", rows)
    put("payer_plan", prow)
    M["cpt"], rows = {}, []
    codes = {}
    for _, (c, typ, label, cat, lvl) in ENC.items():
        codes[c] = (typ, label, cat, lvl)
    for _, (c, typ, label, cat) in PROC.items():
        codes.setdefault(c, (typ, label, cat, None))
    for c, (typ, label, cat, lvl) in sorted(codes.items()):
        M["cpt"][c] = L.key("cpt_code")
        rows.append(dict(cpt_code_id=M["cpt"][c], code=c, code_type=typ, effective_from=START, effective_to=END, short_label=label, category=cat, em_level=lvl, is_unrecognized=False))
    put("cpt_code", rows)
    M["icd"], rows = {}, []
    for _, (c, desc) in sorted(ICD.items(), key=lambda x: x[1][0]):
        if c not in M["icd"]:
            M["icd"][c] = L.key("diagnosis_code")
            rows.append(dict(diagnosis_code_id=M["icd"][c], icd10_code=c, effective_from=START, effective_to=END, description=desc, is_billable=True, is_unrecognized=False))
    put("diagnosis_code", rows)
    M["fee"] = FEE
    conn.commit()

    # ---- facilities and providers
    M["facility"], M["provider"], rows, prow, pp = {}, {}, [], [], []
    org_name = {}
    for r in reader("organizations.csv"):
        if r["Id"] in orgs:
            org_name[r["Id"]] = r
            M["facility"][r["Id"]] = fid = L.key("facility")
            rows.append(dict(facility_id=fid, facility_number=f"F{fid:05d}", facility_name=r["NAME"].title(), practice_id=1, facility_type="clinic", default_place_of_service_id=M["pos"]["11"],
                             facility_npi=r["NPI"][:10] if r["NPI"] else None, state=r["STATE"][:2], open_date=START))
    put("facility", rows)
    for r in reader("providers.csv"):
        if r["Id"] in provs:
            M["provider"][r["Id"]] = pid = L.key("provider")
            prow.append(dict(provider_id=pid, npi=r["NPI"].zfill(10)[:10], provider_number=f"P{pid:05d}", provider_type="physician", specialty_id=M["specialty"][r["SPECIALITY"]], provider_name=r["NAME"],
                             practice_id=1, start_date=START))
            pp.append(dict(provider_practice_id=L.key("provider_practice"), provider_id=pid, practice_id=1, facility_id=M["facility"].get(r["ORGANIZATION"]), start_date=START, end_date=END))
    put("provider", prow)
    put("provider_practice", pp)
    conn.commit()

    # ---- guarantors and patients
    M["patient"], M["guarantor"], grows, prow = {}, {}, [], []
    for r in reader("patients.csv"):
        if r["Id"] not in seen:
            continue
        pid, gid = L.key("patient"), L.key("guarantor")
        M["patient"][r["Id"]] = pid
        birth = date(r["BIRTHDATE"])
        age = (NOW.date() - birth).days // 365
        grows.append(dict(guarantor_id=gid, guarantor_hash=h("guarantor", r["Id"]), guarantor_type="self" if age >= 18 else "parent", practice_id=1, state="TX", account_status="active", is_inferred=True))
        prow.append(dict(patient_id=pid, patient_number_hash=h("patient", r["Id"]), master_patient_hash=h("master", r["Id"]), birth_year=birth.year, is_age_90_plus=age >= 90, sex=r["GENDER"], state="TX",
                         primary_practice_id=1, first_seen_date=seen[r["Id"]][0], last_seen_date=seen[r["Id"]][1], guarantor_id=gid, is_self_pay=False, is_active=not r["DEATHDATE"]))
    put("guarantor", grows)
    put("patient", prow)
    conn.commit()

    # ---- coverage: merge back-to-back years with the same payer into one period
    per = collections.defaultdict(list)
    for r in reader("payer_transitions.csv"):
        if r["PATIENT"] in M["patient"]:
            per[r["PATIENT"]].append(r)
    crow, primary, insured = [], {}, set()
    for pat, trs in per.items():
        trs.sort(key=lambda r: r["START_DATE"])
        for order, field in ((1, "PAYER"), (2, "SECONDARY_PAYER")):
            cur_p = None
            for r in trs + [None]:
                pay = r[field] if r else None
                if pay and pay in M["payer"] and M["payer"][pay] != M["payer"]["SELF"]:
                    start, end = date(r["START_DATE"]), date(r["END_DATE"])
                    if cur_p and cur_p["payer"] == pay and (start - cur_p["end"]).days <= 2:
                        cur_p["end"] = end
                        continue
                else:
                    pay = None
                if cur_p:
                    pidn = M["payer"][cur_p["payer"]]
                    cid = L.key("coverage")
                    typ = M["payer_info"][cur_p["payer"]]
                    crow.append(dict(coverage_id=cid, patient_id=M["patient"][pat], payer_id=pidn, payer_plan_id=M["payer_plan"].get(pidn), member_number_hash=h("member", cur_p["member"]), coverage_order=order,
                                     effective_date=cur_p["start"], termination_date=None if cur_p["end"] >= LIVE_END else cur_p["end"], plan_type=typ[4], plan_name=typ[5], relationship_to_holder="self",
                                     last_verified_date=cur_p["start"], last_verified_status="active"))
                    insured.add(pat)
                    if order == 1:
                        primary[pat] = cid
                    cur_p = None
                if pay:
                    cur_p = dict(payer=pay, start=date(r["START_DATE"]), end=date(r["END_DATE"]), member=r["MEMBERID"])
    # the transition file holds payer ids as UUIDs; the lookups above use the same UUIDs, so nothing is stored outside the hash
    put("coverage", crow)
    execute_values(cur, 'UPDATE "patient" p SET primary_coverage_id = v.c, is_self_pay = false FROM (VALUES %s) AS v(p, c) WHERE p.patient_id = v.p', [(M["patient"][k], v) for k, v in primary.items()])
    cur.execute('UPDATE "patient" SET is_self_pay = true WHERE primary_coverage_id IS NULL')
    cur.execute(FIX_OVERLAP)
    conn.commit()
    L.save_maps()
    print("loaded:", dict(out))
    print(f"patients with coverage: {len(insured)} of {len(M['patient'])}")
    conn.close()


if __name__ == "__main__":
    main("--reset" in sys.argv)
