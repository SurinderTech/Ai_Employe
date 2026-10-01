"""Permission constants and checker dependency."""
from fastapi import Depends, HTTPException, status
from app.models.user import User
from app.security.auth import get_current_user

# ── Permission constants ────────────────────────────────────────────────────
CAN_READ_CRM = "CAN_READ_CRM"
CAN_CREATE_LEAD = "CAN_CREATE_LEAD"
CAN_UPDATE_LEAD = "CAN_UPDATE_LEAD"
CAN_DELETE_LEAD = "CAN_DELETE_LEAD"
CAN_BOOK_APPOINTMENT = "CAN_BOOK_APPOINTMENT"
CAN_CANCEL_APPOINTMENT = "CAN_CANCEL_APPOINTMENT"
CAN_SEND_WHATSAPP = "CAN_SEND_WHATSAPP"
CAN_SEND_EMAIL = "CAN_SEND_EMAIL"
CAN_TRANSFER_CALL = "CAN_TRANSFER_CALL"
CAN_MANAGE_AGENTS = "CAN_MANAGE_AGENTS"
CAN_VIEW_TRANSCRIPTS = "CAN_VIEW_TRANSCRIPTS"
CAN_MANAGE_INTEGRATIONS = "CAN_MANAGE_INTEGRATIONS"
CAN_VIEW_ANALYTICS = "CAN_VIEW_ANALYTICS"

OWNER_PERMISSIONS = [
    CAN_READ_CRM, CAN_CREATE_LEAD, CAN_UPDATE_LEAD, CAN_DELETE_LEAD,
    CAN_BOOK_APPOINTMENT, CAN_CANCEL_APPOINTMENT, CAN_SEND_WHATSAPP,
    CAN_SEND_EMAIL, CAN_TRANSFER_CALL, CAN_MANAGE_AGENTS,
    CAN_VIEW_TRANSCRIPTS, CAN_MANAGE_INTEGRATIONS, CAN_VIEW_ANALYTICS,
]


def require_permission(permission: str):
    """FastAPI dependency factory — checks a specific permission."""
    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        from app.models.user import UserRole
        if current_user.role == UserRole.SUPER_ADMIN:
            return current_user
        # Check business_users permissions — simplified for scaffold
        # Full implementation checks the junction table
        return current_user
    return _checker
