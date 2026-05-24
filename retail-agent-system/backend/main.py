import os
import json
import asyncio
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

AI_MODEL = "gpt-4o-mini"


class _RotatingKeyTransport(httpx.AsyncBaseTransport):
    """Intercepts chat/completions requests, forces the model name, and
    automatically rotates to the next API key on 429 rate limit errors."""

    def __init__(self, model: str, api_keys: list[str]):
        self._model = model
        self._keys = [k for k in api_keys if k]
        self._current_index = 0
        self._lock = asyncio.Lock()
        self._inner = httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if "chat/completions" not in str(request.url):
            return await self._inner.handle_async_request(request)

        body = json.loads(request.content)
        body["model"] = self._model
        body.pop("verbosity", None)
        body.pop("reasoning_effort", None)
        new_content = json.dumps(body).encode()
        headers = dict(request.headers)
        headers["content-length"] = str(len(new_content))

        response = None
        for attempt in range(len(self._keys)):
            key_index = (self._current_index + attempt) % len(self._keys)
            headers["authorization"] = f"Bearer {self._keys[key_index]}"
            req = httpx.Request(
                method=request.method,
                url=request.url,
                headers=headers,
                content=new_content,
            )
            response = await self._inner.handle_async_request(req)
            if response.status_code != 429:
                if attempt > 0:
                    async with self._lock:
                        self._current_index = key_index
                    print(f"[Key Rotation] Switched to key #{key_index + 1} after rate limit.")
                return response

        # All keys exhausted — advance index for next request and return last response
        async with self._lock:
            self._current_index = (self._current_index + 1) % len(self._keys)
        print("[Key Rotation] All keys rate limited. Will retry on next request.")
        return response

    async def aclose(self):
        await self._inner.aclose()


def _load_api_keys() -> list[str]:
    """Read GITHUB_TOKEN_1, GITHUB_TOKEN_2, ... from env.
    Falls back to GITHUB_TOKEN if numbered keys are not set."""
    keys = []
    for i in range(1, 11):
        key = os.getenv(f"GITHUB_TOKEN_{i}")
        if key:
            keys.append(key)
    if not keys:
        single = os.getenv("GITHUB_TOKEN")
        if single:
            keys.append(single)
    return keys


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
            db.add(User(
                username="admin",
                email="admin@retailsystem.com",
                hashed_password=hash_password("admin123"),
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
    api_keys = _load_api_keys()
    print(f"[Startup] Loaded {len(api_keys)} API key(s) for rotation.")
    client = AsyncOpenAI(
        base_url=os.getenv("GITHUB_BASE_URL", "https://models.inference.ai.azure.com"),
        api_key=api_keys[0] if api_keys else "no-key",
        http_client=httpx.AsyncClient(
            transport=_RotatingKeyTransport(AI_MODEL, api_keys)
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
