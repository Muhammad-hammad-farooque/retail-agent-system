"""Sales Tax (SST) by payment method.

Cash sales are taxed at SST_RATE_CASH; card and other digital payments
(JazzCash, EasyPaisa, Bank Transfer) at the reduced SST_RATE_DIGITAL.
Rates are read from the environment on every sale, so they can be changed
without touching code. Each invoice stores the tax it was charged, so a
rate change never alters invoices made before it.
"""
import os
import re
from typing import Optional

DEFAULT_SST_RATE_CASH = 0.15
DEFAULT_SST_RATE_DIGITAL = 0.07

CASH = "Cash"
DIGITAL_METHODS = ("Card", "JazzCash", "EasyPaisa", "Bank Transfer")
PAYMENT_METHODS = (CASH,) + DIGITAL_METHODS

# Spellings people type, reduced to letters only -> canonical name
_ALIASES = {
    "cash": CASH,
    "card": "Card", "creditcard": "Card", "debitcard": "Card", "visa": "Card", "mastercard": "Card",
    "jazzcash": "JazzCash",
    "easypaisa": "EasyPaisa", "easypesa": "EasyPaisa",
    "banktransfer": "Bank Transfer", "bank": "Bank Transfer", "onlinetransfer": "Bank Transfer",
}


def normalize_payment_method(method: Optional[str]) -> Optional[str]:
    """Canonical payment method name, or None if it isn't one we accept."""
    return _ALIASES.get(re.sub(r"[^a-z]", "", (method or "").lower()))


def _rate_from_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        rate = float(raw)
    except ValueError:
        raise ValueError(f"{name}={raw!r} is not a number (expected e.g. 0.15 for 15%)")
    if not 0 <= rate < 1:
        raise ValueError(f"{name}={raw!r} must be a fraction between 0 and 1 (e.g. 0.15 for 15%)")
    return rate


def sst_rate(method: str) -> float:
    """SST rate for a canonical payment method (see normalize_payment_method)."""
    if method == CASH:
        return _rate_from_env("SST_RATE_CASH", DEFAULT_SST_RATE_CASH)
    if method in DIGITAL_METHODS:
        return _rate_from_env("SST_RATE_DIGITAL", DEFAULT_SST_RATE_DIGITAL)
    raise ValueError(f"Unknown payment method {method!r}")


def format_rate(rate: float) -> str:
    """0.15 -> '15%', 0.075 -> '7.5%'."""
    return f"{round(rate * 100, 2):g}%"


def tax_label(rate: float, method: str) -> str:
    """Invoice line label, e.g. 'Tax (15% SST — Cash)'."""
    return f"Tax ({format_rate(rate)} SST — {method})"
