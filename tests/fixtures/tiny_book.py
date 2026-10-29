"""A tiny hand-built book of claims for checking KPIs by eye. Everything is fabricated.

Built straight from model objects (not the X12 generator) so each number can be traced on paper. All claims are
one line, CPT 99213 unless noted, billed 150.00. Fee schedule: payer P1 pays 100.00, payer P2 pays 80.00 for 99213.

    claim  payer  what happens                                                       known / submitted
    C1     P1     paid 90, patient 10, contractual (CO 45) 50                        sub 06-01, paid 06-10
    C2     P1     underpaid: paid 70, patient 10, CO 45 70 (should be 100 allowed)   sub 06-01, paid 06-10
    C3     P2     denied (CLP02 4), CO 16 for 150                                    sub 06-01, paid 06-10
    C4     P2     rejected by the 277CA (A3), never paid                              sub 06-01
    C5     P2     no answer yet at 06-30; paid 90 + patient 10 + CO 45 50 on 08-01    sub 06-01, paid 08-01
    C6     P1     submitted after 06-30 (07-14), never paid                           sub 07-14
    C7     P1     CPT 97110, billed 60, paid 48, patient 12, no fee schedule row     dos 05-20, sub 06-01, paid 06-10
    C8     P1     billed 50, nothing back yet                                        dos 06-10, sub 06-12

Service date for C1-C5 is 2026-01-10 and for C6 2026-07-01. Dates are 2026.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.model import tenant_session

D = Decimal


class Book:
    def __init__(self, engine: Engine, tenant_id: int, tag: str = "a"):
        self.s = tenant_session(engine, tenant_id)
        f = m.SourceFile(file_name="tiny.x12", file_sha256=(tag * 64)[:64], file_type="837P", byte_size=1,
                         status="loaded")  # fmt: skip
        self.s.add(f)
        self.s.flush()
        self.file_id = f.id
        self.seq = 0
        self.payers: dict[str, m.Payer] = {}
        self.provider = self._add(m.Provider(npi="1000000001", name="Synthetic Clinic"))
        self.patient = self._add(m.PatientRef(ref_hash=bytes([int(tenant_id)]) * 32))

    def _add(self, row):
        row.source_file_id = self.file_id
        self.s.add(row)
        self.s.flush()
        return row

    def event(
        self, known: date, event_type: str = "t", st02: str = "1", gs06: str = "1", payload: dict | None = None
    ) -> int:
        self.seq += 1
        e = self._add(m.Event(event_type=event_type, isa13="1", gs06=gs06, st02=st02, seq_in_file=self.seq,
                              known_at=datetime.combine(known, datetime.min.time()), payload=json.dumps(payload or {})))  # fmt: skip
        return e.id

    def payer(self, code: str) -> m.Payer:
        if code not in self.payers:
            self.payers[code] = self._add(m.Payer(payer_id_code=code, name=code))
        return self.payers[code]

    def fee(self, payer: str, cpt: str, allowed: str, effective: date = date(2026, 1, 1)) -> None:
        self._add(m.FeeSchedule(payer_id=self.payer(payer).id, cpt=cpt, modifier="", allowed_amount=D(allowed),
                                effective_date=effective))  # fmt: skip

    def claim(self, sid: str, payer: str, charge: str, dos: date, submitted: date, known: date | None = None,
              cpt: str = "99213"):  # fmt: skip
        c = m.Claim(event_id=self.event(known or submitted, "837P.claim", st02=sid, gs06=sid),
                    payer_id=self.payer(payer).id, provider_id=self.provider.id, patient_ref_id=self.patient.id,
                    claim_submitter_id=sid, total_charge=D(charge), place_of_service="11", frequency_code="1",
                    service_date=dos, submitted_on=submitted)  # fmt: skip
        self._add(c)
        self._add(m.ClaimLine(claim_id=c.id, line_number=1, cpt=cpt, charge=D(charge), units=D(1), unit_basis="UN",
                              service_date=dos))  # fmt: skip
        return c

    def visit(self, ref: str, payer: str, dos: date, cpt: str = "99213", patient: m.PatientRef | None = None) -> None:
        self._add(m.Visit(visit_ref=ref, payer_id=self.payer(payer).id, provider_id=self.provider.id,
                          patient_ref_id=(patient or self.patient).id, service_date=dos, cpt=cpt, units=D(1)))  # fmt: skip

    def appointment(self, ref: str, payer: str, appt: date, booked: date, cpt: str = "99213",
                    patient: m.PatientRef | None = None) -> None:  # fmt: skip
        self._add(m.Appointment(appt_ref=ref, payer_id=self.payer(payer).id, provider_id=self.provider.id,
                                patient_ref_id=(patient or self.patient).id, appt_date=appt, booked_on=booked,
                                cpt=cpt, status="booked"))  # fmt: skip

    def eligibility(self, ref: str, payer: str, checked: date, service: date | None, active: bool = True,
                    plan_begin: date | None = None, plan_end: date | None = None, other: str | None = None,
                    copay: str | None = None, coinsurance: str | None = None, deductible: str | None = None,
                    patient: m.PatientRef | None = None) -> None:  # fmt: skip
        self._add(m.EligibilityResponse(
            event_id=self.event(checked, "271.response", st02=ref, gs06=ref), payer_id=self.payer(payer).id,
            patient_ref_id=(patient or self.patient).id, response_ref=ref, checked_on=checked, service_date=service,
            active=active, plan_begin=plan_begin, plan_end=plan_end, other_payer=other,
            copay=D(copay) if copay else None, coinsurance=D(coinsurance) if coinsurance else None,
            deductible_remaining=D(deductible) if deductible else None,
        ))  # fmt: skip

    def authorization(self, ref: str, payer: str, cpt: str, requested: date, status: str = "approved",
                      decided: date | None = None, start: date | None = None, end: date | None = None,
                      approved: int | None = None, used: int | None = None, units_as_of: date | None = None,
                      patient: m.PatientRef | None = None, appointment: str | None = None) -> None:  # fmt: skip
        self._add(m.Authorization(
            appointment_ref=appointment,
            auth_ref=ref, payer_id=self.payer(payer).id, patient_ref_id=(patient or self.patient).id, cpt=cpt,
            units_approved=approved, units_used=used, units_as_of=units_as_of, start_date=start, end_date=end,
            status=status, requested_on=requested, decided_on=decided,
        ))  # fmt: skip

    def require_auth(self, payer: str, cpt: str, validity_days: int = 90) -> None:
        self._add(m.AuthRequirement(payer_id=self.payer(payer).id, cpt=cpt, validity_days=validity_days))

    def deposit(self, ref: str, on: date, amount: str, payer: str | None = None, trace: str | None = None) -> None:
        self._add(m.BankDeposit(deposit_ref=ref, deposit_date=on, amount=D(amount),
                                payer_id=self.payer(payer).id if payer else None, trace_ref=trace, method="ACH"))  # fmt: skip

    def posting(self, ref: str, trace: str, claim: str, on: date, amount: str) -> None:
        self._add(m.Posting(posting_ref=ref, payment_trace=trace, claim_submitter_id=claim, posted_on=on,
                            posted_amount=D(amount), posted_by_role="payment_poster"))  # fmt: skip

    def enrollment(self, ref: str, npi: str, payer: str, status: str, status_on: date, submitted: date | None = None,
                   effective: date | None = None, expires: date | None = None) -> None:  # fmt: skip
        self._add(m.Enrollment(
            enrollment_ref=ref, provider_id=self.provider_for(npi).id, payer_id=self.payer(payer).id, status=status,
            submitted_on=submitted, effective_on=effective, expires_on=expires, status_on=status_on,
        ))  # fmt: skip

    def screening(self, ref: str, npi: str, on: date, result: str = "clear") -> None:
        self._add(m.ProviderScreening(screening_ref=ref, provider_id=self.provider_for(npi).id, screened_on=on,
                                      result=result, source="OIG"))  # fmt: skip

    def provider_for(self, npi: str) -> m.Provider:
        if not hasattr(self, "_providers_by_npi"):
            self._providers_by_npi = {self.provider.npi: self.provider}
        if npi not in self._providers_by_npi:
            self._providers_by_npi[npi] = self._add(m.Provider(npi=npi, name="Synthetic Provider " + npi))
        return self._providers_by_npi[npi]

    def service(self, ref: str, npi: str, payer: str, dos: date, cpt: str = "99213") -> None:
        self._add(m.Visit(visit_ref=ref, payer_id=self.payer(payer).id, provider_id=self.provider_for(npi).id,
                          patient_ref_id=self.patient.id, service_date=dos, cpt=cpt, units=D(1)))  # fmt: skip

    def patient_payment(self, ref: str, claim: str, on: date, amount: str) -> None:
        self._add(m.PatientPayment(payment_ref=ref, claim_submitter_id=claim, paid_on=on, amount=D(amount),
                                   method="CARD"))  # fmt: skip

    def statement(self, ref: str, claim: str, on: date, status: str = "sent", channel: str = "mail") -> None:
        self._add(m.PatientStatement(statement_ref=ref, claim_submitter_id=claim, sent_on=on, channel=channel,
                                     status=status))  # fmt: skip

    def note(self, ref: str, note_date: date, signed: date | None = None, elements: str = "assessment,plan",
             minutes: int | None = None) -> None:  # fmt: skip
        self._add(m.VisitNote(visit_ref=ref, note_date=note_date, signed_date=signed, minutes=minutes,
                              elements=elements))  # fmt: skip

    def charge(self, ref: str, visit_ref: str, entered: date, cpt: str = "99213") -> None:
        self._add(m.Charge(charge_ref=ref, visit_ref=visit_ref, cpt=cpt, units=D(1), entered_date=entered))

    def ack_277ca(self, claim: m.Claim, category: str, known: date, code: str | None = None,
                  payer_claim_number: str | None = None) -> None:  # fmt: skip
        payload = {"claim_submitter_id": claim.claim_submitter_id, "status_category": category, "status_code": code,
                   "entity_code": None, "payer_claim_number": payer_claim_number}  # fmt: skip
        self._add(m.Ack277Ca(event_id=self.event(known, "277CA.claim_status", payload=payload), claim_id=claim.id,
                             claim_submitter_id=claim.claim_submitter_id, status_category=category, status_code=code,
                             payer_claim_number=payer_claim_number))  # fmt: skip

    def ack_999(self, sid: str, status: str, known: date, errors: str | None = None, gs06: str | None = None,
                st02: str | None = None) -> None:  # fmt: skip
        """999 for the 837 transaction the claim `sid` travelled in (by default the book uses sid as ST02 and GS06)."""
        gs06, st02 = gs06 or sid, st02 or sid
        payload = {"acked_gs06": gs06, "acked_st02": st02, "transaction_set": "837", "transaction_status": status,
                   "group_status": None, "error_codes": errors}  # fmt: skip
        self._add(m.Ack999(event_id=self.event(known, "999.ack", payload=payload), acked_gs06=gs06, acked_st02=st02,
                           transaction_set="837", transaction_status=status, error_codes=errors))  # fmt: skip

    def payment(self, payer: str, known: date, trace: str, amount: str, plb: list[tuple[str, str]] | None = None):
        """`plb` is a list of (reason, amount) provider-level adjustments."""
        payload = {"plb": [{"reason_code": r, "amount": a} for r, a in (plb or [])]}
        pay = self._add(
            m.Payment(
                event_id=self.event(known, "835.payment", payload=payload),
                payer_id=self.payer(payer).id,
                trace_number=trace,
                payment_amount=D(amount),
                credit_debit="C",
                payment_method="ACH",
                payment_date=known,
            )
        )
        for seq, (reason, amt) in enumerate(plb or [], start=1):
            self._add(
                m.PlbAdjustment(payment_id=pay.id, seq=seq, provider_ref="1000000001", fiscal_period_date=known,
                                reason_code=reason, reference_id=None, amount=D(amt))
            )  # fmt: skip
        return pay

    def remit(
        self,
        payment: m.Payment,
        claim: m.Claim,
        status: str,
        paid: str,
        pr: str,
        cas: list[tuple[str, str, str]],
        cpt: str = "99213",
        known: date | None = None,
        lines: list[tuple[str, str, str, list[tuple[str, str, str]]]] | None = None,
    ) -> m.Remit:
        """One CLP. By default one SVC with `cas` as (group, reason, amount) at line level; or give `lines` as
        (cpt, charge, paid, cas) tuples for several service lines."""
        known = known or payment.payment_date
        specs = lines or [(cpt, str(claim.total_charge), paid, cas)]
        payload = {
            "status_code": status,
            "lines": [
                {
                    "paid": ln_paid,
                    "adjustments": [{"group_code": g, "reason_code": r, "amount": a} for g, r, a in ln_cas],
                }
                for _, _, ln_paid, ln_cas in specs
            ],
        }
        r = self._add(
            m.Remit(
                event_id=self.event(known, "835.remit", payload=payload),
                payment_id=payment.id,
                claim_id=claim.id,
                claim_submitter_id=claim.claim_submitter_id,
                claim_status_code=status,
                total_charge=claim.total_charge,
                total_paid=D(paid),
                patient_responsibility=D(pr),
                payer_claim_control_number="PCN" + claim.claim_submitter_id,
                service_date=claim.service_date,
                match_method="clp01",
            )
        )
        for n, (ln_cpt, ln_charge, ln_paid, ln_cas) in enumerate(specs, start=1):
            line = self._add(
                m.RemitLine(remit_id=r.id, claim_line_id=None, line_number=n, cpt=ln_cpt, charge=D(ln_charge),
                            paid=D(ln_paid), units=D(1), service_date=claim.service_date, match_method=None)
            )  # fmt: skip
            for seq, (group, reason, amount) in enumerate(ln_cas, start=1):
                self._add(
                    m.Adjustment(remit_id=r.id, remit_line_id=line.id, seq=seq, group_code=group,
                                 reason_code=reason, amount=D(amount))
                )  # fmt: skip
        return r

    def commit(self) -> None:
        self.s.commit()
        self.s.close()


def build_tiny_book(engine: Engine, tenant_id: int = 1, tag: str = "a") -> None:
    b = Book(engine, tenant_id, tag)
    b.fee("P1", "99213", "100.00")
    b.fee("P2", "99213", "80.00")
    jan10, jun1, jun10 = date(2026, 1, 10), date(2026, 6, 1), date(2026, 6, 10)

    c1 = b.claim("C1", "P1", "150.00", jan10, jun1)
    c2 = b.claim("C2", "P1", "150.00", jan10, jun1)
    c3 = b.claim("C3", "P2", "150.00", jan10, jun1)
    c4 = b.claim("C4", "P2", "150.00", jan10, jun1)
    c5 = b.claim("C5", "P2", "150.00", jan10, jun1)
    b.claim("C6", "P1", "150.00", date(2026, 7, 1), date(2026, 7, 14))
    c7 = b.claim("C7", "P1", "60.00", date(2026, 5, 20), jun1)
    b.claim("C8", "P1", "50.00", jun10, date(2026, 6, 12))

    b.ack_277ca(c4, "A3", date(2026, 6, 2))
    for c in (c1, c2, c3, c5, c7):
        b.ack_277ca(c, "A2", date(2026, 6, 2))

    p1 = b.payment("P1", jun10, "TRC1", "208.00")  # C1 90 + C2 70 + C7 48
    b.remit(p1, c1, "1", "90.00", "10.00", [("CO", "45", "50.00"), ("PR", "2", "10.00")])
    b.remit(p1, c2, "1", "70.00", "10.00", [("CO", "45", "70.00"), ("PR", "2", "10.00")])
    b.remit(p1, c7, "1", "48.00", "12.00", [("PR", "2", "12.00")], cpt="97110")
    p2 = b.payment("P2", jun10, "TRC2", "0.00")
    b.remit(p2, c3, "4", "0.00", "0.00", [("CO", "16", "150.00")])
    p3 = b.payment("P2", date(2026, 8, 1), "TRC3", "90.00")
    b.remit(p3, c5, "1", "90.00", "10.00", [("CO", "45", "50.00"), ("PR", "2", "10.00")])
    b.commit()
