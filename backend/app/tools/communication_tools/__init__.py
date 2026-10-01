"""
Communication Tools — WhatsApp and notification functions for the agent.
"""
from __future__ import annotations
from typing import Any
from app.core.logging import logger
from app.core.config import settings
from app.models.customer import Customer, Lead


def _get_whatsapp():
    """Return real or mock WhatsApp client."""
    use_mock = not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_WHATSAPP_NUMBER)
    from app.integrations.whatsapp.twilio_whatsapp import get_whatsapp
    if use_mock:
        logger.info("[WhatsApp] No credentials — using MockWhatsApp")
    return get_whatsapp(use_mock=use_mock)


async def send_lead_whatsapp(
    customer: Customer,
    properties: list[dict] | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """
    Send property cards or a custom message to a customer after a call.

    properties: [{name, location, price_lakhs, bedrooms, area_sqft}, ...]
    """
    wa = _get_whatsapp()
    try:
        if properties:
            await wa.send_property_cards(customer.phone, properties)
            return {"status": "sent", "type": "property_cards", "count": len(properties)}
        elif message:
            sid = await wa.send_text(customer.phone, message)
            return {"status": "sent", "type": "text", "sid": sid}
        return {"status": "skipped", "reason": "no content"}
    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")
        return {"status": "error", "detail": str(e)}


async def send_appointment_confirmation(
    customer: Customer,
    appointment: dict,
) -> dict[str, Any]:
    """
    Send appointment confirmation to the customer.

    appointment: {date, time, location, ...}
    """
    wa = _get_whatsapp()
    try:
        await wa.send_appointment_confirmation(customer.phone, appointment)
        return {"status": "sent", "type": "appointment_confirmation"}
    except Exception as e:
        logger.error(f"WhatsApp confirmation failed: {e}")
        return {"status": "error", "detail": str(e)}


async def notify_team_new_lead(
    team_phone: str,
    customer: Customer,
    lead: Lead,
    entities: dict,
) -> dict[str, Any]:
    """
    Alert the business team about a hot new lead.
    """
    wa = _get_whatsapp()
    budget = entities.get("budget")
    budget_lakhs = f"{float(budget) / 100000:.0f}" if budget else "?"

    summary = {
        "name": customer.full_name or customer.phone,
        "phone": customer.phone,
        "requirement": f"{entities.get('bedrooms', '?')} BHK in {entities.get('location', '?')}",
        "budget_lakhs": budget_lakhs,
        "location": entities.get("location", ""),
        "intent": "Property purchase inquiry",
        "recommended_action": "Call customer within 30 minutes",
    }

    try:
        await wa.send_lead_summary_to_team(team_phone, summary)
        return {"status": "sent", "type": "team_alert"}
    except Exception as e:
        logger.error(f"Team notification failed: {e}")
        return {"status": "error", "detail": str(e)}


async def notify_human_handoff(
    team_phone: str,
    customer: Customer,
    reason: str,
    conversation_summary: str,
    entities: dict,
) -> dict[str, Any]:
    """
    Notify a human agent that they need to take over immediately.
    """
    wa = _get_whatsapp()
    message = (
        f"🚨 *URGENT: Human Handoff Required*\n\n"
        f"👤 Customer: {customer.full_name or customer.phone}\n"
        f"📞 Phone: {customer.phone}\n"
        f"⚠️ Reason: {reason}\n\n"
        f"*Conversation Summary:*\n{conversation_summary[:500]}\n\n"
        f"*Customer needs:* {entities.get('property_type', '?')} in "
        f"{entities.get('location', '?')} @ "
        f"₹{entities.get('budget', '?')}\n\n"
        f"_Please call immediately_ 📲"
    )
    try:
        sid = await wa.send_text(team_phone, message)
        return {"status": "sent", "sid": sid}
    except Exception as e:
        logger.error(f"Handoff notification failed: {e}")
        return {"status": "error", "detail": str(e)}
