"""Tests for the rule-based query router.

The router decides, without an LLM call, which specialist should handle a
prompt. The costly mistake is sending a prompt to the WRONG agent, so anything
the rules can't place with confidence must fall back to the triage LLM.
"""
import pytest

from backend.agents.query_router import route_query

INV, ACC, CS, MKT = "inventory", "accounting", "customer_service", "marketing"


def _check(query, expected_mode, expected_agents, last_agent=None, awaiting_reply=False):
    decision = route_query(query, last_agent=last_agent, awaiting_reply=awaiting_reply)
    assert (decision.mode, decision.agents) == (expected_mode, expected_agents), (
        f"{query!r} -> {decision.mode} {decision.agents} ({decision.reason})"
    )


# ── Single agent ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "How many Samsung TVs are in stock?",
    "check stock of Lipton tea",
    "show low stock items",
    "create a purchase order for 50 units of sugar",
    "add new product Dettol soap 200 rupees, category Beauty",
    "we received the goods for PO-12-2026",
    "maal aa gaya PO-45 ka",
    "update price of Surf Excel to 450",
    "list all products in Electronics category",
    "restock sugar",
    "is Dettol soap available?",
    "email the supplier about PO-77",
    "short delivery on PO-55, only 40 received",
])
def test_inventory(query):
    _check(query, "direct", (INV,))


@pytest.mark.parametrize("query", [
    "show me the invoice 1023",
    "what is the profit and loss for last 30 days",
    "financial summary for September",
    "revenue by category",
    "what are our purchase expenses this month",
    "approve purchase order 8",
    "reject PO 12 because price too high",
    "GST on last month's sales",
    "What was the total sales yesterday",
])
def test_accounting(query):
    _check(query, "direct", (ACC,))


@pytest.mark.parametrize("query", [
    "customer Ali has a complaint about a damaged product",
    "show order history for customer 45",
    "add 100 loyalty points to customer 12",
    "what is your return policy",
    "can I get a refund for a broken kettle",
    "warranty on Samsung TV?",
    "find customer named Bilal",
    "delivery policy for Karachi",
    "customer 45 wants to return a kettle",
])
def test_customer_service(query):
    _check(query, "direct", (CS,))


@pytest.mark.parametrize("query", [
    "create a 10% discount on LED TVs from 1 Oct to 15 Oct",
    "30% off on all Clothing",
    "show sales trends for Groceries",
    "generate marketing report",
    "send promotional email to VIP customers with 500+ points",
    "send an SMS campaign for Eid sale",
    "promote slow moving products",
])
def test_marketing(query):
    _check(query, "direct", (MKT,))


# ── Conflicts between agents' vocabulary ─────────────────────────────────────

@pytest.mark.parametrize("query, agent", [
    # A sale is an Inventory transaction even when a customer is named
    ("sell 2 LED TVs to Ahmed Ali", INV),
    ("Customer Sara bought 3 bags of rice", INV),
    ("SELL 5 Dettol Soap To Customer 45", INV),
    ("yes sell 2 more TVs", INV),
    # "selling"/"sales" in a report is Accounting, not a sale
    ("top selling products", ACC),
    ("best selling products this month", ACC),
    ("which products sold the most this month", ACC),
    ("sales report for last week", ACC),
    # Approving/rejecting a PO is Accounting; creating one is Inventory
    ("approve PO 8", ACC),
    ("create PO for 20 kettles", INV),
    # A damaged/broken purchase is a complaint, not a sale
    ("i purchased anex electric kettle 1.7L but when the product deliverd it was damaged", CS),
    ("customer bought 2 kettles and one arrived broken", CS),
    ("the iron I bought last week is not working", CS),
    ("jo blender kharida tha woh kharab nikla", CS),
])
def test_conflicts(query, agent):
    _check(query, "direct", (agent,))


# ── Typos, Roman Urdu, formatting ────────────────────────────────────────────

@pytest.mark.parametrize("query, agent", [
    ("show the invoce for order 55", ACC),
    ("check the inventry of rice", INV),
    ("create a discout on rice", MKT),
    ("kitne TV bache hain", INV),
    ("hisaab dikhao is mahine ka", ACC),
    ("profit ka hisaab do", ACC),
    ("what’s the profit on “Lipton” tea?", ACC),
])
def test_typos_and_roman_urdu(query, agent):
    _check(query, "direct", (agent,))


def test_short_typo_is_left_to_llm():
    # 4-letter words are too close to names to guess ("stok" vs "Bilal" ~ "bill")
    _check("check stok for BEAU-001", "llm", ())


@pytest.mark.parametrize("query, agent", [
    ("find customer named Bilal", CS),
    ("show order history for Billa", CS),
    ("sell 3 soaps to Bilal", INV),
])
def test_names_are_not_mistaken_for_keywords(query, agent):
    _check(query, "direct", (agent,))


def test_two_questions_same_agent_go_direct():
    # Both parts are Accounting tools (financial summary + top selling products)
    _check("tell me reveneu of this month and top selling product", "direct", (ACC,))


# ── Two parts, two agents → manager ──────────────────────────────────────────

@pytest.mark.parametrize("query, agents", [
    ("check stock of Samsung TV and create 10% discount on it", (INV, MKT)),
    ("sold 2 TVs to Ali and add 100 loyalty points to his account", (INV, CS)),
    ("show this month's revenue and low stock items", (ACC, INV)),
    ("log a complaint for customer 5 and show invoice 1023", (CS, ACC)),
])
def test_multi_agent(query, agents):
    _check(query, "multi", agents)


# ── Nothing clear → triage LLM ───────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "hello",
    "how is business going?",
    "what can you do?",
    "tell me about Samsung TV",
    "price of Samsung TV",
    "",
])
def test_unclear_falls_back_to_llm(query):
    _check(query, "llm", ())


# ── Short replies continue with the previous agent ───────────────────────────

@pytest.mark.parametrize("query, last", [
    ("yes", INV),
    ("approve", INV),
    ("yes please", MKT),
    ("haan theek hai", MKT),
    ("no thanks", "manager"),
    ("yes, approve it", ACC),
    ("ok", CS),
    ("reject", INV),
])
def test_continuation(query, last):
    _check(query, "continue", (last,), last_agent=last)


@pytest.mark.parametrize("query", ["yes", "approve", "no thanks"])
def test_continuation_without_previous_agent_uses_llm(query):
    _check(query, "llm", (), last_agent=None)


def test_continuation_after_triage_uses_llm():
    _check("yes", "llm", (), last_agent="triage")


@pytest.mark.parametrize("query", ["Ali Khan", "0300-1234567", "+92 300 1234567", "his name is Sara"])
def test_answer_to_agent_question_continues(query):
    # Customer Service asked "What's the customer's name, phone or ID?"
    _check(query, "continue", (CS,), last_agent=CS, awaiting_reply=True)


def test_keywordless_prompt_without_question_uses_llm():
    _check("Ali Khan", "llm", (), last_agent=CS)


def test_new_request_overrides_pending_question():
    _check("show low stock items", "direct", (INV,), last_agent=CS, awaiting_reply=True)


def test_new_request_overrides_previous_agent():
    _check("approve purchase order 8", "direct", (ACC,), last_agent=INV)
    _check("show low stock items", "direct", (INV,), last_agent=MKT)


# ── Real prompts from the app's chat history (labelled by hand) ──────────────
# The router was checked against these after the rules were written; they
# caught "he bought" in complaints and "lowest sell" being treated as sales.

REAL_PROMPTS = [
    ("What is the revenue this month?", "direct", (ACC,)),
    ("5 units of denim jeans men has been sold", "direct", (INV,)),
    ("2 units of Laptop Stand Aluminum has been sold", "direct", (INV,)),
    ("are you added payment of sold item in accounts?", "direct", (ACC,)),
    ("3 units of surf excel 1kg has been sold", "direct", (INV,)),
    ("3 units of HDMI Cable 2m has been sold", "direct", (INV,)),
    ("Show me financial summary for last 30 days", "direct", (ACC,)),
    ("What are the top selling products?", "direct", (ACC,)),
    ("Show me purchase expenses", "direct", (ACC,)),
    ("Show order history for customer ID 5", "direct", (CS,)),
    ("What is your return policy?", "direct", (CS,)),
    ("i want to return electronics item", "direct", (CS,)),
    ("highest loyalty point customer", "direct", (CS,)),
    ("Add 200 loyalty points to customer ID 160", "direct", (CS,)),
    ("Show sales trends for last 30 days", "direct", (MKT,)),
    ("What are the top 5 products for marketing?", "direct", (MKT,)),
    ("5 low selling products", "direct", (ACC,)),
    ("i am looking for marketing view", "direct", (MKT,)),
    ("i give the discount so that the products sell fast", "direct", (MKT,)),
    ("yes i agree, you send the discount email to all customer with the subject of "
     "40% flat discount on all clothing", "direct", (MKT,)),
    ("no, you proceed 40% discount email", "direct", (MKT,)),
    ("ok 30% discount", "direct", (MKT,)),
    ("30% flat discount an all clothing items and start from tommorrow 25/5/2026 to "
     "31/5/2026. email send to all customers", "direct", (MKT,)),
    ("what is the capital of france?", "llm", ()),
    ("today's weather/", "llm", ()),
    ("update the price of tata salt 1kg from 150 to 170", "direct", (INV,)),
    ("2 peices of Perfume Men 100ml sold to customer name ahmed ali", "direct", (INV,)),
    ("Customer Ahmed Ali is complaining that the Perfume Men 100ml he bought smells "
     "different from the original.", "direct", (CS,)),
    ("Customer ID 101 complained that the product packaging was damaged.", "direct", (CS,)),
    ("2 units of sunflower oil 5L sold", "direct", (INV,)),
    ("3 units of Non-Stick Frying Pan has been sold", "direct", (INV,)),
    ("what is the reveneu of this month", "direct", (ACC,)),
    ("top 5 product according to sell", "direct", (ACC,)),
    ("5 products of lowest sell", "direct", (ACC,)),
    ("for specific inventory detail", "direct", (INV,)),
    ("product quantity", "direct", (INV,)),
    ("clothing category", "llm", ()),
    ("information on stock", "direct", (INV,)),
    ("create the purchase order of 10 units of Non-Stick Frying Pan", "direct", (INV,)),
    ("we recieved the 10 units of Non-Stick Frying Pan", "direct", (INV,)),
    ("Customer Ahmed Ali is complaining that the USB-C charger 65watt he bought not "
     "working. His ID is 101.", "direct", (CS,)),
    ("send the promotional message with the subject of 10% discount on all items due "
     "to EID. Email send to all customers", "direct", (MKT,)),
    ("10 quantity of Women's Lawn Suit has been sold", "direct", (INV,)),
    ("tell me any product which is low from critical value", "llm", ()),
    ("check the clothing category", "llm", ()),
    ("10 pieces of ilmi general knowledge encyclopedia has been sold", "direct", (INV,)),
    ("10 units of childern story pack 5 has been sold", "direct", (INV,)),
    ("reorder 10 units", "direct", (INV,)),
]


@pytest.mark.parametrize("query, mode, agents", REAL_PROMPTS)
def test_real_prompts(query, mode, agents):
    _check(query, mode, agents)
