# Intelligent Retail Store Automation and Insight Generation System
### Powered by Agentic AI

A production-ready multi-agent AI system for retail store management built with OpenAI Agents SDK, FastAPI, PostgreSQL, ChromaDB, and Next.js.

---

## Project Structure

```
retail-agent-system/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── database.py                # SQLAlchemy engine + session
│   ├── agents/
│   │   ├── triage_agent.py        # Main orchestrator
│   │   ├── inventory_agent.py
│   │   ├── accounting_agent.py
│   │   ├── customer_service_agent.py
│   │   └── marketing_agent.py
│   ├── tools/
│   │   ├── inventory_tools.py
│   │   ├── accounting_tools.py
│   │   ├── customer_tools.py
│   │   └── marketing_tools.py
│   ├── guardrails/
│   │   ├── input_guardrails.py
│   │   └── output_guardrails.py
│   ├── models/
│   │   ├── product.py
│   │   ├── invoice.py
│   │   ├── customer.py
│   │   ├── sale.py
│   │   ├── user.py
│   │   ├── complaint.py
│   │   ├── purchase_order.py
│   │   ├── promotion.py
│   │   └── notification.py
│   ├── rag/
│   │   ├── pipeline.py            # ChromaDB RAG pipeline
│   │   └── faq_documents.py       # 28 FAQ Q&A pairs
│   ├── auth/
│   │   ├── jwt_handler.py
│   │   └── auth_router.py
│   ├── api/
│   │   ├── agent_router.py
│   │   ├── inventory_router.py
│   │   ├── accounting_router.py
│   │   ├── dashboard_router.py
│   │   ├── customer_router.py
│   │   ├── complaint_router.py
│   │   ├── purchase_order_router.py
│   │   ├── marketing_router.py
│   │   └── notification_router.py
│   └── schemas/
│       ├── auth.py
│       ├── product.py
│       ├── invoice.py
│       └── agent.py
├── frontend/                      # Next.js 14 dashboard
│   ├── app/
│   │   ├── dashboard/page.tsx     # KPI cards + WebSocket alerts
│   │   ├── inventory/page.tsx     # Product list + critical stock
│   │   ├── accounting/page.tsx    # Invoices + financial summary
│   │   ├── agent/page.tsx         # AI agent chat interface
│   │   └── login/page.tsx         # JWT login
│   ├── components/
│   │   ├── Navbar.tsx
│   │   ├── KpiCard.tsx
│   │   ├── AlertBanner.tsx        # Real-time WebSocket alerts
│   │   ├── AgentChat.tsx
│   │   └── ProductTable.tsx
│   ├── lib/api.ts                 # Axios API client
│   └── context/AuthContext.tsx    # JWT auth state
├── scripts/
│   ├── seed_data.py               # Seed 50 products, 100 customers, 6 months sales
│   └── ingest_faq.py              # Embed FAQ docs into ChromaDB
├── tests/
│   ├── conftest.py
│   ├── test_guardrails.py
│   ├── test_tools.py
│   ├── test_api.py
│   └── test_rag.py
├── evaluation/
│   ├── evaluator.py
│   ├── test_cases.py
│   └── run_eval.py
├── chroma_db/                     # ChromaDB persistent store
├── .env
├── requirements.txt
└── pytest.ini
```

---

## Agents

| Agent | Role | Tools |
|-------|------|-------|
| **Triage Agent** | Orchestrator — routes queries to specialist agents | Handoffs |
| **Inventory Agent** | Stock management, reorder alerts, purchase orders | 6 tools |
| **Accounting Agent** | Invoices, financial summaries, profit & loss | 5 tools |
| **Customer Service Agent** | Customer info, complaints, loyalty points, FAQ (RAG) | 6 tools |
| **Marketing Agent** | Promotions, pricing, sales trends, reports | 5 tools |

### Agent Handoff Flow
```
User Query → Triage Agent
  ├── inventory keywords  → Inventory Agent
  ├── finance keywords    → Accounting Agent
  ├── customer keywords   → Customer Service Agent (RAG)
  └── marketing keywords  → Marketing Agent
```

---

## Guardrails

**Input Guardrails** (before agent runs):
1. **Scope check** — blocks non-retail queries
2. **Harmful request check** — blocks hacking, fraud, data manipulation
3. **Language check** — blocks abusive language (English + Urdu)

**Output Guardrails** (before response is sent):
1. **Budget limit** — orders > Rs.100,000 flagged for manager approval
2. **Negative quantity** — invalid stock values blocked
3. **PII masking** — phone, address, email auto-masked

---

## RAG Pipeline (Customer Service Agent)

- **28 FAQ documents** covering: returns, payments, delivery, loyalty, warranty, complaints, discounts
- Embedded using OpenAI `text-embedding-3-small`
- Stored in **ChromaDB** (persistent, cosine similarity)
- Top-3 relevant chunks injected into agent context on every query

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login and get JWT token |
| GET | `/auth/me` | Current user info |
| POST | `/agent/task` | Main agent entry point |
| GET | `/inventory/products` | List all products |
| GET | `/inventory/critical` | Low stock items |
| POST | `/inventory/products` | Add new product |
| PATCH | `/inventory/products/{id}` | Update product |
| GET | `/accounting/invoices` | List invoices |
| GET | `/accounting/summary` | Financial summary |
| GET | `/customers` | List all customers |
| GET | `/customers/{id}` | Get customer by ID |
| PATCH | `/customers/{id}/loyalty` | Update loyalty points |
| GET | `/complaints` | List all complaints |
| PATCH | `/complaints/{id}/status` | Update complaint status |
| GET | `/purchase-orders` | List all purchase orders |
| PATCH | `/purchase-orders/{id}/status` | Approve/reject PO |
| GET | `/marketing/promotions` | List promotions |
| GET | `/marketing/trends` | Sales trends |
| GET | `/marketing/top-products` | Top products by revenue |
| GET | `/notifications` | List all notifications |
| GET | `/notifications/unread-count` | Unread count |
| PATCH | `/notifications/mark-all-read` | Mark all as read |
| GET | `/dashboard/kpis` | Dashboard KPI data |
| WS | `/ws/alerts` | Real-time low stock alerts |

---

## Database Tables

| # | Table | Purpose |
|---|-------|---------|
| 1 | `users` | Authentication and role-based access |
| 2 | `products` | Inventory management |
| 3 | `customers` | Customer profiles and loyalty points |
| 4 | `invoices` | Billing and payments |
| 5 | `invoice_items` | Per-product invoice details |
| 6 | `sales` | Revenue and profit tracking |
| 7 | `complaints` | Customer complaint history |
| 8 | `purchase_orders` | Vendor restock orders |
| 9 | `promotions` | Active discount promotions |
| 10 | `notifications` | System event log |

---

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, PostgreSQL
- **Agents**: OpenAI Agents SDK, GPT-4o
- **RAG**: ChromaDB, OpenAI Embeddings
- **Auth**: JWT (python-jose, bcrypt)
- **Testing**: pytest, pytest-asyncio
- **Frontend**: Next.js 14, Tailwind CSS, Axios, WebSocket
- **Deployment**: Docker Compose (Phase 8)

---

## Getting Started

### 1. Install Dependencies
```bash
cd retail-agent-system
pip install -r requirements.txt
pip install "pydantic[email]"
```

### 2. Configure Environment
```bash
# Edit .env with your credentials
OPENAI_API_KEY=sk-your-key
DATABASE_URL=postgresql://user:pass@localhost/retaildb
JWT_SECRET=your-secret-key
```

### 3. Setup Database
```bash
# Create PostgreSQL database
psql -U postgres -c "CREATE DATABASE retaildb;"

# Seed synthetic data
python scripts/seed_data.py
```

### 4. Ingest FAQ into ChromaDB
```bash
python scripts/ingest_faq.py
```

### 5. Run the Server
```bash
uvicorn backend.main:app --reload
# Swagger docs: http://localhost:8000/docs
```

### 6. Run the Frontend
```bash
cd frontend
npm install
npm run dev
# Dashboard: http://localhost:3000
```

**Dashboard pages:**
- `/dashboard` — KPI cards + real-time low-stock alerts (WebSocket)
- `/inventory` — Product list with category filter and pagination
- `/accounting` — Invoices with status filter + financial summary
- `/agent` — AI chat interface (routes to all 5 agents)

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run evaluation framework
python -m evaluation.run_eval
```

**Test Results:** 40/40 passed | Evaluation: 21/21 — 100%

---

## Build Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | PostgreSQL schema + seed data | ✅ Done |
| 2 | FastAPI backend + JWT auth | ✅ Done |
| 3 | All 5 agents with tools | ✅ Done |
| 4 | Guardrails (input + output) | ✅ Done |
| 5 | RAG pipeline with ChromaDB | ✅ Done |
| 6 | Evaluation framework + tests | ✅ Done |
| 7 | Next.js dashboard + WebSocket | ✅ Done |
| 8 | Docker Compose + deployment | 🔄 Pending |

---

## Environment Variables

```env
OPENAI_API_KEY=
DATABASE_URL=postgresql://user:pass@localhost/retaildb
REDIS_URL=redis://localhost:6379
CHROMA_PERSIST_DIR=./chroma_db
SMTP_EMAIL=
SMTP_PASSWORD=
JWT_SECRET=
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
```
