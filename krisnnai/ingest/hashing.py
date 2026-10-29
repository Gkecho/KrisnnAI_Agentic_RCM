"""Salted patient hash. The raw identifier never leaves the parser."""

from __future__ import annotations

import hashlib


def patient_hash(salt: str, member_id: str) -> bytes:
    if not salt:
        raise ValueError("patient hash salt is empty; set the tenant's salt environment variable")
    return hashlib.sha256(f"{salt}|{member_id.strip().upper()}".encode()).digest()
