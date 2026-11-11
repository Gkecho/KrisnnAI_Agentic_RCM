"""SNOMED to billing-code crosswalk for the Synthea load. Built from the most frequent codes in the 10,000-patient Texas run (seed 20261102).

Synthea codes visits, procedures and conditions in SNOMED CT. A claim needs CPT/HCPCS/CDT and ICD-10. What is not listed here is left out of the claim on purpose:
a social finding such as "Full-time employment", a "Medication review due" situation or a no-charge screening is not something a practice bills, and a procedure with no
code here is dropped from the bill (the bill total is recomputed from the lines that remain, priced from FEE below). Add rows as the coverage report shows gaps.
"""

# encounter SNOMED -> (code, type, short label, category, E/M level)
ENC = {
    "185347001": ("99213", "CPT", "Office visit, established, low", "em", 3),        # encounter for problem
    "162673000": ("99396", "CPT", "Preventive visit, 40-64", "em", None),             # general examination of patient
    "185349003": ("99395", "CPT", "Preventive visit, 18-39", "em", None),             # check up
    "410620009": ("99393", "CPT", "Preventive visit, 5-11", "em", None),              # well child visit
    "185345009": ("99213", "CPT", "Office visit, established, low", "em", 3),        # encounter for symptom
    "702927004": ("99203", "CPT", "Office visit, new, low", "em", 3),                 # urgent care clinic
    "424619006": ("99213", "CPT", "Office visit, established, low", "em", 3),        # prenatal visit
    "50849002": ("99283", "CPT", "Emergency visit, moderate", "em", 3),               # emergency room admission
    "390906007": ("99213", "CPT", "Office visit, established, low", "em", 3),        # follow-up encounter
    "448337001": ("99213", "CPT", "Office visit, established, low", "em", 3),        # telemedicine consultation
    "308335008": ("99213", "CPT", "Office visit, established, low", "em", 3),        # patient encounter procedure
    "371883000": ("99203", "CPT", "Office visit, new, low", "em", 3),                 # outpatient procedure
    "698314001": ("99214", "CPT", "Office visit, established, moderate", "em", 4),   # consultation for treatment
    "36228007": ("92004", "CPT", "Eye exam, new patient", "diagnostic", None),        # ophthalmic examination
    "424441002": ("99204", "CPT", "Office visit, new, moderate", "em", 4),           # prenatal initial visit
    "32485007": ("99223", "CPT", "Hospital admission, high", "em", 5),                # hospital admission
}
# procedure SNOMED -> (code, type, short label, category)
PROC = {
    "171207006": ("G0444", "HCPCS", "Depression screening", "diagnostic"),
    "715252007": ("96127", "CPT", "Brief emotional assessment", "diagnostic"),
    "710841007": ("96127", "CPT", "Brief emotional assessment", "diagnostic"),
    "265764009": ("90935", "CPT", "Hemodialysis, one evaluation", "procedure"),
    "710824005": ("G0136", "HCPCS", "Social needs risk assessment", "diagnostic"),
    "430193006": ("1111F", "CPT2", "Medication reconciliation", "diagnostic"),
    "428211000124100": ("99408", "CPT", "Substance use screening, 15-30 min", "diagnostic"),
    "763302001": ("99408", "CPT", "Substance use screening, 15-30 min", "diagnostic"),
    "713106006": ("99408", "CPT", "Substance use screening, 15-30 min", "diagnostic"),
    "866148006": ("G0136", "HCPCS", "Social needs risk assessment", "diagnostic"),
    "34043003": ("D0120", "CDT", "Periodic oral evaluation", "dental"),
    "274788003": ("D0120", "CDT", "Periodic oral evaluation", "dental"),
    "243085009": ("D1330", "CDT", "Oral hygiene instruction", "dental"),
    "1260009003": ("D1110", "CDT", "Adult prophylaxis", "dental"),
    "1260010008": ("D4346", "CDT", "Scaling for inflammation", "dental"),
    "241046008": ("D0274", "CDT", "Bitewing X-rays, four films", "dental"),
    "68071007": ("D1206", "CDT", "Topical fluoride varnish", "dental"),
    "64544008": ("D4210", "CDT", "Gingivectomy per tooth", "dental"),
    "3802001": ("D9910", "CDT", "Desensitizing medicament", "dental"),
    "703423002": ("96413", "CPT", "Chemotherapy infusion, first hour", "procedure"),
    "398171003": ("92551", "CPT", "Screening hearing test", "diagnostic"),
    "52052004": ("97110", "CPT", "Therapeutic exercise, 15 min", "procedure"),
    "180256009": ("95115", "CPT", "Allergen immunotherapy injection", "procedure"),
    "76601001": ("96372", "CPT", "Therapeutic injection", "procedure"),
    "5880005": ("99211", "CPT", "Office visit, minimal", "em"),
    "252832004": ("92100", "CPT", "Serial tonometry", "diagnostic"),
    "55468007": ("92225", "CPT", "Extended eye exam", "diagnostic"),
    "722161008": ("92250", "CPT", "Fundus photography", "diagnostic"),
    "314971001": ("92250", "CPT", "Fundus photography", "diagnostic"),
    "16830007": ("99173", "CPT", "Visual acuity screening", "diagnostic"),
    "103750000": ("95800", "CPT", "Sleep study, unattended", "diagnostic"),
}
# condition SNOMED -> (ICD-10-CM, description). Social findings and "situation" concepts are not diagnoses and are left out.
ICD = {
    "66383009": ("K0510", "Chronic gingivitis, plaque induced"), "18718003": ("K056", "Periodontal disease, unspecified"),
    "444814009": ("J0190", "Acute sinusitis, unspecified"), "271737000": ("D649", "Anemia, unspecified"),
    "714628002": ("R7303", "Prediabetes"), "162864005": ("E669", "Obesity, unspecified"),
    "59621000": ("I10", "Essential hypertension"), "195662009": ("J029", "Acute pharyngitis, unspecified"),
    "40055000": ("J329", "Chronic sinusitis, unspecified"), "109570002": ("K029", "Dental caries, unspecified"),
    "82423001": ("G8929", "Other chronic pain"), "278860009": ("M5450", "Low back pain, unspecified"),
    "10509002": ("J209", "Acute bronchitis, unspecified"), "72892002": ("Z3400", "Normal pregnancy, unspecified trimester"),
    "414545008": ("I259", "Chronic ischemic heart disease, unspecified"), "237602007": ("E8881", "Metabolic syndrome"),
    "37320007": ("K08109", "Complete loss of teeth, unspecified cause"), "1121000119107": ("M542", "Cervicalgia"),
    "55822004": ("E785", "Hyperlipidemia, unspecified"), "127013003": ("E1122", "Type 2 diabetes with diabetic kidney disease"),
    "65363002": ("H6690", "Otitis media, unspecified"), "431855005": ("N181", "Chronic kidney disease, stage 1"),
    "90781000119102": ("E1129", "Type 2 diabetes with other kidney complication"), "6525002": ("F1920", "Drug dependence, uncomplicated"),
    "73595000": ("Z733", "Stress, not elsewhere classified"), "422650009": ("Z604", "Social exclusion and rejection"),
}
# what the practice charges per code (US dollars, one fee schedule for everybody)
FEE = {"99213": 130, "99396": 210, "99395": 195, "99393": 175, "99203": 190, "99283": 330, "99214": 190, "92004": 220, "99204": 280, "99223": 410, "99211": 55,
       "G0444": 45, "96127": 20, "90935": 330, "G0136": 28, "1111F": 15, "99408": 75, "D0120": 55, "D1330": 30, "D1110": 95, "D4346": 105, "D0274": 55, "D1206": 40, "D4210": 260,
       "D9910": 35, "96413": 240, "92551": 30, "97110": 45, "95115": 40, "96372": 35, "92100": 55, "92225": 70, "92250": 85, "99173": 15, "95800": 310}
# place of service by Synthea encounter class: (POS code, name, setting, is_facility, is_telehealth)
POS = {"ambulatory": ("11", "Office", "office", False, False), "wellness": ("11", "Office", "office", False, False), "outpatient": ("22", "On-campus outpatient hospital", "hospital", True, False),
       "urgentcare": ("20", "Urgent care facility", "urgent_care", True, False), "emergency": ("23", "Emergency room, hospital", "hospital", True, False),
       "inpatient": ("21", "Inpatient hospital", "hospital", True, False), "virtual": ("02", "Telehealth, not in the patient's home", "telehealth", False, True),
       "home": ("12", "Home", "home", False, False), "hospice": ("34", "Hospice", "hospice", True, False), "snf": ("31", "Skilled nursing facility", "snf", True, False)}
