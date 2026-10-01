"""Business and BusinessUser models — multi-tenant core."""
import uuid
import enum
from sqlalchemy import String, Boolean, JSON, ForeignKey, Time, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import GUID as PGUUID
from app.database.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class BusinessStatus(str, enum.Enum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class BusinessUserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Business(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    industry: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(2000))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(500))
    address: Mapped[dict | None] = mapped_column(JSON)  # {street, city, state, country, zip}
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    working_hours: Mapped[dict] = mapped_column(JSON, default=lambda: {
        "monday": {"open": "09:00", "close": "20:00"},
        "tuesday": {"open": "09:00", "close": "20:00"},
        "wednesday": {"open": "09:00", "close": "20:00"},
        "thursday": {"open": "09:00", "close": "20:00"},
        "friday": {"open": "09:00", "close": "20:00"},
        "saturday": {"open": "09:00", "close": "18:00"},
        "sunday": {"open": None, "close": None},
    })
    services: Mapped[list | None] = mapped_column(JSON)  # ["2BHK", "3BHK", "Commercial"]
    logo_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[BusinessStatus] = mapped_column(
        PgEnum(BusinessStatus, name="business_status"), default=BusinessStatus.ONBOARDING
    )
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    business_users: Mapped[list["BusinessUser"]] = relationship(back_populates="business")
    agents: Mapped[list["Agent"]] = relationship(back_populates="business")  # noqa
    customers: Mapped[list["Customer"]] = relationship(back_populates="business")  # noqa
    integrations: Mapped[list["Integration"]] = relationship(back_populates="business")  # noqa
    knowledge_documents: Mapped[list["KnowledgeDocument"]] = relationship(back_populates="business")  # noqa


class BusinessUser(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "business_users"

    business_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("businesses.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("users.id", ondelete="CASCADE")
    )
    role: Mapped[BusinessUserRole] = mapped_column(
        PgEnum(BusinessUserRole, name="business_user_role"), default=BusinessUserRole.MEMBER
    )
    permissions: Mapped[list] = mapped_column(JSON, default=list)  # CAN_READ_CRM, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="business_users")
    user: Mapped["User"] = relationship(back_populates="business_users")
