"""Customer and Lead models."""
import uuid
import enum
from sqlalchemy import String, JSON, ForeignKey, Text, Float, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import GUID as PGUUID
from app.database.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class LeadScore(str, enum.Enum):
    COLD = "cold"
    WARM = "warm"
    HOT = "hot"


class Customer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customers"

    business_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    # Identity
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    # Memory (AI-maintained)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    # External CRM reference
    crm_id: Mapped[str | None] = mapped_column(String(255))
    crm_provider: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="customers")  # noqa
    leads: Mapped[list["Lead"]] = relationship(back_populates="customer")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="customer")  # noqa


class Lead(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "leads"

    business_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    # Lead details
    title: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[LeadStatus] = mapped_column(
        PgEnum(LeadStatus, name="lead_status"), default=LeadStatus.NEW
    )
    score: Mapped[LeadScore] = mapped_column(
        PgEnum(LeadScore, name="lead_score"), default=LeadScore.COLD
    )
    budget: Mapped[float | None] = mapped_column(Float)
    budget_currency: Mapped[str] = mapped_column(String(5), default="INR")
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)  # property_type, location, etc.
    assigned_to: Mapped[str | None] = mapped_column(String(255))
    # CRM sync
    crm_id: Mapped[str | None] = mapped_column(String(255))
    crm_provider: Mapped[str | None] = mapped_column(String(50))
    crm_synced_at: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="leads")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="lead")  # noqa
