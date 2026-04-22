# Retail Agent System — Build & Dev Skill

You are working on the **Intelligent Retail Store Automation and Insight Generation System** — a multi-agent AI system for retail management.

## Project Location
`D:/my project/agentic-project/retail-agent-system/`

## Architecture Summary
- **5 Agents**: Triage (orchestrator) → Inventory, Accounting, Customer Service, Marketing
- **Framework**: OpenAI Agents SDK (with handoffs)
- **Backend**: FastAPI + PostgreSQL + Redis + ChromaDB
- **Auth**: JWT
- **Frontend**: Next.js dashboard with WebSocket alerts
- **Guardrails**: Input (scope/harm/language) + Output (budget/quantity/PII masking)

## Build Phases
| Phase | Description | Status |
|-------|-------------|--------|
| 1 | PostgreSQL schema + seed data | pending |
| 2 | FastAPI backend + JWT auth | pending |
| 3 | All 5 agents with tools | pending |
| 4 | Guardrails (input + output) | pending |
| 5 | RAG pipeline with ChromaDB | pending |
| 6 | Evaluation framework + tests | pending |
| 7 | Next.js dashboard + WebSocket | pending |
| 8 | Docker Compose + deployment | pending |

## Agent Handoff Flow
```
User Query → Triage Agent
  ├── inventory keywords → Inventory Agent
  ├── sales/finance keywords → Accounting Agent
  ├── customer/complaint keywords → Customer Service Agent (RAG)
  └── marketing keywords → Marketing Agent
```

## Key Conventions
- Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic migrations
- OpenAI Agents SDK for agent orchestration
- All money values in PKR (Pakistani Rupees)
- Sensitive customer data (phone/address) must be masked in output
- Orders > Rs.100,000 require manager approval flag
- Always check guardrails before agent runs AND before response is sent

## When asked to continue building:
1. Check current phase status
2. Read existing code before writing new files
3. Maintain consistent naming across agents and tools
4. Run `uvicorn backend.main:app --reload` from retail-agent-system/ to test
