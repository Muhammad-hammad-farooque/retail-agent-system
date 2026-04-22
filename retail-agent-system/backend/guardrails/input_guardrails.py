import re
from agents import (
    Agent,
    InputGuardrail,
    GuardrailFunctionOutput,
    RunContextWrapper,
    TResponseInputItem,
)

# ── 1. Scope Check ────────────────────────────────────────────────────────────

RETAIL_KEYWORDS = {
    "stock", "inventory", "product", "sku", "invoice", "bill", "payment",
    "customer", "order", "sale", "revenue", "profit", "loss", "price",
    "discount", "promotion", "supplier", "warehouse", "reorder", "quantity",
    "category", "marketing", "complaint", "refund", "return", "exchange",
    "loyalty", "delivery", "shipping", "tax", "gst", "purchase", "financial",
    "accounting", "report", "trend", "budget", "expense", "receipt",
    # Urdu transliterations
    "maal", "saaman", "bechna", "kharidna", "hisaab", "raseed", "customer",
    "shikayat", "wapsi", "khareednay", "stock", "inventory",
}

NON_RETAIL_TOPICS = {
    "politics", "cricket", "weather", "news", "religion", "relationship",
    "health advice", "medical", "legal advice", "homework", "essay",
    "code review", "programming help", "recipe", "movie", "song",
    "travel", "hotel", "flight", "visa",
}


def _is_retail_related(query: str) -> bool:
    lower = query.lower()
    if any(kw in lower for kw in RETAIL_KEYWORDS):
        return True
    if any(kw in lower for kw in NON_RETAIL_TOPICS):
        return False
    # Short/greeting queries are allowed through
    if len(query.split()) <= 4:
        return True
    return True  # Default allow — LLM will handle edge cases


# ── 2. Harmful Request Check ──────────────────────────────────────────────────

HARMFUL_PATTERNS = [
    r"\bhack(ing|ed)?\b",
    r"\bexploit\b",
    r"\bsql.?inject",
    r"\bpassword.?leak",
    r"\bsteal\b",
    r"\bfraud\b",
    r"\bcheat\b",
    r"\bcompetitor.{0,20}(destroy|sabotage|hack|spy|steal)",
    r"\bblackmail\b",
    r"\bbribe\b",
    r"\bfake.{0,10}(invoice|receipt|data)",
    r"\bmanipulat.{0,20}(data|record|invoice|sales|profit|stock)",
    r"\bdelete.{0,10}(all|database|record)",
    r"\bdump.{0,10}(database|data|table)",
]


def _is_harmful(query: str) -> tuple[bool, str]:
    lower = query.lower()
    for pattern in HARMFUL_PATTERNS:
        if re.search(pattern, lower):
            return True, f"Request contains potentially harmful content: '{pattern}'"
    return False, ""


# ── 3. Abusive Language Check ─────────────────────────────────────────────────

ABUSIVE_WORDS = {
    # English
    "idiot", "stupid", "moron", "fool", "dumb", "shut up", "bastard",
    "asshole", "bullshit", "crap", "damn you", "screw you",
    # Urdu transliterations (common abusive)
    "gandu", "bewakoof", "harami", "kameena", "gadha", "ullu",
    "chutiya", "madarchod", "bsdk", "bc ", " mc ",
}


def _has_abusive_language(query: str) -> bool:
    lower = query.lower()
    return any(word in lower for word in ABUSIVE_WORDS)


# ── Guardrail Functions ───────────────────────────────────────────────────────

async def scope_guardrail_fn(
    ctx: RunContextWrapper,
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    query = input if isinstance(input, str) else str(input)
    is_retail = _is_retail_related(query)
    return GuardrailFunctionOutput(
        output_info={"check": "scope", "passed": is_retail, "query": query[:100]},
        tripwire_triggered=not is_retail,
    )


async def harmful_guardrail_fn(
    ctx: RunContextWrapper,
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    query = input if isinstance(input, str) else str(input)
    is_harmful, reason = _is_harmful(query)
    return GuardrailFunctionOutput(
        output_info={"check": "harmful", "passed": not is_harmful, "reason": reason},
        tripwire_triggered=is_harmful,
    )


async def language_guardrail_fn(
    ctx: RunContextWrapper,
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    query = input if isinstance(input, str) else str(input)
    is_abusive = _has_abusive_language(query)
    return GuardrailFunctionOutput(
        output_info={"check": "language", "passed": not is_abusive},
        tripwire_triggered=is_abusive,
    )


# ── Exported Guardrail Objects ────────────────────────────────────────────────

scope_guardrail = InputGuardrail(guardrail_function=scope_guardrail_fn)
harmful_guardrail = InputGuardrail(guardrail_function=harmful_guardrail_fn)
language_guardrail = InputGuardrail(guardrail_function=language_guardrail_fn)

ALL_INPUT_GUARDRAILS = [scope_guardrail, harmful_guardrail, language_guardrail]


# ── Plain check_input for direct use (non-SDK path) ──────────────────────────

def check_input(query: str) -> dict:
    """Run all input checks and return result dict. Used outside agent SDK flow."""
    is_retail = _is_retail_related(query)
    if not is_retail:
        return {
            "allowed": False,
            "reason": "Query is not related to retail store operations. Please ask about inventory, sales, customers, or store management.",
        }
    is_harmful, harm_reason = _is_harmful(query)
    if is_harmful:
        return {
            "allowed": False,
            "reason": "Request contains harmful or policy-violating content and cannot be processed.",
        }
    if _has_abusive_language(query):
        return {
            "allowed": False,
            "reason": "Please maintain a respectful tone. Abusive language is not permitted.",
        }
    return {"allowed": True, "reason": ""}
