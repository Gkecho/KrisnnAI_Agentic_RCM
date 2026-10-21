# ruff: noqa: E501
"""The catalog of conditions and services the live stream knows about. One shared contract for three jobs:

  * the transcript generator writes visits from it,
  * the transcript reader (coder) recognises conditions and services in a transcript through its `keywords`,
  * the payer network decides coverage, authorization and denials from the codes in it.

Everything is synthetic and simplified: the ICD-10 and CPT codes are real code values used as labels, but the rules attached
to them are demo settings, not payer policy. `CONDITIONS` and `SERVICES` may be extended freely; other modules read them at
call time, so a new entry is picked up everywhere without further changes. Keep every keyword lower case.
"""

from __future__ import annotations

from dataclasses import dataclass

CATALOG_VERSION = 1


@dataclass(frozen=True)
class Condition:
    icd10: str
    name: str  # the official-style description shown on the claim
    keywords: tuple[str, ...]  # lower-case phrases a transcript may use for it (the reader matches these)
    chronic: bool = False  # a follow-up for it is expected to be documented in depth
    unspecified: bool = False  # the code is an "unspecified" code, which payers often question
    needs_laterality: bool = False  # the transcript must say left or right
    specialty: str = "primary care"


@dataclass(frozen=True)
class Service:
    cpt: str
    name: str
    family: str  # em_established | em_new | procedure | lab | imaging | therapy | injection | preventive | emergency
    keywords: tuple[str, ...]  # lower-case phrases that show the service was done or ordered
    fee: str = "100.00"  # the practice's charge, a decimal string
    unit: str = "each"  # each | 15 minutes | per site
    needs_laterality: bool = False
    needs_time: bool = False  # billed by time: the transcript must state minutes
    specialty: str = "primary care"


CONDITIONS: list[Condition] = [
    Condition("J02.9", "Acute pharyngitis, unspecified", ("pharyngitis", "sore throat", "strep throat"), unspecified=True),
    Condition("M54.50", "Low back pain, unspecified", ("low back pain", "back pain", "lumbago"), unspecified=True),
    Condition("N39.0", "Urinary tract infection, site not specified", ("urinary tract infection", "uti", "burns when i urinate", "burning with urination")),
    Condition("I10", "Essential (primary) hypertension", ("hypertension", "high blood pressure", "blood pressure follow-up"), chronic=True),
    Condition("E11.9", "Type 2 diabetes mellitus without complications", ("type 2 diabetes", "diabetes"), chronic=True),
    Condition("R05.9", "Cough, unspecified", ("cough",), unspecified=True),
    Condition("M25.569", "Pain in unspecified knee", ("knee pain",), unspecified=True, needs_laterality=True, specialty="orthopedics"),
]

SERVICES: list[Service] = [
    Service("99213", "Office visit, established patient, low complexity", "em_established", (), fee="110.00"),
    Service("99214", "Office visit, established patient, moderate complexity", "em_established", (), fee="160.00"),
    Service("99203", "Office visit, new patient, low complexity", "em_new", (), fee="150.00"),
    Service("99204", "Office visit, new patient, moderate complexity", "em_new", (), fee="220.00"),
    Service("97110", "Therapeutic exercise", "therapy", ("therapeutic exercise", "exercise therapy"), fee="65.00", unit="15 minutes", needs_time=True, specialty="physical therapy"),
    Service("71046", "Chest X-ray, two views", "imaging", ("chest x-ray", "chest xray", "chest radiograph"), fee="95.00", specialty="radiology"),
    Service("81002", "Urinalysis, dipstick", "lab", ("urinalysis", "urine dipstick"), fee="18.00"),
    Service("96372", "Therapeutic injection", "injection", ("injection", "injected", "shot of"), fee="45.00"),
]


def condition_by_icd(icd10: str) -> Condition | None:
    return next((c for c in CONDITIONS if c.icd10 == icd10), None)


def service_by_cpt(cpt: str) -> Service | None:
    return next((s for s in SERVICES if s.cpt == cpt), None)
