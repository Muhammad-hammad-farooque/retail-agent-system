# Intelligent Retail Store Automation and Insight Generation System
### Powered by Agentic AI

An intelligent retail store automation platform powered by a multi-agent AI system. The backend is built with FastAPI and PostgreSQL; the frontend with Next.js 14 and Tailwind CSS. AI agents are orchestrated using the OpenAI Agents SDK (openai-agents) via GitHub Models (GPT-4o-mini).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, PostgreSQL |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| AI / Agents | OpenAI Agents SDK (`openai-agents`), GitHub Models (`gpt-4o-mini`) |
| Auth | JWT (HS256), bcrypt |
| Email | SMTP via Gmail (smtplib) |
| Database ORM | SQLAlchemy with Alembic-compatible models |

---

## Project Structure

```
retail-agent-system/
├── backend/
│   ├── agents/               # AI agents
│   │   ├── triage_agent.py       # Orchestrator — routes to sub-agents
│   │   ├── inventory_agent.py    # Stock, products, purchase orders
│   │   ├── accounting_agent.py   # Invoices, P&L, vendor purchases
│   │   ├── customer_service_agent.py
│   │   └── marketing_agent.py
│   ├── api/                  # FastAPI routers
│   │   ├── agent_router.py
│   │   ├── inventory_router.py
│   │   ├── accounting_router.py
│   │   ├── purchase_order_router.py
│   │   ├── customer_router.py
│   │   ├── complaint_router.py
│   │   ├── supplier_router.py
│   │   ├── marketing_router.py
│   │   ├── notification_router.py
│   │   └── dashboard_router.py
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   ├── tools/                # Agent function tools
│   │   ├── inventory_tools.py
│   │   ├── accounting_tools.py
│   │   ├── customer_tools.py
│   │   ├── marketing_tools.py
│   │   └── email_tools.py
│   ├── guardrails/
│   │   ├── input_guardrails.py
│   │   └── output_guardrails.py
│   ├── auth/                 # JWT auth
│   ├── rag/                  # FAQ / RAG pipeline
│   ├── database.py
│   └── main.py               # App entry point, AI client setup
├── frontend/
│   ├── app/
│   │   ├── dashboard/        # KPI dashboard + live alerts
│   │   ├── agent/            # AI chat interface
│   │   ├── inventory/        # Product list and stock management
│   │   ├── accounting/       # Sales invoices + vendor purchases (tabbed)
│   │   ├── purchase-orders/  # PO list with approve/reject/receive actions
│   │   ├── customers/        # Customer list and loyalty points
│   │   ├── complaints/       # Complaint tracker
│   │   ├── suppliers/        # Supplier management
│   │   └── login/
│   ├── components/
│   │   ├── Navbar.tsx
│   │   └── AlertBanner.tsx   # Live WebSocket low-stock alerts
│   └── lib/
│       └── api.ts            # Axios API client
├── scripts/
│   ├── seed_data.py          # Seed products, customers, suppliers, sales
│   └── update_dates.py       # One-time migration: update all record dates to 2026 range
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
├── .env
└── requirements.txt
```

---

## Multi-Agent Architecture

```
User Message
     │
     ▼
Triage Agent  ──── input guardrails (content policy, retail scope)
     │
     ├──▶ Inventory Agent        (stock, products, purchase orders)
     ├──▶ Accounting Agent       (invoices, P&L, vendor purchase expenses)
     ├──▶ Customer Service Agent (complaints, loyalty, order history)
     └──▶ Marketing Agent        (promotions, discounts, sales trends)
               │
               ▼
         output guardrails  (budget limit check, negative quantity, PII masking)
               │
               ▼
         Final Response
```

Routing is done via the OpenAI Agents SDK `handoff()` mechanism. The Triage Agent never answers domain questions itself — it always delegates.

---

## Agents and Their Tools

### Inventory Agent
| Tool | Description |
|------|-------------|
| `search_product_by_name` | Search products by partial name |
| `check_stock` | Check stock level of a product |
| `update_stock` | Add or deduct stock units |
| `get_low_stock_alerts` | List products at or below reorder level |
| `add_product` | Add a new product to inventory |
| `update_price` | Update a product's base selling price (supplier cost change, market adjustment) |
| `sell_product` | Process a customer sale: deducts stock, creates paid invoice + sale record atomically |
| `create_purchase_order` | Create a PO; auto-approves and emails vendor if under Rs.100,000 |
| `receive_purchase_order` | Mark a PO as received and update stock in one step |
| `list_products_by_category` | List all products in a category |

### Accounting Agent
| Tool | Description |
|------|-------------|
| `get_invoice` | Retrieve a specific sales invoice |
| `get_financial_summary` | Revenue summary — pass `days=7` for relative periods or `start_date`/`end_date` for specific ranges |
| `calculate_profit_loss` | P&L report for past N days |
| `get_revenue_by_category` | Revenue and profit by product category |
| `get_top_selling_products` | Top sellers by revenue |
| `get_purchase_expenses` | Vendor purchase history and total spent |
| `approve_purchase_order` | Approve a pending PO (emails vendor automatically) |
| `reject_purchase_order` | Reject a PO with a reason |

### Customer Service Agent
| Tool | Description |
|------|-------------|
| `search_customer_by_name` | Search customers by partial name |
| `get_customer_info` | Full customer profile — loyalty points, total spent, contact |
| `get_order_history` | Recent invoice history for a customer |
| `update_loyalty_points` | Add or deduct loyalty points |
| `handle_complaint` | Log a customer complaint, assign a reference number, create notification |
| `search_faq` | Semantic search over the store FAQ knowledge base (RAG pipeline) |

Resolving a complaint via the `/complaints` page automatically sends a resolution email to the customer.

### Marketing Agent
| Tool | Description |
|------|-------------|
| `get_sales_trends` | Daily sales trends for past N days, optionally filtered by category |
| `get_top_products` | Top performing products by revenue for marketing focus |
| `create_promotion` | Create a time-bound discount for a single product |
| `create_category_promotion` | Apply a discount to all products in a category at once (e.g. "30% off all Clothing") |
| `generate_marketing_report` | Full report: revenue trends, top category, low-margin products |
| `send_promotional_email` | Send a promotional email to all customers (or filtered by loyalty points) via Gmail SMTP |
| `send_promotional_sms` | Send a promotional SMS to all customers (or filtered by loyalty points) via Twilio |

**Discount rules:** 1–30% proceeds immediately. 31–70% requires one-time manager confirmation. Above 70% is hard-blocked to prevent below-cost pricing. Price update (`update_price`) belongs to Inventory Agent — Marketing only handles temporary promotional discounts.

---

## Purchase Order Workflow

```
Agent creates PO
       │
       ├── total ≤ Rs.100,000 ──▶ Auto-approved ──▶ Vendor email sent ──▶ Status: sent_to_vendor
       │
       └── total > Rs.100,000 ──▶ Status: pending ──▶ Manager approves via Purchase Orders page
                                                              │
                                                              ▼
                                                    Vendor email sent ──▶ Status: sent_to_vendor
                                                              │
                                                              ▼
                                               Agent confirms receipt ──▶ Status: received
                                                    (stock updated)
```

**Security rule:** `receive_purchase_order` only accepts POs with status `sent_to_vendor`. The agent is also instructed never to create a PO and immediately receive it in the same conversation turn.

---

## Guardrails

### Input Guardrails
- Blocks off-topic queries (non-retail content)
- Blocks harmful or abusive language

### Output Guardrails
- **Budget limit check:** Flags any response mentioning a monetary amount > Rs.100,000 in an order context. Requires `Rs.` or `PKR` prefix to avoid false matches on timestamps.
- **Negative quantity check:** Blocks responses containing negative stock values.
- **PII masking:** Automatically masks Pakistani phone numbers, physical addresses, and partial emails before returning responses.

---

## API Endpoints

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Get JWT token |
| POST | `/auth/register` | Register new user |
| GET | `/auth/me` | Current user info |

### Agent
| Method | Path | Description |
|--------|------|-------------|
| POST | `/agent/task` | Run a query through the agent system |
| GET | `/chat/history` | Fetch all chat messages for the current user |
| POST | `/chat/messages` | Save a single chat message (role + content) |

### Inventory
| Method | Path | Description |
|--------|------|-------------|
| GET | `/inventory/products` | List products |
| POST | `/inventory/products` | Add product |
| PATCH | `/inventory/products/{id}` | Update product |
| GET | `/inventory/critical` | Products below reorder level |

### Purchase Orders
| Method | Path | Description |
|--------|------|-------------|
| GET | `/purchase-orders` | List all POs (filterable by status) |
| GET | `/purchase-orders/summary` | Total spent, order counts, this month |
| GET | `/purchase-orders/{id}` | Get a single PO |
| PATCH | `/purchase-orders/{id}/status` | Update PO status (approve/reject/receive) |

### Accounting
| Method | Path | Description |
|--------|------|-------------|
| GET | `/accounting/invoices` | List invoices |
| GET | `/accounting/summary` | Revenue, invoice counts, tax |

### Dashboard
| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard/kpis` | KPI metrics (total products, revenue, customers, invoices) |
| GET | `/dashboard/sales-today` | Today's invoice count and revenue |
| GET | `/dashboard/daily-revenue?days=7` | Revenue per day for last N days (7, 14, or 30) |
| GET | `/dashboard/recent-transactions?payment_method=Cash` | Last 10 paid invoices, filterable by payment method |
| GET | `/dashboard/category-revenue` | Revenue and profit grouped by product category |
| GET | `/dashboard/top-products?period=week` | Top selling products by revenue (today / week / month) |
| GET | `/dashboard/profit-summary` | Today's profit, avg order value, payment method breakdown |
| WS | `/ws/alerts` | WebSocket — live low-stock alerts every 30s |

### Other
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customers` | Customer list |
| GET | `/complaints` | Complaint list |
| GET | `/suppliers` | Supplier list |
| GET | `/notifications` | Notification list |
| PATCH | `/notifications/mark-all-read` | Mark all notifications read |

---

## Frontend Pages

| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/dashboard` | KPI cards, revenue chart, live low-stock alerts |
| Sales | `/sales` | Live sales dashboard — 6 KPI cards, daily revenue chart (7/14/30 day), payment method pie, category revenue, top products by period, transactions table with payment filter. Silent background refresh every 30s. |
| AI Agent | `/agent` | Chat interface to all agents — history persists across navigation and refresh |
| Inventory | `/inventory` | Product list, stock levels, low-stock filter |
| Accounting | `/accounting` | **Sales tab** (invoices, revenue summary) + **Purchases tab** (vendor purchase records, total spent) |
| Purchase Orders | `/purchase-orders` | Full PO list with status filters, approve/reject/mark-received actions, auto-refreshes every 30s |
| Customers | `/customers` | Customer list and loyalty points |
| Complaints | `/complaints` | Complaint tracker with status updates |
| Suppliers | `/suppliers` | Supplier management (add, edit, delete) |

---

## Database Tables

| # | Table | Purpose |
|---|-------|---------|
| 1 | `users` | Authentication and role-based access |
| 2 | `products` | Inventory management |
| 3 | `customers` | Customer profiles and loyalty points |
| 4 | `invoices` | Billing and payments (sales) |
| 5 | `invoice_items` | Per-product invoice line items |
| 6 | `sales` | Revenue and profit tracking |
| 7 | `complaints` | Customer complaint history |
| 8 | `purchase_orders` | Vendor restock orders |
| 9 | `suppliers` | Supplier contacts and emails |
| 10 | `promotions` | Active discount promotions |
| 11 | `notifications` | System event log |
| 12 | `chat_messages` | Persisted AI agent chat history per user |

---

## Environment Variables

Create a `.env` file inside the `retail-agent-system/` directory:

```env
# Database
DATABASE_URL=postgresql://postgres:PASSWORD@localhost/retail_db

# Email (Gmail SMTP)
SMTP_EMAIL=your@gmail.com
SMTP_PASSWORD=your_app_password

# JWT
JWT_SECRET=your_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# GitHub Models API (GPT-4o-mini)
# Add up to 10 keys — system rotates automatically on rate limit
GITHUB_TOKEN_1=ghp_...
GITHUB_TOKEN_2=ghp_...
GITHUB_TOKEN_3=ghp_...
GITHUB_BASE_URL=https://models.inference.ai.azure.com

# Twilio SMS (for Marketing Agent SMS campaigns)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
```

To get a GitHub Models API key: GitHub → Settings → Developer settings → Personal access tokens → Generate new token (classic). Free tier includes GPT-4o-mini access.

---

## Setup and Running

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL

### Backend

```bash
cd retail-agent-system

# Install dependencies
pip install -r requirements.txt

# Create the database
createdb retail_db

# Start the backend
uvicorn backend.main:app --reload
```

Backend runs at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd retail-agent-system/frontend

npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run evaluation framework
python -m evaluation.run_eval
```

---

## Build Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | PostgreSQL schema + seed data | Done |
| 2 | FastAPI backend + JWT auth | Done |
| 3 | All 4 agents with tools | Done |
| 4 | Guardrails (input + output + PII masking) | Done |
| 5 | RAG pipeline (Customer Service FAQ) | Done |
| 6 | Evaluation framework + tests | Done |
| 7 | Next.js dashboard + WebSocket alerts | Done |
| 8 | Purchase Orders + Supplier management | Done |
| 9 | Accounting Purchases tab + vendor expense tracking | Done |
| 10 | AI Agent chat history persistence (PostgreSQL) | Done |
| 11 | Sales Dashboard (KPIs, charts, filters, silent refresh) | Done |
| 12 | Email + SMS marketing tools for Marketing Agent | Done |
| 13 | Docker Compose + deployment | Pending |

---

## Key Design Decisions

- **API key rotation:** A custom `httpx.AsyncBaseTransport` (`_RotatingKeyTransport`) intercepts all chat/completions requests, forces the model name, and automatically cycles through up to 10 GitHub tokens when a 429 rate limit is hit.
- **Auto-approval threshold:** Purchase orders under Rs.100,000 are auto-approved by the agent and a vendor email is sent immediately. Orders over Rs.100,000 stay pending for manager approval via the UI.
- **Duplicate PO prevention:** `create_purchase_order` checks for an existing open PO for the same product on the same day before creating a new one.
- **Strict receive validation:** `receive_purchase_order` only accepts POs with status `sent_to_vendor`. The agent is also instructed never to create and receive a PO in the same conversation turn.
- **Vendor purchase accounting:** The Accounting page has a dedicated Purchases tab showing all received POs as expense records with a monthly summary. The Accounting Agent has a `get_purchase_expenses` tool to answer purchase-related financial questions.
- **Persistent chat history:** Every user and assistant message is saved to the `chat_messages` table immediately. On page load, the AI Agent page fetches the full conversation history from the database — history survives navigation, refresh, and device switches. Error messages (guardrail blocks, network failures) are intentionally not persisted.
- **Timezone-aware datetimes:** All datetime comparisons use `datetime.now(timezone.utc)` throughout the backend to correctly compare against PostgreSQL `timestamptz` columns.
- **Atomic sell_product tool:** The `sell_product` agent tool deducts stock and creates the Invoice, InvoiceItem, and Sale records in a single database transaction — ensuring sales always appear in Accounting and never leave orphaned stock changes.
- **Silent background refresh:** The Sales Dashboard uses a two-state loading model — `loading` (skeletons, first mount only) and `syncing` (background indicator only). After the initial load, data refreshes every 30s in the background without blanking the page; a small animated dot in the header signals the sync.
- **Email and SMS marketing:** The Marketing Agent can send promotional emails to customers via Gmail SMTP and promotional SMS via Twilio. Both tools accept an optional `min_loyalty_points` filter; defaulting to 0 sends to all customers.
- **Agent date awareness:** GPT-4o-mini has no knowledge of the current date. Every query is prepended with `[System: Today's date is <weekday, DD Month YYYY>]` in `agent_router.py` before being passed to the Triage Agent — ensuring date-relative queries ("last 7 days", "this month") resolve correctly.
- **Financial summary `days` parameter:** `get_financial_summary` accepts a `days` integer for relative lookups (e.g. `days=7`) in addition to explicit `start_date`/`end_date` strings. Using `days` avoids the need for the agent to construct date strings and eliminates timezone parsing bugs.
- **Category bulk promotions:** `create_category_promotion` takes a category name and applies a discount to all active products in that category in one call — the agent never needs individual product IDs. It automatically caps any product's discount to avoid below-cost pricing and reports which products were included.
- **Price update ownership:** `update_price` belongs to the Inventory Agent, not Marketing. Changing a product's base selling price is a permanent supplier-cost or market-rate adjustment. Marketing Agent handles only temporary promotional discounts via `create_promotion` and `create_category_promotion`.
- **PII masking precision:** The `ADDRESS_PATTERN` regex uses `\b` word boundaries and requires an explicit dot on `St.` to prevent false positives. Generic words like `Flat` and `Phase` were removed from the pattern after they triggered false matches on retail phrases ("Flat Discount", "Phase 2 promotion").
- **Consistent date format:** All date displays across the frontend (Accounting, Purchase Orders, Complaints, Sales) use `toLocaleDateString('en-GB')` to enforce dd/mm/yyyy format regardless of the user's browser locale. Chart axis labels use `%d/%m` strftime format on the backend.
- **Historical data migration:** `scripts/update_dates.py` is a one-time migration that back-fills all existing records (invoices, sales, purchase orders, complaints, notifications, chat messages, promotions) with realistic random timestamps from 2026-01-01 to today. Distribution is weighted toward weekdays and business hours to simulate real store traffic.
