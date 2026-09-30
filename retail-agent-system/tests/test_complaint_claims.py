"""A reply must not say a complaint was registered unless one was saved."""
from types import SimpleNamespace

import pytest
from agents import Agent
from agents.items import ToolCallItem

from backend.api.agent_router import _claims_unsaved_complaint

# The real (deployed) reply from triage, which has no tools: nothing was saved
INVENTED_REPLY = (
    "I'm very sorry that your Anex electric kettle arrived damaged. I've logged your complaint and "
    "forwarded it to a Customer Service Agent who will contact you shortly to arrange a replacement "
    "or refund.\n\n**Reference number:** COM-20260930-001"
)


AGENT = Agent(name="Test Agent")


def _result(text, tool_names=()):
    items = [ToolCallItem(agent=AGENT, raw_item=SimpleNamespace(name=n)) for n in tool_names]
    return SimpleNamespace(final_output=text, new_items=items)


@pytest.mark.parametrize("text", [
    INVENTED_REPLY,
    "Your complaint has been registered. Reference: COMP-2026-001",
    "I have recorded the complaint for the damaged iron.",
])
def test_invented_confirmation_is_caught(text):
    assert _claims_unsaved_complaint(_result(text)) is True


def test_real_tool_call_passes():
    text = "Complaint Registered for Ali Khan. Reference: COMP-12-20260930101500"
    assert _claims_unsaved_complaint(_result(text, ["find_customer", "handle_complaint"])) is False


def test_real_reference_from_manager_agent_passes():
    # The manager runs specialists as tools, so their inner handle_complaint call isn't listed
    text = "Your complaint has been registered. Reference: COMP-12-20260930101500"
    assert _claims_unsaved_complaint(_result(text, ["customer_service"])) is False


@pytest.mark.parametrize("text", [
    "Sorry to hear that! What's the customer's name, phone number or customer ID so I can register the complaint?",
    "Our complaint policy: damaged items can be returned within 7 days.",
])
def test_replies_without_a_claim_pass(text):
    assert _claims_unsaved_complaint(_result(text)) is False
