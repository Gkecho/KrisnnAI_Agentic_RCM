"""A plain-language explanation of a patient's share, built from the 835 patient-responsibility reason codes.

For staff to read or adapt before they talk to a patient. Template text, no model, no patient identifiers. This agent
never sends it anywhere.
"""

from __future__ import annotations

from decimal import Decimal

PR_WORDS = {
    "1": "your deductible (the amount you pay before your plan starts paying)",
    "2": "your coinsurance (your share of the allowed amount)",
    "3": "your copayment (a fixed amount for the visit)",
}


def explain(owed: Decimal, codes: dict[str, Decimal], paid: Decimal = Decimal(0)) -> str:
    parts = [f"{amount} is {PR_WORDS.get(code, 'an amount your plan assigns to you (code ' + code + ')')}"
             for code, amount in sorted(codes.items()) if amount > 0]  # fmt: skip
    why = "; ".join(parts) if parts else "the part of this visit your plan assigns to you"
    text = f"Your insurance has processed this visit. Of the total, {owed} is your share: {why}."
    if paid > 0:
        text += f" You have paid {paid} so far, leaving {owed - paid}."
    return text + " If something looks wrong, tell us and we will check it with your plan before asking for payment."
