<div align="center">

 <img src="./assets/ai-employee.gif" alt="AI Employee Demo" width="850">
 
# VoxAI — AI Business Employee

**An autonomous AI worker that answers every call, qualifies every lead, books appointments, and updates your CRM — without a single human touch.**

VoxAI plugs a phone number and a WhatsApp line into an intelligent agent that understands natural language, acts on business data, and hands off to your team only when a human is genuinely needed.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2015-black?logo=next.js)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/AI-LangGraph-4B6BFB?logo=langchain)](https://langchain-ai.github.io/langgraph/)
[![Gemini](https://img.shields.io/badge/LLM-Gemini%201.5-4285F4?logo=google)](https://ai.google.dev)
[![Twilio](https://img.shields.io/badge/Telephony-Twilio-F22F46?logo=twilio&logoColor=white)](https://twilio.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

</div>

---

## What Is VoxAI?

Most businesses lose leads because their phone goes unanswered at 9 PM, their WhatsApp replies take 4 hours, and their sales team forgets to update the CRM after every call.

VoxAI is a software-deployed AI employee that takes ownership of your inbound communication channel. When a customer calls or messages, the AI employee answers, understands what they want, looks up relevant business information, creates a lead, updates HubSpot, books a calendar appointment if needed, sends a WhatsApp confirmation, and — only if the situation demands it — transfers the call live to a human agent with a full conversation brief already in hand.

**Who it is for:** Real estate agencies, clinics, automotive dealers, and any service business that handles inbound customer enquiries at scale and cannot afford to miss a single lead.

---

## The Problem

| Traditional Workflow | What It Costs |
|---|---|
| Customer calls → rings out → missed | Lead lost forever |
| Receptionist takes notes → forgets to update CRM | Pipeline blind spots |
| Sales team manually qualifies via phone | 3–4 hours of low-value work daily |
| WhatsApp handled by individuals | Inconsistent, slow, no tracking |
| Follow-up depends on individual memory | Deals fall through |

The bottleneck is not your team's skill — it is the volume of repetitive, structured communication that happens before a real conversation is needed.

---

## The Solution

VoxAI replaces that bottleneck with an autonomous agent that runs 24/7.

```
Customer (Phone / WhatsApp)
        │
        ▼
  AI Receptionist ──► Load customer memory + RAG business context
        │
        ▼
  Intent Classifier ──► property_inquiry | appointment_request | support | complaint
        │
   ┌────┼────┐
   ▼    ▼    ▼
Lead  Booking  Support      Human Handoff (escalation)
Agent  Agent   Agent             │
   └────┼────┘                   │
        ▼                        ▼
   Tool Calls              Live dial + team
  (CRM, Calendar,          WhatsApp alert +
   WhatsApp, RAG)          conversation brief
        │
        ▼
   Responder ──► Natural voice / text reply to customer
        │
        ▼
   Database ──► Conversation logged, lead scored, memory updated
```

---

## Core Features

### AI Orchestrator (LangGraph)
A stateful multi-agent graph built on LangGraph. Every customer message passes through a `receptionist → intent_classifier → [lead|booking|support|human_handoff] → responder` pipeline. Each node uses real tool calls and persists `AgentRun` + `ToolCall` records to the database for full observability.

### Voice AI (Twilio)
Inbound calls are answered by the AI using Amazon Polly (Aditi, Indian English). Speech is transcribed, processed by the orchestrator, and the response is read back — looping until the call ends or escalates. Call duration, recordings, and status are persisted on completion.

### WhatsApp AI
Inbound WhatsApp messages hit a Twilio webhook, route through the same AI orchestrator, and receive a text reply within seconds. For leads, property details are sent as rich WhatsApp messages.

### Lead Management + Scoring
Every enquiry automatically creates a `Lead` record scored COLD / WARM / HOT based on extracted budget (₹20L threshold for WARM, ₹50L for HOT). Hot leads trigger an immediate WhatsApp alert to your sales team.

### HubSpot CRM Sync
Leads are synced to HubSpot on creation. Stage updates (NEW → QUALIFIED → PROPOSAL → WON) propagate back to CRM in real time. A `MockCRM` is provided for development without credentials.

### Calendar Booking
The booking agent calls Google Calendar to find available slots and creates a confirmed appointment. The customer receives a WhatsApp confirmation with the date/time and (if enabled) a Google Meet link. The lead stage advances to `qualified` automatically.

### RAG Knowledge Base
Business owners upload documents (PDF or text). VoxAI chunks them, embeds them with `text-embedding-004`, and stores vectors in pgvector. Every customer query triggers a semantic search so the AI always answers from your actual business data — not hallucinations.

### Customer Memory
Preferences extracted from every conversation (location, budget, property type, bedrooms) are persisted to the `Customer.preferences` JSON column. The next time the same number calls, the AI greets them by name and knows their history.

### Human Escalation
When the AI detects a complaint, an angry customer, or an explicit request for a human, it:
1. Creates a `HumanHandoff` DB record with a conversation summary
2. Sends a WhatsApp alert to the team with the customer brief
3. Live-dials the escalation phone via Twilio `<Dial>`
4. If no answer, leaves a callback promise and closes gracefully

### Dashboard (Next.js)
Real-time dashboard showing: live calls, AI handle rate, lead pipeline by stage, agent run logs, call history, knowledge base management, integrations, and settings — all pulling from the live FastAPI backend.

### Email OTP Auth
Registration and login use Brevo-powered OTP email verification (2FA). JWT access + refresh tokens with bcrypt+SHA-256 password hashing.

---

## End-to-End Business Workflow

```mermaid
sequenceDiagram
    participant C as Customer
    participant T as Twilio
    participant W as Webhook Handler
    participant O as AI Orchestrator
    participant L as LLM (Gemini)
    participant DB as Database
    participant CRM as HubSpot CRM
    participant CAL as Google Calendar
    participant WA as WhatsApp

    C->>T: Calls business number
    T->>W: POST /webhooks/twilio/voice/inbound
    W->>DB: Create Conversation + Call record
    W->>T: TwiML: greet + Gather(speech)
    C->>T: Speaks ("I want a 3BHK in Pune under 80 lakhs")
    T->>W: POST /webhooks/twilio/voice/process (SpeechResult)
    W->>DB: Save customer message
    W->>O: process_customer_input()
    O->>DB: Load customer memory
    O->>DB: RAG search (property context)
    O->>L: Classify intent + extract entities
    L-->>O: intent=property_inquiry, budget=8000000, location=Pune, bedrooms=3
    O->>DB: get_or_create_customer(phone)
    O->>DB: create_lead(score=HOT)
    O->>CRM: Sync lead to HubSpot
    O->>WA: Send property cards to customer
    O->>L: Generate natural voice response
    L-->>O: "Great, I found 4 properties in Pune within your budget..."
    O->>DB: Save AgentRun + ToolCall records
    W->>T: TwiML: say(response) + Gather(next turn)
    T->>C: AI speaks response
    C->>T: "Can I visit tomorrow at 11 AM?"
    T->>W: POST /webhooks/twilio/voice/process
    W->>O: process_customer_input()
    O->>CAL: get_available_slots()
    O->>CAL: create_appointment(tomorrow 11AM)
    O->>CRM: update_lead_stage(qualified)
    O->>WA: Send appointment confirmation
    W->>T: TwiML: "Your visit is confirmed for tomorrow at 11 AM..."
    T->>C: AI confirms booking + hangs up
    T->>W: POST /webhooks/twilio/voice/status (completed)
    W->>DB: Finalise Call record + close Conversation
```

---

## System Architecture

```mermaid
graph TD
    subgraph Channels["Customer Channels"]
        PHONE[📞 Inbound Phone Call]
        WA_IN[💬 WhatsApp Message]
    end

    subgraph Twilio["Twilio"]
        TW_VOICE[Voice / TwiML]
        TW_WA[WhatsApp API]
    end

    subgraph Backend["FastAPI Backend  :8000"]
        WEBHOOK[Webhook Handler]
        AUTH[Auth API  /auth]
        BIZ[Business API  /businesses]
        LEADS_API[Leads API  /leads]
        CONV_API[Conversations API]
        KNOW_API[Knowledge API]
    end

    subgraph Agent["AI Orchestrator  LangGraph"]
        RECEP[Receptionist Node]
        IC[Intent Classifier]
        LA[Lead Agent]
        BA[Booking Agent]
        SA[Support Agent]
        HH[Human Handoff]
        RESP[Responder Node]
    end

    subgraph LLM["Google AI"]
        GEMINI_PRO[Gemini 1.5 Pro]
        GEMINI_FLASH[Gemini 1.5 Flash]
        EMBED[text-embedding-004]
    end

    subgraph Tools["Agent Tools"]
        CRM_TOOL[CRM Tools]
        CAL_TOOL[Calendar Tools]
        COMM_TOOL[Communication Tools]
        SEARCH_TOOL[Search / RAG Tools]
    end

    subgraph Storage["Storage"]
        SQLITE[(SQLite / Dev)]
        PG[(PostgreSQL + pgvector / Prod)]
        REDIS[(Redis  Rate Limiting)]
    end

    subgraph Integrations["External Integrations"]
        HUBSPOT[HubSpot CRM]
        GCAL[Google Calendar]
        BREVO[Brevo  Email OTP]
        WA_OUT[WhatsApp  Twilio]
    end

    subgraph Frontend["Next.js Dashboard  :3000"]
        DASH[Dashboard]
        SIGNUP[Auth / Signup]
        SETTINGS[Settings]
    end

    PHONE --> TW_VOICE --> WEBHOOK
    WA_IN --> TW_WA --> WEBHOOK
    WEBHOOK --> Agent
    RECEP --> IC --> LA & BA & SA & HH
    LA & BA & SA --> RESP
    IC --> GEMINI_FLASH
    RESP --> GEMINI_FLASH
    RECEP --> SEARCH_TOOL --> EMBED
    LA --> CRM_TOOL --> HUBSPOT
    BA --> CAL_TOOL --> GCAL
    LA & BA --> COMM_TOOL --> WA_OUT
    Agent --> Storage
    Backend --> Storage
    Frontend --> Backend
    AUTH --> BREVO
```

---

## AI Employee: How It Thinks

Each customer message triggers the following sequence inside the agent:

| Step | Node | What Happens |
|---|---|---|
| 1 | **Receptionist** | Loads customer memory from DB; runs RAG search against business knowledge base |
| 2 | **Intent Classifier** | Gemini Flash classifies intent and extracts entities (budget, location, bedrooms, datetime) as structured JSON |
| 3 | **Router** | Conditional edge routes to Lead / Booking / Support / Human Handoff node |
| 4 | **Specialist Agent** | Calls real tools — creates lead, books calendar slot, searches knowledge, or initiates escalation |
| 5 | **Responder** | Gemini Flash generates a warm, natural 1–3 sentence voice response with the context of all tool results |
| 6 | **Persistence** | `AgentRun` + `ToolCall` records saved; customer preferences updated; message stored |

### This Is Not a Chatbot

| Chatbot | VoxAI AI Employee |
|---|---|
| Answers questions | Takes actions |
| Stores nothing | Updates CRM, DB, Calendar |
| Stateless per session | Persistent customer memory across calls |
| No external tools | CRM sync, calendar booking, WhatsApp messaging |
| Rule-based routing | Semantic intent classification |
| No escalation logic | Structured handoff with conversation brief |

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Next.js 15, TypeScript | Business owner dashboard |
| Styling | Vanilla CSS, Lucide icons | UI components |
| Backend | FastAPI, Python 3.11+ | REST API + webhooks |
| AI Framework | LangGraph 0.2 | Agent orchestration graph |
| LLM | Gemini 1.5 Pro / Flash | Intent classification, response generation |
| Embeddings | Google text-embedding-004 | Semantic search / RAG |
| Vector Store | pgvector (PostgreSQL) | Knowledge base retrieval |
| ORM | SQLAlchemy 2.0 async | Database access |
| Database (dev) | SQLite + aiosqlite | Zero-config local development |
| Database (prod) | PostgreSQL + pgvector | Production storage |
| Cache / Rate Limit | Redis + ARQ | Per-caller rate limiting, background jobs |
| Telephony | Twilio Voice + TwiML | Inbound calls, speech recognition, TTS |
| Messaging | Twilio WhatsApp API | Customer messaging, notifications |
| CRM | HubSpot API v3 | Lead and contact management |
| Calendar | Google Calendar API | Appointment booking |
| Email | Brevo Transactional API | OTP emails for auth |
| Auth | JWT (python-jose), bcrypt | Stateless auth + OTP 2FA |
| PDF Ingestion | pypdf | Knowledge base document loading |

---

## Project Structure

```
Ai_Employe/
├── backend/
│   ├── main.py                        # FastAPI app, middleware, routers
│   ├── requirements.txt
│   ├── app/
│   │   ├── agents/
│   │   │   └── orchestrator/
│   │   │       └── graph.py           # LangGraph agent graph (the core brain)
│   │   ├── api/v1/
│   │   │   ├── auth/                  # Register, login, OTP verify, refresh
│   │   │   ├── businesses/            # Business profile CRUD
│   │   │   ├── leads/                 # Lead pipeline endpoints
│   │   │   ├── conversations/         # Conversation + message history
│   │   │   ├── knowledge/             # Document upload + RAG ingestion
│   │   │   ├── agents/                # AI agent configuration
│   │   │   ├── calls/                 # Call log endpoints
│   │   │   └── webhooks/              # Twilio voice + WhatsApp webhooks
│   │   ├── core/
│   │   │   ├── config.py              # Settings (pydantic-settings)
│   │   │   ├── logging.py             # Loguru setup
│   │   │   └── redis.py               # Redis client + rate limiting
│   │   ├── integrations/
│   │   │   ├── crm/hubspot.py         # HubSpot + MockCRM (provider-agnostic)
│   │   │   ├── calendar/google_calendar.py
│   │   │   └── whatsapp/twilio_whatsapp.py
│   │   ├── memory/                    # Customer memory, conversation history
│   │   ├── models/                    # SQLAlchemy ORM models
│   │   ├── rag/pipeline.py            # RAG: chunk, embed, pgvector search
│   │   ├── security/auth.py           # JWT, bcrypt, get_current_user
│   │   ├── services/
│   │   │   ├── email.py               # Brevo OTP email
│   │   │   └── otp.py                 # OTP create / verify
│   │   └── tools/
│   │       ├── crm_tools/             # Agent-callable CRM functions
│   │       ├── calendar_tools/        # Agent-callable calendar functions
│   │       ├── communication_tools/   # WhatsApp send helpers
│   │       └── search_tools/          # RAG + property search
│   └── database/session.py            # Async SQLAlchemy engine
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── auth/login/            # Login page (2FA OTP)
│   │   │   ├── auth/signup/           # 3-step signup
│   │   │   └── dashboard/            # Main dashboard
│   │   ├── components/dashboard/
│   │   │   ├── DashboardOverview.tsx  # KPIs, live calls, lead table
│   │   │   ├── LiveCalls.tsx
│   │   │   ├── LeadPipeline.tsx
│   │   │   ├── AgentLogs.tsx
│   │   │   ├── KnowledgeBase.tsx
│   │   │   ├── Integrations.tsx
│   │   │   └── Settings.tsx
│   │   └── lib/
│   │       ├── auth.tsx               # Auth context + OTP flow
│   │       └── api.ts                 # Backend API client
│   └── package.json
├── .env.example                       # All required variables documented
├── docker-compose.yml                 # PostgreSQL + Redis
├── LICENSE
└── README.md
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

> **No Docker required for basic development.** The backend defaults to SQLite so you can run without PostgreSQL.

### 1. Clone

```bash
git clone https://github.com/SurinderTech/Ai_Employe.git
cd Ai_Employe
```

### 2. Environment Variables

```bash
cp .env.example backend/.env
```

Edit `backend/.env`:

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | ✅ | Gemini LLM + embeddings API key |
| `BREVO_API_KEY` | ✅ | Email OTP delivery (Brevo transactional) |
| `BREVO_SENDER_EMAIL` | ✅ | Verified sender address in Brevo |
| `JWT_SECRET_KEY` | ✅ | Random string for JWT signing |
| `DATABASE_URL` | — | Defaults to `sqlite+aiosqlite:///./ai_employee_dev.db` |
| `TWILIO_ACCOUNT_SID` | Voice/WA | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Voice/WA | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | Voice | Twilio voice phone number |
| `TWILIO_WHATSAPP_NUMBER` | WhatsApp | Twilio WhatsApp sender |
| `ESCALATION_PHONE` | Escalation | Human agent phone for live call transfer |
| `HUBSPOT_ACCESS_TOKEN` | CRM | HubSpot private app token (MockCRM used if empty) |
| `GOOGLE_CALENDAR_CREDENTIALS_JSON` | Calendar | Google service account credentials |

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend (hot-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Dashboard: [http://localhost:3000](http://localhost:3000)

### 5. Twilio Webhooks (Local)

To test voice/WhatsApp locally, expose your backend using [ngrok](https://ngrok.com):

```bash
ngrok http 8000
```

In Twilio Console, set:
- **Voice webhook:** `https://<ngrok-url>/api/v1/webhooks/twilio/voice/inbound`
- **WhatsApp webhook:** `https://<ngrok-url>/api/v1/webhooks/twilio/whatsapp/inbound`

---

## Production Deployment

### Recommended Stack

| Component | Service |
|---|---|
| Frontend | Vercel |
| Backend | Render / Railway / EC2 |
| Database | Supabase (PostgreSQL + pgvector) |
| Redis | Redis Cloud / Upstash |
| Messaging | Twilio (production number) |

### Backend (Render)

```
Build command: pip install -r requirements.txt
Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Set all environment variables in the Render dashboard. Switch `DATABASE_URL` to your PostgreSQL connection string and `APP_ENV=production`.

### Frontend (Vercel)

```bash
cd frontend
vercel deploy
```

Set `NEXT_PUBLIC_API_URL=https://your-backend-url.com` in Vercel environment variables.

### Database with Docker (Local PostgreSQL + pgvector)

```bash
docker-compose up -d
```

Updates `DATABASE_URL` to:
```
postgresql+asyncpg://aiemployee:aiemployee_secret@localhost:5432/ai_employee_db
```

---

## Security

| Mechanism | Implementation |
|---|---|
| Password hashing | bcrypt (12 rounds) + SHA-256 pre-hash (handles >72 byte passwords) |
| Authentication | JWT Bearer tokens (access: 60 min, refresh: 30 days) |
| 2FA | Email OTP via Brevo, 5-minute expiry, single-use |
| Webhook validation | Twilio signature verification (bypassed in `DEBUG=True`) |
| Rate limiting | Per-caller Redis rate limit on inbound voice + WhatsApp |
| CORS | Explicit allowlist — no wildcard in production |
| Secrets | All credentials via environment variables, never committed |

---

## Observability

Every AI agent execution produces a complete audit trail:

- **`AgentRun`** — per-message record: input, intent, output, latency, status
- **`ToolCall`** — per-tool record: tool name, input args, output, status, latency_ms
- **`Conversation` / `Message`** — full conversation transcript per customer per session
- **`HumanHandoff`** — escalation record with conversation summary and recommended action
- **Backend console** — structured request logging with method, path, status, duration
- **OTP console print** — OTP codes always printed to terminal in development

Errors in tool calls are logged and caught gracefully; the agent never crashes a call due to a CRM or calendar failure.

---

## Real-World Scenario

**A real estate agency receives 80+ inbound calls per day. Their 3-person team cannot qualify every lead before end of business.**

1. Customer calls at 8:45 PM — after office hours
2. VoxAI answers: *"Thank you for calling ABC Realty, how can I help you today?"*
3. Customer: *"I'm looking for a 3BHK in Baner, budget around 90 lakhs"*
4. AI classifies intent: `property_inquiry`, budget: `9,000,000`, location: `Baner`, bedrooms: `3`
5. Lead scored **HOT** — team receives WhatsApp alert instantly
6. AI searches knowledge base — finds 3 matching listings, sends them via WhatsApp to customer
7. Customer: *"Can I see the second one this Saturday?"*
8. AI checks Google Calendar — Saturday 11 AM available
9. Books appointment, updates lead to `qualified` in HubSpot
10. WhatsApp confirmation sent: *"Your visit is confirmed for Saturday at 11:00 AM"*
11. Call ends. `AgentRun`, `ToolCall`, `Conversation`, `Lead`, and `Appointment` all persisted.

Total human effort: **zero.** The agent handled intake, qualification, CRM entry, and booking automatically.

---

## Integrations

| Integration | Purpose | Status |
|---|---|---|
| Twilio Voice | Inbound phone calls, TTS, STT, live transfer | ✅ Implemented |
| Twilio WhatsApp | Customer messaging, confirmations, team alerts | ✅ Implemented |
| HubSpot CRM | Lead creation, stage updates, contact management | ✅ Implemented |
| Google Calendar | Slot availability, appointment creation, Meet links | ✅ Implemented |
| Google Gemini 1.5 | Intent classification, response generation | ✅ Implemented |
| Google Embeddings | Knowledge base vector search | ✅ Implemented |
| Brevo | OTP email delivery for authentication | ✅ Implemented |
| pgvector | Vector similarity search for RAG | ✅ Implemented |
| Redis | Rate limiting, background job queue | ✅ Implemented |

---

## Limitations

- **LLM latency:** Gemini Flash adds ~400–800ms per agent turn. Total response time including webhook round-trip is typically 1.5–3 seconds on voice.
- **Intent coverage:** The intent classifier is currently tuned for real estate. Other verticals require prompt updates to the classifier and lead agent.
- **RAG storage:** pgvector is used in production; SQLite fallback does not support vector search — the agent will use the LLM without retrieval in dev mode without PostgreSQL.
- **WhatsApp sandbox:** Twilio WhatsApp sandbox requires customers to opt-in. Production deployment requires WhatsApp Business approval.
- **Twilio Gather:** Speech recognition accuracy depends on call quality and language. Currently configured for `en-IN` (Indian English).
- **Calendar:** Google Calendar integration requires a service account or OAuth credentials; mock is provided for development.

---

## Roadmap

### Completed
- [x] LangGraph multi-agent orchestrator (Receptionist → Classifier → Lead/Booking/Support/Handoff → Responder)
- [x] Twilio voice webhook with full TwiML conversation loop
- [x] WhatsApp inbound/outbound via Twilio
- [x] HubSpot CRM sync with lead scoring
- [x] Google Calendar appointment booking
- [x] pgvector RAG knowledge base
- [x] Customer memory persistence
- [x] Live call transfer with team WhatsApp alert
- [x] JWT + OTP 2FA email authentication
- [x] Next.js business dashboard
- [x] Rate limiting, call status tracking, AgentRun observability

### In Progress
- [ ] Dashboard live data refresh (WebSocket or polling)
- [ ] Agent configuration UI (name, greeting, personality)
- [ ] Knowledge base upload UI

### Planned
- [ ] Zoho / Salesforce CRM adapters
- [ ] Multi-language support (Hindi, regional)
- [ ] Outbound call campaigns
- [ ] SMS follow-up automation
- [ ] Custom industry intent classifiers (healthcare, automotive)
- [ ] Usage analytics and conversion reporting
- [ ] Multi-business / SaaS tenancy

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes with tests where appropriate
4. Commit with a clear message: `git commit -m "feat: add X"`
5. Push and open a Pull Request against `main`

**Code conventions:**
- Python: type annotations on all public functions, `async/await` throughout
- TypeScript: strict mode, no `any` where avoidable
- Commit format: `feat | fix | refactor | docs | test: description`

---

## License

[MIT License](./LICENSE) — © 2024 SurinderTech

---

<div align="center">

**VoxAI turns your inbound phone line into a tireless, intelligent employee that qualifies leads, books appointments, updates your CRM, and escalates only what matters — so your team can focus on closing.**

[⭐ Star this repo](https://github.com/SurinderTech/Ai_Employe) · [🐛 Report a Bug](https://github.com/SurinderTech/Ai_Employe/issues) · [ Request a Feature](https://github.com/SurinderTech/Ai_Employe/issues)

</div>
