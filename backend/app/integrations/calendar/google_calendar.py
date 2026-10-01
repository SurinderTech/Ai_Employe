"""Google Calendar integration — check availability and book appointments."""
import asyncio
from datetime import datetime, timedelta, timezone
from app.core.logging import logger


class GoogleCalendarIntegration:
    def __init__(self, credentials_json: str, token_json: str):
        self.credentials_json = credentials_json
        self.token_json = token_json
        self._service = None

    def _get_service(self):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        import json

        creds = Credentials.from_authorized_user_info(
            json.loads(self.token_json),
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        return build("calendar", "v3", credentials=creds)

    async def get_available_slots(
        self,
        calendar_id: str = "primary",
        date: datetime | None = None,
        duration_minutes: int = 60,
        num_slots: int = 5,
    ) -> list[dict]:
        """Returns available time slots for a given date."""
        loop = asyncio.get_event_loop()

        def _fetch():
            service = self._get_service()
            if not date:
                target_date = datetime.now(timezone.utc) + timedelta(days=1)
            else:
                target_date = date

            time_min = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            time_max = target_date.replace(hour=20, minute=0, second=0, microsecond=0)

            # Get busy slots
            body = {"timeMin": time_min.isoformat(), "timeMax": time_max.isoformat(), "items": [{"id": calendar_id}]}
            freebusy = service.freebusy().query(body=body).execute()
            busy = freebusy.get("calendars", {}).get(calendar_id, {}).get("busy", [])

            # Generate available slots
            available = []
            slot_start = time_min
            while slot_start + timedelta(minutes=duration_minutes) <= time_max and len(available) < num_slots:
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                is_busy = any(
                    datetime.fromisoformat(b["start"]) < slot_end and
                    datetime.fromisoformat(b["end"]) > slot_start
                    for b in busy
                )
                if not is_busy:
                    available.append({
                        "start": slot_start.isoformat(),
                        "end": slot_end.isoformat(),
                        "label": slot_start.strftime("%I:%M %p"),
                    })
                slot_start += timedelta(minutes=30)
            return available

        return await loop.run_in_executor(None, _fetch)

    async def create_event(
        self,
        title: str,
        start_time: datetime,
        duration_minutes: int,
        attendee_email: str | None = None,
        description: str | None = None,
        calendar_id: str = "primary",
    ) -> dict:
        """Creates a calendar event and returns event ID + meet link."""
        loop = asyncio.get_event_loop()

        def _create():
            service = self._get_service()
            end_time = start_time + timedelta(minutes=duration_minutes)
            event = {
                "summary": title,
                "description": description or "",
                "start": {"dateTime": start_time.isoformat(), "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": end_time.isoformat(), "timeZone": "Asia/Kolkata"},
                "conferenceData": {"createRequest": {"requestId": f"ai-{start_time.timestamp()}"}},
                "reminders": {"useDefault": False, "overrides": [
                    {"method": "email", "minutes": 60},
                    {"method": "popup", "minutes": 30},
                ]},
            }
            if attendee_email:
                event["attendees"] = [{"email": attendee_email}]

            result = service.events().insert(
                calendarId=calendar_id,
                body=event,
                conferenceDataVersion=1,
                sendUpdates="all",
            ).execute()
            return {
                "event_id": result["id"],
                "html_link": result.get("htmlLink"),
                "meet_link": result.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri"),
            }

        return await loop.run_in_executor(None, _create)

    async def cancel_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        loop = asyncio.get_event_loop()
        def _cancel():
            service = self._get_service()
            service.events().delete(calendarId=calendar_id, eventId=event_id, sendUpdates="all").execute()
        await loop.run_in_executor(None, _cancel)
        logger.info(f"🗑️ Calendar event cancelled: {event_id}")
        return True


class MockCalendar:
    """Development mock — no real Google API calls."""
    async def get_available_slots(self, **kwargs) -> list[dict]:
        from datetime import date
        tomorrow = datetime.now() + timedelta(days=1)
        return [
            {"start": tomorrow.replace(hour=11, minute=0).isoformat(), "label": "11:00 AM"},
            {"start": tomorrow.replace(hour=14, minute=30).isoformat(), "label": "2:30 PM"},
            {"start": tomorrow.replace(hour=17, minute=0).isoformat(), "label": "5:00 PM"},
        ]

    async def create_event(self, **kwargs) -> dict:
        return {"event_id": "mock-event-123", "html_link": "#", "meet_link": None}

    async def cancel_event(self, event_id: str, **kwargs) -> bool:
        logger.info(f"[MOCK Calendar] cancel: {event_id}")
        return True
