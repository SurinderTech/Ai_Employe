"""
Calendar Tools — callable functions the booking agent uses to check
availability and create appointments.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.logging import logger
from app.models.appointment import Appointment, AppointmentStatus
from app.models.customer import Customer
from app.core.config import settings


def _get_calendar(business_id: str | None = None):
    """Return real or mock Google Calendar instance."""
    if settings.GOOGLE_CALENDAR_TOKEN_JSON:
        from app.integrations.calendar.google_calendar import GoogleCalendarIntegration
        return GoogleCalendarIntegration(
            credentials_json=settings.GOOGLE_CALENDAR_CREDENTIALS_JSON,
            token_json=settings.GOOGLE_CALENDAR_TOKEN_JSON,
        )
    from app.integrations.calendar.google_calendar import MockCalendar
    logger.info("[Calendar] No credentials — using MockCalendar")
    return MockCalendar()


async def get_available_slots(
    business_id: str,
    preferred_datetime: str | None = None,
    duration_minutes: int = 60,
) -> dict[str, Any]:
    """
    Return available appointment slots.

    preferred_datetime: ISO string or natural-language hint (best-effort parsed).
    Returns: {slots: [{label, start, end}, ...]}
    """
    cal = _get_calendar(business_id)

    # Parse preferred date
    target_date: datetime | None = None
    if preferred_datetime:
        try:
            # Try ISO parse first
            target_date = datetime.fromisoformat(preferred_datetime.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            # Fallback: tomorrow
            target_date = datetime.now(timezone.utc) + timedelta(days=1)
    else:
        target_date = datetime.now(timezone.utc) + timedelta(days=1)

    slots = await cal.get_available_slots(
        date=target_date,
        duration_minutes=duration_minutes,
        num_slots=5,
    )

    return {"slots": slots, "date": target_date.strftime("%A, %d %B %Y")}


async def create_appointment(
    business_id: str,
    customer: Customer,
    slot_start: str,
    title: str,
    duration_minutes: int = 60,
    description: str | None = None,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Book a slot: create Google Calendar event + persist Appointment to DB.

    slot_start: ISO datetime string for the appointment start.
    Returns: {appointment_id, google_event_id, meet_link, start_label}
    """
    cal = _get_calendar(business_id)

    try:
        start_dt = datetime.fromisoformat(slot_start.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        # Fallback to tomorrow 5 PM
        start_dt = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
            hour=17, minute=0, second=0, microsecond=0
        )

    event_result = await cal.create_event(
        title=title,
        start_time=start_dt,
        duration_minutes=duration_minutes,
        attendee_email=customer.email,
        description=description or f"Property visit for {customer.full_name or customer.phone}",
    )

    google_event_id = event_result.get("event_id")
    meet_link = event_result.get("meet_link")

    # Persist to DB
    appointment: Appointment | None = None
    if db:
        appointment = Appointment(
            business_id=uuid.UUID(business_id),
            customer_id=customer.id,
            title=title,
            description=description,
            scheduled_at=start_dt,
            duration_minutes=duration_minutes,
            status=AppointmentStatus.CONFIRMED,
            google_event_id=google_event_id,
            meeting_link=meet_link,
        )
        db.add(appointment)
        await db.flush()
        logger.info(f"📅 Appointment created: {appointment.id}")

    start_label = start_dt.strftime("%I:%M %p, %A %d %B")

    return {
        "appointment_id": str(appointment.id) if appointment else None,
        "google_event_id": google_event_id,
        "meet_link": meet_link,
        "start": slot_start,
        "start_label": start_label,
        "status": "confirmed",
    }


async def cancel_appointment(
    appointment_id: str,
    db: AsyncSession,
    business_id: str | None = None,
) -> dict[str, Any]:
    """Cancel an appointment in DB and Google Calendar."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == uuid.UUID(appointment_id))
    )
    appt = result.scalar_one_or_none()
    if not appt:
        return {"status": "error", "detail": "Appointment not found"}

    appt.status = AppointmentStatus.CANCELLED
    await db.flush()

    if appt.google_event_id:
        try:
            cal = _get_calendar(business_id)
            await cal.cancel_event(appt.google_event_id)
        except Exception as e:
            logger.error(f"Google Calendar cancel failed: {e}")

    return {"status": "cancelled", "appointment_id": appointment_id}
