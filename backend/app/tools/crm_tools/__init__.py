"""
CRM Tools — callable functions the agent invokes to interact with the CRM.

These bridge the agent (LangGraph nodes) to the CRM integration layer.
Business ID is used to fetch the right credentials from the DB.
"""
from __future__ import annotations
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.logging import logger
from app.integrations.crm.hubspot import CRMLead, get_crm
from app.models.customer import Customer, Lead, LeadStatus, LeadScore
from app.models.integration import Integration, IntegrationType, IntegrationStatus


async def _get_crm_for_business(business_id: str, db: AsyncSession):
    """Load the CRM integration for a business and return the provider instance."""
    result = await db.execute(
        select(Integration).where(
            Integration.business_id == uuid.UUID(business_id),
            Integration.integration_type == IntegrationType.HUBSPOT,
            Integration.status == IntegrationStatus.CONNECTED,
            Integration.is_active == True,
        )
    )
    integration = result.scalar_one_or_none()

    if integration and integration.credential:
        # Decrypt and use real HubSpot
        # For now: fall back to mock if no real token
        from app.core.config import settings
        if settings.HUBSPOT_ACCESS_TOKEN:
            return get_crm("hubspot")

    logger.info("[CRM] No active HubSpot integration found — using MockCRM")
    return get_crm("mock")


async def get_or_create_customer(
    business_id: str,
    phone: str,
    db: AsyncSession,
    full_name: str | None = None,
    email: str | None = None,
) -> Customer:
    """Find existing customer by phone or create a new one."""
    result = await db.execute(
        select(Customer).where(
            Customer.business_id == uuid.UUID(business_id),
            Customer.phone == phone,
        )
    )
    customer = result.scalar_one_or_none()

    if not customer:
        customer = Customer(
            business_id=uuid.UUID(business_id),
            phone=phone,
            full_name=full_name,
            email=email,
        )
        db.add(customer)
        await db.flush()
        logger.info(f"👤 New customer created: {phone}")
    elif full_name and not customer.full_name:
        customer.full_name = full_name

    return customer


async def create_lead(
    business_id: str,
    customer: Customer,
    entities: dict,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Create a Lead in the local DB and sync to CRM.

    entities: {budget, location, property_type, bedrooms, ...}
    Returns: {lead_id, crm_id, status}
    """
    # Score the lead
    score = LeadScore.COLD
    budget = entities.get("budget")
    if budget:
        try:
            budget_val = float(str(budget).replace(",", "").replace("₹", "").replace("L", "").strip())
            if budget_val >= 50:
                score = LeadScore.HOT
            elif budget_val >= 20:
                score = LeadScore.WARM
        except (ValueError, TypeError):
            pass

    # Build requirements dict
    requirements = {
        k: v for k, v in entities.items()
        if k in ("location", "property_type", "bedrooms", "area", "preferred_datetime")
        and v is not None
    }

    lead = Lead(
        business_id=uuid.UUID(business_id),
        customer_id=customer.id,
        title=f"{entities.get('property_type', 'Property')} inquiry — {entities.get('location', 'unknown')}",
        status=LeadStatus.NEW,
        score=score,
        budget=float(budget) if budget else None,
        requirements=requirements,
    )
    db.add(lead)
    await db.flush()
    logger.info(f"🏠 Lead created: {lead.id} | score={score.value}")

    # Sync to CRM
    crm_id: str | None = None
    try:
        crm = await _get_crm_for_business(business_id, db)
        crm_lead = CRMLead(
            id=None,
            full_name=customer.full_name or "Unknown",
            phone=customer.phone,
            email=customer.email,
            budget=lead.budget,
            requirements=requirements,
            status="NEW",
            score=score.value.upper(),
            notes=f"Lead created by AI agent. Requirements: {requirements}",
        )
        crm_id = await crm.create_lead(crm_lead)
        lead.crm_id = crm_id
        lead.crm_provider = "hubspot"
        if customer.crm_id is None:
            customer.crm_id = crm_id
        logger.info(f"✅ CRM lead synced: {crm_id}")
    except Exception as e:
        logger.error(f"CRM sync failed (non-fatal): {e}")

    return {
        "lead_id": str(lead.id),
        "crm_id": crm_id,
        "score": score.value,
        "status": "created",
    }


async def update_lead_stage(
    business_id: str,
    lead_id: str,
    stage: str,
    note: str | None = None,
    db: AsyncSession = None,
) -> dict[str, Any]:
    """Advance a lead's pipeline stage and optionally add a CRM note."""
    result = await db.execute(select(Lead).where(Lead.id == uuid.UUID(lead_id)))
    lead = result.scalar_one_or_none()
    if not lead:
        return {"status": "error", "detail": "Lead not found"}

    lead.status = LeadStatus(stage)
    await db.flush()

    if lead.crm_id:
        try:
            crm = await _get_crm_for_business(business_id, db)
            await crm.change_stage(lead.crm_id, stage)
            if note:
                await crm.add_note(lead.crm_id, note)
        except Exception as e:
            logger.error(f"CRM stage update failed: {e}")

    return {"status": "updated", "stage": stage, "lead_id": lead_id}


async def add_crm_note(
    business_id: str,
    lead: Lead,
    note: str,
    db: AsyncSession,
) -> bool:
    """Add a note to the lead's CRM record."""
    if not lead.crm_id:
        return False
    try:
        crm = await _get_crm_for_business(business_id, db)
        return await crm.add_note(lead.crm_id, note)
    except Exception as e:
        logger.error(f"add_crm_note failed: {e}")
        return False
