"""Placeholder code crosswalks from Synthea's SNOMED world to the CPT / ICD-10 world the claim agents read.

Synthea codes its clinical data in SNOMED CT and does not ship CPT or ICD-10. These small tables are STAND-INS so a
Synthea run can be billed; they are not a medical coding reference. Anything not listed falls back (E/M by visit class,
a general-exam diagnosis) and is counted in the build report so the gap is visible.
"""

from __future__ import annotations

from decimal import Decimal

# Visit class (Synthea ENCOUNTERCLASS) -> professional E/M CPT. Classes not listed are not billed on a 837P.
EM_BY_CLASS: dict[str, tuple[str, ...]] = {
    "wellness": ("99395", "99396"),  # by age: under 40, 40 and over
    "ambulatory": ("99213", "99214"),
    "outpatient": ("99213", "99214"),
    "urgentcare": ("99203", "99204"),
    "emergency": ("99283",),
}

# SNOMED procedure -> CPT (a handful of common ones; placeholder)
PROCEDURE_CPT: dict[str, str] = {
    "399208008": "71046",  # plain chest x-ray
    "29303009": "93000",  # electrocardiogram
    "73761001": "45378",  # colonoscopy
    "24623002": "77067",  # screening mammography
    "169553002": "11981",  # insertion of subcutaneous contraceptive
    "171207006": "96127",  # depression screening
}

# SNOMED condition -> ICD-10-CM (placeholder)
CONDITION_ICD10: dict[str, str] = {
    "59621000": "I10",
    "38341003": "I10",
    "44054006": "E119",
    "15777000": "R7303",
    "195662009": "J029",
    "10509002": "J209",
    "444814009": "J0190",
    "40055000": "J329",
    "36971009": "J329",
    "72892002": "Z3400",
    "414545008": "I259",
    "271737000": "D649",
    "195967001": "J45909",
    "233678006": "J45909",
    "49436004": "I4891",
    "65363002": "H669",
    "44465007": "S934",
    "110030002": "S060",
    "84757009": "G409",
    "128613002": "G409",
    "431855005": "N181",
    "431856006": "N182",
    "433144002": "N183",
    "87433001": "J439",
    "162864005": "E669",
}
FALLBACK_ICD10 = "Z0000"  # encounter for general adult medical examination

# Contract-style base fee per CPT; the simulated payers pay base x their multiplier. Billed charge = base x 1.6.
CPT_BASE_FEE: dict[str, Decimal] = {
    "99213": Decimal("92.00"),
    "99214": Decimal("130.00"),
    "99203": Decimal("120.00"),
    "99204": Decimal("180.00"),
    "99283": Decimal("210.00"),
    "99395": Decimal("140.00"),
    "99396": Decimal("150.00"),
    "71046": Decimal("55.00"),
    "93000": Decimal("22.00"),
    "45378": Decimal("900.00"),
    "77067": Decimal("150.00"),
    "11981": Decimal("150.00"),
    "96127": Decimal("6.00"),
}
