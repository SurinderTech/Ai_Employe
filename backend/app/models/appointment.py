"""Appointment model."""
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, JSON, ForeignKey, Text, DateTime, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import GUID as PGUUID
from app.database.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class Appointment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "appointments"

    business_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(), ForeignKey("leads.id", ondelete="SET NULL")
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("customers.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(default=60)
    status: Mapped[AppointmentStatus] = mapped_column(
        PgEnum(AppointmentStatus, name="appointment_status"), default=AppointmentStatus.SCHEDULED
    )
    location: Mapped[str | None] = mapped_column(String(500))
    meeting_link: Mapped[str | None] = mapped_column(String(500))
    # Google Calendar
    google_event_id: Mapped[str | None] = mapped_column(String(255))
    # CRM sync
    crm_id: Mapped[str | None] = mapped_column(String(255))
    reminder_sent: Mapped[bool] = mapped_column(default=False)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)

    lead: Mapped["Lead"] = relationship(back_populates="appointments")  # noqa
