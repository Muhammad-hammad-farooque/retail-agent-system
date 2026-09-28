import os
import secrets
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import set_default_openai_client, set_tracing_disabled, set_default_openai_api

from .ai_failover import FailoverTransport, load_providers
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

# AI providers in priority order (see ai_failover.py). With AI_PROVIDER_n_*
# unset, AI_BASE_URL / AI_API_KEY / AI_MODEL is the single provider, e.g. an
# OmniRoute gateway. Every model listed must handle tool calls reliably.
AI_PROVIDERS = load_providers(os.environ)


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
    for n, p in enumerate(AI_PROVIDERS, 1):
        print(f"[Startup] AI provider {n}: {p.name} ({p.base_url}, model: {p.model})")
    if AI_PROVIDERS[0].api_key == "missing-key":
        print("[Startup] WARNING: no AI key set. Agent requests will fail until you set "
              "AI_PROVIDER_1_KEY (or AI_API_KEY for a single gateway) in .env.")
    client = AsyncOpenAI(
        base_url=AI_PROVIDERS[0].base_url,
        # The transport sets each provider's own key; this one is never sent
        api_key=AI_PROVIDERS[0].api_key,
        http_client=httpx.AsyncClient(
            transport=FailoverTransport(AI_PROVIDERS),
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
