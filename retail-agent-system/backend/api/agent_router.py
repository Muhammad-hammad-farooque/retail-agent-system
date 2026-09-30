from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from agents import Runner, InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from agents.items import ToolCallItem
from datetime import datetime, timezone
import logging
import re
import openai

from ..database import get_db
from ..schemas.agent import AgentTaskRequest, AgentTaskResponse
from ..auth.jwt_handler import get_current_user
from ..models.user import User
from ..agents import (
    inventory_agent,
    accounting_agent,
    customer_service_agent,
    marketing_agent,
    manager_agent,
    triage_agent,
)
from ..agents.query_router import route_query
from ..guardrails.input_guardrails import check_input
from ..guardrails.output_guardrails import check_output
from ..models.chat_message import ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

AGENTS = {
    "inventory": inventory_agent,
    "accounting": accounting_agent,
    "customer_service": customer_service_agent,
    "marketing": marketing_agent,
    "manager": manager_agent,
    "triage": triage_agent,
}
AGENT_KEYS = {id(agent): key for key, agent in AGENTS.items()}

# user_id -> key of the agent that answered last, so a reply like "yes" goes
# back to it. In memory only: after a restart a reply goes to the triage LLM,
# which works it out from the chat history as before.
_last_agent: dict[int, str] = {}
# Whether that agent's last reply ended with a question (e.g. "What's the customer's name?")
_awaiting_reply: dict[int, bool] = {}


# handle_complaint's reference format: COMP-<customer id>-<YYYYmmddHHMMSS>
REAL_COMPLAINT_REF = re.compile(r"\bCOMP-\d+-\d{14}\b")
COMPLAINT_CLAIM = re.compile(
    r"complaint[^.]{0,60}\b(registered|logged|recorded|filed|submitted)\b"
    r"|\b(registered|logged|recorded|filed|submitted)\b[^.]{0,60}complaint",
    re.IGNORECASE,
)
UNSAVED_COMPLAINT_NOTICE = (
    "\n\n⚠️ This complaint was NOT saved. Please give the customer's name, phone number "
    "or customer ID so it can be registered."
)


TRIAGE_NO_HANDOFF_REPLY = (
    "Sorry, I couldn't work out which department should handle that, so nothing was done. "
    "Please rephrase it, e.g. \"create purchase order for 5 units of <product>\"."
)


def _claims_unsaved_complaint(result) -> bool:
    """True when the reply says a complaint was registered but none was saved.

    Models sometimes invent a confirmation and reference number instead of
    calling handle_complaint. A real save either shows up as that tool call or,
    when the manager agent ran the specialist as a tool, as its COMP- reference.
    """
    text = str(result.final_output)
    if not COMPLAINT_CLAIM.search(text) or REAL_COMPLAINT_REF.search(text):
        return False
    return not any(
        isinstance(item, ToolCallItem) and getattr(item.raw_item, "name", None) == "handle_complaint"
        for item in result.new_items
    )


def _pick_agent(query: str, user_id: int):
    decision = route_query(
        query,
        last_agent=_last_agent.get(user_id),
        awaiting_reply=_awaiting_reply.get(user_id, False),
    )
    logger.info("route %s %s (%s)", decision.mode, decision.agents, decision.reason)
    if decision.mode in ("direct", "continue"):
        return AGENTS[decision.agents[0]]
    if decision.mode == "multi":
        return manager_agent
    return triage_agent


@router.post("/task", response_model=AgentTaskResponse)
async def run_agent_task(
    payload: AgentTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Pre-flight input check (fast path before hitting the agent)
    input_check = check_input(payload.query)
    if not input_check["allowed"]:
        return AgentTaskResponse(
            response=input_check["reason"],
            agent_used="input_guardrail",
            success=False,
        )

    try:
        today = datetime.now(timezone.utc).strftime("%A, %d %B %Y")

        # Fetch last 10 messages for conversation context (5 exchanges)
        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == current_user.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
            .all()
        )
        history.reverse()  # oldest first

        # Build messages list with full history + current query
        messages = [{"role": msg.role.value, "content": msg.content} for msg in history]
        messages.append({"role": "user", "content": f"{payload.query}\n\n(Today's date: {today})"})

        start_agent = _pick_agent(payload.query, current_user.id)
        result = await Runner.run(start_agent, input=messages)

        agent_used = "triage_agent"
        key = None
        if result.last_agent:
            agent_used = result.last_agent.name.lower().replace(" ", "_")
            key = AGENT_KEYS.get(id(result.last_agent))
            if key:
                _last_agent[current_user.id] = key
        # Only a known agent's question counts: a triage question would otherwise
        # send the answer to whichever specialist ran before it
        asked = str(result.final_output).rstrip().endswith("?")
        _awaiting_reply[current_user.id] = asked and key is not None

        # Triage must always hand off (tool_choice="required"). If a provider ignored
        # that and triage answered itself, its text can't be trusted: it has no tools,
        # yet it has claimed "I've logged your complaint" / "forwarded your order".
        if key == "triage":
            logger.warning("triage answered without handing off: %r", str(result.final_output)[:200])
            return AgentTaskResponse(
                response=TRIAGE_NO_HANDOFF_REPLY,
                agent_used=agent_used,
                success=False,
            )

        # Post-flight output check — mask PII and check flags
        output_check = check_output(result.final_output)

        if output_check["blocked"]:
            return AgentTaskResponse(
                response=f"Response blocked: {output_check['flags'][0]['reason']}",
                agent_used=agent_used,
                success=False,
            )

        final_response = output_check["response"]

        if _claims_unsaved_complaint(result):
            logger.warning("reply claimed a complaint was registered without saving one")
            final_response += UNSAVED_COMPLAINT_NOTICE

        # Append manager approval notice if required
        if output_check["requires_approval"]:
            notice = "\n\n⚠️ MANAGER APPROVAL REQUIRED: This transaction exceeds Rs.100,000."
            final_response += notice

        return AgentTaskResponse(
            response=final_response,
            agent_used=agent_used,
            success=True,
        )

    except InputGuardrailTripwireTriggered:
        return AgentTaskResponse(
            response="Your request was blocked by our content policy. Please ensure your query is related to retail store operations and uses respectful language.",
            agent_used="input_guardrail",
            success=False,
        )
    except OutputGuardrailTripwireTriggered:
        return AgentTaskResponse(
            response="The agent response was blocked due to policy violations (invalid data or approval required).",
            agent_used="output_guardrail",
            success=False,
        )
    except openai.BadRequestError as e:
        err_str = str(e)
        if "content_filter" in err_str or "content management policy" in err_str:
            return AgentTaskResponse(
                response="Your request was flagged by the AI content filter. Please rephrase your query and try again.",
                agent_used="triage_agent",
                success=False,
            )
        return AgentTaskResponse(
            response=f"Bad request error: {err_str[:200]}",
            agent_used="triage_agent",
            success=False,
        )
    except openai.RateLimitError as e:
        logger.warning("AI rate limit on all providers: %s", e)
        return AgentTaskResponse(
            response="The AI assistant is busy right now. Please wait a minute and try again.",
            agent_used="triage_agent",
            success=False,
        )
    except openai.AuthenticationError:
        logger.error("AI provider rejected its API key (AI_PROVIDER_n_KEY or AI_API_KEY)")
        return AgentTaskResponse(
            response="The AI service is not configured correctly. Please ask an administrator to check the AI provider keys in .env.",
            agent_used="triage_agent",
            success=False,
        )
    except openai.APITimeoutError:
        return AgentTaskResponse(
            response="The AI assistant took too long to respond. Please try again.",
            agent_used="triage_agent",
            success=False,
        )
    except openai.APIConnectionError:
        logger.error("Cannot reach AI gateway")
        return AgentTaskResponse(
            response="The AI assistant is unavailable right now. Other features still work; please try again shortly.",
            agent_used="triage_agent",
            success=False,
        )
    except openai.InternalServerError as e:
        # The gateway returns 5xx when every configured provider has failed
        logger.error("AI gateway 5xx (all providers failing?): %s", e)
        return AgentTaskResponse(
            response="The AI assistant is temporarily unavailable. Please try again in a few minutes.",
            agent_used="triage_agent",
            success=False,
        )
    except Exception:
        logger.exception("Unexpected agent error")
        return AgentTaskResponse(
            response="Something went wrong while processing your request. Please try again.",
            agent_used="triage_agent",
            success=False,
        )
