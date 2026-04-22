from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .database import create_tables
from .auth.auth_router import router as auth_router
from .api.inventory_router import router as inventory_router
from .api.accounting_router import router as accounting_router
from .api.dashboard_router import router as dashboard_router
from .api.agent_router import router as agent_router

load_dotenv()

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


@app.on_event("startup")
def startup():
    create_tables()


app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(inventory_router)
app.include_router(accounting_router)
app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "retail-agent-system"}
