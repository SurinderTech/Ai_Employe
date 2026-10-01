"""
Agents API — dashboard stats, agent run logs, chat test, and WebSocket stream.

GET  /api/v1/agents/stats          — aggregate stats for the dashboard overview
GET  /api/v1/agents/runs           — agent run logs (conversations view)
GET  /api/v1/agents/runs/{run_id}  — single run with tool calls
POST /api/v1/agents/chat           — test the AI agent with a message (no Twilio needed)
WS   /api/v1/agents/ws/logs        — WebSocket that streams live AgentRun events
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from app.database.session import get_db
from app.models.conversation import AgentRun, ToolCall, Call, CallStatus
from app.models.customer import Lead, LeadScore, LeadStatus
from app.models.appointment import Appointment
from app.models.business import Business
from app.models.integration import HumanHandoff

router = APIRouter()


# ── Helper: resolve first business for single-tenant dev ──────────────────────

async def _get_demo_business_id(db: AsyncSession) -> uuid.UUID | None:
    result = await db.execute(select(Business).limit(1))
    biz = result.scalar_one_or_none()
    return biz.id if biz else None


# ── Dashboard Stats ───────────────────────────────────────────────────────────

@router.get("/stats")
async def dashboard_stats(
    business_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregate stats for the dashboard Overview page.
    If business_id is omitted, falls back to the first business in DB (dev mode).
    """
    if business_id is None:
        business_id = await _get_demo_business_id(db)
    if business_id is None:
        # No data at all — return zeros
        return _zero_stats()

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # ── Calls ─────────────────────────────────────────────────────────────────
    calls_today = (await db.execute(
        select(func.count()).where(
            Call.business_id == business_id,
            Call.created_at >= today_start,
        )
    )).scalar() or 0

    calls_live = (await db.execute(
        select(func.count()).where(
            Call.business_id == business_id,
            Call.status == CallStatus.IN_PROGRESS,
        )
    )).scalar() or 0

    calls_completed_today = (await db.execute(
        select(func.count()).where(
            Call.business_id == business_id,
            Call.status == CallStatus.COMPLETED,
            Call.created_at >= today_start,
        )
    )).scalar() or 0

    avg_duration = (await db.execute(
        select(func.avg(Call.duration_seconds)).where(
            Call.business_id == business_id,
            Call.status == CallStatus.COMPLETED,
            Call.created_at >= today_start,
        )
    )).scalar()

    # ── Agent Runs ────────────────────────────────────────────────────────────
    runs_today = (await db.execute(
        select(func.count()).where(
            AgentRun.created_at >= today_start
        )
    )).scalar() or 0

    escalated_today = (await db.execute(
        select(func.count()).where(
            AgentRun.status == "escalated",
            AgentRun.created_at >= today_start,
        )
    )).scalar() or 0

    # Intent breakdown (today)
    intent_rows = (await db.execute(
        select(AgentRun.intent, func.count().label("cnt"))
        .where(
            AgentRun.created_at >= today_start,
            AgentRun.intent.isnot(None),
        )
        .group_by(AgentRun.intent)
    )).all()
    intent_breakdown = {row.intent: row.cnt for row in intent_rows}

    # AI handle rate: completed / (completed + escalated), today
    ai_handled = (await db.execute(
        select(func.count()).where(
            AgentRun.status == "completed",
            AgentRun.created_at >= today_start,
        )
    )).scalar() or 0

    total_runs_today = ai_handled + escalated_today
    ai_handle_rate = round((ai_handled / total_runs_today * 100) if total_runs_today else 0)

    # Avg latency today
    avg_latency = (await db.execute(
        select(func.avg(AgentRun.latency_ms)).where(
            AgentRun.created_at >= today_start,
            AgentRun.latency_ms.isnot(None),
        )
    )).scalar()

    # ── Leads ─────────────────────────────────────────────────────────────────
    leads_today = (await db.execute(
        select(func.count()).where(
            Lead.business_id == business_id,
            Lead.created_at >= today_start,
        )
    )).scalar() or 0

    hot_leads = (await db.execute(
        select(func.count()).where(
            Lead.business_id == business_id,
            Lead.score == LeadScore.HOT,
        )
    )).scalar() or 0

    leads_by_stage = (await db.execute(
        select(Lead.status, func.count().label("cnt"))
        .where(Lead.business_id == business_id)
        .group_by(Lead.status)
    )).all()
    stage_breakdown = {row.status.value: row.cnt for row in leads_by_stage}

    # ── Appointments ──────────────────────────────────────────────────────────
    appointments_today = (await db.execute(
        select(func.count()).where(
            Appointment.business_id == business_id,
            Appointment.created_at >= today_start,
        )
    )).scalar() or 0

    # ── Human Handoffs ────────────────────────────────────────────────────────
    handoffs_today = (await db.execute(
        select(func.count()).where(
            HumanHandoff.business_id == business_id,
            HumanHandoff.created_at >= today_start,
        )
    )).scalar() or 0

    return {
        "calls": {
            "today": calls_today,
            "live": calls_live,
            "completed_today": calls_completed_today,
            "avg_duration_seconds": round(avg_duration or 0),
        },
        "ai": {
            "runs_today": runs_today,
            "handled_today": ai_handled,
            "escalated_today": escalated_today,
            "handle_rate_pct": ai_handle_rate,
            "avg_latency_ms": round(avg_latency or 0),
            "intent_breakdown": intent_breakdown,
        },
        "leads": {
            "today": leads_today,
            "hot": hot_leads,
            "stage_breakdown": stage_breakdown,
        },
        "appointments": {
            "today": appointments_today,
        },
        "handoffs": {
            "today": handoffs_today,
        },
    }


def _zero_stats() -> dict:
    return {
        "calls": {"today": 0, "live": 0, "completed_today": 0, "avg_duration_seconds": 0},
        "ai": {"runs_today": 0, "handled_today": 0, "escalated_today": 0,
               "handle_rate_pct": 0, "avg_latency_ms": 0, "intent_breakdown": {}},
        "leads": {"today": 0, "hot": 0, "stage_breakdown": {}},
        "appointments": {"today": 0},
        "handoffs": {"today": 0},
    }


# ── Agent Runs (Conversations view) ───────────────────────────────────────────

@router.get("/runs")
async def list_agent_runs(
    business_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Recent agent runs for the Conversations / AgentLogs dashboard view.
    Intentionally no auth for dev — add get_current_user when ready.
    """
    query = (
        select(AgentRun)
        .order_by(desc(AgentRun.created_at))
        .limit(limit)
    )
    result = await db.execute(query)
    runs = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "status": r.status,
            "intent": r.intent,
            "input_text": r.input_text,
            "output_text": r.output_text,
            "latency_ms": r.latency_ms,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
async def get_agent_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Single agent run with all tool calls."""
    run_result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = run_result.scalar_one_or_none()
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Agent run not found")

    tools_result = await db.execute(
        select(ToolCall)
        .where(ToolCall.agent_run_id == run_id)
        .order_by(ToolCall.created_at)
    )
    tools = tools_result.scalars().all()

    return {
        "id": str(run.id),
        "status": run.status,
        "intent": run.intent,
        "input_text": run.input_text,
        "output_text": run.output_text,
        "latency_ms": run.latency_ms,
        "created_at": run.created_at.isoformat(),
        "tool_calls": [
            {
                "tool_name": t.tool_name,
                "status": t.status,
                "latency_ms": t.latency_ms,
                "created_at": t.created_at.isoformat(),
            }
            for t in tools
        ],
    }
