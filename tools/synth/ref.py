"""Stage 1: the practice, its people, payers, code sets, fees and contract rates (all synthetic).

The practice is "Valley Wellness Health": outpatient physical and occupational therapy at two locations, plus family medicine
(with nurse practitioners and registered nurses), orthopedics and pain management, with a third facility for the physician services.
"""
import datetime as dt
from decimal import Decimal

FROM, TO = dt.date(2020, 1, 1), dt.date(2099, 12, 31)
D = Decimal

# code, label, timed?, max units/day, base fee per unit
CPT = [
    ("97110", "Therapeutic exercise", True, 4, "52.00"), ("97112", "Neuromuscular re-education", True, 3, "55.00"),
    ("97116", "Gait training", True, 2, "49.00"), ("97140", "Manual therapy", True, 3, "48.00"),
    ("97530", "Therapeutic activities", True, 4, "58.00"), ("97535", "Self-care / home management training", True, 3, "54.00"),
    ("97032", "Electrical stimulation, attended", True, 1, "30.00"), ("97035", "Ultrasound", True, 1, "28.00"),
    ("97124", "Massage", True, 2, "42.00"), ("97750", "Physical performance test", True, 4, "60.00"),
    ("97161", "PT evaluation, low complexity", False, 1, "135.00"), ("97162", "PT evaluation, moderate complexity", False, 1, "160.00"),
    ("97163", "PT evaluation, high complexity", False, 1, "185.00"), ("97164", "PT re-evaluation", False, 1, "105.00"),
    ("97165", "OT evaluation, low complexity", False, 1, "135.00"), ("97166", "OT evaluation, moderate complexity", False, 1, "160.00"),
    ("97010", "Hot or cold pack", False, 1, "14.00"), ("G0283", "Electrical stimulation, unattended", False, 1, "22.00"),
    ("97150", "Group therapeutic procedures", False, 1, "32.00"), ("97542", "Wheelchair management training", True, 2, "50.00"),
    # family medicine, orthopedics and pain management
    ("99211", "Office visit, nurse (established)", False, 1, "35.00"), ("99203", "Office visit, new patient, low complexity", False, 1, "135.00"),
    ("99204", "Office visit, new patient, moderate complexity", False, 1, "210.00"), ("99213", "Office visit, established, low complexity", False, 1, "120.00"),
    ("99214", "Office visit, established, moderate complexity", False, 1, "175.00"), ("99395", "Preventive visit, established, 18-39", False, 1, "190.00"),
    ("36415", "Venipuncture", False, 1, "15.00"), ("93000", "ECG with interpretation", False, 1, "45.00"), ("96372", "Therapeutic injection", False, 2, "40.00"),
    ("73030", "X-ray, shoulder", False, 2, "70.00"), ("73560", "X-ray, knee, 1-2 views", False, 2, "65.00"), ("72100", "X-ray, lumbar spine, 2-3 views", False, 1, "85.00"),
    ("76881", "Ultrasound, joint, complete", False, 1, "130.00"), ("95907", "Nerve conduction studies, 1-2", False, 1, "220.00"),
    ("20610", "Joint injection, major joint", False, 2, "155.00"), ("20552", "Trigger point injection, 1-2 muscles", False, 1, "95.00"),
    ("62323", "Lumbar epidural injection with imaging", False, 1, "520.00"), ("64483", "Transforaminal epidural, lumbar, single level", False, 1, "560.00"),
    ("64493", "Facet joint injection, lumbar, single level", False, 1, "480.00"), ("64635", "Radiofrequency ablation, lumbar facet, single level", False, 1, "1050.00"),
]
CPT_CATEGORY = {**{c: "em" for c in ("99211", "99203", "99204", "99213", "99214", "99395")}, **{c: "imaging" for c in ("73030", "73560", "72100", "76881")},
                **{c: "diagnostic" for c in ("36415", "93000", "95907")}, **{c: "procedure" for c in ("96372", "20610", "20552", "62323", "64483", "64493", "64635")}}
ICD = [
    ("M5450", "Low back pain, unspecified"), ("M5459", "Other low back pain"), ("M542", "Cervicalgia"),
    ("M25511", "Pain in right shoulder"), ("M25512", "Pain in left shoulder"), ("M25561", "Pain in right knee"),
    ("M25562", "Pain in left knee"), ("M6281", "Muscle weakness (generalized)"), ("R2689", "Other abnormalities of gait and mobility"),
    ("M7521", "Bicipital tendinitis, right shoulder"), ("M7541", "Impingement syndrome of right shoulder"),
    ("M170", "Bilateral primary osteoarthritis of knee"), ("M1711", "Unilateral primary osteoarthritis, right knee"),
    ("S83511A", "Sprain of anterior cruciate ligament, right knee, initial"), ("M545", "Low back pain"),
    ("M4802", "Spinal stenosis, cervical region"), ("M5416", "Radiculopathy, lumbar region"), ("M25551", "Pain in right hip"),
    ("G8929", "Other chronic pain"), ("Z9889", "Other specified postprocedural states"),
]
ICD_PT = [c for c, _ in ICD]                           # the therapy diagnoses (the first twenty)
ICD += [("E119", "Type 2 diabetes mellitus without complications"), ("I10", "Essential hypertension"), ("E785", "Hyperlipidemia, unspecified"),
        ("J069", "Acute upper respiratory infection, unspecified"), ("Z0000", "General adult medical examination"), ("E669", "Obesity, unspecified"),
        ("F419", "Anxiety disorder, unspecified"), ("N390", "Urinary tract infection, site not specified"), ("M1612", "Unilateral primary osteoarthritis, left hip"),
        ("M75100", "Rotator cuff tear, unspecified shoulder"), ("M4806", "Spinal stenosis, lumbar region"), ("M5126", "Other intervertebral disc displacement, lumbar region"),
        ("G894", "Chronic pain syndrome"), ("M47816", "Spondylosis without myelopathy, lumbar region"), ("M792", "Neuralgia and neuritis, unspecified"),
        ("M7062", "Trochanteric bursitis, left hip")]
ICD_BY_SPEC = {"FM": ["E119", "I10", "E785", "J069", "Z0000", "E669", "F419", "N390", "M545"],
               "ORTHO": ["M25511", "M25512", "M25561", "M25562", "M170", "M1711", "M1612", "M75100", "M7541", "S83511A", "M25551", "M7062"],
               "PAIN": ["M5459", "M5416", "M4806", "M5126", "G894", "M47816", "M792", "M545", "M4802"]}
# carc, label, class, category, owner, stage, appealable, technical, preventable
CARC = [
    ("1", "Deductible amount", "patient_responsibility", "patient", "patient_accounts", "registration", 0, 0, 0),
    ("2", "Coinsurance amount", "patient_responsibility", "patient", "patient_accounts", "registration", 0, 0, 0),
    ("3", "Copayment amount", "patient_responsibility", "patient", "patient_accounts", "registration", 0, 0, 0),
    ("4", "Modifier missing or inconsistent with the procedure", "denial", "coding", "coder", "coding", 1, 1, 1),
    ("11", "Diagnosis inconsistent with the procedure", "denial", "coding", "coder", "coding", 1, 0, 1),
    ("16", "Claim lacks information needed to adjudicate", "denial", "billing", "biller", "billing", 1, 1, 1),
    ("18", "Exact duplicate claim or service", "denial", "billing", "biller", "billing", 0, 1, 1),
    ("22", "Coordination of benefits: another payer is primary", "denial", "eligibility", "front_desk", "eligibility", 1, 0, 1),
    ("27", "Expenses incurred after coverage terminated", "denial", "eligibility", "front_desk", "eligibility", 0, 0, 1),
    ("29", "Time limit for filing has expired", "denial", "timely_filing", "billing_lead", "billing", 1, 0, 1),
    ("45", "Charge exceeds the contracted fee schedule", "contractual", "contractual", "none", "none", 0, 0, 0),
    ("50", "Not medically necessary", "denial", "documentation", "denial_specialist", "documentation", 1, 0, 1),
    ("96", "Non-covered charge", "denial", "coverage", "billing_lead", "eligibility", 1, 0, 0),
    ("97", "Included in the payment for another service", "denial", "coding", "coder", "coding", 1, 0, 1),
    ("119", "Benefit maximum reached", "denial", "coverage", "front_desk", "eligibility", 0, 0, 1),
    ("197", "Precertification or authorization absent", "denial", "authorization", "front_desk", "authorization", 1, 0, 1),
    ("198", "Precertification or authorization exceeded", "denial", "authorization", "front_desk", "authorization", 1, 0, 1),
    ("252", "Attachment or documentation required", "denial", "documentation", "denial_specialist", "documentation", 1, 1, 1),
    ("253", "Sequestration reduction", "other_adjustment", "other", "none", "none", 0, 0, 0),
]
RARC = [("N115", "This decision was based on a local coverage determination", "alert", "appeal", "plan_of_care"),
        ("N130", "Consult plan benefit documents for coverage", "alert", "none", "none"),
        ("N362", "Units of service exceed the acceptable maximum", "alert", "fix_units", "none"),
        ("N479", "Missing explanation of benefits from the primary payer", "alert", "send_primary_eob", "primary_eob"),
        ("M86", "Payment already made for the same service", "alert", "none", "none"),
        ("MA130", "Claim contains incomplete or invalid information", "alert", "fix_and_resubmit", "none"),
        ("N522", "Duplicate of a claim processed", "alert", "none", "none"),
        ("N704", "Alert: you may not appeal this decision", "alert", "none", "none")]
# code, name, type, filing days, corrected days, appeal days, turnaround, share of patients, fee multiplier for the contract rate
PAYERS = [
    ("SYNUHC", "UnitedHealthcare", "commercial", 90, 180, 180, 21, 0.24, 0.83),
    ("SYNBCBS", "Blue Cross Blue Shield", "commercial", 180, 365, 180, 24, 0.22, 0.78),
    ("SYNAET", "Aetna", "commercial", 180, 180, 180, 21, 0.15, 0.80),
    ("SYNCIG", "Cigna", "commercial", 90, 180, 180, 24, 0.12, 0.81),
    ("SYNMCR", "Medicare", "medicare", 365, 365, 120, 14, 0.20, 0.60),
    ("SYNSELF", "Self pay", "self_pay", 0, 0, 0, 0, 0.07, 1.00),
    ("SYNHUM", "Humana Medicare Advantage", "medicare_advantage", 180, 180, 60, 18, 0.08, 0.58),
    ("SYNMCD", "Texas Medicaid", "medicaid", 95, 95, 30, 30, 0.06, 0.48),
]
PROVIDERS = [("Rao", "PT", "DPT"), ("Lee", "PT", "DPT"), ("Okafor", "PT", "DPT"), ("Chen", "PT", "DPT"), ("Patel", "PT", "DPT"),
             ("Nguyen", "OT", "OTR"), ("Brooks", "PTA", "PTA"), ("Haines", "PTA", "PTA"),
             ("Dsouza", "PT", "DPT"), ("Walker", "PT", "DPT"), ("Ito", "PT", "DPT"), ("Khan", "OT", "OTR"), ("Moreno", "PTA", "PTA")]
# name, type, credential, specialty code, taxonomy, supervising physician (nurse practitioners and registered nurses work under one)
CLINIC = [("Alvarez", "MD", "MD", "FM", "207Q00000X", None), ("Whitfield", "MD", "MD", "FM", "207Q00000X", None), ("Nakamura", "MD", "MD", "FM", "207Q00000X", None),
          ("Ostrowski", "MD", "MD", "FM", "207Q00000X", None),
          ("Kim", "NP", "FNP-C", "FM", "363LF0000X", "Alvarez"), ("Torres", "NP", "FNP-C", "FM", "363LF0000X", "Whitfield"), ("Bell", "NP", "FNP-C", "FM", "363LF0000X", "Nakamura"),
          ("Garcia", "RN", "RN", "FM", "163W00000X", "Alvarez"), ("Okoye", "RN", "RN", "FM", "163W00000X", "Whitfield"), ("Rivera", "RN", "RN", "FM", "163W00000X", "Ostrowski"),
          ("Singh", "MD", "MD", "ORTHO", "207X00000X", None), ("Brennan", "MD", "MD", "ORTHO", "207X00000X", None), ("Castillo", "MD", "MD", "ORTHO", "207X00000X", None),
          ("Foster", "NP", "NP-C", "ORTHO", "363LX0001X", "Singh"), ("Yamamoto", "NP", "NP-C", "ORTHO", "363LX0001X", "Brennan"),
          ("Hughes", "RN", "RN", "ORTHO", "163W00000X", "Singh"), ("Pruitt", "RN", "RN", "ORTHO", "163W00000X", "Castillo"),
          ("Moreau", "MD", "MD", "PAIN", "208VP0000X", None), ("Banerjee", "MD", "MD", "PAIN", "208VP0000X", None),
          ("Ellis", "NP", "NP-C", "PAIN", "363LP0200X", "Moreau"), ("Park", "NP", "NP-C", "PAIN", "363LP0200X", "Banerjee"),
          ("Lindqvist", "RN", "RN", "PAIN", "163W00000X", "Moreau"), ("Adeyemi", "RN", "RN", "PAIN", "163W00000X", "Banerjee")]
# facility index -> equipment and rooms (name, how many). Becomes one row per unit in the resource table (multispec.build_resource_master).
RESOURCES = {0: [("Treatment table", 14), ("Gym station", 12), ("E-stim unit", 5), ("Therapeutic ultrasound", 2), ("Traction unit", 1)],
             1: [("Treatment table", 10), ("Gym station", 8), ("E-stim unit", 4), ("Therapeutic ultrasound", 2), ("Exam room", 2), ("ECG cart", 1), ("Nurse treatment room", 1)],
             2: [("Exam room", 8), ("X-ray room", 1), ("Ultrasound suite", 1), ("EMG lab", 1), ("ECG cart", 2), ("Nurse treatment room", 2), ("Procedure room", 2), ("C-arm suite", 2)]}
# staff_number, role, team, weekly hours
STAFF = [("FD01", "front desk", "billing", 40), ("FD02", "front desk", "billing", 40), ("B01", "billing specialist", "billing", 40),
         ("B02", "billing specialist", "billing", 40), ("B03", "billing lead", "billing", 40), ("D01", "denial specialist", "billing", 40),
         ("AR01", "AR specialist", "billing", 40), ("PP01", "payment poster", "billing", 32), ("C01", "coder", "coding", 40),
         ("C02", "coder", "coding", 40), ("C03", "coder (cross-trained)", "coding", 20), ("M01", "practice manager", "billing", 40),
         ("FD03", "front desk", "billing", 40), ("FD04", "front desk", "billing", 40), ("B04", "billing specialist", "billing", 40), ("D02", "denial specialist", "billing", 40),
         ("AR02", "AR specialist", "billing", 40), ("C04", "coder", "coding", 40), ("PA01", "prior authorization specialist", "billing", 40)]


def _nth(year, month, weekday, n):
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))
    return d


def _last(year, month, weekday):
    d = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - weekday) % 7)


def holidays(year):
    obs = lambda d: d + dt.timedelta(days=1) if d.weekday() == 6 else d - dt.timedelta(days=1) if d.weekday() == 5 else d
    return {obs(dt.date(year, 1, 1)): "new_year", _nth(year, 1, 0, 3): "mlk", _nth(year, 2, 0, 3): "presidents",
            _last(year, 5, 0): "memorial", obs(dt.date(year, 6, 19)): "juneteenth", obs(dt.date(year, 7, 4)): "independence",
            _nth(year, 9, 0, 1): "labor", _nth(year, 10, 0, 2): "columbus", obs(dt.date(year, 11, 11)): "veterans",
            _nth(year, 11, 3, 4): "thanksgiving", obs(dt.date(year, 12, 25)): "christmas"}


def build_reference(s):
    """Adds the reference tables to Synth `s`; returns a context dict of ids for later stages."""
    ctx = {}
    ctx["practice"] = s.add("practice", practice_number="VW01", practice_name="Valley Wellness Health", tax_id="990000001",
                            group_npi="1900000000", time_zone="America/Chicago", fiscal_year_start_month=1, go_live_date=dt.date(2025, 11, 1))
    ctx["specialty"] = {c: s.add("specialty", specialty_code=c, specialty_name=n, specialty_group=g, is_primary_care=(c == "FM"), taxonomy_prefix=t, cms_specialty_code=cms)
                        for c, n, g, t, cms in [("PT", "Physical therapy", "therapy", "2251", "65"), ("OT", "Occupational therapy", "therapy", "225X", "67"),
                                                ("FM", "Family medicine", "primary_care", "207Q", "08"), ("ORTHO", "Orthopedics", "surgical", "207X", "20"),
                                                ("PAIN", "Pain management", "procedural", "208V", "09")]}
    ctx["pos"] = {c: s.add("place_of_service", pos_code=c, pos_name=n, setting=st, is_facility=False, is_telehealth=(c == "02"),
                           effective_from=FROM, effective_to=TO)
                  for c, n, st in [("11", "Office", "outpatient"), ("12", "Home", "home"), ("02", "Telehealth", "telehealth")]}
    ctx["facility"] = [s.add("facility", facility_number=f"LOC{i + 1}", facility_name=name, practice_id=ctx["practice"], facility_type="clinic",
                             default_place_of_service_id=ctx["pos"]["11"], facility_npi=f"19000001{i:02d}", state="TX", open_date=dt.date(2019, 1, 1),
                             zip=z, rooms=r, time_zone="America/Chicago")
                       for i, (name, z, r) in enumerate([("Valley Wellness Health, Main Street", "75001", 14), ("Valley Wellness Health, Northgate", "75002", 10),
                                                         ("Valley Wellness Health, Southlake", "76092", 17)])]
    ctx["provider"] = {}
    for i, (name, kind, cred) in enumerate(PROVIDERS):
        spec = ctx["specialty"]["OT" if kind == "OT" else "PT"]
        ctx["provider"][name] = s.add("provider", npi=f"19000002{i:02d}", provider_number=f"PRV{i + 1:02d}", provider_type=kind, specialty_id=spec,
                                      taxonomy_code="225X00000X" if kind == "OT" else "225100000X", credential=cred, provider_name=f"{name}, {cred}",
                                      practice_id=ctx["practice"], start_date=dt.date(2019, 1, 1))
    for n, sup in (("Brooks", "Rao"), ("Haines", "Lee"), ("Moreno", "Okafor")):     # assistants work under a supervising therapist
        r = next(r for r in s.rows["provider"] if r["provider_id"] == ctx["provider"][n])
        r["supervising_provider_id"] = ctx["provider"][sup]
    ctx["roster"] = {c: dict(MD=[], NP=[], RN=[]) for c in ("FM", "ORTHO", "PAIN")}
    ctx["supervisor"] = {}
    for i, (name, kind, cred, spec, tax, sup) in enumerate(CLINIC):
        ctx["provider"][name] = s.add("provider", npi=f"19000004{i:02d}", provider_number=f"CLN{i + 1:02d}", provider_type=kind, specialty_id=ctx["specialty"][spec],
                                      taxonomy_code=tax, credential=cred, provider_name=f"{name}, {cred}", practice_id=ctx["practice"], start_date=dt.date(2019, 1, 1),
                                      supervising_provider_id=ctx["provider"][sup] if sup else None)
        ctx["roster"][spec][kind].append(name)
        ctx["supervisor"][name] = sup or name
    ctx["payer"] = {}
    for code, name, typ, fil, cor, app, turn, share, mult in PAYERS:
        ctx["payer"][code] = s.add("payer", payer_code=code, payer_name=name, payer_number=code, payer_type=typ, filing_days=fil, corrected_claim_days=cor,
                                   appeal_days=app, standard_turnaround_days=turn, supports_electronic_auth=(typ == "commercial"), state="TX",
                                   filing_clock_basis="service_date")
    ctx["modifier"] = {c: s.add("modifier", modifier_code=c, modifier_group=g, affects_payment=ap, short_label=lab, effective_from=FROM, effective_to=TO)
                       for c, g, ap, lab in [("GP", "therapy", False, "Services under a PT plan of care"), ("GO", "therapy", False, "Services under an OT plan of care"),
                                             ("KX", "therapy", False, "Requirements specified in the policy are met"), ("59", "ncci", False, "Distinct procedural service"),
                                             ("XU", "ncci", False, "Unusual non-overlapping service"), ("95", "telehealth", False, "Synchronous telemedicine"),
                                             ("CQ", "therapy", True, "Services furnished by a PTA"), ("CO", "therapy", True, "Services furnished by an OTA"),
                                             ("25", "em", False, "Separate E/M on the day of a procedure"),
                                             ("RT", "anatomic", False, "Right side"), ("LT", "anatomic", False, "Left side")]}
    ctx["cpt"] = {}
    for code, lab, timed, lim, fee in CPT:
        ctx["cpt"][code] = s.add("cpt_code", code=code, code_type="HCPCS" if code[0] == "G" else "CPT", effective_from=FROM, effective_to=TO, short_label=lab,
                                 category=CPT_CATEGORY.get(code) or ("evaluation" if lab.find("evaluation") >= 0 or lab.find("re-eval") >= 0 else "therapy"),
                                 is_add_on=False, is_timed=timed, unit_limit_per_day=lim, is_unrecognized=False, unit_limit_basis="per_day")
    ctx["icd_pt"] = ICD_PT
    ctx["icd"] = {c: s.add("diagnosis_code", icd10_code=c, effective_from=FROM, effective_to=TO, description=d, is_billable=True, is_unspecified=c.endswith("0") and c != "M5450" or c == "M5450",
                           is_unrecognized=False) for c, d in ICD}
    ctx["carc"] = {c: s.add("adjustment_reason", carc_code=c, effective_from=FROM, effective_to=TO, reason_class=cls, short_label=lab, reason_category=cat,
                            owner_role=own, upstream_stage=stage, is_appealable=bool(ap), is_technical=bool(tech), is_preventable_default=bool(prev),
                            typical_group="PR" if cls == "patient_responsibility" else "CO", is_unrecognized=False)
                   for c, lab, cls, cat, own, stage, ap, tech, prev in CARC}
    ctx["rarc"] = {c: s.add("remark_code", rarc_code=c, effective_from=FROM, effective_to=TO, code_qualifier="RARC", short_label=lab, remark_type=t, suggests_action=a,
                            documents_needed=d, is_unrecognized=False) for c, lab, t, a, d in RARC}
    ctx["staff"] = {num: s.add("staff", staff_number=num, practice_id=ctx["practice"], staff_role=role, team=team, weekly_hours=D(hrs), start_date=dt.date(2024, 1, 1))
                    for num, role, team, hrs in STAFF}
    # calendar covers the history, the future schedule and the forecast horizon
    day, n = dt.date(2025, 1, 1), 0
    hol = {**holidays(2025), **holidays(2026), **holidays(2027)}
    while day <= dt.date(2027, 3, 31):
        biz = day.weekday() < 5 and day not in hol
        n += biz
        s.add("calendar", calendar_date=day, is_business_day=biz, is_holiday=day in hol, holiday_code=hol.get(day), business_day_number=n if biz else None)
        day += dt.timedelta(days=1)
    # fees and contract rates: the same code set, one list for the practice and one allowed amount per payer
    ctx["fee"] = {}
    for code, lab, timed, lim, fee in CPT:
        ctx["fee"][code] = D(fee)
        s.add("fee_list", practice_id=ctx["practice"], fee_list_name="Standard fee schedule", cpt_code_id=ctx["cpt"][code], fee_per_unit=D(fee),
              effective_from=dt.date(2025, 1, 1), is_inferred=False, is_default=True, fee_basis="per_unit")
    ctx["rate"] = {}
    for code, name, typ, fil, cor, app, turn, share, mult in PAYERS:
        if typ == "self_pay":
            continue
        for c, lab, timed, lim, fee in CPT:
            allowed = (D(fee) * D(str(mult))).quantize(D("0.01"))
            ctx["rate"][(code, c)] = allowed
            s.add("contract_rate", practice_id=ctx["practice"], payer_id=ctx["payer"][code], cpt_code_id=ctx["cpt"][c], allowed_per_unit=allowed,
                  effective_from=dt.date(2025, 1, 1), rate_source="contract", is_inferred=False, rate_setting="per_unit", rate_basis="fee_schedule",
                  lesser_of_billed=True, confidence=D("1.0000"))
    for k, v, t in [("autonomy_default_level", "L0", "text"), ("timely_filing_alert_days", "30", "int"), ("qa_sample_pct", "5", "int"),
                    ("write_off_requires_two_approvers", "true", "bool")]:
        s.add("practice_settings", practice_id=ctx["practice"], setting_key=k, setting_value=v, value_type=t, effective_from=dt.date(2025, 11, 1),
              effective_to=TO, set_by_role="manager")
    return ctx
