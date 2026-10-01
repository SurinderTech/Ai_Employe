from fastapi import APIRouter, Depends
from app.models.user import User
from app.security.auth import get_current_user

router = APIRouter()

@router.get("")
async def list_items(current_user: User = Depends(get_current_user)):
    return {"items": [], "note": "Appointments endpoint — coming soon"}
