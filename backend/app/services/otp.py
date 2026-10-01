"""OTP service — generate, store, verify OTP codes."""
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.otp import OtpCode, OtpPurpose
from app.core.logging import logger

OTP_EXPIRE_MINUTES = 5


def _generate_otp() -> str:
    """Generate a secure 6-digit OTP."""
    return str(secrets.randbelow(900000) + 100000)  # 100000–999999


async def create_otp(db: AsyncSession, user_id, purpose: OtpPurpose) -> str:
    """
    Invalidate any existing OTPs for the same user+purpose,
    create a new one, and return the plaintext code.
    """
    import uuid
    # Mark all previous OTPs for this user+purpose as used
    await db.execute(
        update(OtpCode)
        .where(OtpCode.user_id == user_id, OtpCode.purpose == purpose, OtpCode.is_used == False)
        .values(is_used=True)
    )

    code = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    otp = OtpCode(
        user_id=user_id,
        code=code,
        purpose=purpose,
        expires_at=expires_at,
        is_used=False,
    )
    db.add(otp)
    await db.flush()
    logger.info(f"[OTP] Created OTP for user={user_id} purpose={purpose}")
    # ── Dev helper: always print OTP so it's visible in terminal ──────────────
    print(f"\n{'='*50}")
    print(f"  🔐 OTP CODE  →  {code}  (purpose: {purpose.value})")
    print(f"  📧 Email: {user_id} | Expires in {OTP_EXPIRE_MINUTES} min")
    print(f"{'='*50}\n")
    return code


async def verify_otp(
    db: AsyncSession, user_id, code: str, purpose: OtpPurpose
) -> bool:
    """
    Check if the OTP is valid (correct code, correct purpose,
    not expired, not used). Marks it as used on success.
    Returns True if valid, False otherwise.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(OtpCode).where(
            OtpCode.user_id == user_id,
            OtpCode.code == code,
            OtpCode.purpose == purpose,
            OtpCode.is_used == False,
            OtpCode.expires_at > now,
        )
    )
    otp = result.scalar_one_or_none()
    if not otp:
        logger.warning(f"[OTP] Invalid/expired OTP attempt: user={user_id} purpose={purpose}")
        return False

    otp.is_used = True
    await db.flush()
    logger.info(f"[OTP] Verified OTP for user={user_id} purpose={purpose}")
    return True
