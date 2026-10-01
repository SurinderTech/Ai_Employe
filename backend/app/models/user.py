"""User model — authentication, roles."""
import uuid
import enum
from sqlalchemy import String, Boolean, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import GUID as PGUUID
from app.database.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    BUSINESS_OWNER = "business_owner"
    BUSINESS_ADMIN = "business_admin"
    AGENT = "agent"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[UserRole] = mapped_column(
        PgEnum(UserRole, name="user_role"), default=UserRole.BUSINESS_OWNER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    business_users: Mapped[list["BusinessUser"]] = relationship(back_populates="user")  # noqa

    def __repr__(self) -> str:
        return f"<User {self.email}>"
