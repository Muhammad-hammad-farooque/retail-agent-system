import os
import json
import secrets
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import set_default_openai_client, set_tracing_disabled, set_default_openai_api

from .database import create_tables
from .auth.auth_router import router as auth_router
from .api.inventory_router import router as inventory_router
from .api.accounting_router import router as accounting_router
from .api.dashboard_router import router as dashboard_router
from .api.agent_router import router as agent_router
from .api.customer_router import router as customer_router
from .api.complaint_router import router as complaint_router
from .api.purchase_order_router import router as purchase_order_router
from .api.marketing_router import router as marketing_router
from .api.notification_router import router as notification_router
from .api.supplier_router import router as supplier_router
from .api.chat_router import router as chat_router

load_dotenv()

# All AI traffic goes through the OmniRoute gateway, which handles provider
# failover and rate limits. AI_MODEL should name an OmniRoute combo made of
# models with reliable tool calling (the agents depend on it).
AI_BASE_URL = os.getenv("AI_BASE_URL", "http://localhost:20128/v1")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "auto")

# Parameters the Agents SDK may send that most non-OpenAI providers reject.
_UNSUPPORTED_PARAMS = ("verbosity", "reasoning_effort")


class _ModelOverrideTransport(httpx.AsyncBaseTransport):
    """Rewrites chat/completions requests to use AI_MODEL and strips
    parameters unsupported by the gateway's upstream providers."""

    def __init__(self, model: str):
        self._model = model
        self._inner = httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if "chat/completions" not in str(request.url):
            return await self._inner.handle_async_request(request)

        body = json.loads(request.content)
        body["model"] = self._model
        for param in _UNSUPPORTED_PARAMS:
            body.pop(param, None)
        # Handoff tools have no arguments and are sent as
        # {"properties": {}, "required": []}. The empty properties object gets
        # dropped on the way upstream, and Groq then rejects the schema for having
        # "required" without "properties". An empty "required" means nothing, so drop it.
        for tool in body.get("tools") or []:
            params = (tool.get("function") or {}).get("parameters") or {}
            if params.get("required") == []:
                params.pop("required")
        new_content = json.dumps(body).encode()
        headers = dict(request.headers)
        headers["content-length"] = str(len(new_content))

        req = httpx.Request(
            method=request.method,
            url=request.url,
            headers=headers,
            content=new_content,
        )
        return await self._inner.handle_async_request(req)

    async def aclose(self):
        await self._inner.aclose()


app = FastAPI(
    title="Retail Agent System",
    description="Intelligent Retail Store Automation powered by Agentic AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _seed_admin():
    from .database import SessionLocal
    from .models.user import User, UserRole
    from .auth.jwt_handler import hash_password
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            password = os.getenv("ADMIN_PASSWORD")
            if not password:
                password = secrets.token_urlsafe(12)
                print(f"[Startup] ADMIN_PASSWORD not set. Generated admin password: {password}")
            db.add(User(
                username="admin",
                email="admin@retailsystem.com",
                hashed_password=hash_password(password),
                role=UserRole.admin,
                is_active=True,
            ))
            db.commit()
            print("[Startup] Default admin user created.")
    finally:
        db.close()


@app.on_event("startup")
def startup():
    create_tables()
    _seed_admin()
    if not AI_API_KEY:
        print("[Startup] WARNING: AI_API_KEY is not set. Agent requests will fail "
              "until you add an OmniRoute endpoint key to .env.")
    print(f"[Startup] AI gateway: {AI_BASE_URL} (model: {AI_MODEL})")
    client = AsyncOpenAI(
        base_url=AI_BASE_URL,
        api_key=AI_API_KEY or "missing-key",
        http_client=httpx.AsyncClient(
            transport=_ModelOverrideTransport(AI_MODEL),
            timeout=httpx.Timeout(120.0, connect=10.0),
        ),
    )
    set_default_openai_client(client)
    set_default_openai_api("chat_completions")
    set_tracing_disabled(True)


app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(inventory_router)
app.include_router(accounting_router)
app.include_router(dashboard_router)
app.include_router(customer_router)
app.include_router(complaint_router)
app.include_router(purchase_order_router)
app.include_router(marketing_router)
app.include_router(notification_router)
app.include_router(supplier_router)
app.include_router(chat_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "retail-agent-system"}
