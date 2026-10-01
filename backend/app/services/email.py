"""Brevo (Sendinblue) email service — send transactional OTP emails."""
import httpx
from app.core.config import settings
from app.core.logging import logger

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


async def send_otp_email(to_email: str, to_name: str, otp_code: str, purpose: str) -> bool:
    """
    Send an OTP email via Brevo transactional API.
    Returns True on success, False on failure.
    """
    subject_map = {
        "email_verify": "Verify Your Email — AI Employee",
        "two_factor": "Your Login OTP — AI Employee",
        "forgot_password": "Reset Your Password — AI Employee",
    }
    title_map = {
        "email_verify": "Email Verification Code",
        "two_factor": "Two-Factor Authentication",
        "forgot_password": "Password Reset Code",
    }
    desc_map = {
        "email_verify": "Please use the code below to verify your email address.",
        "two_factor": "Use this code to complete your login. Do not share it with anyone.",
        "forgot_password": "Use this code to reset your password. It expires in 5 minutes.",
    }

    subject = subject_map.get(purpose, "Your OTP Code — AI Employee")
    title = title_map.get(purpose, "One-Time Password")
    description = desc_map.get(purpose, "Your OTP code is below.")

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#0f0f1a;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f1a;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background:linear-gradient(145deg,#1a1a2e,#16213e);border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,0.08);">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:32px 40px;text-align:center;">
              <div style="font-size:28px;font-weight:700;color:#fff;letter-spacing:-0.5px;">
                🤖 AI Employee
              </div>
              <div style="color:rgba(255,255,255,0.8);font-size:14px;margin-top:4px;">{title}</div>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px;">
              <p style="color:#e2e8f0;font-size:16px;margin:0 0 8px;">Hi <strong>{to_name}</strong>,</p>
              <p style="color:#94a3b8;font-size:15px;margin:0 0 32px;">{description}</p>

              <!-- OTP Box -->
              <div style="background:rgba(99,102,241,0.12);border:1px solid rgba(99,102,241,0.4);border-radius:12px;padding:28px;text-align:center;margin-bottom:32px;">
                <div style="font-size:11px;text-transform:uppercase;letter-spacing:2px;color:#6366f1;font-weight:600;margin-bottom:12px;">Your One-Time Code</div>
                <div style="font-size:48px;font-weight:800;letter-spacing:16px;color:#ffffff;font-family:'Courier New',monospace;">{otp_code}</div>
                <div style="font-size:12px;color:#64748b;margin-top:12px;">⏱ Expires in <strong style="color:#f59e0b;">5 minutes</strong></div>
              </div>

              <p style="color:#64748b;font-size:13px;margin:0;line-height:1.6;">
                If you didn't request this, you can safely ignore this email. 
                Never share your OTP with anyone — our team will never ask for it.
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px 32px;border-top:1px solid rgba(255,255,255,0.06);">
              <p style="color:#475569;font-size:12px;text-align:center;margin:0;">
                © 2024 AI Employee · Secure automated email
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    payload = {
        "sender": {"name": "AI Employee", "email": settings.BREVO_SENDER_EMAIL},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": settings.BREVO_API_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(BREVO_API_URL, json=payload, headers=headers)
            if response.status_code in (200, 201):
                logger.info(f"[EMAIL] OTP sent to {to_email} (purpose={purpose})")
                return True
            else:
                logger.error(f"[EMAIL] Brevo error {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send OTP email: {e}")
        return False
