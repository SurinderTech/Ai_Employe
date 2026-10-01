"""OTP codes model — email verification, 2FA login, forgot password."""
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import GUID, UUIDMixin, TimestampMixin
from app.database.session import Base


class OtpPurpose(str, enum.Enum):
    EMAIL_VERIFY = "email_verify"
    TWO_FACTOR = "two_factor"
    FORGOT_PASSWORD = "forgot_password"


class OtpCode(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "otp_codes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    purpose: Mapped[OtpPurpose] = mapped_column(
        PgEnum(OtpPurpose, name="otp_purpose"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<OtpCode user={self.user_id} purpose={self.purpose} used={self.is_used}>"
