# ruff: noqa: E501
"""An OPTIONAL AI second opinion on a visit note, always checked by the rules (rule 6: rules first, AI second).

`AiReader` asks a `ModelProvider` (krisnai/engine/models.py) to propose a structured reading of the transcript:

    {"status": "new|established", "status_evidence": "<quote>",
     "conditions": [{"icd10": "I10", "evidence": "<exact words from the note>"}],
     "services":   [{"cpt": "97110", "evidence": "<exact words from the note>", "minutes": 30}]}

and then VALIDATES every proposal before anything is used:

  * a code that is not in the catalog (read at call time) is a hallucination and is rejected;
  * a quote that does not appear VERBATIM in the transcript (whitespace may differ, nothing else) is fabricated and the proposal is rejected;
  * the AI can only ADD a suggestion or RAISE a disagreement, it can never remove or change what the rules found: a validated proposal the
    rules did not find is added with `source="ai"`, and every addition or disagreement is also an uncertainty, so the visit goes to a coder;
  * a code the AI proposes that the rules read as denied, uncertain or historical is a disagreement, not an addition; a code the rules found that
    the AI did not propose is a disagreement too; a different patient status is a disagreement; none of this changes the rules' answer.

DEFAULTS AND SAFETY. The default provider is the repo's deterministic `StubProvider`: no network, and its answer is not JSON, so it proposes
nothing (the reading is unchanged and `reading.ai["usable"]` is False). Any other provider is refused with `BaaNotApproved` (engine/models.py)
unless `baa_approved=True` is passed. This module holds no API key and no network client, and it must stay that way.

HOW A REAL PROVIDER WOULD BE ENABLED (not done here, needs an approved BAA and a security review first):
  1. the tenant's BAA with the model vendor is approved and recorded;
  2. write a class with `model_id`, `model_version` and `complete(prompt) -> str` that calls the vendor from deployment code (keys from the
     environment, never from the repo) and put it in the deployment, not here;
  3. build `Coder(policy, reader="rules+ai", ai=AiReader(MyProvider(), baa_approved=True))`; `StreamConfig(reader="rules+ai")` does the same
     with the stub until a provider is injected;
  4. only synthetic transcripts may be sent until step 1 is true; the prompt hash and model id are stored in `reading.ai`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from krisnai.engine.models import ModelProvider, StubProvider, call_model
from krisnai.live import catalog
from krisnai.live.reader import ConditionHit, Reading, ServiceHit

PROMPT = (
    "You are helping a medical coder. Read the visit note below and answer with ONE JSON object only, no prose, in this shape: "
    '{{"status": "new" or "established" or "unknown", "status_evidence": "<exact words>", '
    '"conditions": [{{"icd10": "<code from the list>", "evidence": "<exact words copied from the note>"}}], '
    '"services": [{{"cpt": "<code from the list>", "evidence": "<exact words copied from the note>", "minutes": <number or null>}}]}}. '
    "Use only codes from these lists, copy evidence word for word, and leave a list empty when unsure.\n"
    "CONDITIONS: {conditions}\nSERVICES: {services}\nNOTE:\n{note}"
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


class FakeAi:
    """A scripted provider for tests. `answer` is a dict (sent as JSON), a string (sent as is) or a function of the prompt.
    Its model id is not 'stub', so using it needs `baa_approved=True`, exactly like a real provider; it never touches the network."""

    model_id = "fake-ai"
    model_version = "test"

    def __init__(self, answer: dict | str | Callable[[str], str] | None = None):
        self.answer = {} if answer is None else answer
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        a = self.answer
        if callable(a):
            return a(prompt)
        return a if isinstance(a, str) else json.dumps(a)


@dataclass
class AiReport:
    usable: bool = False
    model_id: str = ""
    model_version: str = ""
    prompt_hash: str = ""
    accepted: list[str] = field(default_factory=list)  # proposals that passed validation and agree with, or were added to, the rules
    added: list[str] = field(default_factory=list)  # validated proposals the rules had not found
    rejected: list[str] = field(default_factory=list)  # hallucinated codes and fabricated quotes, with the reason
    disagreements: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class AiReader:
    def __init__(self, provider: ModelProvider | None = None, baa_approved: bool = False):
        self.provider: ModelProvider = provider or StubProvider()
        self.baa_approved = baa_approved

    # ------------------------------------------------------------------ ask
    def prompt(self, text: str) -> str:
        conds = "; ".join(f"{c.icd10} {c.name}" for c in catalog.CONDITIONS)
        svcs = "; ".join(f"{s.cpt} {s.name}" for s in catalog.SERVICES if not s.family.startswith("em"))
        return PROMPT.format(conditions=conds, services=svcs, note=text)

    def propose(self, text: str) -> tuple[dict | None, AiReport]:
        """Ask the provider. Raises `BaaNotApproved` for a non-stub provider without an approved BAA. Returns (parsed JSON or None, report)."""
        res = call_model(self.provider, self.prompt(text), self.baa_approved)
        rep = AiReport(model_id=res.model_id, model_version=res.model_version, prompt_hash=res.prompt_hash)
        m = re.search(r"\{.*\}", res.text, re.S)
        if not m:
            return None, rep
        try:
            data = json.loads(m.group(0))
        except ValueError:
            return None, rep
        return (data, rep) if isinstance(data, dict) else (None, rep)

    # ------------------------------------------------------------------ validate and merge
    def apply(self, text: str, rd: Reading) -> Reading:
        """Return `rd` with the validated AI proposals merged in. The rules' own findings are never removed or changed."""
        data, rep = self.propose(text)
        rd.ai = rep.to_dict()
        if data is None:
            rd.note("the AI layer gave no usable answer; the rules' reading stands")
            return rd
        rep.usable = True
        flat = _norm(text)

        def quote_ok(q: object) -> bool:
            return isinstance(q, str) and bool(_norm(q)) and _norm(q) in flat

        # ---- conditions
        ai_codes: set[str] = set()
        conds = data.get("conditions")
        if conds is not None and not isinstance(conds, list):
            rep.rejected.append("conditions was not a list")
            conds = []
        for p in conds or []:
            if not isinstance(p, dict):
                rep.rejected.append(f"malformed condition proposal: {_norm(str(p))[:60]}")
                continue
            icd, ev = p.get("icd10"), p.get("evidence")
            c = catalog.condition_by_icd(icd) if isinstance(icd, str) else None
            if c is None:
                rep.rejected.append(f"hallucinated code {icd!r}: not in the catalog")
                continue
            if not quote_ok(ev):
                rep.rejected.append(f"fabricated quote for {icd}: {_norm(str(ev))[:60]!r} is not in the transcript")
                continue
            ai_codes.add(c.icd10)
            mine = [h for h in rd.conditions if h.icd10 == c.icd10]
            if any(h.status == "active" for h in mine):
                rep.accepted.append(f"{c.icd10} (agrees with the rules)")
            elif mine:
                msg = f"the AI proposes {c.icd10} {c.name}, but the rules read that mention as {mine[0].status}"
                rep.disagreements.append(msg)
                rd.uncertain("AI disagreement: " + msg)
            else:
                rd.conditions.append(ConditionHit(c.icd10, c.name, _norm(str(ev)), "", "ai", "active", "", c.unspecified, c.needs_laterality,
                                                  c.chronic, source="ai", note="proposed by the AI, validated, not found by the rules"))
                rep.added.append(c.icd10)
                rep.accepted.append(f"{c.icd10} (added)")
                rd.uncertain(f"AI proposal not found by the rules: {c.icd10} {c.name} (evidence: \"{_norm(str(ev))[:80]}\")")
        if "conditions" in data:  # the AI gave a list: any code the rules found that it did not name is a disagreement
            for h in rd.conditions:
                if h.source == "rules" and h.status == "active" and h.icd10 not in ai_codes:
                    msg = f"the rules found {h.icd10} {h.name} but the AI did not propose it"
                    rep.disagreements.append(msg)
                    rd.uncertain("AI disagreement: " + msg)

        # ---- services
        ai_cpts: set[str] = set()
        svcs = data.get("services")
        if svcs is not None and not isinstance(svcs, list):
            rep.rejected.append("services was not a list")
            svcs = []
        for p in svcs or []:
            if not isinstance(p, dict):
                rep.rejected.append(f"malformed service proposal: {_norm(str(p))[:60]}")
                continue
            cpt, ev = p.get("cpt"), p.get("evidence")
            s = catalog.service_by_cpt(cpt) if isinstance(cpt, str) else None
            if s is None or s.family.startswith("em"):
                rep.rejected.append(f"hallucinated code {cpt!r}: not a catalog service")
                continue
            if not quote_ok(ev):
                rep.rejected.append(f"fabricated quote for {cpt}: {_norm(str(ev))[:60]!r} is not in the transcript")
                continue
            ai_cpts.add(s.cpt)
            if any(x.cpt == s.cpt for x in rd.services):
                rep.accepted.append(f"{s.cpt} (agrees with the rules)")
            else:
                minutes = p.get("minutes") if isinstance(p.get("minutes"), int) and not isinstance(p.get("minutes"), bool) else None
                units = ((minutes + 7) // 15 if minutes else 0) if s.needs_time else 1
                rd.services.append(ServiceHit(s.cpt, s.name, s.family, _norm(str(ev)), "performed", minutes if s.needs_time else None, units, "",
                                              s.needs_laterality, s.needs_time, source="ai"))
                rep.added.append(s.cpt)
                rep.accepted.append(f"{s.cpt} (added)")
                rd.uncertain(f"AI proposal not found by the rules: {s.cpt} {s.name} (evidence: \"{_norm(str(ev))[:80]}\")")
        if "services" in data:
            for x in rd.services:
                if x.source == "rules" and x.cpt not in ai_cpts:
                    msg = f"the rules found {x.cpt} {x.name} but the AI did not propose it"
                    rep.disagreements.append(msg)
                    rd.uncertain("AI disagreement: " + msg)

        # ---- status: the AI never sets it
        st = data.get("status")
        if st in ("new", "established") and quote_ok(data.get("status_evidence")):
            if rd.status == "unknown":
                msg = f"the AI reads the patient as {st} ({_norm(str(data.get('status_evidence')))[:60]!r}) but the rules could not tell"
                rep.disagreements.append(msg)
                rd.uncertain("AI suggestion: " + msg)
            elif rd.status != st:
                msg = f"the AI reads the patient as {st} but the rules read {rd.status}"
                rep.disagreements.append(msg)
                rd.uncertain("AI disagreement: " + msg)
        elif st in ("new", "established"):
            rep.rejected.append(f"fabricated quote for status {st}")
        rd.ai = rep.to_dict()
        return rd
