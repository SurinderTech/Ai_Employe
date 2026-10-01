"""Integration, IntegrationCredential, HumanHandoff, AuditLog models."""
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, JSON, ForeignKey, Text, Boolean, DateTime, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import GUID as PGUUID
from app.database.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class IntegrationType(str, enum.Enum):
    TWILIO = "twilio"
    HUBSPOT = "hubspot"
    GOOGLE_CALENDAR = "google_calendar"
    WHATSAPP = "whatsapp"
    GMAIL = "gmail"
    SALESFORCE = "salesforce"
    ZOHO = "zoho"
    CUSTOM = "custom"


class IntegrationStatus(str, enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PENDING = "pending"


class Integration(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "integrations"

    business_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    integration_type: Mapped[IntegrationType] = mapped_column(
        PgEnum(IntegrationType, name="integration_type")
    )
    status: Mapped[IntegrationStatus] = mapped_column(
        PgEnum(IntegrationStatus, name="integration_status"), default=IntegrationStatus.PENDING
    )
    display_name: Mapped[str | None] = mapped_column(String(255))
    config: Mapped[dict] = mapped_column(JSON, default=dict)  # non-secret config
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    business: Mapped["Business"] = relationship(back_populates="integrations")  # noqa
    credential: Mapped["IntegrationCredential"] = relationship(
        back_populates="integration", uselist=False
    )


class IntegrationCredential(Base, UUIDMixin, TimestampMixin):
    """
    Encrypted secrets — never returned in API responses.
    In production: use a vault (AWS Secrets Manager, GCP Secret Manager).
    For now: encrypted JSON column.
    """
    __tablename__ = "integration_credentials"

    integration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("integrations.id", ondelete="CASCADE"), unique=True
    )
    # Encrypted blob — encrypt/decrypt in the security layer
    encrypted_credentials: Mapped[str | None] = mapped_column(Text)

    integration: Mapped["Integration"] = relationship(back_populates="credential")


# ── Human Handoff ─────────────────────────────────────────────────────────────

class HandoffStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    RESOLVED = "resolved"
    MISSED = "missed"


class HumanHandoff(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "human_handoffs"

    business_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    trigger_reason: Mapped[str | None] = mapped_column(String(255))  # angry, complex_query, etc.
    context_summary: Mapped[str | None] = mapped_column(Text)
    customer_intent: Mapped[str | None] = mapped_column(String(255))
    recommended_action: Mapped[str | None] = mapped_column(Text)
    status: Mapped[HandoffStatus] = mapped_column(
        PgEnum(HandoffStatus, name="handoff_status"), default=HandoffStatus.PENDING
    )
    accepted_by: Mapped[str | None] = mapped_column(String(255))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    business_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(), ForeignKey("businesses.id", ondelete="SET NULL")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # CREATE_LEAD, UPDATE_CRM, etc.
    resource_type: Mapped[str | None] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(255))
    changes: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(500))
