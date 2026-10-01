"""API v1 router — aggregates all sub-routers."""
from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.businesses import router as businesses_router
from app.api.v1.agents import router as agents_router
from app.api.v1.calls import router as calls_router
from app.api.v1.leads import router as leads_router
from app.api.v1.appointments import router as appointments_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.knowledge import router as knowledge_router

router = APIRouter()

router.include_router(auth_router,          prefix="/auth",          tags=["Auth"])
router.include_router(businesses_router,    prefix="/businesses",    tags=["Businesses"])
router.include_router(agents_router,        prefix="/agents",        tags=["Agents"])
router.include_router(calls_router,         prefix="/calls",         tags=["Calls"])
router.include_router(leads_router,         prefix="/leads",         tags=["Leads"])
router.include_router(appointments_router,  prefix="/appointments",  tags=["Appointments"])
router.include_router(conversations_router, prefix="/conversations",  tags=["Conversations"])
router.include_router(integrations_router,  prefix="/integrations",  tags=["Integrations"])
router.include_router(webhooks_router,      prefix="/webhooks",      tags=["Webhooks"])
router.include_router(knowledge_router,     prefix="/knowledge",     tags=["Knowledge"])
