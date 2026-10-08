"""Plain parsed records. Parsers return these; the loader turns them into rows.

Patient identifiers appear only as `patient_hash`, so the JSON stored in the event log holds no PHI.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class ClaimLineRec:
    line_number: int
    cpt: str
    modifiers: list[str]
    charge: Decimal
    units: Decimal
    unit_basis: str
    dx_pointer: str | None
    service_date: date | None


@dataclass
class ClaimRec:
    claim_submitter_id: str
    total_charge: Decimal
    place_of_service: str | None
    frequency_code: str
    payer_claim_control_number: str | None
    service_date: date | None
    submitted_on: date | None
    payer_code: str
    payer_name: str
    provider_npi: str
    provider_name: str
    tax_id: str | None
    patient_hash: bytes
    dx: list[tuple[str, str]] = field(default_factory=list)
    lines: list[ClaimLineRec] = field(default_factory=list)


@dataclass
class AdjustmentRec:
    group_code: str
    reason_code: str
    amount: Decimal
    quantity: Decimal | None


@dataclass
class RemitLineRec:
    line_number: int
    cpt: str
    modifiers: list[str]
    charge: Decimal
    paid: Decimal
    units: Decimal | None
    allowed: Decimal | None
    service_date: date | None
    adjustments: list[AdjustmentRec] = field(default_factory=list)
    remarks: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class RemitRec:
    claim_submitter_id: str
    status_code: str
    total_charge: Decimal
    total_paid: Decimal
    patient_responsibility: Decimal
    filing_indicator: str | None
    payer_claim_control_number: str
    patient_hash: bytes | None
    service_date: date | None
    adjustments: list[AdjustmentRec] = field(default_factory=list)
    remarks: list[tuple[str, str]] = field(default_factory=list)
    lines: list[RemitLineRec] = field(default_factory=list)


@dataclass
class PlbRec:
    seq: int
    provider_ref: str
    fiscal_period_date: date
    reason_code: str
    reference_id: str | None
    amount: Decimal


@dataclass
class PaymentRec:
    trace_number: str
    amount: Decimal
    credit_debit: str
    method: str
    payment_date: date
    payer_code: str
    payer_name: str
    plb: list[PlbRec] = field(default_factory=list)


@dataclass
class Ack999Rec:
    acked_gs06: str
    acked_st02: str
    transaction_set: str
    transaction_status: str
    group_status: str | None
    error_codes: str | None


@dataclass
class Ack277Rec:
    claim_submitter_id: str
    status_category: str
    status_code: str | None
    entity_code: str | None
    status_date: date | None
    total_charge: Decimal | None
    payer_claim_number: str | None


def _default(value):
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(type(value))


def to_json(rec) -> str:
    """Deterministic JSON for the event payload."""
    return json.dumps(asdict(rec), default=_default, sort_keys=True)
