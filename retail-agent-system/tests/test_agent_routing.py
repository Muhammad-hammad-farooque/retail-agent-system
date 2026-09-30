"""Tests that /agent/task starts the agent chosen by the query router.

Runner.run is mocked, so no LLM is called; each test checks which agent the
endpoint started and what it remembers for follow-up replies.
"""
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.agents import (
    inventory_agent,
    accounting_agent,
    customer_service_agent,
    marketing_agent,
    manager_agent,
    triage_agent,
)
from backend.guardrails.input_guardrails import ALL_INPUT_GUARDRAILS

# backend.api re-exports each module's `router` under the module's name
agent_router = importlib.import_module("backend.api.agent_router")

SPECIALISTS = [inventory_agent, accounting_agent, customer_service_agent, marketing_agent]


@pytest.fixture(autouse=True)
def clear_last_agent():
    agent_router._last_agent.clear()
    agent_router._awaiting_reply.clear()
    yield
    agent_router._last_agent.clear()
    agent_router._awaiting_reply.clear()


def _mock_run(answered_by=None):
    """Mock Runner.run; the run ends on `answered_by`, or on the agent it started with."""
    async def run(agent, input):
        return SimpleNamespace(final_output="Done.", last_agent=answered_by or agent)
    return AsyncMock(side_effect=run)


def _ask(client, auth_headers, query, answered_by=None):
    mock = _mock_run(answered_by)
    with patch.object(agent_router.Runner, "run", mock):
        resp = client.post("/agent/task", json={"query": query}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return mock.call_args.args[0], mock.call_args.kwargs["input"], resp.json()


@pytest.mark.parametrize("query, expected", [
    ("check stock of Lipton tea", inventory_agent),
    ("show me the invoice 1023", accounting_agent),
    ("what is your return policy", customer_service_agent),
    ("create a 10% discount on rice", marketing_agent),
    ("check stock of Samsung TV and create 10% discount on it", manager_agent),
    ("hello", triage_agent),
])
def test_starts_routed_agent(client, auth_headers, query, expected):
    # The mock ends the run on the starting agent; for triage that means it never
    # handed off, which is reported as a failure (see test_triage_text_reply_is_never_shown)
    started, _, body = _ask(client, auth_headers, query)
    assert started is expected
    assert body["success"] is (expected is not triage_agent)


def test_query_and_date_still_sent_to_agent(client, auth_headers):
    _, messages, _ = _ask(client, auth_headers, "check stock of Lipton tea")
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"].startswith("check stock of Lipton tea")
    assert "Today's date" in messages[-1]["content"]


def test_yes_goes_back_to_previous_agent(client, auth_headers):
    _ask(client, auth_headers, "create a 40% discount on all clothing")
    started, _, _ = _ask(client, auth_headers, "yes")
    assert started is marketing_agent


def test_yes_after_triage_handoff_goes_to_specialist(client, auth_headers):
    # Triage picked Accounting last time, so the follow-up skips triage
    _ask(client, auth_headers, "how is business going?", answered_by=accounting_agent)
    started, _, _ = _ask(client, auth_headers, "yes please")
    assert started is accounting_agent


def test_yes_after_triage_answered_itself_goes_to_triage(client, auth_headers):
    _ask(client, auth_headers, "hello")
    started, _, _ = _ask(client, auth_headers, "yes")
    assert started is triage_agent


def test_yes_after_manager_goes_to_manager(client, auth_headers):
    _ask(client, auth_headers, "check stock of Samsung TV and create 10% discount on it")
    started, _, _ = _ask(client, auth_headers, "yes")
    assert started is manager_agent


def test_yes_with_no_history_goes_to_triage(client, auth_headers):
    started, _, _ = _ask(client, auth_headers, "yes")
    assert started is triage_agent


def test_harmful_query_blocked_before_any_agent(client, auth_headers):
    mock = _mock_run()
    with patch.object(agent_router.Runner, "run", mock):
        resp = client.post("/agent/task", json={"query": "hack the stock database"}, headers=auth_headers)
    assert resp.json()["success"] is False
    mock.assert_not_called()


# ── Agent configuration ──────────────────────────────────────────────────────

@pytest.mark.parametrize("agent", SPECIALISTS + [manager_agent, triage_agent])
def test_every_entry_agent_has_input_guardrails(agent):
    # Any of these can now be the first agent of a run, where the SDK runs input guardrails
    assert agent.input_guardrails == ALL_INPUT_GUARDRAILS


@pytest.mark.parametrize("agent", SPECIALISTS + [manager_agent])
def test_no_sdk_output_guardrails_on_specialists(agent):
    # The SDK budget guardrail raises on any "order ... Rs.>100,000" text, which would
    # block normal "PO pending approval" replies. check_output() in the endpoint
    # handles that instead, by adding the approval notice.
    assert agent.output_guardrails == []


def test_manager_can_reach_every_department():
    names = {tool.name for tool in manager_agent.tools}
    assert names == {
        "inventory_department",
        "accounting_department",
        "customer_service_department",
        "marketing_department",
    }


def test_triage_must_always_hand_off():
    assert triage_agent.model_settings.tool_choice == "required"


def test_triage_text_reply_is_never_shown(client, auth_headers):
    # e.g. "I've forwarded your request to the Inventory Agent" — nothing was done
    _, _, body = _ask(client, auth_headers, "hello")
    assert body["response"] == agent_router.TRIAGE_NO_HANDOFF_REPLY
    assert body["success"] is False


def test_specialist_after_triage_handoff_is_shown(client, auth_headers):
    _, _, body = _ask(client, auth_headers, "hello", answered_by=customer_service_agent)
    assert body["response"] == "Done."
    assert body["success"] is True


def test_triage_can_hand_off_to_manager():
    # A multi-department prompt the router couldn't read reaches triage, which
    # must be able to pass it to the manager rather than one specialist
    assert manager_agent.name in [h.agent_name for h in triage_agent.handoffs]
