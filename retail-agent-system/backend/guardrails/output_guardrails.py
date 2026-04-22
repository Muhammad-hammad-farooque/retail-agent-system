import re
from agents import (
    Agent,
    OutputGuardrail,
    GuardrailFunctionOutput,
    RunContextWrapper,
)

# ── 1. Budget Limit Check ─────────────────────────────────────────────────────

BUDGET_THRESHOLD = 100_000  # Rs.100,000

# Matches: Rs.150,000 | Rs.1,50,000 | 150000 | 1,50,000 near order/cost keywords
AMOUNT_PATTERN = re.compile(
    r"(?:Rs\.?|PKR)?\s*([\d,]+(?:\.\d+)?)\s*(?:rupees?|pkr)?",
    re.IGNORECASE,
)
ORDER_KEYWORDS = {"total cost", "order", "purchase order", "net amount", "total amount"}


def _parse_amount(text: str) -> float:
    cleaned = text.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _check_budget_limit(response: str) -> tuple[bool, str]:
    lower = response.lower()
    if not any(kw in lower for kw in ORDER_KEYWORDS):
        return False, ""
    for match in AMOUNT_PATTERN.finditer(response):
        amount = _parse_amount(match.group(1))
        if amount > BUDGET_THRESHOLD:
            return True, f"Amount Rs.{amount:,.0f} exceeds Rs.{BUDGET_THRESHOLD:,.0f} — manager approval required."
    return False, ""


# ── 2. Negative Quantity Check ────────────────────────────────────────────────

NEG_QTY_PATTERN = re.compile(
    r"(?:quantity|stock|units?|qty)[:\s]+(-\d+)",
    re.IGNORECASE,
)


def _check_negative_quantity(response: str) -> tuple[bool, str]:
    match = NEG_QTY_PATTERN.search(response)
    if match:
        return True, f"Invalid negative quantity detected: {match.group(1)}."
    return False, ""


# ── 3. Sensitive Data Masking ─────────────────────────────────────────────────

# Pakistani phone patterns: 03XXXXXXXXX, +923XXXXXXXXX, 923XXXXXXXXX
PHONE_PATTERN = re.compile(r"(?:\+92|92|0)(3\d{2})[-\s]?(\d{3})[-\s]?(\d{4})")

# Address patterns — mask detailed address but keep city
ADDRESS_PATTERN = re.compile(
    r"(?:House|H\.?No\.?|Plot|Street|St\.?|Block|Sector|Phase|Flat|Apartment)\s+[\w\d\-/,\s]{3,40}",
    re.IGNORECASE,
)

# Email masking — show first 2 chars + domain only
EMAIL_PATTERN = re.compile(r"([a-zA-Z0-9._%+-]{2})[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")


def mask_sensitive_data(response: str) -> str:
    """Mask phone numbers, addresses, and partial emails in agent response."""
    # Mask phone: keep last 4 digits visible
    response = PHONE_PATTERN.sub(lambda m: f"****-***-{m.group(3)}", response)
    # Mask address: replace with [ADDRESS MASKED]
    response = ADDRESS_PATTERN.sub("[ADDRESS MASKED]", response)
    # Mask email: show first 2 chars + domain
    response = EMAIL_PATTERN.sub(lambda m: f"{m.group(1)}***@{m.group(2)}", response)
    return response


# ── Guardrail Functions ───────────────────────────────────────────────────────

async def budget_guardrail_fn(
    ctx: RunContextWrapper,
    agent: Agent,
    output,
) -> GuardrailFunctionOutput:
    response = output if isinstance(output, str) else str(output)
    triggered, reason = _check_budget_limit(response)
    return GuardrailFunctionOutput(
        output_info={"check": "budget_limit", "passed": not triggered, "reason": reason},
        tripwire_triggered=triggered,
    )


async def quantity_guardrail_fn(
    ctx: RunContextWrapper,
    agent: Agent,
    output,
) -> GuardrailFunctionOutput:
    response = output if isinstance(output, str) else str(output)
    triggered, reason = _check_negative_quantity(response)
    return GuardrailFunctionOutput(
        output_info={"check": "negative_quantity", "passed": not triggered, "reason": reason},
        tripwire_triggered=triggered,
    )


# ── Exported Guardrail Objects ────────────────────────────────────────────────

budget_guardrail = OutputGuardrail(guardrail_function=budget_guardrail_fn)
quantity_guardrail = OutputGuardrail(guardrail_function=quantity_guardrail_fn)

ALL_OUTPUT_GUARDRAILS = [budget_guardrail, quantity_guardrail]


# ── Plain check_output for direct use ────────────────────────────────────────

def check_output(response: str) -> dict:
    """Run all output checks. Returns masked response and any flags."""
    flags = []

    budget_triggered, budget_reason = _check_budget_limit(response)
    if budget_triggered:
        flags.append({"type": "MANAGER_APPROVAL_REQUIRED", "reason": budget_reason})

    qty_triggered, qty_reason = _check_negative_quantity(response)
    if qty_triggered:
        flags.append({"type": "INVALID_QUANTITY", "reason": qty_reason})

    # Always mask sensitive data before returning
    safe_response = mask_sensitive_data(response)

    return {
        "response": safe_response,
        "flags": flags,
        "requires_approval": budget_triggered,
        "blocked": qty_triggered,
    }
