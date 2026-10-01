"""Auth endpoints — register, verify-email, login, verify-otp (2FA),
forgot-password, reset-password, refresh, me."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, field_serializer

from app.database.session import get_db
from app.models.user import User, UserRole
from app.models.otp import OtpPurpose
from app.security.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_user,
)
from app.services.otp import create_otp, verify_otp
from app.services.email import send_otp_email

router = APIRouter()


# ─── Request / Response schemas ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class VerifyOtpRequest(BaseModel):
    """Used for 2FA after login — exchange OTP for real tokens."""
    email: EmailStr
    code: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str


class ResendOtpRequest(BaseModel):
    email: EmailStr
    purpose: str  # "email_verify" | "two_factor" | "forgot_password"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class PendingOtpResponse(BaseModel):
    """Returned after login when 2FA OTP has been sent."""
    requires_otp: bool = True
    message: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_verified: bool

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, v: uuid.UUID) -> str:
        return str(v)


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and send an email-verification OTP."""
    print(f"\n[REGISTER] Attempt: email={body.email}, name={body.full_name}")

    existing = await _get_user_by_email(db, body.email)
    if existing:
        print(f"  [REGISTER] FAIL -- email already registered: {body.email}")
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        phone=body.phone,
        role=UserRole.BUSINESS_OWNER,
        is_verified=False,
    )
    db.add(user)
    await db.flush()
    print(f"  [REGISTER] User created: user_id={user.id}")

    # Generate & send verification OTP
    code = await create_otp(db, user.id, OtpPurpose.EMAIL_VERIFY)
    sent = await send_otp_email(body.email, body.full_name, code, "email_verify")
    if not sent:
        print(f"  [REGISTER] WARNING -- OTP email delivery failed for {body.email}")

    print(f"  [REGISTER] OTP sent to {body.email}")
    return MessageResponse(
        message="Registration successful! Please check your email for the verification code."
    )


@router.post("/verify-email", response_model=TokenResponse)
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Verify email with OTP. Returns tokens on success."""
    print(f"\n[VERIFY-EMAIL] email={body.email}")

    user = await _get_user_by_email(db, body.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    valid = await verify_otp(db, user.id, body.code, OtpPurpose.EMAIL_VERIFY)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    user.is_verified = True
    await db.flush()
    print(f"  [VERIFY-EMAIL] OK -- user_id={user.id}")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login flow:
    - Unverified users → 400 (must verify email first)
    - Verified users → sends 2FA OTP, returns pending status
    """
    print(f"\n[LOGIN] Attempt: email={body.email}")

    user = await _get_user_by_email(db, body.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please check your inbox for the verification code."
        )

    # Send 2FA OTP
    code = await create_otp(db, user.id, OtpPurpose.TWO_FACTOR)
    sent = await send_otp_email(body.email, user.full_name, code, "two_factor")
    if not sent:
        print(f"  [LOGIN] WARNING -- 2FA OTP email failed for {body.email}")

    print(f"  [LOGIN] 2FA OTP sent to {body.email}")
    return PendingOtpResponse(
        requires_otp=True,
        message="A one-time login code has been sent to your email."
    )


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_login(body: VerifyOtpRequest, db: AsyncSession = Depends(get_db)):
    """Verify the 2FA OTP after login and return real JWT tokens."""
    print(f"\n[VERIFY-OTP] email={body.email}")

    user = await _get_user_by_email(db, body.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    valid = await verify_otp(db, user.id, body.code, OtpPurpose.TWO_FACTOR)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    print(f"  [VERIFY-OTP] OK -- user_id={user.id}")
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send a password-reset OTP to the user's email."""
    print(f"\n[FORGOT-PASSWORD] email={body.email}")

    user = await _get_user_by_email(db, body.email)
    # Always return success to avoid email enumeration
    if not user:
        return MessageResponse(
            message="If that email is registered, a reset code has been sent."
        )

    code = await create_otp(db, user.id, OtpPurpose.FORGOT_PASSWORD)
    await send_otp_email(body.email, user.full_name, code, "forgot_password")
    print(f"  [FORGOT-PASSWORD] OTP sent to {body.email}")

    return MessageResponse(
        message="If that email is registered, a reset code has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Verify reset OTP and set a new password."""
    print(f"\n[RESET-PASSWORD] email={body.email}")

    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = await _get_user_by_email(db, body.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    valid = await verify_otp(db, user.id, body.code, OtpPurpose.FORGOT_PASSWORD)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    user.hashed_password = hash_password(body.new_password)
    await db.flush()
    print(f"  [RESET-PASSWORD] Password updated: user_id={user.id}")

    return MessageResponse(message="Password reset successfully. You can now log in.")


@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp(body: ResendOtpRequest, db: AsyncSession = Depends(get_db)):
    """Resend an OTP for email_verify or forgot_password purposes."""
    purpose_map = {
        "email_verify": OtpPurpose.EMAIL_VERIFY,
        "two_factor": OtpPurpose.TWO_FACTOR,
        "forgot_password": OtpPurpose.FORGOT_PASSWORD,
    }
    purpose = purpose_map.get(body.purpose)
    if not purpose:
        raise HTTPException(status_code=400, detail="Invalid purpose")

    user = await _get_user_by_email(db, body.email)
    if not user:
        return MessageResponse(message="If that email is registered, a code has been sent.")

    code = await create_otp(db, user.id, purpose)
    await send_otp_email(body.email, user.full_name, code, body.purpose)
    print(f"  [RESEND-OTP] Resent {body.purpose} OTP to {body.email}")

    return MessageResponse(message="A new code has been sent to your email.")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_token: str):
    print(f"\n[REFRESH] Token refresh attempt")
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload["sub"]
    print(f"  [REFRESH] OK -- user_id={user_id}")
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    print(f"\n[ME] Profile fetched: user_id={current_user.id}, email={current_user.email}")
    return current_user
