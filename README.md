# AI Business Employee

## What We're Building
A production-grade AI employee that handles customer calls, qualifies leads, books appointments, updates your CRM, and sends WhatsApp confirmations — all autonomously.

## Tech Stack
- **Backend**: FastAPI + Python 3.11 (c:\Ai_Employe\backend)
- **Frontend**: Next.js 14 (c:\Ai_Employe\frontend)  
- **Database**: PostgreSQL + pgvector (Docker)
- **Cache**: Redis (Docker)
- **AI Brain**: LangGraph + Google Gemini
- **Voice**: Twilio
- **CRM**: HubSpot
- **Calendar**: Google Calendar API
- **WhatsApp**: Twilio WhatsApp API

## Quick Start

### 1. Prerequisites
- Docker Desktop running
- Python 3.11
- Node.js 22

### 2. Environment Setup
```bash
# Copy env file and fill in your credentials
cp .env.example .env
```

### 3. Start Infrastructure
```bash
docker-compose up -d
```

### 4. Start Backend
```bash
cd backend
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn main:app --reload
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 5. Start Frontend
```bash
cd frontend
npm install
npm run dev
# Dashboard: http://localhost:3000
```

## Project Structure
```
backend/
  app/
    api/v1/         # REST endpoints (auth, businesses, leads, calls...)
    agents/         # LangGraph AI agents (orchestrator, lead, booking, support)
    integrations/   # Twilio, HubSpot, Google Calendar, WhatsApp
    models/         # SQLAlchemy database models (20 tables)
    rag/            # Document ingestion + pgvector semantic search
    security/       # JWT auth + permissions
    core/           # Config, logging, LLM abstraction

frontend/
  src/app/          # Next.js App Router pages
    dashboard/      # Main control center
    onboarding/     # Business setup flow
    leads/          # Lead pipeline
    conversations/  # Call transcripts
    settings/       # Integrations config
```

## Twilio Webhook Setup
After starting the backend, configure these webhook URLs in your Twilio console:
- **Voice webhook**: `https://your-domain.com/api/v1/webhooks/twilio/voice/inbound`
- **Status callback**: `https://your-domain.com/api/v1/webhooks/twilio/voice/status`
- **WhatsApp webhook**: `https://your-domain.com/api/v1/webhooks/twilio/whatsapp/inbound`

For local development, use [ngrok](https://ngrok.com/):
```bash
ngrok http 8000
```

## The Complete Customer Journey
```
Customer calls → Twilio → /webhooks/twilio/voice/inbound
  → TwiML Gather (listen for speech)
  → /webhooks/twilio/voice/process
  → LangGraph Orchestrator
      → Intent Classification (Gemini)
      → Context Load (RAG search)
      → Tool Execution (CRM/Calendar/WhatsApp)
      → Response Generation
  → TTS → Twilio plays audio
  → Post-call: WhatsApp confirmation + CRM update
```
