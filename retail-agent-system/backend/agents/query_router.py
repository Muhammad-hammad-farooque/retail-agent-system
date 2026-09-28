"""Rule-based routing of chat prompts to specialist agents, without an LLM call.

Skipping the triage agent saves one LLM request per instruction. The rules only
act when they are confident; anything unclear goes to the triage LLM as before.

Rules are matched in order and each match is blanked out of the text, so a
specific phrase claims its words before a generic rule can: "sales report"
(Accounting) is matched before "sale", "top selling" before "sell", and
"approve PO" before "PO".
"""
import re
from dataclasses import dataclass
from difflib import get_close_matches
from typing import Literal, Optional

from ..search_utils import normalize_search_text

INVENTORY = "inventory"
ACCOUNTING = "accounting"
CUSTOMER_SERVICE = "customer_service"
MARKETING = "marketing"
SPECIALISTS = (INVENTORY, ACCOUNTING, CUSTOMER_SERVICE, MARKETING)

# Agents that can receive a follow-up like "yes" (the triage LLM re-reads history instead)
CONTINUABLE = SPECIALISTS + ("manager",)


@dataclass(frozen=True)
class RouteDecision:
    # direct: one specialist | multi: manager calls several | continue: previous agent | llm: triage decides
    mode: Literal["direct", "multi", "continue", "llm"]
    agents: tuple[str, ...]
    reason: str


def _rule(pattern: str, agent: str) -> tuple[re.Pattern, str]:
    return re.compile(pattern), agent


SALE_UNITS = r"(units?|pieces?|peices?|pcs|qty|quantity|items?|bags?|boxes?|packs?|packets?|bottles?|cartons?)"
SALE_TO_CUSTOMER = r"(?:[^.]*?\bto\s+(?:customer|client)\s*(?:#|id)?\s*\w+)?"


# Order matters: earlier rules claim their words first.
RULES: list[tuple[re.Pattern, str]] = [
    # Phrases that contain another agent's words
    _rule(r"\bsales?\s+reports?\b", ACCOUNTING),
    _rule(r"\bsales?\s+trends?\b", MARKETING),
    _rule(r"\b(top|best|most|highest|least|lowest|low)[\s-]+(selling|sold|sells?|sellers?)\b", ACCOUNTING),
    _rule(r"\bsold\s+the\s+(most|least)\b|\b(by|according\s+to)\s+(sells?|sales?)\b", ACCOUNTING),
    # Before the sale rule: "complaining that the X he bought..." is not a sale
    _rule(r"\bcomplain\w*", CUSTOMER_SERVICE),
    _rule(r"\b(approv|reject)\w*\b[^.]{0,25}?\b(po|purchase\s+orders?)\b", ACCOUNTING),
    _rule(r"\bpurchase\s+expenses?\b", ACCOUNTING),
    _rule(r"\bprofit\s*(and|&)\s*loss\b|\bp\s*&\s*l\b", ACCOUNTING),
    _rule(r"\btotal\s+sales\b", ACCOUNTING),
    _rule(r"\border\s+history\b", CUSTOMER_SERVICE),
    _rule(r"\b(return|refund|exchange|delivery|shipping|warranty|payment)\s+polic(y|ies)\b", CUSTOMER_SERVICE),
    _rule(r"\bdelivery\s+(charges?|time|fee)\b", CUSTOMER_SERVICE),
    _rule(r"\b(short|over)[\s-]+deliver(y|ed)\b", INVENTORY),
    _rule(r"\b(goods|stock|order|shipment|delivery|maal)\s+(received|arrived|aa\s+gaya|agaya)\b", INVENTORY),
    _rule(r"\b(receiv|reciev)(e|ed)\s+(the\s+)?(goods|stock|order|shipment|delivery)\b"
          r"|\bwe\s+(have\s+)?(receiv|reciev)(e|ed)\b", INVENTORY),
    # A sale always carries a quantity: "sell 2 TVs", "5 units of rice sold".
    # Without one, "he bought" (complaint) or "products sell fast" isn't a sale.
    # The optional "to customer X" keeps the customer from counting as a
    # separate Customer Service request.
    _rule(r"\b(sell|sold|bought|purchased)\s+(\w+\s+){0,2}?\d+" + SALE_TO_CUSTOMER, INVENTORY),
    _rule(r"\b\d+\s*" + SALE_UNITS + r"\b[^.]{0,60}?\b(sold|sell|bought|purchased)\b" + SALE_TO_CUSTOMER, INVENTORY),
    _rule(r"\b(update|change|set|increase|decrease|raise|lower)\s+(the\s+)?price\b|\bprice\s+(update|change)\b", INVENTORY),
    _rule(r"\b(low|out\s+of)\s+stock\b", INVENTORY),
    _rule(r"\bpurchase\s+orders?\b|\bpo\b", INVENTORY),
    _rule(r"\b(add|new)\s+(a\s+)?(new\s+)?products?\b", INVENTORY),
    _rule(r"\b(list|show)\s+(all\s+)?(the\s+)?products?\b", INVENTORY),
    _rule(r"\bcustomers?\s*(#|id|no\.?)?\s*\d+\b", CUSTOMER_SERVICE),
    _rule(r"\b(find|search|look\s*up)\s+(for\s+)?(a\s+)?customers?\b", CUSTOMER_SERVICE),
    _rule(r"\bcustomer\s+(details|info|information|profile)\b", CUSTOMER_SERVICE),
    _rule(r"\b\d+\s*%\s*off\b", MARKETING),
    _rule(r"\bpromot\w*|\bpromos?\b", MARKETING),
    _rule(r"\bpricing\s+strategy\b", MARKETING),
    _rule(r"\bmaal\b", INVENTORY),
]

# Single words, matched exactly or (for typos) approximately
KEYWORDS: dict[str, str] = {}
for _agent, _words in {
    INVENTORY: "stock stocks inventory quantity qty reorder restock warehouse sku supplier "
               "available availability bache bacha bachay",
    ACCOUNTING: "invoice invoices bill bills revenue profit profits loss losses financial finance "
                "finances tax gst expense expenses income earnings payment payments "
                "hisaab hisab munafa nuqsan aamdani",
    CUSTOMER_SERVICE: "complaint complaints complain refund refunds warranty exchange return returns "
                      "loyalty policy policies faq shikayat wapsi",
    MARKETING: "discount discounts discounted campaign campaigns marketing sms",
}.items():
    for _word in _words.split():
        KEYWORDS[_word] = _agent

# Typo matching only between words of 5+ letters: at 4, names match keywords
# ("Bilal" ~ "bill"), and a wrong agent costs more than an extra LLM call.
FUZZY_MIN_LEN = 5
FUZZY_CUTOFF = 0.85
FUZZY_VOCAB = [w for w in KEYWORDS if len(w) >= FUZZY_MIN_LEN]

# A reply made only of these words is an answer to the previous agent's question
CONTINUATION_WORDS = set(
    "yes yeah yep yup y no nope ok okay sure please thanks thank you approve approved accept "
    "reject rejected proceed confirm confirmed cancel send it dont don't skip go ahead do "
    "haan han ji jee nahi nahin theek thik hai notify return".split()
)
MAX_CONTINUATION_WORDS = 5


def route_query(query: str, last_agent: Optional[str] = None) -> RouteDecision:
    text = normalize_search_text(query).lower()
    words = re.findall(r"[a-z0-9']+", text)

    if words and len(words) <= MAX_CONTINUATION_WORDS and all(w in CONTINUATION_WORDS for w in words):
        if last_agent in CONTINUABLE:
            return RouteDecision("continue", (last_agent,), f"reply to previous {last_agent} question")
        return RouteDecision("llm", (), "reply with no known previous agent")

    # agent -> position of its first match, so agents are listed in prompt order
    hits: dict[str, int] = {}
    matched: list[str] = []

    def record(agent: str, pos: int, label: str) -> None:
        hits[agent] = min(pos, hits.get(agent, pos))
        matched.append(f"{label}->{agent}")

    for pattern, agent in RULES:
        for m in pattern.finditer(text):
            record(agent, m.start(), m.group(0).strip())
        # Blank out matches (same length, so positions stay valid)
        text = pattern.sub(lambda m: " " * len(m.group(0)), text)

    for m in re.finditer(r"[a-z']+", text):
        word = m.group(0)
        agent = KEYWORDS.get(word)
        if agent is None and len(word) >= FUZZY_MIN_LEN:
            close = get_close_matches(word, FUZZY_VOCAB, n=1, cutoff=FUZZY_CUTOFF)
            if close:
                agent = KEYWORDS[close[0]]
                word = f"{word}~{close[0]}"
        if agent:
            record(agent, m.start(), word)

    agents = tuple(sorted(hits, key=hits.get))
    reason = ", ".join(matched) or "no keywords"
    if not agents:
        return RouteDecision("llm", (), reason)
    if len(agents) == 1:
        return RouteDecision("direct", agents, reason)
    return RouteDecision("multi", agents, reason)
