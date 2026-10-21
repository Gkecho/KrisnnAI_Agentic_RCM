# ruff: noqa: E501  (regex tables and phrase pools read better on one line)
"""The transcript reader: turns ANY visit note into a structured, explainable `Reading`. Rules only, no model, no network.

A client may type or paste a note in any layout: our own "Provider:/Patient:" dialogue, a SOAP note (S:/O:/A:/P: or Subjective/
Objective/Assessment/Plan), a narrative paragraph, dictation without punctuation, a bullet list, shouting capitals, stray whitespace.
The reader finds the named sections where they exist and falls back to cue words where they do not. It extracts

  * patient status (new / established / unknown), the history-of-present-illness components, the body systems examined;
  * the conditions named in the ASSESSMENT, matched to the catalog (`krisnai.live.catalog`) by its keywords plus a table of
    synonyms and abbreviations (HTN, DM2, UTI, LBP ...), plurals and one-letter typos, each with the words that justify it;
  * negation ("no fever", "denies chest pain"), uncertainty ("rule out", "possible"), history ("history of") and family history,
    which keep a mention out of the diagnosis list;
  * services performed or ordered (catalog services by keyword), minutes converted to 15-minute units, laterality
    (left / right / bilateral), whether a plan and a signature are present.

THE RULE THAT MATTERS: the reader never guesses. Whatever it cannot interpret (an unknown diagnosis phrase, a mention that may
be a rule-out, a spelling it had to repair, conflicting statements, a service offered with no outcome) is written to
`Reading.uncertainties`, and the coder routes any visit with an uncertainty to a person. The catalog is read at CALL time, never
copied, so entries added to `catalog.CONDITIONS` / `catalog.SERVICES` are recognised at once.

Everything here is synthetic-data tooling for the demo; a certified coder decides every code.
"""

from __future__ import annotations

import re
import unicodedata
from bisect import bisect_right
from dataclasses import dataclass, field
from functools import lru_cache

from krisnai.live import catalog

# ---------------------------------------------------------------------------------------------------- vocabulary
# alias -> a phrase that is (or names) a catalog keyword. The alias resolves to whichever catalog condition holds that phrase at
# call time, so an alias whose condition is not in the catalog is simply inert.
SYNONYMS: dict[str, str] = {
    # hypertension
    "htn": "hypertension", "hbp": "high blood pressure", "high bp": "high blood pressure", "elevated blood pressure": "high blood pressure",
    "elevated bp": "high blood pressure", "hypertensive": "hypertension", "essential hypertension": "hypertension",
    "hypertension": "hypertension", "bp follow-up": "high blood pressure", "bp check": "high blood pressure",
    # diabetes
    "dm2": "type 2 diabetes", "dm 2": "type 2 diabetes", "t2dm": "type 2 diabetes", "t2 dm": "type 2 diabetes", "niddm": "type 2 diabetes",
    "type ii diabetes": "type 2 diabetes", "type two diabetes": "type 2 diabetes", "diabetes mellitus type 2": "type 2 diabetes",
    "diabetes mellitus type ii": "type 2 diabetes", "diabetes mellitus type two": "type 2 diabetes", "diabetes mellitus 2": "type 2 diabetes",
    "adult onset diabetes": "type 2 diabetes", "diabetes mellitus": "diabetes", "sugar diabetes": "diabetes",
    "dm1": "type 1 diabetes", "t1dm": "type 1 diabetes", "type i diabetes": "type 1 diabetes",
    # urinary
    "uti": "urinary tract infection", "utis": "urinary tract infection", "urinary infection": "urinary tract infection",
    "bladder infection": "urinary tract infection", "cystitis": "urinary tract infection", "urine infection": "urinary tract infection",
    "uti symptoms": "urinary tract infection", "dysuria": "burning with urination",
    # back / joints
    "lbp": "low back pain", "low-back pain": "low back pain", "lumbar pain": "low back pain", "lumbalgia": "low back pain",
    "backache": "back pain", "back ache": "back pain", "lower back pain": "low back pain", "lumbar strain": "low back pain",
    "knee ache": "knee pain", "pain in the knee": "knee pain", "pain in knee": "knee pain", "knee discomfort": "knee pain",
    "oa": "osteoarthritis", "degenerative joint disease": "osteoarthritis", "djd": "osteoarthritis",
    "shoulder ache": "shoulder pain", "neck ache": "neck pain", "cervicalgia": "neck pain", "hip ache": "hip pain",
    # throat / chest / breathing
    "pharyngitis": "pharyngitis", "strep": "strep throat", "strep pharyngitis": "strep throat", "throat infection": "pharyngitis",
    "scratchy throat": "sore throat", "throat pain": "sore throat", "uri": "upper respiratory infection", "urti": "upper respiratory infection",
    "common cold": "upper respiratory infection", "head cold": "upper respiratory infection", "dry cough": "cough", "coughing": "cough",
    "persistent cough": "cough", "sob": "shortness of breath", "dyspnea": "shortness of breath", "short of breath": "shortness of breath",
    "difficulty breathing": "shortness of breath", "cp": "chest pain", "chest discomfort": "chest pain", "chest tightness": "chest pain",
    "copd": "chronic obstructive pulmonary disease", "emphysema": "chronic obstructive pulmonary disease",
    "reactive airway disease": "asthma", "wheezing": "asthma", "bronchitis": "bronchitis", "pna": "pneumonia",
    # heart / metabolic / other chronic
    "afib": "atrial fibrillation", "a-fib": "atrial fibrillation", "a fib": "atrial fibrillation", "chf": "heart failure",
    "congestive heart failure": "heart failure", "cad": "coronary artery disease", "ckd": "chronic kidney disease",
    "kidney disease": "chronic kidney disease", "hld": "hyperlipidemia", "high cholesterol": "hyperlipidemia",
    "elevated cholesterol": "hyperlipidemia", "dyslipidemia": "hyperlipidemia", "hypercholesterolemia": "hyperlipidemia",
    "gerd": "gastroesophageal reflux", "acid reflux": "gastroesophageal reflux", "reflux": "gastroesophageal reflux",
    "heartburn": "gastroesophageal reflux", "hypothyroid": "hypothyroidism", "underactive thyroid": "hypothyroidism",
    "obese": "obesity", "overweight": "obesity", "anaemia": "anemia", "low iron": "anemia", "depressed": "depression",
    "major depression": "depression", "anxious": "anxiety", "gad": "anxiety", "panic attacks": "anxiety", "trouble sleeping": "insomnia",
    "cant sleep": "insomnia", "sleep difficulty": "insomnia", "migraines": "migraine", "headaches": "headache",
    "stomach pain": "abdominal pain", "belly pain": "abdominal pain", "stomach ache": "abdominal pain", "abd pain": "abdominal pain",
    "tummy ache": "abdominal pain", "dizzy": "dizziness", "lightheadedness": "dizziness", "vertigo": "dizziness",
    "allergic rhinitis": "allergic rhinitis", "hay fever": "allergic rhinitis", "seasonal allergies": "allergic rhinitis",
    "allergies": "allergic rhinitis", "sinus infection": "sinusitis", "ear infection": "otitis media", "pink eye": "conjunctivitis",
    "skin infection": "cellulitis", "eczema": "dermatitis", "rash": "dermatitis", "sprain": "sprain", "ankle sprain": "ankle sprain",
    "tiredness": "fatigue", "tired": "fatigue", "nausea and vomiting": "nausea", "throwing up": "vomiting", "loose stools": "diarrhea",
}
# ambiguous abbreviations are never mapped; they are reported if they appear in the assessment
AMBIGUOUS = {"dm": "diabetes of an unstated type", "ms": "multiple sclerosis or mitral stenosis", "ra": "rheumatoid arthritis or right atrium",
             "pt": "patient or physical therapy", "cp": "chest pain or cerebral palsy"}  # fmt: skip
# alias -> a phrase that is (or names) a catalog service keyword
SERVICE_SYNONYMS: dict[str, str] = {
    "cxr": "chest x-ray", "chest film": "chest x-ray", "chest x ray": "chest x-ray", "chest xr": "chest x-ray",
    "ekg": "electrocardiogram", "ecg": "electrocardiogram", "12 lead": "electrocardiogram", "12-lead": "electrocardiogram",
    "ua": "urinalysis", "urine dip": "urinalysis", "dipstick": "urinalysis", "urine dipstick": "urinalysis", "urine test": "urinalysis",
    "ther ex": "therapeutic exercise", "therex": "therapeutic exercise", "therapeutic exercises": "therapeutic exercise",
    "ther-ex": "therapeutic exercise", "exercise therapy": "therapeutic exercise", "strengthening exercises": "therapeutic exercise",
    "cortisone shot": "injection", "steroid shot": "injection", "b12 shot": "injection", "b12 injection": "injection", "shot": "injection",
    "cortisone injection": "injection", "steroid injection": "injection", "im injection": "injection", "flu shot": "influenza vaccine",
}
# things that look like a billable service; if one is named and no catalog service explains it, that is an uncertainty
UNKNOWN_SERVICE_TERMS = (r"mri", r"ct scan", r"cat scan", r"ultrasound", r"sonogram", r"biopsy", r"colonoscopy", r"endoscopy", r"culture", r"swab",
                         r"rapid strep(?: test)?", r"strep test", r"vaccine", r"vaccination", r"immuni[sz]ation", r"excision", r"suture\w*",
                         r"laceration repair", r"splint\w*", r"cast", r"spirometry", r"nebuli[sz]er(?: treatment)?", r"audiogram", r"x[\s-]?rays?",
                         r"radiograph\w*", r"electrocardiogram", r"ekg", r"ecg", r"injections?", r"blood draw", r"venipuncture", r"cryotherapy",
                         r"aspiration", r"drain\w*", r"hearing test", r"eye exam", r"pap smear", r"mammogram", r"echocardiogram", r"stress test",
                         r"physical therapy session", r"massage", r"manual therapy", r"ultrasound therapy")  # fmt: skip

STOP = frozenset(
    """a an the and or of for to in on at by with without from as is are was were be been being it its this that these those patient pt pts today
    stable uncontrolled controlled control well poorly not acute chronic mild moderate severe improving improved improvement worsening resolving
    resolved recurrent persistent new onset unspecified uncomplicated essential primary secondary due likely viral bacterial goal symptoms symptom
    follow up followup visit visits status post history also still now more less some any other otherwise otherwise per see seen noted note per
    left right bilateral both side sided lower upper stage type benign probable possible possibly question questionable rule ruled out versus
    exacerbation flare flares episode episodes problem problems issue issues condition diagnosis diagnoses assessment impression plan overall
    given has have had having his her their he she they who which while during after before about around roughly approximately mostly mainly
    currently today's again just very slightly slight little bit better worse same unchanged baseline normal abnormal routine annual exam
    check checks checkup medication medications meds regimen therapy treatment management manage managed refill refills review reviewed
    labs lab results result discussed discuss reviewed counseling counselled counseled education educated""".split()
)
PLAN_START = frozenset(
    """start started starting continue continued cont increase increased decrease decreased order ordered send sent refer referred recheck
    re-check return rtc follow fu f/u prescribe prescribed rx advise advised counsel counseled counselled discuss discussed will plan schedule
    scheduled rest fluids hydration avoid ice heat stretching stretch obtain repeat refill refilled titrate stop hold restart begin began treat
    treated give given administer administered perform performed check monitor recommend recommended encourage encouraged resume add added switch
    change changed taper lifestyle diet exercise antibiotics antibiotic nsaid nsaids tylenol ibuprofen pt on taking managed under sx""".split()
)

# ---------------------------------------------------------------------------------------------------- regexes
NEG_PRE = re.compile(
    r"\b(?:no(?!\s+(?:significant\s+|further\s+|real\s+|much\s+)?(?:improvement|relief|change|better|response|benefit|resolution|worsening|longer))|"
    r"denies|denied|denying|without|negative\s+for|neg\s+for|free\s+of|absence\s+of|absent|never\s+had|never|ruled\s+out|nor|"
    r"no\s+evidence\s+of|no\s+signs?\s+of|no\s+history\s+of|does\s+not\s+have|doesn'?t\s+have|did\s+not\s+have|didn'?t\s+have|"
    r"not\s+having|not\s+experiencing|not\s+complaining\s+of|no\s+longer(?:\s+has|\s+have)?|(?:is|was|are|isn'?t|wasn'?t)\s+not\s+(?:a\s+|an\s+|the\s+)?)\b", re.I)
NEG_POST = re.compile(r"^[\s,(:\-]*(?:(?:was|is|has\s+been|were|came\s+back|came\s+out|test(?:ed)?)\s+)*(?:ruled\s+out|negative|excluded|not\s+present|absent|resolved|not\s+found|not\s+seen|not\s+detected|r/o'?d)\b", re.I)
UNC_PRE = re.compile(
    r"\b(?:rule\s+out|r/o|ruling\s+out|possible|possibly|probable|probably|likely|suspect(?:ed)?|suspicious\s+for|suspicion\s+of|questionable|query|"
    r"concern(?:ed)?\s+(?:for|about|of)|may\s+(?:be|have)|might\s+(?:be|have)|could\s+be|differential(?:\s+diagnosis)?(?:\s+includes?)?|versus|vs\.?|"
    r"cannot\s+exclude|can'?t\s+exclude|consider(?:ing)?|evaluate\s+for|to\s+exclude|assess\s+for|check\s+for|working\s+diagnosis|"
    r"vs|appears\s+to\s+be|seems\s+to\s+be|r\s*/\s*o)\b|\?", re.I)
UNC_POST = re.compile(r"^\s*\?|^[\s,(]*(?:\?|questionable|probable|possible|not\s+excluded)", re.I)
HIST_PRE = re.compile(r"\b(?:history\s+of|hx\s+of|h/o|hx|past\s+medical\s+history|pmh|prior|previous(?:ly)?|remote|status\s+post|s/p|resolved|former|old)\b", re.I)
FAMILY_PRE = re.compile(r"\b(?:family\s+history|fhx|fh|mother|father|sister|brother|grandmother|grandfather|aunt|uncle|runs\s+in)\b", re.I)
CONTRAST = re.compile(r"\b(?:but|however|although|though|except|whereas|yet)\b", re.I)
SPEAKER = re.compile(r"\b(?:provider|patient|doctor|physician|clinician|nurse|dr|pt|md|therapist)\s*:", re.I)
CONN = re.compile(r"[,/]|\b(?:and|or|nor)\b", re.I)

HPI_PATTERNS = {
    "onset": r"\b(started|began|onset|since)\b",
    "duration": r"\bfor (about |over |almost |around |the past |the last )?(\w+ )?(hours?|days?|weeks?|months?|wks?|mos?)\b|\bover (a|the past|the last) (\w+ )?(week|month|day)|\bx\s?\d+\s*(d|days?|wks?|weeks?|mos?|months?|hrs?|hours?)\b|\b\d+\s*(days?|weeks?|wks?|months?|years?)\s+(ago|of)\b",
    "severity": r"\b\d+ out of (10|ten)\b|\b\d{1,2}\s*/\s*10\b|\b(mild|moderate|severe)\b",
    "location": r"\b(left|right|lower|upper) (side|back|knee|chest|abdomen)\b|\b(in|on) my (\w+ )?(throat|back|chest|abdomen|side)\b",
    "associated": r"\b(also|along with|with some|plus|accompanied by)\b[^.]{0,40}\b(fever|nausea|cough|fatigue|dizz\w+|headache|chills|vomiting|diarrhea|rash|swelling|sweats|weakness|numbness|thirst|polyuria|frequency|urgency)\b",
    "modifying": r"\b(worse when|better with|worse at|relieved by|gets worse|improves with|worse with|aggravated by|alleviated by|worse on|helped by)\b",
}
SYSTEM_PATTERNS = {
    "throat": r"throat|pharynx|oropharynx|tonsil\w*|pharyngeal", "neck": r"neck|cervical|thyroid|lymph nodes?",
    "lungs": r"lungs?|ctab|clear to auscultation|breath sounds|respiratory|wheez\w*|rales|crackles",
    "heart": r"heart|cardiac|cardiovascular|rrr|murmur|regular rate and rhythm", "abdomen": r"abdomen|abdominal|abd|bowel sounds|suprapubic",
    "skin": r"skin|rash|dermat\w*|ulcers?", "back": r"back|spine|spinal|lumbar|paraspinal",
    "extremities": r"extremit\w+|feet|foot|edema|knees?|joints?|ankles?|hands?|legs?|musculoskeletal|msk|gait",
    "eyes": r"eyes?|pupils?|conjunctiv\w+|fundus", "ears": r"ears?|tympanic|tms?|ear canals?",
}  # fmt: skip
EXAM_CUE = re.compile(r"\b(?:on exam|exam(?:ination)? (?:shows?|reveals?|is|was|notable|today)|auscultat\w+|palpat\w+|vitals?|bp \d|temp(?:erature)? \d|pulse)\b", re.I)
NEW_RE = re.compile(r"first (time|visit)|new patient|new pt\b|never been seen|not been here before|first appointment|establish(?:ing)? care|new to (?:our |the )?(?:clinic|practice)", re.I)
NOT_NEW_RE = re.compile(r"\b(?:not|isn'?t|no longer)\s+(?:a\s+)?new\s+(?:patient|pt)\b", re.I)
EST_RE = re.compile(r"last (here|seen|visit|saw)|returning (?:pt|patient)|established (?:pt|patient)|\best\.? (?:pt|patient)\b|(?:been|seen) (?:here|with us|by us) before|welcome back|was seen here|seen here (?:in|last)|return(?:ing)? visit", re.I)
SIG_RE = re.compile(r"(?:signed\s+electronically|electronically\s+signed|e-?signed|digitally\s+signed|signed\s+(?:by|off)|signature\s*:)[^\n]*", re.I)
UNSIGNED_RE = re.compile(r"\b(?:unsigned|not\s+(?:yet\s+)?signed|pending\s+(?:signature|sign-?off)|awaiting\s+(?:signature|sign-?off))\b", re.I)
PLAN_CUE = re.compile(r"\bplan\s*:|\b(prescrib\w*|follow[- ]?up|return|rtc|refer\w*|recommend\w*|start(?:ed)?|continue|cont|increase|decrease|order(?:ed)?|schedul\w+|advis\w+|counsel\w*|instruct\w*|recheck|re-check|will)\b", re.I)
ASSESS_CUE = re.compile(r"\b(?:diagnos(?:is|ed)|impression|assessed|consistent with|suffering from|likely has|appears to have|found to have|i think|this is (?:a|an)|suspect|(?:is|are|remains?)\s+(?:well |poorly |not |un)?(?:controlled|stable|improving|worsening|resolving|resolved|at goal))\b", re.I)

PARTS = r"knees?|shoulders?|hips?|ankles?|feet|foot|hands?|wrists?|elbows?|arms?|legs?|ears?|eyes?|side|sided|flank|calf|calves|thighs?|heels?|fingers?|toes?|thumbs?|extremit(?:y|ies)|breasts?|quadrant|lungs?|kidneys?|jaw|temple|neck|chest|back|lower|upper"
LAT_A = re.compile(rf"\b(left|right|bilateral(?:ly)?|both|lt|rt)\b[\s,\-]*(?:(?:sided|lower|upper|mid|distal|proximal|anterior|posterior|medial|lateral)\s+)*(?:{PARTS})\b", re.I)
LAT_B = re.compile(rf"\b(?:{PARTS})\b(?:\s+(?:pain|swelling|injury|sprain))?\s*[(,:\-]?\s*(left|right|bilateral|lt|rt)\b", re.I)
LAT_A1 = re.compile(rf"(?<![A-Za-z])([LR])(?![A-Za-z])\.?[\s\-]+(?:{PARTS})\b")  # "R knee" (capital letter only)
LAT_B1 = re.compile(rf"\b(?:{PARTS})\b(?:\s+(?:pain|swelling|injury|sprain))?\s*[(,:\-]?\s*([LR])(?![A-Za-z])")
LAT_C = re.compile(r"\b(?:on|to|in) the (left|right)\b|\b(bilateral(?:ly)?)\b|\b(lt|rt)\b", re.I)
MINUTES = re.compile(r"(\d{1,3})\s*[- ]?\s*(?:minutes?|mins?\b|min\.)|\b(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b|\b(an|one)\s+hour\b|\bhalf\s+an?\s+hour\b", re.I)

NEG_SERVICE = re.compile(r"\b(?:declin\w+|refus\w+|defer\w*|cancel+ed|postpone\w*|not\s+(?:needed|indicated|necessary|done|performed|ordered|required|today)|unnecessary|no\s+(?:need|indication)|without|no\b|not\b|never|didn'?t|did\s+not|won'?t|wasn'?t)\b", re.I)
STRONG_NEG_SERVICE = re.compile(r"\b(?:declin\w+|refus\w+|defer\w*|cancel+ed|postpone\w*|not\s+(?:needed|indicated|necessary|done|performed|ordered|required)|unnecessary|no\s+(?:need|indication)\s+(?:for|of))\b", re.I)
COND_SERVICE = re.compile(r"\b(?:if|should|in\s+case|would\s+consider|may\s+need|might\s+need|consider(?:ing)?|unless|when\s+needed|as\s+needed|prn|pending\s+results?)\b", re.I)
PAST_SERVICE = re.compile(r"\b(?:last\s+(?:year|month|week|visit|time)|previous(?:ly)?|prior|history\s+of|in\s+the\s+past|\d+\s+(?:days?|weeks?|months?|years?)\s+ago|years?\s+ago|before)\b", re.I)
OFFER_SERVICE = re.compile(r"\b(?:offered|discussed|discussing|counsel(?:l)?ed\s+(?:on|about)|talked\s+about|mention(?:ed)?)\b", re.I)
ACCEPT_SERVICE = re.compile(r"\b(?:accept\w*|agreed|consented|given|performed|administered|done|completed|tolerated|elected)\b", re.I)
ORDERED_SERVICE = re.compile(r"\b(?:order(?:ed|ing|s)?|send|sent|refer(?:red)?|schedule[d]?|will\s+(?:get|obtain|do)|to\s+(?:get|obtain)|recommend\w*|requested|pending)\b", re.I)
PERFORMED_SERVICE = re.compile(r"\b(?:done|performed|given|administered|obtained\s+today|injected|today|in\s+office|placed|completed|did|tolerated|reviewed)\b", re.I)


# ---------------------------------------------------------------------------------------------------- results
@dataclass
class ConditionHit:
    icd10: str
    name: str
    evidence: str  # the clause the mention was found in
    keyword: str = ""  # the catalog keyword or synonym that matched
    via: str = "keyword"  # keyword | synonym | spelling | ai
    status: str = "active"  # active | negated | uncertain | historical | family
    laterality: str = ""  # left | right | bilateral | ""
    unspecified: bool = False
    needs_laterality: bool = False
    chronic: bool = False
    source: str = "rules"  # rules | ai
    note: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class ServiceHit:
    cpt: str
    name: str
    family: str
    evidence: str
    status: str = "performed"  # performed | ordered
    minutes: int | None = None
    units: int = 1
    laterality: str = ""
    needs_laterality: bool = False
    needs_time: bool = False
    source: str = "rules"
    keyword: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class Reading:
    text: str = ""
    layout: str = "unknown"  # sections | dialogue | bullets | narrative
    status: str = "unknown"  # new | established | unknown
    status_evidence: str = ""
    hpi: dict[str, str] = field(default_factory=dict)  # component -> the words that show it
    systems: list[str] = field(default_factory=list)
    conditions: list[ConditionHit] = field(default_factory=list)  # every mention in the assessment, with its status
    services: list[ServiceHit] = field(default_factory=list)
    laterality: str = ""
    assessment_present: bool = False
    plan_present: bool = False
    signature_present: bool = False
    signed: bool = False  # the caller's flag AND a signature in the text
    uncertainties: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # things seen and deliberately not coded (history, declined services ...)
    candidates: list[str] = field(default_factory=list)  # conditions mentioned outside any assessment: shown to a coder, never coded
    ai: dict = field(default_factory=dict)  # filled by krisnai.live.ai_reader when the AI layer ran

    @property
    def diagnoses(self) -> list[ConditionHit]:
        return [c for c in self.conditions if c.status == "active"]

    @property
    def elements(self) -> set[str]:
        els: set[str] = set()
        if self.assessment_present:
            els.add("assessment")
        if self.plan_present:
            els.add("plan")
        if len(self.hpi) >= 3:
            els.add("history_detailed")
        if len(self.systems) >= 2:
            els.add("exam_expanded")
        return els

    def uncertain(self, msg: str) -> None:
        if msg not in self.uncertainties:
            self.uncertainties.append(msg)

    def note(self, msg: str) -> None:
        if msg not in self.notes:
            self.notes.append(msg)

    def to_dict(self) -> dict:
        return {
            "layout": self.layout, "status": self.status, "status_evidence": self.status_evidence, "hpi": dict(self.hpi),
            "systems": list(self.systems), "conditions": [c.to_dict() for c in self.conditions],
            "services": [s.to_dict() for s in self.services], "laterality": self.laterality,
            "assessment_present": self.assessment_present, "plan_present": self.plan_present, "signature_present": self.signature_present,
            "signed": self.signed, "uncertainties": list(self.uncertainties), "notes": list(self.notes), "candidates": list(self.candidates),
            "ai": dict(self.ai),
        }  # fmt: skip


# ---------------------------------------------------------------------------------------------------- text helpers
def _osa(a: str, b: str) -> int:
    """Edit distance counting a swap of two neighbours as one edit."""
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


@lru_cache(maxsize=4096)
def _kw_regex(kw: str) -> re.Pattern:
    toks = [t for t in re.split(r"[\s\-]+", kw.strip().lower()) if t]
    pieces = []
    for i, t in enumerate(toks):
        e = re.escape(t)
        if i == len(toks) - 1:
            e = (e[:-1] + "(?:y|ies)") if t.endswith("y") and len(t) > 3 else e + "(?:s|es)?"
        pieces.append(e)
    pat = r"[\s\-]+".join(pieces)
    pat = pat.replace(r"x[\s\-]+ray", r"x[\s\-]?ray")
    return re.compile(rf"(?<![A-Za-z0-9]){pat}(?![A-Za-z0-9])", re.I)


def _compact(s: str, limit: int = 140) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= limit else s[: limit - 3] + "..."


class _Doc:
    """The masked text plus clause boundaries, so every mention can be looked at in its own clause."""

    def __init__(self, text: str):
        self.text = text
        self.bounds = sorted({0, len(text)} | {m.end() for m in re.finditer(r"\.(?=\s|$)|[;\n!?]|:\s", text)})

    def clause(self, pos: int) -> tuple[int, int]:
        i = bisect_right(self.bounds, pos) - 1
        i = max(0, min(i, len(self.bounds) - 2))
        return self.bounds[i], self.bounds[i + 1]


def _prepare(raw: str) -> str:
    t = unicodedata.normalize("NFKC", raw or "").replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ").replace("\u00a0", " ")
    return t


# ---------------------------------------------------------------------------------------------------- sections
_KIND = {
    "subjective": "subjective", "hpi": "subjective", "history of present illness": "subjective", "chief complaint": "subjective", "cc": "subjective", "s": "subjective",
    "objective": "objective", "physical examination": "objective", "physical exam": "objective", "examination": "objective", "exam": "objective", "vital": "objective",
    "vitals": "objective", "o": "objective",
    "assessment": "assessment", "assesment": "assessment", "impression": "assessment", "diagnosis": "assessment", "diagnoses": "assessment", "dx": "assessment", "a": "assessment",
    "plan": "plan", "p": "plan",
}  # fmt: skip
_COLON = re.compile(r"(?<![\w/])(subjective|objective|hpi|history of present illness|chief complaint|cc|physical examination|physical exam|examination|exam|vitals?|"
                    r"assessment\s*(?:and|&|/|\+)\s*plan|assessment|assesment|impression|diagnos[ie]s|dx|a\s*/\s*p|plan)\s*(?::|[-–—](?=\s))", re.I)
_BARE = re.compile(r"(?:^|\n|[.!?]\s+|\b\w{2,12}:\s+)(?:my |the |our )?(assessment|impression|diagnosis|plan|physical exam|exam|history of present illness|chief complaint|subjective|objective|hpi)\b(?=\s|$|[.,])", re.I)
_LETTER = re.compile(r"(?m)^[ \t]*(?:[-*\u2022][ \t]*)?([SOAP])[ \t]*[:\)]")
_LETTER_MID = re.compile(r"(?<=[.!?])[ \t]+([SOAP]):(?=\s)")  # "... est pt. A: lbp. P: cont." (capital letters only)


def _header_kind(word: str) -> str:
    w = re.sub(r"\s+", " ", word.lower().strip())
    if re.fullmatch(r"assessment ?(and|&|/|\+) ?plan|a ?/ ?p", w):
        return "ap"
    return _KIND.get(w, _KIND.get(w.rstrip("s"), ""))


def _sections(text: str) -> tuple[list[tuple[str, int, int]], int]:
    """(kind, start, end) of each section, and the position where the first header starts."""
    hdrs: list[tuple[int, int, str]] = []
    for m in _COLON.finditer(text):
        hdrs.append((m.start(1), m.end(), _header_kind(m.group(1))))
    for m in _LETTER.finditer(text):
        hdrs.append((m.start(1), m.end(), _header_kind(m.group(1))))
    for m in _LETTER_MID.finditer(text):
        hdrs.append((m.start(1), m.end(), _header_kind(m.group(1))))
    for m in _BARE.finditer(text):
        # a bare word counts only when no colon-header already sits on it
        if not any(s <= m.start(1) < e for s, e, _ in hdrs):
            hdrs.append((m.start(1), m.end(1), _header_kind(m.group(1))))
    hdrs = [h for h in hdrs if h[2]]
    hdrs.sort()
    clean: list[tuple[int, int, str]] = []
    for h in hdrs:  # drop headers that sit inside the previous header
        if clean and h[0] < clean[-1][1]:
            continue
        clean.append(h)
    out = []
    for i, (_s, e, kind) in enumerate(clean):
        nxt = clean[i + 1][0] if i + 1 < len(clean) else len(text)
        out.append((kind, e, nxt))
    return out, (clean[0][0] if clean else len(text))


# ---------------------------------------------------------------------------------------------------- laterality
def lateral_of(s: str) -> tuple[str, bool]:
    """('left'|'right'|'bilateral'|'', conflict). 'conflict' means both a left and a right were named without 'and'/'both'."""
    sides: list[str] = []
    for m in LAT_A.finditer(s):
        sides.append(m.group(1).lower())
    for m in LAT_B.finditer(s):
        sides.append(m.group(1).lower())
    for m in LAT_A1.finditer(s):
        sides.append("left" if m.group(1) == "L" else "right")
    for m in LAT_B1.finditer(s):
        sides.append("left" if m.group(1) == "L" else "right")
    for m in LAT_C.finditer(s):
        sides.append(next(g for g in m.groups() if g).lower())
    norm = {"lt": "left", "rt": "right", "both": "bilateral", "bilaterally": "bilateral"}
    sides = [norm.get(x, x) for x in sides]
    if not sides:
        return "", False
    uniq = set(sides)
    if "bilateral" in uniq:
        return "bilateral", False
    if uniq == {"left", "right"}:
        if re.search(r"\b(left|right|lt|rt)\b\s*(?:and|&|/|,|or)\s*(left|right|lt|rt)\b", s, re.I):
            return "bilateral", False
        return "", True
    return uniq.pop(), False


# ---------------------------------------------------------------------------------------------------- conditions
def _kw_hit(s: catalog.Service, text: str) -> bool:
    return any(_kw_regex(k).search(text) for k in s.keywords)


def _conds_for_phrase(phrase: str) -> list[catalog.Condition]:
    exact = [c for c in catalog.CONDITIONS if phrase in c.keywords]
    if exact:
        return exact
    rx = _kw_regex(phrase)
    return [c for c in catalog.CONDITIONS if rx.search(c.name)]


def _services_for_phrase(phrase: str) -> list[catalog.Service]:
    exact = [s for s in catalog.SERVICES if phrase in s.keywords and not s.family.startswith("em")]
    if exact:
        return exact
    rx = _kw_regex(phrase)
    return [s for s in catalog.SERVICES if not s.family.startswith("em") and rx.search(s.name)]


@dataclass
class _Match:
    start: int
    end: int
    obj: object
    kw: str
    via: str


def _condition_entries() -> list[tuple[re.Pattern, catalog.Condition, str, str]]:
    entries = []
    for c in catalog.CONDITIONS:
        for kw in c.keywords:
            entries.append((_kw_regex(kw), c, kw, "keyword"))
    for alias, canon in SYNONYMS.items():
        for c in _conds_for_phrase(canon):
            entries.append((_kw_regex(alias), c, alias, "synonym"))
    return entries


def _service_entries() -> list[tuple[re.Pattern, catalog.Service, str, str]]:
    entries = []
    for s in catalog.SERVICES:
        if s.family.startswith("em"):
            continue
        for kw in s.keywords:
            entries.append((_kw_regex(kw), s, kw, "keyword"))
            m = re.match(r"^(.*?)\s*(?:x[\s-]?rays?|radiographs?)$", kw)
            if m and m.group(1):  # "knee x-ray" is also written "x-ray of the left knee"
                body = re.escape(m.group(1).strip())
                entries.append((re.compile(rf"x[\s\-]?rays?\s+(?:of|for)\s+(?:the\s+)?(?:(?:left|right)\s+)?{body}s?\b", re.I), s, kw, "keyword"))
    for alias, canon in SERVICE_SYNONYMS.items():
        for s in _services_for_phrase(canon):
            entries.append((_kw_regex(alias), s, alias, "synonym"))
    return entries


def _resolve(matches: list[_Match]) -> tuple[list[_Match], list[tuple[_Match, _Match]]]:
    """Longest phrase wins. Two different catalog entries on the very same words are reported as ambiguous, not chosen."""
    matches = sorted(matches, key=lambda m: (-(m.end - m.start), m.via != "keyword", m.start))
    acc: list[_Match] = []
    ambiguous: list[tuple[_Match, _Match]] = []
    for m in matches:
        over = [a for a in acc if a.start < m.end and m.start < a.end]
        if not over:
            acc.append(m)
        elif all(a.obj is m.obj or getattr(a.obj, "icd10", getattr(a.obj, "cpt", None)) == getattr(m.obj, "icd10", getattr(m.obj, "cpt", None)) for a in over):
            continue
        elif any((a.start, a.end) == (m.start, m.end) for a in over):
            other = next(a for a in over if (a.start, a.end) == (m.start, m.end))
            ambiguous.append((other, m))
    return sorted(acc, key=lambda m: m.start), ambiguous


def _scan(text: str, entries) -> list[_Match]:
    out = []
    for rx, obj, kw, via in entries:
        for m in rx.finditer(text):
            out.append(_Match(m.start(), m.end(), obj, kw, via))
    return out


def _fuzzy(text: str, taken: list[_Match]) -> list[_Match]:
    """A one-letter slip in a long catalog word ('pharyngits'). Reported as uncertain by the caller, never trusted silently."""
    vocab: dict[str, set[str]] = {}
    for c in catalog.CONDITIONS:
        for kw in c.keywords:
            if " " not in kw and "-" not in kw and len(kw) >= 6:
                vocab.setdefault(kw, set()).add(c.icd10)
    for alias, canon in SYNONYMS.items():
        if " " not in alias and "-" not in alias and len(alias) >= 7:
            for c in _conds_for_phrase(canon):
                vocab.setdefault(alias, set()).add(c.icd10)
    out = []
    for m in re.finditer(r"[A-Za-z][A-Za-z]{5,}", text):
        if any(t.start < m.end() and m.start() < t.end for t in taken):
            continue
        w = m.group(0).lower()
        best = None
        for kw, icds in vocab.items():
            if abs(len(kw) - len(w)) > 1 or w[0] != kw[0] or w == kw:
                continue
            d = _osa(w, kw)
            if d == 1 or (d == 2 and len(kw) >= 11 and 1 - d / max(len(w), len(kw)) >= 0.9):
                if best is None or d < best[0]:
                    best = (d, kw, icds)
        if best:
            conds = [catalog.condition_by_icd(i) for i in sorted(best[2])]
            conds = [c for c in conds if c]
            if len(conds) == 1:
                out.append(_Match(m.start(), m.end(), conds[0], best[1], "spelling"))
    return out


def _status_of(doc: _Doc, m: _Match) -> tuple[str, bool, str]:
    """(status, negation-came-through-a-list, the cue). Looks only inside the mention's own clause."""
    cs, ce = doc.clause(m.start)
    prefix = doc.text[cs : m.start]
    cut = list(CONTRAST.finditer(prefix))
    if cut:
        prefix = prefix[cut[-1].end() :]
    suffix = doc.text[m.end : min(ce, m.end + 60)]
    negs = list(NEG_PRE.finditer(prefix))
    if negs:
        between = prefix[negs[-1].end() :]
        return "negated", bool(CONN.search(between)), negs[-1].group(0)
    if NEG_POST.search(suffix):
        return "negated", False, "after the term"
    if FAMILY_PRE.search(prefix):
        return "family", False, "family history"
    unc = UNC_PRE.search(prefix) or UNC_POST.search(suffix)
    if unc:
        return "uncertain", False, unc.group(0)
    if HIST_PRE.search(prefix):
        return "historical", False, "history"
    return "active", False, ""


def _items(doc: _Doc, s: int, e: int) -> list[tuple[int, int]]:
    """Split an assessment span into its items: lines, numbered or bulleted entries, commas, 'and', dashes."""
    text = doc.text
    out = []
    pos = s
    for m in re.finditer(r"[\n;,]|\s+-\s+|\s+[–—]\s+|\.(?=\s|$)|\b(?:and|plus|with)\b|\s*&\s*|\d+\s*[.)]\s+", text[s:e], re.I):
        out.append((pos, s + m.start()))
        pos = s + m.end()
    out.append((pos, e))
    return [(a, b) for a, b in out if text[a:b].strip()]


def _words(s: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z']+", s)


# ---------------------------------------------------------------------------------------------------- the reader
def read(text: str, signed: bool = True) -> Reading:
    """Read one visit note. `signed` is the record's own flag; the note must also carry a signature line to count as signed."""
    rd = Reading()
    t = _prepare(text)
    rd.text = t
    sig_present = bool(SIG_RE.search(t)) and not UNSIGNED_RE.search(t)
    masked = SIG_RE.sub(lambda m: " " * len(m.group(0)), t)
    rd.signature_present = sig_present
    rd.signed = bool(signed) and sig_present
    if not masked.strip():
        rd.uncertain("the transcript is empty")
        return rd
    doc = _Doc(masked)

    secs, first_hdr = _sections(masked)
    spans: dict[str, list[tuple[int, int]]] = {}
    for kind, s, e in secs:
        spans.setdefault(kind, []).append((s, e))
    lines = [ln for ln in masked.split("\n") if ln.strip()]
    if re.search(r"(?mi)^\s*(?:provider|doctor|dr\.?|physician|patient|pt|clinician|md|nurse)\s*:", masked):
        rd.layout = "dialogue"
    elif lines and sum(1 for ln in lines if re.match(r"\s*(?:[-*\u2022]|\d+[.)])\s+", ln)) >= max(2, len(lines) // 2):
        rd.layout = "bullets"
    elif secs:
        rd.layout = "sections"
    else:
        rd.layout = "narrative"

    # ---- status
    new_m, est_m, notnew = NEW_RE.search(masked), EST_RE.search(masked), NOT_NEW_RE.search(masked)
    if notnew:
        new_m, est_m = None, est_m or notnew
    if new_m and est_m:
        rd.status = "unknown"
        rd.uncertain(f"the note says both new ('{_compact(new_m.group(0))}') and established ('{_compact(est_m.group(0))}')")
    elif new_m:
        rd.status, rd.status_evidence = "new", _compact(new_m.group(0))
    elif est_m:
        rd.status, rd.status_evidence = "established", _compact(est_m.group(0))

    # ---- history of present illness
    hpi_parts = [masked[:first_hdr]] + [masked[s:e] for k in ("subjective",) for s, e in spans.get(k, [])]
    hpi_text = "\n".join(hpi_parts)
    wb = list(re.finditer(r"what brings you in", hpi_text, re.I))
    if wb:
        hpi_text = hpi_text[wb[-1].end() :]
    for comp, pat in HPI_PATTERNS.items():
        m = re.search(pat, hpi_text, re.I)
        if m:
            rd.hpi[comp] = _compact(m.group(0), 60)

    # ---- exam
    exam_parts = [masked[s:e] for k in ("objective",) for s, e in spans.get(k, [])]
    if not exam_parts:
        exam_parts = [masked[a:b] for a, b in zip(doc.bounds, doc.bounds[1:], strict=False) if EXAM_CUE.search(masked[a:b])]
    exam_text = "\n".join(exam_parts)
    rd.systems = [name for name, pat in SYSTEM_PATTERNS.items() if re.search(rf"\b(?:{pat})\b", exam_text, re.I)]

    # ---- the assessment region
    ass_spans = list(spans.get("assessment", [])) + list(spans.get("ap", []))
    ass_spans = [(s, e) for s, e in ass_spans if masked[s:e].strip()]
    from_cue = False
    if not ass_spans:
        cues = [(a, b) for a, b in zip(doc.bounds, doc.bounds[1:], strict=False) if ASSESS_CUE.search(masked[a:b]) and masked[a:b].strip()]
        if cues:
            ass_spans, from_cue = cues, True
    rd.assessment_present = bool(ass_spans) and bool(_words(SPEAKER.sub(" ", " ".join(masked[s:e] for s, e in ass_spans))))

    # ---- plan
    plan_spans = [(s, e) for s, e in spans.get("plan", []) if masked[s:e].strip()]
    if plan_spans:
        rd.plan_present = bool(_words(SPEAKER.sub(" ", " ".join(masked[s:e] for s, e in plan_spans))))
    elif "ap" in spans:
        rd.plan_present = any(PLAN_CUE.search(masked[s:e]) for s, e in spans["ap"])
    else:
        first_ass = min((s for k in ("assessment",) for s, _ in spans.get(k, [])), default=None)
        if first_ass is None and from_cue:
            first_ass = min(s for s, _ in ass_spans)
        rd.plan_present = bool(PLAN_CUE.search(masked[first_ass:] if first_ass is not None else masked))

    # ---- conditions (assessment only)
    centries = _condition_entries()
    taken_all: list[tuple[int, int]] = []
    sentinel_names: set[str] = set()
    for s, e in ass_spans:
        sub = masked[s:e]
        raw = _scan(sub, centries)
        for m in raw:
            m.start, m.end = m.start + s, m.end + s
        acc, amb = _resolve(raw)
        fz = _fuzzy(masked[s:e], [_Match(a.start - s, a.end - s, a.obj, a.kw, a.via) for a in acc])
        for m in fz:
            m.start, m.end = m.start + s, m.end + s
        acc = sorted(acc + fz, key=lambda m: m.start)
        for a, b in amb:
            rd.uncertain(f"'{_compact(masked[a.start:a.end])}' fits more than one catalog condition ({a.obj.icd10} and {b.obj.icd10})")  # type: ignore[attr-defined]
        for m in acc:
            c = m.obj
            status, listy, cue = _status_of(doc, m)
            cs, ce = doc.clause(m.start)
            ev = _compact(masked[cs:ce])
            hit = ConditionHit(c.icd10, c.name, ev, m.kw, m.via, status, "", c.unspecified, c.needs_laterality, c.chronic)  # type: ignore[attr-defined]
            if status == "negated" and listy:
                rd.uncertain(f"'{_compact(masked[m.start:m.end])}' sits in a list after '{cue}': is it denied? ({ev})")
            if status == "uncertain":
                rd.uncertain(f"'{_compact(masked[m.start:m.end])}' is worded as uncertain ('{_compact(cue)}'), so it was not coded ({ev})")
            elif status == "historical":
                rd.uncertain(f"'{_compact(masked[m.start:m.end])}' is worded as history; is it current? ({ev})")
            elif status == "family":
                rd.note(f"family history, not coded: {ev}")
            elif status == "negated":
                rd.note(f"denied, not coded: {ev}")
            if m.via == "spelling":
                rd.uncertain(f"'{_compact(masked[m.start:m.end])}' was read as '{m.kw}' by spelling")
            lat, conflict = lateral_of(masked[cs:ce])
            hit.laterality = lat
            if conflict:
                rd.uncertain(f"left and right are both named for '{_compact(masked[m.start:m.end])}' ({ev})")
            rd.conditions.append(hit)
            taken_all.append((m.start, m.end))
            sentinel_names.add(c.icd10)
        # items of the assessment that explain nothing
        svc_spans = [(m.start + s, m.end + s) for m in _scan(sub, _service_entries())]
        for a, b in _items(doc, s, e):
            item = SPEAKER.sub(" ", masked[a:b])
            if any(x < b and a < y for x, y in taken_all + svc_spans):
                continue
            first = (_words(item) or [""])[0].lower()
            if first in PLAN_START and first not in ("on",):
                continue
            if NEG_PRE.search(masked[doc.clause(a)[0] : b]) or (re.match(r"\s*(?:on|taking|managed|treated)\b", item, re.I)):
                continue
            left = [w for w in _words(item) if len(w) >= 2 and w.lower() not in STOP and not NEG_PRE.fullmatch(w) and not UNC_PRE.fullmatch(w)]
            left = [w for w in left if not re.fullmatch(r"(?:r|o|a|p|s|n|e|d|i|ii|iii|iv|bp|f|u|rtc|wk|wks|mo|mos|mg|bid|tid|prn|rx|dx|hx|sx|tx|lt|rt)", w.lower())]
            if left:
                amb_abbr = [AMBIGUOUS[w.lower()] for w in left if w.lower() in AMBIGUOUS]
                if amb_abbr:
                    rd.uncertain(f"the abbreviation '{left[0]}' in the assessment is ambiguous ({amb_abbr[0]})")
                else:
                    rd.uncertain(f"not recognised in the assessment: '{_compact(item, 80)}'")
    # the same condition both asserted and denied
    by_icd: dict[str, set[str]] = {}
    for h in rd.conditions:
        by_icd.setdefault(h.icd10, set()).add(h.status)
    for icd, sts in by_icd.items():
        if "active" in sts and "negated" in sts:
            rd.uncertain(f"{icd} is both stated and denied in the assessment")
    # keep one active hit per code, first mention wins; laterality merged
    seen: dict[str, ConditionHit] = {}
    deduped = []
    for h in rd.conditions:
        key = f"{h.icd10}:{h.status}"
        if key in seen:
            if not seen[key].laterality and h.laterality:
                seen[key].laterality = h.laterality
            continue
        seen[key] = h
        deduped.append(h)
    rd.conditions = deduped

    # ---- no assessment: show a coder what was mentioned, code nothing
    if not ass_spans:
        names = []
        for m in _resolve(_scan(masked, centries))[0]:
            st, _, _ = _status_of(doc, m)
            if st == "active" and m.obj.name not in names:  # type: ignore[attr-defined]
                names.append(m.obj.name)  # type: ignore[attr-defined]
        rd.candidates = names
        if names:
            rd.uncertain("no assessment or diagnosis statement was found; conditions mentioned elsewhere: " + "; ".join(names))

    # ---- condition laterality from other mentions of the same condition
    for h in rd.conditions:
        if h.laterality or not h.needs_laterality:
            continue
        sides = set()
        for m in _resolve(_scan(masked, centries))[0]:
            if getattr(m.obj, "icd10", "") == h.icd10 and m.via != "spelling":
                cs, ce = doc.clause(m.start)
                lat, _ = lateral_of(masked[cs:ce])
                if lat:
                    sides.add(lat)
        if len(sides) == 1:
            h.laterality = sides.pop()
        elif len(sides) > 1:
            rd.uncertain(f"conflicting sides are given for {h.name}")
    if any(h.needs_laterality for h in rd.diagnoses) or any(s.needs_laterality for s in catalog.SERVICES if _kw_hit(s, masked)):
        doc_sides = set()
        for a, b in zip(doc.bounds, doc.bounds[1:], strict=False):
            lat, clash = lateral_of(masked[a:b])
            if clash:
                doc_sides |= {"left", "right"}
            elif lat in ("left", "right"):
                doc_sides.add(lat)
        if doc_sides == {"left", "right"}:
            rd.uncertain("both left and right are mentioned in the note and a side is needed: which side is meant?")
    act_lat = {h.laterality for h in rd.diagnoses if h.laterality}
    if len(act_lat) == 1:
        rd.laterality = next(iter(act_lat))

    _read_services(rd, doc, masked)
    return rd


# ---------------------------------------------------------------------------------------------------- services
def _minutes_near(masked: str, pos: int, end: int) -> list[int]:
    """Minutes stated in the same line within 90 characters of the service words, nearest first."""
    ls = masked.rfind("\n", 0, pos) + 1
    le = masked.find("\n", end)
    le = len(masked) if le < 0 else le
    lo, hi = max(ls, pos - 90), min(le, end + 90)
    found = []
    for m in MINUTES.finditer(masked, lo, hi):
        if m.group(1):
            v = int(m.group(1))
        elif m.group(2):
            v = round(float(m.group(2)) * 60)
        elif m.group(3):
            v = 60
        else:
            v = 30
        found.append((min(abs(m.start() - end), abs(m.end() - pos)), v))
    return [v for _, v in sorted(found)]


def _read_services(rd: Reading, doc: _Doc, masked: str) -> None:
    entries = _service_entries()
    acc, amb = _resolve(_scan(masked, entries))
    for a, b in amb:
        rd.uncertain(f"'{_compact(masked[a.start:a.end])}' fits more than one catalog service ({a.obj.cpt} and {b.obj.cpt})")  # type: ignore[attr-defined]
    merged: dict[str, ServiceHit] = {}
    minutes_seen: dict[str, set[int]] = {}
    for m in acc:
        sv = m.obj
        cs, ce = doc.clause(m.start)
        clause = masked[cs:ce]
        seg_s = masked.rfind(",", cs, m.start) + 1 or cs
        seg_e = masked.find(",", m.end, ce)
        seg = masked[seg_s : ce if seg_e < 0 else seg_e]
        name = _compact(masked[m.start : m.end], 50)
        cuts = [cs] + [cs + i + 1 for i, ch in enumerate(clause) if ch == ","] + [ce]
        others = [(a, b) for a, b in zip(cuts, cuts[1:], strict=False) if not (a <= m.start < b) and not any(x.start < b and a < x.end for x in acc)]
        strong_elsewhere = any(STRONG_NEG_SERVICE.search(masked[a:b]) for a, b in others)  # "Offered an injection, patient declined."
        if STRONG_NEG_SERVICE.search(seg) or strong_elsewhere or (NEG_SERVICE.search(seg) and not PERFORMED_SERVICE.search(seg)):
            rd.note(f"service not done or not wanted, not coded: {_compact(clause)}")
            continue
        if COND_SERVICE.search(seg):
            rd.note(f"service only conditional, not coded: {_compact(clause)}")
            continue
        if PAST_SERVICE.search(seg) and not re.search(r"\btoday\b|\bagain\b|\bnow\b", seg, re.I):
            rd.note(f"service mentioned as past history, not coded: {_compact(clause)}")
            continue
        if OFFER_SERVICE.search(clause) and not ACCEPT_SERVICE.search(clause) and not PERFORMED_SERVICE.search(clause):
            rd.uncertain(f"'{name}' was offered or discussed, but the note does not say whether it was done")
            continue
        status = "ordered" if ORDERED_SERVICE.search(clause) and not PERFORMED_SERVICE.search(clause) else "performed"
        lat, conflict = lateral_of(clause)
        if conflict:
            rd.uncertain(f"left and right are both named near '{name}' ({_compact(clause)})")
        mins = _minutes_near(masked, m.start, m.end) if sv.needs_time else []  # type: ignore[attr-defined]
        key = sv.cpt  # type: ignore[attr-defined]
        hit = merged.get(key)
        if hit is None:
            hit = ServiceHit(sv.cpt, sv.name, sv.family, _compact(clause), status, None, 1, lat, sv.needs_laterality, sv.needs_time, "rules", m.kw)  # type: ignore[attr-defined]
            merged[key] = hit
        else:
            if status == "performed":
                hit.status = "performed"
            if lat and not hit.laterality:
                hit.laterality = lat
        if mins:
            minutes_seen.setdefault(key, set()).add(mins[0])
    for key, hit in merged.items():
        if hit.needs_time:
            mins = minutes_seen.get(key, set())
            if len(mins) == 1:
                hit.minutes = next(iter(mins))
                hit.units = (hit.minutes + 7) // 15
                if hit.units == 0:
                    rd.uncertain(f"{hit.name}: {hit.minutes} minutes is under the 8 needed for one 15-minute unit")
            elif len(mins) > 1:
                rd.uncertain(f"{hit.name}: more than one duration is given ({', '.join(str(x) for x in sorted(mins))} minutes)")
                hit.units = 0
            else:
                hit.units = 0
        rd.services.append(hit)
    # laterality for a service that needs it and does not carry its own: the diagnosis's side, when there is exactly one
    for hit in rd.services:
        if hit.needs_laterality and not hit.laterality and len({h.laterality for h in rd.diagnoses if h.laterality}) == 1:
            hit.laterality = next(h.laterality for h in rd.diagnoses if h.laterality)
            rd.note(f"{hit.name}: side taken from the diagnosis ({hit.laterality})")
    # a procedure word that no catalog service explains
    covered = [(m.start, m.end) for m in acc]
    for term in UNKNOWN_SERVICE_TERMS:
        for m in re.finditer(rf"(?<![A-Za-z0-9]){term}(?![A-Za-z0-9])", masked, re.I):
            if any(a < m.end() and m.start() < b for a, b in covered):
                continue
            cs, ce = doc.clause(m.start())
            cl = masked[cs:ce]
            if STRONG_NEG_SERVICE.search(cl) or COND_SERVICE.search(cl) or PAST_SERVICE.search(cl) or NEG_SERVICE.search(masked[cs : m.start()]):
                continue
            rd.uncertain(f"'{_compact(m.group(0))}' looks like a service, but no catalog service matches it ({_compact(cl, 80)})")
