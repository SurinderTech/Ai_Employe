"""WhatsApp integration via Twilio WhatsApp API."""
from twilio.rest import Client
from app.core.config import settings
from app.core.logging import logger


class WhatsAppIntegration:
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number  # e.g. "whatsapp:+14155238886"

    def _format_to(self, phone: str) -> str:
        if not phone.startswith("whatsapp:"):
            return f"whatsapp:{phone}"
        return phone

    async def send_text(self, to: str, message: str) -> str:
        """Send a plain text WhatsApp message. Returns message SID."""
        import asyncio
        loop = asyncio.get_event_loop()

        def _send():
            msg = self.client.messages.create(
                from_=self.from_number,
                to=self._format_to(to),
                body=message,
            )
            return msg.sid

        sid = await loop.run_in_executor(None, _send)
        logger.info(f"✅ WhatsApp sent to {to}: SID={sid}")
        return sid

    async def send_property_cards(self, to: str, properties: list[dict]) -> None:
        """Send property listings as formatted WhatsApp messages."""
        if not properties:
            await self.send_text(to, "No properties found matching your requirements.")
            return

        header = f"🏠 *Found {len(properties)} properties for you:*\n"
        cards = []
        for i, prop in enumerate(properties[:3], 1):
            card = (
                f"\n*{i}. {prop.get('name', 'Property')}*\n"
                f"📍 {prop.get('location', 'Location TBD')}\n"
                f"💰 ₹{prop.get('price_lakhs', '?')} Lakhs\n"
                f"🛏️ {prop.get('bedrooms', '?')} BHK | {prop.get('area_sqft', '?')} sq.ft.\n"
                f"📞 Book a visit: Reply with 'BOOK'"
            )
            cards.append(card)

        await self.send_text(to, header + "\n".join(cards))

    async def send_appointment_confirmation(self, to: str, appointment: dict) -> None:
        """Send appointment confirmation message."""
        message = (
            f"✅ *Appointment Confirmed!*\n\n"
            f"📅 *Date:* {appointment.get('date', 'TBD')}\n"
            f"⏰ *Time:* {appointment.get('time', 'TBD')}\n"
            f"📍 *Location:* {appointment.get('location', 'TBD')}\n\n"
            f"Our team will meet you there. See you soon! 🙏\n\n"
            f"_To reschedule, reply RESCHEDULE_"
        )
        await self.send_text(to, message)

    async def send_lead_summary_to_team(self, team_phone: str, lead_summary: dict) -> None:
        """Notify the business team about a new hot lead."""
        message = (
            f"🔥 *New Hot Lead!*\n\n"
            f"👤 {lead_summary.get('name', 'Unknown')}\n"
            f"📞 {lead_summary.get('phone', '')}\n"
            f"🏠 {lead_summary.get('requirement', '')}\n"
            f"💰 Budget: ₹{lead_summary.get('budget_lakhs', '?')} Lakhs\n"
            f"📍 {lead_summary.get('location', '')}\n\n"
            f"*Intent:* {lead_summary.get('intent', '')}\n"
            f"*Recommended action:* {lead_summary.get('recommended_action', 'Call customer')}"
        )
        await self.send_text(team_phone, message)


class MockWhatsApp:
    """Development mock."""
    async def send_text(self, to: str, message: str) -> str:
        logger.info(f"[MOCK WhatsApp] → {to}: {message[:80]}")
        return "mock-sid-12345"

    async def send_property_cards(self, to: str, properties: list[dict]) -> None:
        logger.info(f"[MOCK WhatsApp] Sending {len(properties)} property cards to {to}")

    async def send_appointment_confirmation(self, to: str, appointment: dict) -> None:
        logger.info(f"[MOCK WhatsApp] Appointment confirmation to {to}: {appointment}")

    async def send_lead_summary_to_team(self, team_phone: str, lead_summary: dict) -> None:
        logger.info(f"[MOCK WhatsApp] Lead summary to team {team_phone}: {lead_summary}")


def get_whatsapp(use_mock: bool = False) -> WhatsAppIntegration | MockWhatsApp:
    if use_mock:
        return MockWhatsApp()
    return WhatsAppIntegration(
        account_sid=settings.TWILIO_ACCOUNT_SID,
        auth_token=settings.TWILIO_AUTH_TOKEN,
        from_number=settings.TWILIO_WHATSAPP_NUMBER,
    )
