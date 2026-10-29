"""Tolerant X12 reader: delimiters from ISA, envelope validation, transaction extraction.

Nothing here touches a database. A structural problem raises X12Error, and the caller marks the
file failed with that reason instead of crashing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation


class X12Error(Exception):
    """The file is not valid X12 (or not a transaction we understand)."""


@dataclass(frozen=True)
class Segment:
    """One segment. `els[0]` is the segment id, `els[1]` is element 01, and so on."""

    els: tuple[str, ...]
    sub: str  # component separator

    @property
    def id(self) -> str:
        return self.els[0]

    def __getitem__(self, i: int) -> str:
        return self.els[i] if i < len(self.els) else ""

    def comps(self, i: int) -> list[str]:
        return self[i].split(self.sub)

    def comp(self, i: int, j: int) -> str:
        """Component j (1-based) of element i."""
        parts = self.comps(i)
        return parts[j - 1] if j - 1 < len(parts) else ""


@dataclass
class Transaction:
    isa13: str
    gs06: str
    gs01: str
    st01: str
    st02: str
    version: str
    isa_date: date
    segments: list[Segment] = field(default_factory=list)  # between ST and SE, exclusive


def money(text: str, where: str) -> Decimal:
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise X12Error(f"{where}: '{text}' is not a valid amount") from None
    if not value.is_finite():
        raise X12Error(f"{where}: '{text}' is not a valid amount")
    return value


def x12_date(text: str, where: str) -> date:
    try:
        if len(text) == 8:
            return date(int(text[:4]), int(text[4:6]), int(text[6:]))
        if len(text) == 6:
            return date(2000 + int(text[:2]), int(text[2:4]), int(text[4:]))
    except ValueError:
        pass
    raise X12Error(f"{where}: '{text}' is not a valid date")


def tokenize(text: str) -> list[Segment]:
    text = text.lstrip("﻿ \t\r\n")
    if not text.startswith("ISA"):
        raise X12Error("file does not start with an ISA segment")
    if len(text) < 106:
        raise X12Error("ISA segment is shorter than the fixed 106 characters")
    element_sep, sub_sep, terminator = text[3], text[104], text[105]
    if element_sep.isalnum() or terminator.isalnum() or sub_sep.isalnum():
        raise X12Error("ISA delimiters are alphanumeric, ISA is malformed")
    if len(text[:105].split(element_sep)) != 17:
        raise X12Error("ISA segment does not have 16 elements")
    segments = []
    for raw in text.split(terminator):
        raw = raw.strip("\r\n \t")
        if raw:
            segments.append(Segment(tuple(raw.split(element_sep)), sub_sep))
    return segments


def read_transactions(text: str) -> list[Transaction]:
    """Validate ISA/GS/ST envelopes and counts, and return every transaction set."""
    segments = tokenize(text)
    out: list[Transaction] = []
    isa = gs = st = None
    tx_in_group = 0
    isa_groups = 0
    for seg in segments:
        sid = seg.id
        if sid == "ISA":
            if isa is not None:
                raise X12Error("ISA inside an open interchange")
            isa, isa_groups = seg, 0
        elif isa is None:
            raise X12Error(f"segment {sid} found before ISA")
        elif sid == "GS":
            if gs is not None:
                raise X12Error("GS inside an open functional group")
            gs, tx_in_group = seg, 0
            isa_groups += 1
        elif sid == "ST":
            if gs is None or st is not None:
                raise X12Error("ST outside a functional group or inside an open transaction")
            st = Transaction(
                isa13=isa[13], gs06=gs[6], gs01=gs[1], st01=seg[1], st02=seg[2],
                version=seg[3], isa_date=x12_date(isa[9], "ISA09"),
            )  # fmt: skip
            st.segments.append(seg)  # counted for SE01, removed below
        elif sid == "SE":
            if st is None:
                raise X12Error("SE without ST")
            st.segments.append(seg)
            if seg[2] != st.st02:
                raise X12Error(f"SE02 {seg[2]} does not match ST02 {st.st02}")
            if seg[1] != str(len(st.segments)):
                raise X12Error(f"SE01 says {seg[1]} segments, found {len(st.segments)}")
            st.segments = st.segments[1:-1]
            out.append(st)
            st = None
            tx_in_group += 1
        elif sid == "GE":
            if gs is None or st is not None:
                raise X12Error("GE without a closed functional group")
            if seg[2] != gs[6] or seg[1] != str(tx_in_group):
                raise X12Error(f"GE does not match GS06 {gs[6]} / {tx_in_group} transactions")
            gs = None
        elif sid == "IEA":
            if isa is None or gs is not None:
                raise X12Error("IEA without a closed interchange")
            if seg[2] != isa[13] or seg[1] != str(isa_groups):
                raise X12Error(f"IEA does not match ISA13 {isa[13]} / {isa_groups} groups")
            isa = None
        elif st is not None:
            st.segments.append(seg)
        else:
            raise X12Error(f"segment {sid} outside a transaction set")
    if isa is not None or gs is not None or st is not None:
        raise X12Error("file ends inside an open interchange (truncated?)")
    if not out:
        raise X12Error("no transaction sets found")
    return out
