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

CATALOG_VERSION = 2


@dataclass(frozen=True)
class Condition:
    icd10: str
    name: str  # the official-style description shown on the claim
    keywords: tuple[str, ...]  # lower-case phrases a transcript may use for it (the reader matches these)
    chronic: bool = False  # a follow-up for it is expected to be documented in depth
    unspecified: bool = False  # the code is an "unspecified" code, which payers often question
    needs_laterality: bool = False  # the transcript must say left or right
    specialty: str = "primary care"
    complaint: str = ""  # what a patient says in their own words (the generator falls back to the keywords when empty)
    services: tuple[str, ...] = ()  # CPTs commonly done or ordered for it, besides the visit itself
    visit_kind: str = ""  # "" (an ordinary problem visit) | preventive | emergency
    age: str = "adult"  # adult | child: picks the preventive visit code


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
    time_range: tuple[int, int] = (0, 0)  # minutes a documented, billable session may last (timed services only)
    needs_indication: bool = False  # the order must state why (medical necessity), as imaging and special tests do


CONDITIONS: list[Condition] = [
    # ---- the original seven (codes, names and keywords unchanged) ----
    Condition("J02.9", "Acute pharyngitis, unspecified", ("pharyngitis", "sore throat", "strep throat"), unspecified=True),
    Condition("M54.50", "Low back pain, unspecified", ("low back pain", "back pain", "lumbago"), unspecified=True),
    Condition("N39.0", "Urinary tract infection, site not specified", ("urinary tract infection", "uti", "burns when i urinate", "burning with urination")),
    Condition("I10", "Essential (primary) hypertension", ("hypertension", "high blood pressure", "blood pressure follow-up"), chronic=True),
    Condition("E11.9", "Type 2 diabetes mellitus without complications", ("type 2 diabetes", "diabetes"), chronic=True),
    Condition("R05.9", "Cough, unspecified", ("cough",), unspecified=True),
    Condition("M25.569", "Pain in unspecified knee", ("knee pain",), unspecified=True, needs_laterality=True, specialty="orthopedics"),
    # ---- primary care ----
    Condition("E78.5", "Hyperlipidemia, unspecified", ("hyperlipidemia", "high cholesterol", "elevated cholesterol"), chronic=True, unspecified=True,
              complaint="I am here to recheck my cholesterol", services=("80061",)),
    Condition("J06.9", "Acute upper respiratory infection, unspecified", ("upper respiratory infection", "head cold", "common cold"), unspecified=True,
              complaint="I have had a stuffy nose and a scratchy throat for a few days"),
    Condition("J20.9", "Acute bronchitis, unspecified", ("acute bronchitis", "chest cold", "bronchitis"), unspecified=True,
              complaint="I have a deep chest cough with phlegm", services=("71046",)),
    Condition("B34.9", "Viral infection, unspecified", ("viral infection", "viral syndrome", "virus going around"), unspecified=True,
              complaint="I feel achy and run down, like I caught a bug"),
    Condition("R51.9", "Headache, unspecified", ("headache", "headaches"), unspecified=True,
              complaint="I keep getting headaches that will not quit", services=("70450",)),
    Condition("R10.9", "Unspecified abdominal pain", ("abdominal pain", "stomach pain", "belly pain"), unspecified=True,
              complaint="my stomach has been hurting for days", services=("85025", "80053")),
    Condition("K21.9", "Gastro-esophageal reflux disease without esophagitis", ("reflux", "gerd", "acid reflux", "heartburn"), chronic=True,
              complaint="I get heartburn almost every night"),
    Condition("E66.9", "Obesity, unspecified", ("obesity", "weight management", "overweight"), chronic=True, unspecified=True,
              complaint="I want help with my weight", services=("83036",)),
    Condition("E03.9", "Hypothyroidism, unspecified", ("hypothyroidism", "underactive thyroid", "thyroid follow-up"), chronic=True, unspecified=True,
              complaint="I am here to recheck my thyroid", services=("84443",)),
    Condition("D64.9", "Anemia, unspecified", ("anemia", "low iron", "low blood count"), unspecified=True,
              complaint="I have been tired and pale and my last blood count was low", services=("85025",)),
    Condition("R50.9", "Fever, unspecified", ("fever", "feverish"), unspecified=True,
              complaint="I have had a fever since yesterday"),
    Condition("R42", "Dizziness and giddiness", ("dizziness", "lightheaded", "lightheadedness"), unspecified=True,
              complaint="I feel dizzy when I stand up", services=("93000",)),
    Condition("R53.83", "Other fatigue", ("fatigue", "tiredness", "always tired"), unspecified=True,
              complaint="I am tired all the time", services=("85025", "84443")),
    Condition("G47.00", "Insomnia, unspecified", ("insomnia", "cannot sleep", "trouble sleeping"), chronic=True, unspecified=True,
              complaint="I cannot fall asleep at night"),
    Condition("H66.90", "Otitis media, unspecified, unspecified ear", ("otitis media", "ear infection"), unspecified=True, needs_laterality=True,
              complaint="my ear hurts and I cannot hear well", age="child"),
    Condition("Z00.00", "Encounter for general adult medical examination without abnormal findings", ("annual physical", "yearly physical", "preventive visit", "wellness exam"),
              complaint="I am here for my yearly physical", services=("80053", "80061", "85025"), visit_kind="preventive"),
    Condition("Z23", "Encounter for immunization", ("flu shot", "influenza vaccine", "vaccination"),
              complaint="I would like my flu shot", services=("90686", "90471")),
    # ---- orthopedics ----
    Condition("M25.519", "Pain in unspecified shoulder", ("shoulder pain",), unspecified=True, needs_laterality=True, specialty="orthopedics",
              complaint="my shoulder hurts when I lift my arm", services=("73030", "20610")),
    Condition("M17.9", "Osteoarthritis of knee, unspecified", ("osteoarthritis of the knee", "knee osteoarthritis", "knee arthritis"), chronic=True, unspecified=True, needs_laterality=True, specialty="orthopedics",
              complaint="my knee is stiff and aching again", services=("20610", "73560", "97110")),
    Condition("S93.409A", "Sprain of unspecified ligament of unspecified ankle, initial encounter", ("ankle sprain", "sprained ankle", "twisted my ankle"), unspecified=True, needs_laterality=True, specialty="orthopedics",
              complaint="I rolled my ankle playing basketball", services=("73600",)),
    Condition("M54.2", "Cervicalgia", ("neck pain", "cervicalgia", "stiff neck"), specialty="orthopedics",
              complaint="my neck has been stiff and sore", services=("97140", "97110")),
    Condition("M54.16", "Radiculopathy, lumbar region", ("lumbar radiculopathy", "sciatica", "pain shooting down my leg"), specialty="orthopedics",
              complaint="I have pain shooting down my leg", services=("72148", "97110", "97140")),
    Condition("M79.609", "Pain in unspecified limb", ("limb pain", "pain in my arm", "pain in my leg"), unspecified=True, needs_laterality=True, specialty="orthopedics",
              complaint="my arm has been sore for weeks"),
    Condition("S61.419A", "Laceration without foreign body of unspecified hand, initial encounter", ("hand laceration", "cut on my hand", "laceration of the hand"), unspecified=True, needs_laterality=True, specialty="orthopedics",
              complaint="I cut my hand on a kitchen knife", services=("12001",)),
    # ---- cardiology ----
    Condition("I25.10", "Atherosclerotic heart disease of native coronary artery without angina pectoris", ("coronary artery disease", "cad", "coronary disease"), chronic=True, specialty="cardiology",
              complaint="I am here for my heart follow-up", services=("93000",)),
    Condition("I48.91", "Unspecified atrial fibrillation", ("atrial fibrillation", "afib", "irregular heartbeat"), chronic=True, unspecified=True, specialty="cardiology",
              complaint="my heart feels like it flutters and skips", services=("93000",)),
    Condition("I50.9", "Heart failure, unspecified", ("heart failure", "chf", "swelling in my legs and short of breath"), chronic=True, unspecified=True, specialty="cardiology",
              complaint="my ankles are swollen and I get winded on stairs", services=("93000", "71046")),
    Condition("R07.9", "Chest pain, unspecified", ("chest pain", "pressure in my chest"), unspecified=True, specialty="cardiology",
              complaint="I have had chest pain on and off", services=("93000", "71046")),
    Condition("R00.2", "Palpitations", ("palpitations", "heart racing", "pounding heart"), specialty="cardiology",
              complaint="my heart has been racing at random times", services=("93000",)),
    # ---- pulmonology ----
    Condition("J45.909", "Unspecified asthma, uncomplicated", ("asthma", "wheezing", "asthma follow-up"), chronic=True, unspecified=True, specialty="pulmonology",
              complaint="my asthma has been acting up", services=("94010", "94640")),
    Condition("J44.9", "Chronic obstructive pulmonary disease, unspecified", ("copd", "chronic obstructive pulmonary disease", "emphysema"), chronic=True, unspecified=True, specialty="pulmonology",
              complaint="I am more short of breath than usual", services=("94010", "71046")),
    Condition("J18.9", "Pneumonia, unspecified organism", ("pneumonia", "lung infection"), unspecified=True, specialty="pulmonology",
              complaint="I have a fever, cough and chest pain when I breathe", services=("71046",)),
    Condition("R06.02", "Shortness of breath", ("shortness of breath", "short of breath", "trouble breathing"), specialty="pulmonology",
              complaint="I cannot catch my breath", services=("94010", "71046", "93000")),
    Condition("G47.33", "Obstructive sleep apnea (adult) (pediatric)", ("sleep apnea", "obstructive sleep apnea", "osa"), chronic=True, specialty="pulmonology",
              complaint="my wife says I stop breathing at night"),
    # ---- dermatology ----
    Condition("L30.9", "Dermatitis, unspecified", ("dermatitis", "itchy rash", "skin rash"), unspecified=True, specialty="dermatology",
              complaint="I have an itchy rash that keeps spreading"),
    Condition("L70.0", "Acne vulgaris", ("acne", "acne vulgaris", "breakouts"), specialty="dermatology",
              complaint="my acne is getting worse"),
    Condition("L40.9", "Psoriasis, unspecified", ("psoriasis", "psoriatic plaques", "scaly plaques"), chronic=True, unspecified=True, specialty="dermatology",
              complaint="the scaly patches on my elbows are flaring"),
    Condition("B35.3", "Tinea pedis", ("tinea pedis", "athlete's foot", "foot fungus"), specialty="dermatology",
              complaint="the skin between my toes is peeling and itchy"),
    Condition("D22.9", "Melanocytic nevi, unspecified", ("atypical mole", "changing mole", "melanocytic nevus"), unspecified=True, specialty="dermatology",
              complaint="a mole on my back has changed color", services=("11102",)),
    Condition("L02.91", "Cutaneous abscess, unspecified", ("skin abscess", "boil", "abscess"), unspecified=True, specialty="dermatology",
              complaint="I have a painful boil that keeps getting bigger", services=("10060",)),
    Condition("B07.9", "Viral wart, unspecified", ("viral wart", "warts", "wart"), unspecified=True, specialty="dermatology",
              complaint="I have a wart on my hand that will not go away", services=("17110",)),
    # ---- mental health ----
    Condition("F32.A", "Depression, unspecified", ("depression", "feeling down", "low mood"), chronic=True, unspecified=True, specialty="mental health",
              complaint="I have been feeling down for weeks", services=("90834", "90837")),
    Condition("F41.9", "Anxiety disorder, unspecified", ("anxiety", "anxiety disorder", "panic and worry"), chronic=True, unspecified=True, specialty="mental health",
              complaint="I worry constantly and cannot relax", services=("90834", "90837")),
    Condition("F43.10", "Post-traumatic stress disorder, unspecified", ("ptsd", "post-traumatic stress", "flashbacks"), chronic=True, unspecified=True, specialty="mental health",
              complaint="I keep having flashbacks and nightmares", services=("90837",)),
    Condition("F90.9", "Attention-deficit hyperactivity disorder, unspecified type", ("adhd", "attention deficit", "trouble focusing"), chronic=True, unspecified=True, specialty="mental health",
              complaint="I cannot focus at work", services=("90791",)),
    Condition("F17.210", "Nicotine dependence, cigarettes, uncomplicated", ("smoking cessation", "nicotine dependence", "want to quit smoking"), chronic=True, specialty="mental health",
              complaint="I want to quit smoking", services=("99406",)),
    # ---- OB-GYN basics ----
    Condition("Z34.00", "Encounter for supervision of normal first pregnancy, unspecified trimester", ("prenatal visit", "routine prenatal", "pregnancy supervision"), unspecified=True, specialty="obstetrics and gynecology",
              complaint="I am pregnant and here for my checkup", services=("81002",)),
    Condition("N76.0", "Acute vaginitis", ("vaginitis", "vaginal irritation", "vaginal discharge"), specialty="obstetrics and gynecology",
              complaint="I have vaginal itching and discharge", services=("81002",)),
    Condition("N93.9", "Abnormal uterine and vaginal bleeding, unspecified", ("abnormal uterine bleeding", "irregular periods", "heavy periods"), unspecified=True, specialty="obstetrics and gynecology",
              complaint="my periods have been heavy and irregular", services=("85025",)),
    Condition("Z01.419", "Encounter for gynecological examination (general) (routine) without abnormal findings", ("well woman exam", "gynecologic exam", "pap smear visit"), specialty="obstetrics and gynecology",
              complaint="I am here for my annual women's health exam", visit_kind="preventive"),
    # ---- pediatrics ----
    Condition("Z00.129", "Encounter for routine child health examination without abnormal findings", ("well child visit", "well-child check", "routine child exam"), specialty="pediatrics",
              complaint="she is here for her yearly checkup", services=("90471",), visit_kind="preventive", age="child"),
    Condition("J21.9", "Acute bronchiolitis, unspecified", ("bronchiolitis", "wheezy cold", "baby is wheezing"), unspecified=True, specialty="pediatrics",
              complaint="my baby is wheezing and not feeding well", age="child"),
    Condition("A08.4", "Viral intestinal infection, unspecified", ("stomach virus", "viral gastroenteritis", "vomiting and diarrhea"), unspecified=True, specialty="pediatrics",
              complaint="he has been throwing up and has loose stools", age="child"),
    Condition("B08.4", "Enteroviral vesicular stomatitis with exanthem", ("hand foot and mouth", "hand, foot and mouth disease"), specialty="pediatrics",
              complaint="she has blisters in her mouth and on her hands", age="child"),
    Condition("R11.10", "Vomiting, unspecified", ("vomiting", "throwing up"), unspecified=True, specialty="pediatrics",
              complaint="he keeps throwing up", age="child"),
    # ---- emergency department ----
    Condition("S06.0X0A", "Concussion without loss of consciousness, initial encounter", ("concussion", "hit my head", "head injury"), specialty="emergency", visit_kind="emergency",
              complaint="I hit my head and feel foggy", services=("70450",)),
    Condition("R55", "Syncope and collapse", ("syncope", "passed out", "fainted"), unspecified=True, specialty="emergency", visit_kind="emergency",
              complaint="I passed out at work", services=("93000", "80053")),
    Condition("N20.0", "Calculus of kidney", ("kidney stone", "renal colic", "stone in my kidney"), specialty="emergency", visit_kind="emergency",
              complaint="I have terrible pain in my side and blood in my urine", services=("81002", "80053")),
    Condition("T78.40XA", "Allergy, unspecified, initial encounter", ("allergic reaction", "hives and swelling", "allergy attack"), unspecified=True, specialty="emergency", visit_kind="emergency",
              complaint="my face and lips swelled up after dinner", services=("96372",)),
    Condition("S01.01XA", "Laceration without foreign body of scalp, initial encounter", ("scalp laceration", "cut on my head", "scalp cut"), specialty="emergency", visit_kind="emergency",
              complaint="I split my head open on a cabinet", services=("12001",)),
]

SERVICES: list[Service] = [
    # ---- the original eight (codes, names and fees unchanged) ----
    Service("99213", "Office visit, established patient, low complexity", "em_established", (), fee="110.00"),
    Service("99214", "Office visit, established patient, moderate complexity", "em_established", (), fee="160.00"),
    Service("99203", "Office visit, new patient, low complexity", "em_new", (), fee="150.00"),
    Service("99204", "Office visit, new patient, moderate complexity", "em_new", (), fee="220.00"),
    Service("97110", "Therapeutic exercise", "therapy", ("therapeutic exercise", "exercise therapy"), fee="65.00", unit="15 minutes", needs_time=True, specialty="physical therapy", time_range=(8, 60)),
    Service("71046", "Chest X-ray, two views", "imaging", ("chest x-ray", "chest xray", "chest radiograph"), fee="95.00", specialty="radiology", needs_indication=True),
    Service("81002", "Urinalysis, dipstick", "lab", ("urinalysis", "urine dipstick"), fee="18.00"),
    Service("96372", "Therapeutic injection", "injection", ("injection", "injected", "shot of"), fee="45.00"),
    # ---- office visits at the other levels ----
    Service("99202", "Office visit, new patient, straightforward", "em_new", (), fee="95.00"),
    Service("99205", "Office visit, new patient, high complexity", "em_new", (), fee="295.00"),
    Service("99211", "Office visit, established patient, minimal (nurse visit)", "em_established", (), fee="40.00"),
    Service("99212", "Office visit, established patient, straightforward", "em_established", (), fee="75.00"),
    Service("99215", "Office visit, established patient, high complexity", "em_established", (), fee="225.00"),
    # ---- emergency department visits ----
    Service("99283", "Emergency department visit, moderate severity", "emergency", (), fee="260.00", specialty="emergency"),
    Service("99284", "Emergency department visit, high severity", "emergency", (), fee="410.00", specialty="emergency"),
    Service("99285", "Emergency department visit, high severity with threat to life", "emergency", (), fee="590.00", specialty="emergency"),
    # ---- preventive visits ----
    Service("99385", "Preventive visit, new patient, age 18 to 39", "preventive", (), fee="230.00"),
    Service("99395", "Preventive visit, established patient, age 18 to 39", "preventive", (), fee="210.00"),
    Service("99396", "Preventive visit, established patient, age 40 to 64", "preventive", (), fee="235.00"),
    Service("99393", "Preventive visit, established patient, age 5 to 11", "preventive", (), fee="195.00", specialty="pediatrics"),
    # ---- laboratory ----
    Service("80053", "Comprehensive metabolic panel", "lab", ("comprehensive metabolic panel", "cmp", "metabolic panel"), fee="35.00"),
    Service("85025", "Complete blood count with differential", "lab", ("complete blood count", "cbc", "blood count"), fee="28.00"),
    Service("83036", "Hemoglobin A1c", "lab", ("hemoglobin a1c", "a1c", "glycohemoglobin"), fee="30.00"),
    Service("80061", "Lipid panel", "lab", ("lipid panel", "cholesterol panel", "lipids"), fee="40.00"),
    Service("84443", "Thyroid stimulating hormone (TSH)", "lab", ("tsh", "thyroid stimulating hormone", "thyroid level"), fee="38.00"),
    Service("87880", "Rapid strep test (group A streptococcus antigen)", "lab", ("rapid strep", "strep test", "throat swab for strep"), fee="25.00"),
    Service("36415", "Venipuncture (blood draw)", "lab", ("venipuncture", "blood draw", "drew blood"), fee="12.00"),
    Service("87086", "Urine culture", "lab", ("urine culture", "culture of the urine"), fee="32.00"),
    # ---- imaging ----
    Service("73560", "Knee X-ray, 1 or 2 views", "imaging", ("knee x-ray", "knee xray", "x-ray of the knee"), fee="85.00", needs_laterality=True, specialty="radiology", needs_indication=True),
    Service("72100", "Lumbar spine X-ray, 2 or 3 views", "imaging", ("lumbar spine x-ray", "low back x-ray", "x-ray of the lower back"), fee="105.00", specialty="radiology", needs_indication=True),
    Service("73030", "Shoulder X-ray, minimum 2 views", "imaging", ("shoulder x-ray", "x-ray of the shoulder"), fee="90.00", needs_laterality=True, specialty="radiology", needs_indication=True),
    Service("73600", "Ankle X-ray, 2 views", "imaging", ("ankle x-ray", "x-ray of the ankle"), fee="88.00", needs_laterality=True, specialty="radiology", needs_indication=True),
    Service("70450", "CT of the head without contrast", "imaging", ("ct of the head", "head ct", "ct scan of the head"), fee="520.00", specialty="radiology", needs_indication=True),
    Service("72148", "MRI of the lumbar spine without contrast", "imaging", ("mri of the lumbar spine", "lumbar mri", "mri of the low back"), fee="880.00", specialty="radiology", needs_indication=True),
    # ---- physical and mental health therapy (timed) ----
    Service("97112", "Neuromuscular re-education", "therapy", ("neuromuscular re-education", "balance training", "neuromuscular reeducation"), fee="68.00", unit="15 minutes", needs_time=True, specialty="physical therapy", time_range=(8, 45)),
    Service("97140", "Manual therapy techniques", "therapy", ("manual therapy", "joint mobilization", "soft tissue mobilization"), fee="62.00", unit="15 minutes", needs_time=True, specialty="physical therapy", time_range=(8, 45)),
    Service("97530", "Therapeutic activities", "therapy", ("therapeutic activities", "functional activities training"), fee="70.00", unit="15 minutes", needs_time=True, specialty="physical therapy", time_range=(8, 45)),
    Service("97161", "Physical therapy evaluation, low complexity", "therapy", ("physical therapy evaluation", "pt evaluation", "initial pt assessment"), fee="120.00", specialty="physical therapy"),
    Service("90834", "Psychotherapy, 45 minutes", "therapy", ("psychotherapy session", "talk therapy", "counseling session"), fee="125.00", needs_time=True, specialty="mental health", time_range=(38, 52)),
    Service("90837", "Psychotherapy, 60 minutes", "therapy", ("extended psychotherapy", "hour-long psychotherapy", "60-minute therapy session"), fee="170.00", needs_time=True, specialty="mental health", time_range=(53, 70)),
    Service("90791", "Psychiatric diagnostic evaluation", "therapy", ("psychiatric diagnostic evaluation", "psychiatric evaluation", "diagnostic interview"), fee="210.00", specialty="mental health"),
    Service("99406", "Smoking and tobacco cessation counseling, 3 to 10 minutes", "therapy", ("smoking cessation counseling", "tobacco cessation counseling", "counseled on quitting smoking"), fee="22.00", needs_time=True, time_range=(3, 10)),
    # ---- injections and vaccines ----
    Service("20610", "Arthrocentesis or injection, major joint", "injection", ("joint injection", "injected the joint", "steroid injection into the", "aspirated and injected"), fee="130.00", needs_laterality=True, specialty="orthopedics"),
    Service("90471", "Immunization administration", "injection", ("immunization administration", "vaccine was given", "administered the vaccine"), fee="28.00"),
    Service("90686", "Influenza vaccine, quadrivalent, preservative free", "injection", ("flu vaccine", "influenza vaccine given", "flu shot given"), fee="24.00"),
    # ---- office procedures and tests ----
    Service("12001", "Simple repair of superficial wound, 2.5 cm or less", "procedure", ("laceration repair", "sutured the laceration", "simple wound repair"), fee="185.00", needs_laterality=True, specialty="dermatology"),
    Service("11102", "Tangential skin biopsy, single lesion", "procedure", ("skin biopsy", "shave biopsy", "biopsy of the lesion"), fee="150.00", specialty="dermatology"),
    Service("17110", "Destruction of benign lesions, up to 14", "procedure", ("cryotherapy of the wart", "wart destruction", "liquid nitrogen"), fee="115.00", specialty="dermatology"),
    Service("10060", "Incision and drainage of abscess, simple", "procedure", ("incision and drainage", "drained the abscess", "i&d of the abscess"), fee="175.00", specialty="dermatology"),
    Service("69210", "Removal of impacted cerumen", "procedure", ("cerumen removal", "ear wax removal", "irrigated the ear wax"), fee="55.00", needs_laterality=True),
    Service("93000", "Electrocardiogram, 12 lead with interpretation", "procedure", ("ekg", "ecg", "electrocardiogram", "12-lead tracing"), fee="45.00", specialty="cardiology", needs_indication=True),
    Service("94010", "Spirometry", "procedure", ("spirometry", "pulmonary function test", "breathing test"), fee="60.00", specialty="pulmonology", needs_indication=True),
    Service("94640", "Nebulizer treatment", "procedure", ("nebulizer treatment", "breathing treatment", "albuterol neb"), fee="35.00", specialty="pulmonology"),
]

# Pairs billed together that payers commonly bundle: (the payment-bearing code, the component code that is folded into it).
# The payer network turns some of these into bundling edits; the transcript generator uses them to create "bundled" visits.
COMMON_BUNDLES: tuple[tuple[str, str], ...] = (
    ("80053", "36415"), ("85025", "36415"), ("20610", "96372"), ("94010", "94640"), ("97530", "97140"),
    ("12001", "99213"), ("10060", "99213"), ("11102", "99213"), ("17110", "99213"), ("93000", "99213"),
)

def condition_by_icd(icd10: str) -> Condition | None:
    return next((c for c in CONDITIONS if c.icd10 == icd10), None)


def service_by_cpt(cpt: str) -> Service | None:
    return next((s for s in SERVICES if s.cpt == cpt), None)
