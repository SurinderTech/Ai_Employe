"""
Calls API — list calls, get transcript, live call status for dashboard.

Public routes (no auth) for dev:
  GET /api/v1/calls/public/live    — live calls (no JWT)
  GET /api/v1/calls/public/recent  — recent completed calls (no JWT)
  GET /api/v1/calls/public/stats   — today's stats (no JWT)

Auth-protected routes:
  GET /api/v1/calls                — full list
  GET /api/v1/calls/stats          — stats
  GET /api/v1/calls/live           — live calls
  GET /api/v1/calls/{id}/transcript
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database.session import get_db
from app.models.conversation import Call, CallStatus, Conversation, Message
from app.models.customer import Customer
from app.models.business import Business
from app.models.user import User
from app.security.auth import get_current_user

router = APIRouter()


async def _first_business_id(db: AsyncSession) -> uuid.UUID | None:
    result = await db.execute(select(Business).limit(1))
    biz = result.scalar_one_or_none()
    return biz.id if biz else None


# ── Public (dev / no auth) ────────────────────────────────────────────────────

@router.get("/public/stats")
async def public_call_stats(db: AsyncSession = Depends(get_db)):
    """Today's call stats — no auth, for dev dashboard."""
    business_id = await _first_business_id(db)
    if not business_id:
        return {"today_total": 0, "today_completed": 0, "live_now": 0, "avg_duration_seconds": 0}

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_today = (await db.execute(
        select(func.count()).where(Call.business_id == business_id, Call.created_at >= today_start)
    )).scalar() or 0

    completed = (await db.execute(
        select(func.count()).where(
            Call.business_id == business_id,
            Call.status == CallStatus.COMPLETED,
            Call.created_at >= today_start,
        )
    )).scalar() or 0

    live = (await db.execute(
        select(func.count()).where(
            Call.business_id == business_id,
            Call.status == CallStatus.IN_PROGRESS,
        )
    )).scalar() or 0

    avg = (await db.execute(
        select(func.avg(Call.duration_seconds)).where(
            Call.business_id == business_id,
            Call.status == CallStatus.COMPLETED,
            Call.created_at >= today_start,
        )
    )).scalar()

    return {
        "today_total": total_today,
        "today_completed": completed,
        "live_now": live,
        "avg_duration_seconds": round(avg or 0),
    }


@router.get("/public/live")
async def public_live_calls(db: AsyncSession = Depends(get_db)):
    """Live calls — no auth, for dev dashboard."""
    business_id = await _first_business_id(db)
    if not business_id:
        return []

    result = await db.execute(
        select(Call, Customer)
        .outerjoin(Conversation, Conversation.id == Call.conversation_id)
        .outerjoin(Customer, Customer.phone == Call.from_number)
        .where(
            Call.business_id == business_id,
            Call.status == CallStatus.IN_PROGRESS,
        )
        .order_by(desc(Call.answered_at))
    )
    rows = result.all()

    live = []
    for row in rows:
        call = row[0]
        customer = row[1]
        duration = 0
        if call.answered_at:
            duration = int((datetime.now(timezone.utc) - call.answered_at).total_seconds())
        live.append({
            "call_id": str(call.id),
            "customer_name": customer.full_name if customer else "Unknown",
            "from_number": call.from_number,
            "duration_seconds": duration,
            "conversation_id": str(call.conversation_id) if call.conversation_id else None,
            "intent": None,
        })

    return live


@router.get("/public/recent")
async def public_recent_calls(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Recent completed calls — no auth, for dev dashboard."""
    business_id = await _first_business_id(db)
    if not business_id:
        return []

    result = await db.execute(
        select(Call, Customer)
        .outerjoin(Customer, Customer.phone == Call.from_number)
        .where(
            Call.business_id == business_id,
            Call.status.in_([CallStatus.COMPLETED, CallStatus.NO_ANSWER, CallStatus.FAILED]),
        )
        .order_by(desc(Call.created_at))
        .limit(limit)
    )
    rows = result.all()

    return [
        {
            "call_id": str(call.id),
            "customer_name": customer.full_name if customer else "Unknown",
            "from_number": call.from_number,
            "status": call.status.value,
            "duration_seconds": call.duration_seconds,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "created_at": call.created_at.isoformat(),
        }
        for call, customer in rows
    ]


# ── Auth-protected ────────────────────────────────────────────────────────────

@router.get("")
async def list_calls(
    business_id: uuid.UUID,
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List calls for a business, newest first."""
    query = (
        select(Call)
        .where(Call.business_id == business_id)
        .order_by(desc(Call.created_at))
        .limit(limit)
        .offset(offset)
    )
    if status:
        query = query.where(Call.status == CallStatus(status))

    result = await db.execute(query)
    calls = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "twilio_call_sid": c.twilio_call_sid,
            "from_number": c.from_number,
            "to_number": c.to_number,
            "direction": c.direction,
            "status": c.status.value,
            "duration_seconds": c.duration_seconds,
            "answered_at": c.answered_at.isoformat() if c.answered_at else None,
            "ended_at": c.ended_at.isoformat() if c.ended_at else None,
            "created_at": c.created_at.isoformat(),
        }
        for c in calls
    ]


@router.get("/stats")
async def call_stats(
    business_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Today's call stats for the dashboard overview."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_today = (await db.execute(
        select(func.count()).where(Call.business_id == business_id, Call.created_at >= today_start)
    )).scalar() or 0
    completed = (await db.execute(
        select(func.count()).where(
            Call.business_id == business_id, Call.status == CallStatus.COMPLETED, Call.created_at >= today_start
        )
    )).scalar() or 0
    live = (await db.execute(
        select(func.count()).where(Call.business_id == business_id, Call.status == CallStatus.IN_PROGRESS)
    )).scalar() or 0
    avg_duration = (await db.execute(
        select(func.avg(Call.duration_seconds)).where(
            Call.business_id == business_id, Call.status == CallStatus.COMPLETED, Call.created_at >= today_start
        )
    )).scalar()

    return {
        "today_total": total_today,
        "today_completed": completed,
        "live_now": live,
        "avg_duration_seconds": round(avg_duration or 0),
    }


@router.get("/live")
async def list_live_calls(
    business_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return currently active calls for the Live Calls dashboard view."""
    result = await db.execute(
        select(Call)
        .where(Call.business_id == business_id, Call.status == CallStatus.IN_PROGRESS)
        .order_by(desc(Call.answered_at))
    )
    calls = result.scalars().all()

    live = []
    for c in calls:
        duration = 0
        if c.answered_at:
            duration = int((datetime.now(timezone.utc) - c.answered_at).total_seconds())
        live.append({
            "call_id": str(c.id),
            "from_number": c.from_number,
            "duration_seconds": duration,
            "conversation_id": str(c.conversation_id) if c.conversation_id else None,
        })

    return live


@router.get("/{call_id}/transcript")
async def get_call_transcript(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full conversation transcript for a call."""
    call_result = await db.execute(select(Call).where(Call.id == call_id))
    call = call_result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    messages = []
    if call.conversation_id:
        msgs_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == call.conversation_id)
            .order_by(Message.created_at)
        )
        messages = [
            {"role": m.role.value, "content": m.content, "timestamp": m.created_at.isoformat()}
            for m in msgs_result.scalars().all()
        ]

    return {
        "call_id": str(call_id),
        "from_number": call.from_number,
        "duration_seconds": call.duration_seconds,
        "status": call.status.value,
        "messages": messages,
    }
