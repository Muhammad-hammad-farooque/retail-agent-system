from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from agents import Runner, InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered

from ..database import get_db
from ..schemas.agent import AgentTaskRequest, AgentTaskResponse
from ..auth.jwt_handler import get_current_user
from ..models.user import User
from ..agents.triage_agent import triage_agent
from ..guardrails.input_guardrails import check_input
from ..guardrails.output_guardrails import check_output

router = APIRouter(prefix="/agent", tags=["agent"])


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
        result = await Runner.run(triage_agent, input=payload.query)

        agent_used = "triage_agent"
        if result.last_agent:
            agent_used = result.last_agent.name.lower().replace(" ", "_")

        # Post-flight output check — mask PII and check flags
        output_check = check_output(result.final_output)

        if output_check["blocked"]:
            return AgentTaskResponse(
                response=f"Response blocked: {output_check['flags'][0]['reason']}",
                agent_used=agent_used,
                success=False,
            )

        final_response = output_check["response"]

        # Append manager approval notice if required
        if output_check["requires_approval"]:
            notice = "\n\n⚠️ MANAGER APPROVAL REQUIRED: This transaction exceeds Rs.100,000."
            final_response += notice

        return AgentTaskResponse(
            response=final_response,
            agent_used=agent_used,
            success=True,
        )

    except InputGuardrailTripwireTriggered as e:
        return AgentTaskResponse(
            response="Your request was blocked by our content policy. Please ensure your query is related to retail store operations and uses respectful language.",
            agent_used="input_guardrail",
            success=False,
        )
    except OutputGuardrailTripwireTriggered as e:
        return AgentTaskResponse(
            response="The agent response was blocked due to policy violations (invalid data or approval required).",
            agent_used="output_guardrail",
            success=False,
        )
    except Exception as e:
        return AgentTaskResponse(
            response=f"Agent error: {str(e)}",
            agent_used="triage_agent",
            success=False,
        )
