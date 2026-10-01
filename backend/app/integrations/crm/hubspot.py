"""
CRM abstraction — provider-agnostic interface.
Start with HubSpot; swap with Salesforce/Zoho by swapping the provider.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from app.core.logging import logger


@dataclass
class CRMLead:
    id: str | None
    full_name: str
    phone: str
    email: str | None
    budget: float | None
    requirements: dict
    status: str
    score: str
    notes: str | None


class CRMProvider(ABC):
    @abstractmethod
    async def create_lead(self, lead: CRMLead) -> str:
        """Returns the CRM lead/contact ID."""
        pass

    @abstractmethod
    async def update_lead(self, crm_id: str, updates: dict) -> bool:
        pass

    @abstractmethod
    async def add_note(self, crm_id: str, note: str) -> bool:
        pass

    @abstractmethod
    async def change_stage(self, crm_id: str, stage: str) -> bool:
        pass

    @abstractmethod
    async def get_lead(self, crm_id: str) -> CRMLead | None:
        pass


class HubSpotCRM(CRMProvider):
    def __init__(self, access_token: str):
        from hubspot import HubSpot
        self.client = HubSpot(access_token=access_token)

    async def create_lead(self, lead: CRMLead) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        
        def _create():
            from hubspot.crm.contacts import SimplePublicObjectInput
            properties = {
                "firstname": lead.full_name.split()[0] if lead.full_name else "",
                "lastname": " ".join(lead.full_name.split()[1:]) if lead.full_name and len(lead.full_name.split()) > 1 else "",
                "phone": lead.phone,
                "email": lead.email or "",
                "hs_lead_status": "NEW",
            }
            contact = self.client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=SimplePublicObjectInput(properties=properties)
            )
            return contact.id

        contact_id = await loop.run_in_executor(None, _create)
        logger.info(f"✅ HubSpot lead created: {contact_id}")
        return contact_id

    async def update_lead(self, crm_id: str, updates: dict) -> bool:
        import asyncio
        loop = asyncio.get_event_loop()

        def _update():
            from hubspot.crm.contacts import SimplePublicObjectInput
            self.client.crm.contacts.basic_api.update(
                contact_id=crm_id,
                simple_public_object_input=SimplePublicObjectInput(properties=updates),
            )
        await loop.run_in_executor(None, _update)
        return True

    async def add_note(self, crm_id: str, note: str) -> bool:
        # HubSpot notes are Engagements
        logger.info(f"📝 Adding note to HubSpot contact {crm_id}")
        return True  # TODO: implement via engagements API

    async def change_stage(self, crm_id: str, stage: str) -> bool:
        return await self.update_lead(crm_id, {"hs_lead_status": stage.upper()})

    async def get_lead(self, crm_id: str) -> CRMLead | None:
        import asyncio
        loop = asyncio.get_event_loop()

        def _get():
            return self.client.crm.contacts.basic_api.get_by_id(contact_id=crm_id)

        contact = await loop.run_in_executor(None, _get)
        p = contact.properties
        return CRMLead(
            id=contact.id,
            full_name=f"{p.get('firstname', '')} {p.get('lastname', '')}".strip(),
            phone=p.get("phone", ""),
            email=p.get("email"),
            budget=None,
            requirements={},
            status=p.get("hs_lead_status", "NEW"),
            score="cold",
            notes=None,
        )


class MockCRM(CRMProvider):
    """Use this for development/testing without real CRM credentials."""
    async def create_lead(self, lead: CRMLead) -> str:
        logger.info(f"[MOCK CRM] create_lead: {lead.full_name} ({lead.phone})")
        return f"mock-lead-{lead.phone[-4:]}"

    async def update_lead(self, crm_id: str, updates: dict) -> bool:
        logger.info(f"[MOCK CRM] update_lead {crm_id}: {updates}")
        return True

    async def add_note(self, crm_id: str, note: str) -> bool:
        logger.info(f"[MOCK CRM] add_note {crm_id}: {note[:60]}")
        return True

    async def change_stage(self, crm_id: str, stage: str) -> bool:
        logger.info(f"[MOCK CRM] change_stage {crm_id} → {stage}")
        return True

    async def get_lead(self, crm_id: str) -> CRMLead | None:
        return None


def get_crm(provider: str = "hubspot", **kwargs) -> CRMProvider:
    if provider == "hubspot":
        from app.core.config import settings
        return HubSpotCRM(access_token=settings.HUBSPOT_ACCESS_TOKEN)
    elif provider == "mock":
        return MockCRM()
    raise ValueError(f"Unknown CRM provider: {provider}")
