"""
Leads API — list, get, update leads for the dashboard.

Public (no-auth) for dev:
  GET /api/v1/leads/public/list   — leads list (no JWT)
  GET /api/v1/leads/public/stats  — lead stage counts (no JWT)

Auth-protected:
  GET /api/v1/leads
  GET /api/v1/leads/stats
  GET /api/v1/leads/{id}
  PATCH /api/v1/leads/{id}/stage
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from app.database.session import get_db
from app.models.customer import Lead, Customer, LeadStatus, LeadScore
from app.models.business import Business
from app.models.user import User
from app.security.auth import get_current_user

router = APIRouter()


async def _first_business_id(db: AsyncSession) -> uuid.UUID | None:
    result = await db.execute(select(Business).limit(1))
    biz = result.scalar_one_or_none()
    return biz.id if biz else None


def _fmt_budget(budget: float | None) -> str | None:
    """Format budget in Indian notation."""
    if budget is None:
        return None
    if budget >= 10_000_000:
        return f"₹{budget/10_000_000:.1f}Cr"
    if budget >= 100_000:
        return f"₹{budget/100_000:.0f}L"
    return f"₹{budget:,.0f}"


# ── Public (dev / no auth) ────────────────────────────────────────────────────

@router.get("/public/stats")
async def public_lead_stats(db: AsyncSession = Depends(get_db)):
    """Lead pipeline summary — no auth, for dev dashboard."""
    business_id = await _first_business_id(db)
    if not business_id:
        return {"total": 0, "hot": 0, "new": 0, "stage_breakdown": {}}

    total = (await db.execute(
        select(func.count()).where(Lead.business_id == business_id)
    )).scalar() or 0

    hot = (await db.execute(
        select(func.count()).where(Lead.business_id == business_id, Lead.score == LeadScore.HOT)
    )).scalar() or 0

    new = (await db.execute(
        select(func.count()).where(Lead.business_id == business_id, Lead.status == LeadStatus.NEW)
    )).scalar() or 0

    stage_rows = (await db.execute(
        select(Lead.status, func.count().label("cnt"))
        .where(Lead.business_id == business_id)
        .group_by(Lead.status)
    )).all()

    return {
        "total": total,
        "hot": hot,
        "new": new,
        "stage_breakdown": {row.status.value: row.cnt for row in stage_rows},
    }


@router.get("/public/list")
async def public_lead_list(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Lead list — no auth, for dev dashboard."""
    business_id = await _first_business_id(db)
    if not business_id:
        return []

    result = await db.execute(
        select(Lead, Customer)
        .join(Customer, Customer.id == Lead.customer_id)
        .where(Lead.business_id == business_id)
        .order_by(desc(Lead.created_at))
        .limit(limit)
    )
    rows = result.all()

    return [
        {
            "id": str(lead.id),
            "customer_name": customer.full_name or "Unknown",
            "customer_phone": customer.phone,
            "status": lead.status.value,
            "score": lead.score.value.upper(),
            "budget": _fmt_budget(lead.budget),
            "budget_raw": lead.budget,
            "requirements": lead.requirements,
            "requirement_label": _requirement_label(lead.requirements),
            "crm_id": lead.crm_id,
            "created_at": lead.created_at.isoformat(),
        }
        for lead, customer in rows
    ]


def _requirement_label(req: dict) -> str:
    """Build a human-readable requirement string from the requirements dict."""
    parts = []
    if req.get("property_type"):
        parts.append(str(req["property_type"]))
    if req.get("location"):
        parts.append(str(req["location"]))
    return ", ".join(parts) if parts else "—"


# ── Auth-protected ────────────────────────────────────────────────────────────

class LeadResponse(BaseModel):
    id: str
    customer_name: str | None
    customer_phone: str
    status: str
    score: str
    budget: float | None
    requirements: dict
    crm_id: str | None
    created_at: str

    class Config:
        from_attributes = True


@router.get("")
async def list_leads(
    business_id: uuid.UUID,
    status: str | None = Query(None),
    score: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List leads for a business with optional filters."""
    query = (
        select(Lead, Customer)
        .join(Customer, Customer.id == Lead.customer_id)
        .where(Lead.business_id == business_id)
        .order_by(Lead.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status:
        query = query.where(Lead.status == LeadStatus(status))
    if score:
        query = query.where(Lead.score == LeadScore(score))

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": str(lead.id),
            "customer_name": customer.full_name,
            "customer_phone": customer.phone,
            "status": lead.status.value,
            "score": lead.score.value,
            "budget": lead.budget,
            "requirements": lead.requirements,
            "crm_id": lead.crm_id,
            "created_at": lead.created_at.isoformat(),
        }
        for lead, customer in rows
    ]


@router.get("/stats")
async def lead_stats(
    business_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Summary counts for the dashboard."""
    total = (await db.execute(
        select(func.count()).where(Lead.business_id == business_id)
    )).scalar() or 0

    hot = (await db.execute(
        select(func.count()).where(Lead.business_id == business_id, Lead.score == LeadScore.HOT)
    )).scalar() or 0

    new = (await db.execute(
        select(func.count()).where(Lead.business_id == business_id, Lead.status == LeadStatus.NEW)
    )).scalar() or 0

    return {"total": total, "hot": hot, "new": new}


@router.get("/{lead_id}")
async def get_lead(
    lead_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Lead, Customer)
        .join(Customer, Customer.id == Lead.customer_id)
        .where(Lead.id == lead_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead, customer = row
    return {
        "id": str(lead.id),
        "customer_name": customer.full_name,
        "customer_phone": customer.phone,
        "customer_email": customer.email,
        "status": lead.status.value,
        "score": lead.score.value,
        "budget": lead.budget,
        "requirements": lead.requirements,
        "crm_id": lead.crm_id,
        "crm_provider": lead.crm_provider,
        "created_at": lead.created_at.isoformat(),
    }


@router.patch("/{lead_id}/stage")
async def update_lead_stage(
    lead_id: uuid.UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually advance a lead's stage."""
    from app.tools.crm_tools import update_lead_stage as _update
    result = await _update(
        business_id=str(body.get("business_id", "")),
        lead_id=str(lead_id),
        stage=body.get("stage", "contacted"),
        note=body.get("note"),
        db=db,
    )
    return result
