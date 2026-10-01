"""Integrations API — list and status of connected services."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db
from app.models.integration import Integration, IntegrationStatus, IntegrationType
from app.models.business import Business
from app.models.user import User
from app.security.auth import get_current_user
from app.core.config import settings

router = APIRouter()


async def _first_business_id(db: AsyncSession) -> uuid.UUID | None:
    result = await db.execute(select(Business).limit(1))
    biz = result.scalar_one_or_none()
    return biz.id if biz else None


def _integration_status_from_env() -> list[dict]:
    """
    Generate integration status from environment config.
    This gives the dashboard a real view of what's configured
    even before the Integration DB rows are created.
    """
    return [
        {
            "id": "env-twilio",
            "integration_type": "twilio",
            "display_name": "Twilio (Voice + WhatsApp)",
            "status": "connected" if settings.TWILIO_ACCOUNT_SID else "disconnected",
            "icon": "📞",
            "description": "Handles inbound/outbound voice calls and WhatsApp messages",
            "config_keys": ["TWILIO_ACCOUNT_SID", "TWILIO_PHONE_NUMBER", "TWILIO_WHATSAPP_NUMBER"],
            "configured": bool(settings.TWILIO_ACCOUNT_SID),
            "last_synced_at": None,
            "error_message": None if settings.TWILIO_ACCOUNT_SID else "TWILIO_ACCOUNT_SID not set",
        },
        {
            "id": "env-gemini",
            "integration_type": "gemini",
            "display_name": "Google Gemini AI",
            "status": "connected" if settings.GOOGLE_API_KEY else "disconnected",
            "icon": "🧠",
            "description": f"AI engine — {settings.GEMINI_MODEL} / {settings.GEMINI_FAST_MODEL}",
            "config_keys": ["GOOGLE_API_KEY"],
            "configured": bool(settings.GOOGLE_API_KEY),
            "last_synced_at": None,
            "error_message": None if settings.GOOGLE_API_KEY else "GOOGLE_API_KEY not set",
        },
        {
            "id": "env-hubspot",
            "integration_type": "hubspot",
            "display_name": "HubSpot CRM",
            "status": "connected" if settings.HUBSPOT_ACCESS_TOKEN else "disconnected",
            "icon": "🗂️",
            "description": "CRM — contacts, deals, and lead pipeline sync",
            "config_keys": ["HUBSPOT_ACCESS_TOKEN", "HUBSPOT_PORTAL_ID"],
            "configured": bool(settings.HUBSPOT_ACCESS_TOKEN),
            "last_synced_at": None,
            "error_message": None if settings.HUBSPOT_ACCESS_TOKEN else "HUBSPOT_ACCESS_TOKEN not set",
        },
        {
            "id": "env-google-calendar",
            "integration_type": "google_calendar",
            "display_name": "Google Calendar",
            "status": "connected" if settings.GOOGLE_CALENDAR_CREDENTIALS_JSON else "disconnected",
            "icon": "📅",
            "description": "Calendar access for appointment booking and availability checks",
            "config_keys": ["GOOGLE_CALENDAR_CREDENTIALS_JSON", "GOOGLE_CALENDAR_ID"],
            "configured": bool(settings.GOOGLE_CALENDAR_CREDENTIALS_JSON),
            "last_synced_at": None,
            "error_message": None if settings.GOOGLE_CALENDAR_CREDENTIALS_JSON else "Calendar credentials not configured",
        },
        {
            "id": "env-whatsapp",
            "integration_type": "whatsapp",
            "display_name": "WhatsApp Business",
            "status": "connected" if settings.TWILIO_WHATSAPP_NUMBER else "disconnected",
            "icon": "💬",
            "description": "Send property details, appointment confirmations, and follow-ups",
            "config_keys": ["TWILIO_WHATSAPP_NUMBER"],
            "configured": bool(settings.TWILIO_WHATSAPP_NUMBER),
            "last_synced_at": None,
            "error_message": None if settings.TWILIO_WHATSAPP_NUMBER else "WhatsApp number not configured",
        },
    ]


# ── Public (dev / no auth) ────────────────────────────────────────────────────

@router.get("/public/list")
async def public_list_integrations(db: AsyncSession = Depends(get_db)):
    """
    Integration status — no auth, for dev dashboard.
    Returns env-derived status so dashboard shows real config state.
    """
    return _integration_status_from_env()


@router.get("/public/env-status")
async def public_env_status():
    """Return which env vars are set (no values, just booleans)."""
    return {
        "GOOGLE_API_KEY":                    bool(settings.GOOGLE_API_KEY),
        "TWILIO_ACCOUNT_SID":                bool(settings.TWILIO_ACCOUNT_SID),
        "TWILIO_PHONE_NUMBER":               bool(settings.TWILIO_PHONE_NUMBER),
        "TWILIO_WHATSAPP_NUMBER":            bool(settings.TWILIO_WHATSAPP_NUMBER),
        "HUBSPOT_ACCESS_TOKEN":              bool(settings.HUBSPOT_ACCESS_TOKEN),
        "GOOGLE_CALENDAR_CREDENTIALS_JSON":  bool(settings.GOOGLE_CALENDAR_CREDENTIALS_JSON),
        "ESCALATION_PHONE":                  bool(settings.ESCALATION_PHONE),
        "TEAM_WHATSAPP_PHONE":               bool(settings.TEAM_WHATSAPP_PHONE),
    }


# ── Auth-protected ────────────────────────────────────────────────────────────

@router.get("")
async def list_items(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List integration records from the DB."""
    biz_id = await _first_business_id(db)
    if not biz_id:
        return []
    result = await db.execute(
        select(Integration).where(Integration.business_id == biz_id)
    )
    items = result.scalars().all()
    return [
        {
            "id": str(i.id),
            "integration_type": i.integration_type.value,
            "status": i.status.value,
            "display_name": i.display_name,
            "is_active": i.is_active,
            "last_synced_at": i.last_synced_at.isoformat() if i.last_synced_at else None,
            "error_message": i.error_message,
        }
        for i in items
    ]
