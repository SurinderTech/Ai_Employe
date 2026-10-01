"""
Twilio Webhooks — entry point for all inbound calls and WhatsApp messages.

Flow (voice):
  Customer calls Twilio number
    → POST /webhooks/twilio/voice/inbound   (greeting + Gather)
    → POST /webhooks/twilio/voice/process   (speech → AI → TwiML response, loop)
    → POST /webhooks/twilio/voice/status    (call ended → finalise DB records)

Flow (WhatsApp):
  Customer sends message
    → POST /webhooks/twilio/whatsapp/inbound → AI → send reply
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response, Depends
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse, Gather
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.database.session import get_db

router = APIRouter()


# ── Twilio Signature Validation ───────────────────────────────────────────────

async def _validate_twilio(request: Request) -> bool:
    """Verify request is genuinely from Twilio."""
    if settings.DEBUG:
        return True  # Skip validation in dev
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    form = dict(await request.form())
    return validator.validate(url, form, signature)


# ── Business lookup helpers ───────────────────────────────────────────────────

async def _get_business_and_agent(to_number: str, db: AsyncSession):
    """
    Look up which Business owns this Twilio number, and return its active agent.
    Falls back gracefully for dev/demo.
    """
    from app.models.agent import Agent, AgentStatus
    from app.models.business import Business

    # Find agent with this phone number
    result = await db.execute(
        select(Agent).where(
            Agent.phone_number == to_number,
            Agent.is_active == True,
            Agent.status == AgentStatus.ACTIVE,
        )
    )
    agent = result.scalar_one_or_none()

    if agent:
        biz_result = await db.execute(
            select(Business).where(Business.id == agent.business_id)
        )
        business = biz_result.scalar_one_or_none()
        return business, agent

    # Dev fallback: return first active business + agent
    biz_result = await db.execute(select(Business).limit(1))
    business = biz_result.scalar_one_or_none()
    agent_result = await db.execute(select(Agent).limit(1))
    agent = agent_result.scalar_one_or_none()
    return business, agent


async def _get_or_create_conversation(
    business_id: uuid.UUID,
    customer_phone: str,
    call_sid: str,
    db: AsyncSession,
    agent_id: uuid.UUID | None = None,
):
    """Find an existing active conversation for this call SID or create one."""
    from app.models.conversation import Conversation, Call, ConversationChannel, ConversationStatus, CallStatus

    # Find existing Call by SID
    call_result = await db.execute(
        select(Call).where(Call.twilio_call_sid == call_sid)
    )
    existing_call = call_result.scalar_one_or_none()
    if existing_call and existing_call.conversation_id:
        conv_result = await db.execute(
            select(Conversation).where(Conversation.id == existing_call.conversation_id)
        )
        return conv_result.scalar_one_or_none(), existing_call

    # Create new conversation
    conversation = Conversation(
        business_id=business_id,
        agent_id=agent_id,
        channel=ConversationChannel.PHONE,
        status=ConversationStatus.ACTIVE,
    )
    db.add(conversation)
    await db.flush()

    # Create Call record
    call = Call(
        business_id=business_id,
        conversation_id=conversation.id,
        twilio_call_sid=call_sid,
        from_number=customer_phone,
        to_number="",   # updated below by caller
        direction="inbound",
        status=CallStatus.IN_PROGRESS,
        answered_at=datetime.now(timezone.utc),
    )
    db.add(call)
    await db.flush()

    return conversation, call


# ── Voice: Inbound ────────────────────────────────────────────────────────────

@router.post("/twilio/voice/inbound")
async def twilio_voice_inbound(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Twilio calls this when a customer rings our number.
    1. Look up business + agent
    2. Create Conversation + Call records
    3. Respond with TwiML greeting + Gather (speech input)
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")

    logger.info(f"Inbound call | from={from_number} to={to_number} SID={call_sid}")

    # ── Rate limit per caller number ──────────────────────────────────────────
    from app.core.redis import check_rate_limit
    rate_key = f"rl:voice:{from_number}"
    allowed, hit_count = await check_rate_limit(rate_key)
    if not allowed:
        logger.warning(f"Rate limit exceeded for {from_number} ({hit_count} calls)")
        twiml = VoiceResponse()
        twiml.say(
            "We are currently experiencing high call volume. "
            "Please try again in a few minutes. Goodbye!",
            voice="Polly.Aditi",
            language="en-IN",
        )
        twiml.hangup()
        return Response(content=str(twiml), media_type="application/xml")


    # Look up business and agent
    business, agent = await _get_business_and_agent(to_number, db)
    business_id = str(business.id) if business else "00000000-0000-0000-0000-000000000000"
    agent_id = str(agent.id) if agent else None

    # Create conversation + call records
    try:
        conversation, call = await _get_or_create_conversation(
            business_id=uuid.UUID(business_id),
            customer_phone=from_number,
            call_sid=call_sid,
            db=db,
            agent_id=uuid.UUID(agent_id) if agent_id else None,
        )
        call.to_number = to_number
        conversation_id = str(conversation.id)
    except Exception as e:
        logger.error(f"Conversation creation failed: {e}")
        conversation_id = str(uuid.uuid4())

    # Determine greeting
    greeting = "Hello! Thank you for calling. How can I help you today?"
    if agent and agent.config and agent.config.greeting_message:
        greeting = agent.config.greeting_message
    elif business:
        greeting = f"Hello! Thank you for calling {business.name}. How can I help you today?"

    # TwiML response: greet + gather speech
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=(
            f"/api/v1/webhooks/twilio/voice/process"
            f"?business_id={business_id}"
            f"&conversation_id={conversation_id}"
            f"&agent_id={agent_id or ''}"
            f"&call_sid={call_sid}"
        ),
        method="POST",
        speech_timeout="auto",
        language="en-IN",
        action_on_empty_result=True,
    )
    gather.say(greeting, voice="Polly.Aditi", language="en-IN")
    response.append(gather)
    # Fallback if no speech detected
    response.say("I didn't catch that. Please try again.", voice="Polly.Aditi")
    response.redirect(
        f"/api/v1/webhooks/twilio/voice/inbound?business_id={business_id}",
        method="POST",
    )

    return Response(content=str(response), media_type="application/xml")


# ── Voice: Process (main AI loop) ─────────────────────────────────────────────

@router.post("/twilio/voice/process")
async def twilio_voice_process(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Receives transcribed speech from Twilio Gather.
    Passes to the AI orchestrator → gets response → returns TwiML to Twilio.
    This is the main conversation loop.
    """
    form_data = await request.form()
    speech_result = form_data.get("SpeechResult", "").strip()
    call_sid = form_data.get("CallSid", "")
    confidence = form_data.get("Confidence", "0")

    # Read from query params (set by inbound handler)
    params = request.query_params
    business_id = params.get("business_id", "")
    conversation_id = params.get("conversation_id", str(uuid.uuid4()))
    agent_id = params.get("agent_id") or None

    logger.info(
        f"🎤 Speech received | '{speech_result}' | SID={call_sid} "
        f"confidence={confidence}"
    )

    # Handle empty speech
    if not speech_result:
        response = VoiceResponse()
        gather = Gather(
            input="speech",
            action=(
                f"/api/v1/webhooks/twilio/voice/process"
                f"?business_id={business_id}"
                f"&conversation_id={conversation_id}"
                f"&agent_id={agent_id or ''}"
                f"&call_sid={call_sid}"
            ),
            method="POST",
            speech_timeout="auto",
            language="en-IN",
        )
        gather.say(
            "I'm sorry, I didn't catch that. Could you please repeat?",
            voice="Polly.Aditi",
            language="en-IN",
        )
        response.append(gather)
        return Response(content=str(response), media_type="application/xml")

    # ── Save customer message to DB ───────────────────────────────────────────
    from_number = form_data.get("From", "unknown")
    try:
        from app.memory import save_message
        from app.models.conversation import MessageRole
        await save_message(
            conversation_id=conversation_id,
            role=MessageRole.CUSTOMER,
            content=speech_result,
            db=db,
            metadata={"call_sid": call_sid, "confidence": confidence},
        )
    except Exception as e:
        logger.error(f"Save customer message failed: {e}")

    # ── Load conversation history ─────────────────────────────────────────────
    try:
        from app.memory import load_conversation_history
        history = await load_conversation_history(conversation_id, db, limit=10)
    except Exception as e:
        logger.error(f"Load history failed: {e}")
        history = []

    # ── Run AI orchestrator ───────────────────────────────────────────────────
    try:
        from app.agents.orchestrator.graph import process_customer_input
        ai_result = await process_customer_input(
            user_input=speech_result,
            conversation_id=conversation_id,
            business_id=business_id,
            customer_phone=from_number,
            conversation_history=history,
            db=db,
            agent_id=agent_id,
        )
        ai_response = ai_result["response"]
        next_action = ai_result["next_action"]
        logger.info(
            f"🤖 AI responded in {ai_result['latency_ms']}ms | "
            f"intent={ai_result['intent']} | action={next_action}"
        )
    except Exception as e:
        logger.error(f"AI orchestrator failed: {e}")
        ai_response = (
            "I apologise, I'm experiencing a brief technical issue. "
            "Please hold and one of our team members will assist you shortly."
        )
        next_action = "continue"

    # ── Save AI response to DB ────────────────────────────────────────────────
    try:
        from app.memory import save_message
        from app.models.conversation import MessageRole
        await save_message(
            conversation_id=conversation_id,
            role=MessageRole.AGENT,
            content=ai_response,
            db=db,
        )
    except Exception as e:
        logger.error(f"Save agent message failed: {e}")

    # ── Build TwiML response ──────────────────────────────────────────────────
    response = VoiceResponse()

    if next_action == "human_handoff":
        # Say the AI transition message, then dial the real team phone.
        # Falls back gracefully if ESCALATION_PHONE is not configured.
        response.say(ai_response, voice="Polly.Aditi", language="en-IN")

        escalation_phone = settings.ESCALATION_PHONE.strip()
        if escalation_phone:
            # Brief hold while we connect
            response.say(
                "Please hold for a moment while I connect you.",
                voice="Polly.Aditi", language="en-IN",
            )
            dial = response.dial(
                action=(
                    f"/api/v1/webhooks/twilio/voice/dial-status"
                    f"?business_id={business_id}&conversation_id={conversation_id}"
                ),
                timeout=settings.ESCALATION_DIAL_TIMEOUT,
                caller_id=settings.TWILIO_PHONE_NUMBER or None,
            )
            dial.number(escalation_phone)
        else:
            # No escalation number — tell customer team will call back
            response.say(
                "Our team will call you back within the next few minutes. "
                "Thank you for your patience. Goodbye!",
                voice="Polly.Aditi", language="en-IN",
            )
            response.hangup()

    elif next_action == "end_call":
        response.say(ai_response, voice="Polly.Aditi", language="en-IN")
        response.hangup()

    else:
        # Continue conversation loop
        gather = Gather(
            input="speech",
            action=(
                f"/api/v1/webhooks/twilio/voice/process"
                f"?business_id={business_id}"
                f"&conversation_id={conversation_id}"
                f"&agent_id={agent_id or ''}"
                f"&call_sid={call_sid}"
            ),
            method="POST",
            speech_timeout="auto",
            language="en-IN",
            action_on_empty_result=True,
        )
        gather.say(ai_response, voice="Polly.Aditi", language="en-IN")
        response.append(gather)
        # Fallback: if no response, say goodbye
        response.say(
            "I didn't hear anything. Thank you for calling. Goodbye!",
            voice="Polly.Aditi",
        )
        response.hangup()

    return Response(content=str(response), media_type="application/xml")


# ── Voice: Status Callback ────────────────────────────────────────────────────

@router.post("/twilio/voice/status")
async def twilio_call_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Twilio calls this when call status changes (completed, failed, busy, no-answer).
    Finalises the Call record and triggers post-call automation.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")
    duration = form_data.get("CallDuration")
    recording_url = form_data.get("RecordingUrl")

    logger.info(f"📞 Call status | SID={call_sid} status={call_status} duration={duration}s")

    try:
        from app.models.conversation import Call, CallStatus, Conversation, ConversationStatus
        from sqlalchemy import select

        result = await db.execute(select(Call).where(Call.twilio_call_sid == call_sid))
        call = result.scalar_one_or_none()

        if call:
            status_map = {
                "completed": CallStatus.COMPLETED,
                "failed": CallStatus.FAILED,
                "busy": CallStatus.BUSY,
                "no-answer": CallStatus.NO_ANSWER,
                "canceled": CallStatus.FAILED,
            }
            call.status = status_map.get(call_status, CallStatus.COMPLETED)
            call.duration_seconds = int(duration) if duration else None
            call.recording_url = recording_url
            call.ended_at = datetime.now(timezone.utc)

            # Close conversation
            if call.conversation_id:
                conv_result = await db.execute(
                    select(Conversation).where(Conversation.id == call.conversation_id)
                )
                conv = conv_result.scalar_one_or_none()
                if conv and conv.status == ConversationStatus.ACTIVE:
                    conv.status = ConversationStatus.COMPLETED
                    conv.ended_at = datetime.now(timezone.utc)

    except Exception as e:
        logger.error(f"Call status update failed: {e}")

    return Response(status_code=204)


# ── WhatsApp: Inbound ─────────────────────────────────────────────────────────

@router.post("/twilio/whatsapp/inbound")
async def twilio_whatsapp_inbound(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Receives inbound WhatsApp messages.
    Routes through the AI orchestrator and sends a reply.
    """
    form_data = await request.form()
    from_number = form_data.get("From", "").replace("whatsapp:", "")
    body = form_data.get("Body", "").strip()
    num_media = int(form_data.get("NumMedia", "0"))

    logger.info(f"💬 WhatsApp inbound | from={from_number} body='{body[:80]}'")

    if not body and num_media == 0:
        return Response(status_code=204)

    # Get or create conversation for this WhatsApp customer
    # Use a simple business lookup (first active business for now)
    from app.models.business import Business
    biz_result = await db.execute(select(Business).limit(1))
    business = biz_result.scalar_one_or_none()

    if not business:
        logger.warning("No business found for WhatsApp inbound")
        return Response(status_code=204)

    business_id = str(business.id)

    # Create/find conversation
    from app.models.conversation import Conversation, ConversationChannel, ConversationStatus
    conv = Conversation(
        business_id=business.id,
        channel=ConversationChannel.WHATSAPP,
        status=ConversationStatus.ACTIVE,
    )
    db.add(conv)
    await db.flush()
    conversation_id = str(conv.id)

    # Save inbound message
    try:
        from app.memory import save_message
        from app.models.conversation import MessageRole
        await save_message(conversation_id, MessageRole.CUSTOMER, body, db)
    except Exception as e:
        logger.error(f"Save WhatsApp message failed: {e}")

    # Run AI
    try:
        from app.agents.orchestrator.graph import process_customer_input
        ai_result = await process_customer_input(
            user_input=body,
            conversation_id=conversation_id,
            business_id=business_id,
            customer_phone=from_number,
            db=db,
        )
        ai_response = ai_result["response"]

        # Send WhatsApp reply
        from app.tools.communication_tools import _get_whatsapp
        wa = _get_whatsapp()
        await wa.send_text(from_number, ai_response)

        # Save agent response
        from app.memory import save_message
        from app.models.conversation import MessageRole
        await save_message(conversation_id, MessageRole.AGENT, ai_response, db)

    except Exception as e:
        logger.error(f"WhatsApp AI processing failed: {e}")

    return Response(status_code=204)


# ── Voice: Dial Status (escalation outcome) ───────────────────────────────────

@router.post("/twilio/voice/dial-status")
async def twilio_dial_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Called by Twilio after a <Dial> completes.
    DialCallStatus can be: completed | busy | no-answer | failed | canceled

    If the human agent didn't pick up, we play a fallback message
    instead of leaving the customer in dead air.
    """
    form_data = await request.form()
    dial_status = form_data.get("DialCallStatus", "")
    call_sid = form_data.get("CallSid", "")
    params = request.query_params
    conversation_id = params.get("conversation_id", "")

    logger.info(f"📞 Dial status | SID={call_sid} status={dial_status}")

    response = VoiceResponse()

    if dial_status == "completed":
        # Human picked up and call completed normally — just hang up
        response.hangup()

    else:
        # Human didn't answer (busy / no-answer / failed / canceled)
        logger.warning(
            f"Human agent did not answer escalation | "
            f"status={dial_status} conversation={conversation_id}"
        )
        response.say(
            "I'm sorry, our team member is currently unavailable. "
            "We have noted your request and someone will call you back "
            "within 15 minutes. Thank you for your patience. Goodbye!",
            voice="Polly.Aditi",
            language="en-IN",
        )
        response.hangup()

        # Update conversation status to reflect missed escalation
        if conversation_id:
            try:
                from app.models.conversation import Conversation, ConversationStatus
                from sqlalchemy import select
                result = await db.execute(
                    select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
                )
                conv = result.scalar_one_or_none()
                if conv:
                    conv.status = ConversationStatus.ESCALATED
                    await db.flush()
            except Exception as e:
                logger.error(f"Dial status conversation update failed: {e}")

    return Response(content=str(response), media_type="application/xml")

