from pydantic import BaseModel
from typing import Optional


class AgentTaskRequest(BaseModel):
    query: str
    user_id: Optional[int] = None
    context: Optional[dict] = None


class AgentTaskResponse(BaseModel):
    response: str
    agent_used: str
    success: bool
