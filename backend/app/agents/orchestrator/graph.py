"""
AI Orchestrator — the central brain using LangGraph.

Graph:
  START → receptionist → intent_classifier → router
                                                ├─ lead_agent    → responder → END
                                                ├─ booking_agent → responder → END
                                                ├─ support_agent → responder → END
                                                └─ human_handoff → END

Every node now:
  - Uses real tool calls (CRM, Calendar, WhatsApp, RAG)
  - Persists AgentRun + ToolCall records to DB
  - Loads from and writes to customer memory
"""
from __future__ import annotations
import json
import time
import uuid
from datetime import datetime, timezone
from typing import TypedDict, Annotated, Literal, Any

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger


# ── Agent State ───────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    # ── Identifiers ──────────────────────────────────────────────────────────
    conversation_id: str
    business_id: str
    customer_phone: str
    agent_run_id: str | None   # set after AgentRun row is created

    # ── Input ────────────────────────────────────────────────────────────────
    user_input: str

    # ── Context (loaded at start) ────────────────────────────────────────────
    conversation_history: list[dict]
    customer_memory: dict            # from Customer.preferences
    business_context: str            # top RAG chunks

    # ── AI Decisions ─────────────────────────────────────────────────────────
    intent: str
    entities: dict
    plan: list[str]

    # ── Tool Results ─────────────────────────────────────────────────────────
    tool_results: dict

    # ── Output ───────────────────────────────────────────────────────────────
    response: str
    escalate: bool
    escalation_reason: str
    next_action: str   # continue | end_call | human_handoff

    # ── Runtime (injected, not part of LangGraph routing) ────────────────────
    # We pass db as a dict key so nodes can persist without side channels.
    # LangGraph serialises state via TypedDict; we store it as an opaque Any.
    _db: Any | None


# ── LLM helper ───────────────────────────────────────────────────────────────

def _llm(fast: bool = False) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_FAST_MODEL if fast else settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.3,
    )


def _db(state: AgentState) -> AsyncSession | None:
    return state.get("_db")


# ── Observability helpers ─────────────────────────────────────────────────────

async def _log_tool_call(
    agent_run_id: str,
    tool_name: str,
    input_args: dict,
    output: dict,
    status: str,
    latency_ms: int,
    db: AsyncSession,
) -> None:
    """Persist a ToolCall row for observability."""
    from app.models.conversation import ToolCall
    tc = ToolCall(
        agent_run_id=uuid.UUID(agent_run_id),
        tool_name=tool_name,
        input_args=input_args,
        output=output,
        status=status,
        latency_ms=latency_ms,
    )
    db.add(tc)
    try:
        await db.flush()
    except Exception as e:
        logger.warning(f"ToolCall flush failed: {e}")


# ── Graph Nodes ───────────────────────────────────────────────────────────────

async def receptionist_node(state: AgentState) -> AgentState:
    """
    1. Load customer memory from DB.
    2. Run RAG search over business knowledge base.
    3. Set business_context for downstream nodes.
    """
    logger.info(f"🎙️ Receptionist | input: {state['user_input'][:80]}")
    db = _db(state)

    # ── Load customer memory ──────────────────────────────────────────────────
    if db:
        try:
            from app.memory import load_customer_memory
            memory = await load_customer_memory(
                business_id=state["business_id"],
                phone=state["customer_phone"],
                db=db,
            )
            state["customer_memory"] = memory
            logger.info(
                f"🧠 Customer memory loaded | new={memory.get('is_new')} "
                f"name={memory.get('full_name')}"
            )
        except Exception as e:
            logger.error(f"Memory load failed: {e}")

    # ── RAG context ───────────────────────────────────────────────────────────
    if db:
        try:
            from app.tools.search_tools import search_knowledge
            rag_result = await search_knowledge(
                query=state["user_input"],
                business_id=state["business_id"],
                db=db,
                top_k=4,
            )
            state["business_context"] = rag_result["context"]
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            state["business_context"] = ""
    else:
        state["business_context"] = ""

    return state


async def intent_classifier_node(state: AgentState) -> AgentState:
    """
    Classify customer intent and extract entities using Gemini Flash.
    Produces structured JSON: intent + entities + escalation flag.
    """
    llm = _llm(fast=True)

    # Build a concise customer profile for the prompt
    mem = state.get("customer_memory", {})
    customer_context = ""
    if mem and not mem.get("is_new"):
        prefs = mem.get("preferences", {})
        customer_context = (
            f"Returning customer: {mem.get('full_name', 'Unknown')}. "
            f"Known preferences: {json.dumps(prefs)}"
        )

    system = f"""You are an intent classifier for a real estate AI assistant.

Business context (from knowledge base):
{state.get('business_context', '')[:800]}

{customer_context}

Classify the customer's message into ONE intent:
- property_inquiry: asking about properties, listings, availability
- appointment_request: wants to schedule/book a visit or meeting
- price_inquiry: asking about pricing, costs, payment plans
- support: general support question, status check
- complaint: expressing frustration, anger, dissatisfaction
- out_of_scope: completely unrelated to the business

Extract entities:
- budget: numeric value in INR (e.g. 5000000 for 50 Lakhs). null if not mentioned.
- location: city/area name. null if not mentioned.
- property_type: e.g. "2BHK", "3BHK", "villa", "commercial". null if not mentioned.
- bedrooms: integer. null if not mentioned.
- preferred_datetime: ISO string if date/time mentioned. null otherwise.
- customer_name: name if introduced themselves. null otherwise.

Respond ONLY with valid JSON — no markdown, no explanation:
{{
  "intent": "...",
  "confidence": 0.0,
  "entities": {{
    "budget": null,
    "location": null,
    "property_type": null,
    "bedrooms": null,
    "preferred_datetime": null,
    "customer_name": null
  }},
  "requires_escalation": false,
  "escalation_reason": null
}}"""

    history_str = json.dumps(state.get("conversation_history", [])[-6:], indent=2)
    prompt = f"Conversation history:\n{history_str}\n\nCustomer message: {state['user_input']}"

    try:
        resp = await llm.ainvoke([
            {"role": "system", "content": system},
            {"role": "human", "content": prompt},
        ])
        content = resp.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)
        state["intent"] = result.get("intent", "support")
        state["entities"] = result.get("entities", {})
        state["escalate"] = result.get("requires_escalation", False)
        state["escalation_reason"] = result.get("escalation_reason") or ""

        # Merge known customer name into entities
        if not state["entities"].get("customer_name") and state.get("customer_memory", {}).get("full_name"):
            state["entities"]["customer_name"] = state["customer_memory"]["full_name"]

        logger.info(f"🧠 Intent={state['intent']} | Entities={state['entities']} | Escalate={state['escalate']}")

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Intent classification failed: {e} — defaulting to support")
        state["intent"] = "support"
        state["entities"] = {}

    return state


async def lead_agent_node(state: AgentState) -> AgentState:
    """
    Handles property_inquiry / price_inquiry:
    1. Search properties in knowledge base
    2. Get or create customer
    3. Create lead in DB + CRM
    4. Send WhatsApp property cards
    5. Notify team if hot lead
    """
    logger.info(f"🏠 Lead Agent | intent={state['intent']}")
    db = _db(state)
    tool_results: dict = {}
    entities = state.get("entities", {})
    t0 = time.monotonic()

    # ── 1. Search properties ──────────────────────────────────────────────────
    if db:
        try:
            from app.tools.search_tools import search_properties
            search_result = await search_properties(
                query=state["user_input"],
                business_id=state["business_id"],
                db=db,
                filters={
                    "location": entities.get("location"),
                    "bedrooms": entities.get("bedrooms"),
                    "budget": entities.get("budget"),
                    "property_type": entities.get("property_type"),
                },
            )
            tool_results["properties"] = {
                "found": search_result["found"],
                "count": len(search_result["properties"]),
                "items": search_result["properties"],
                "context": search_result["context"][:500],
            }
            # Enrich business context with property results
            if search_result["context"]:
                state["business_context"] = (
                    state.get("business_context", "") + "\n\n" + search_result["context"]
                )
            if state.get("agent_run_id"):
                latency = int((time.monotonic() - t0) * 1000)
                await _log_tool_call(
                    state["agent_run_id"], "search_properties",
                    {"query": state["user_input"], "filters": entities},
                    tool_results["properties"], "success", latency, db,
                )
        except Exception as e:
            logger.error(f"search_properties failed: {e}")
            tool_results["properties"] = {"found": False, "error": str(e)}

    # ── 2. Get/create customer ────────────────────────────────────────────────
    customer = None
    if db:
        try:
            from app.tools.crm_tools import get_or_create_customer
            customer = await get_or_create_customer(
                business_id=state["business_id"],
                phone=state["customer_phone"],
                db=db,
                full_name=entities.get("customer_name"),
            )
        except Exception as e:
            logger.error(f"get_or_create_customer failed: {e}")

    # ── 3. Create lead ────────────────────────────────────────────────────────
    if db and customer:
        try:
            from app.tools.crm_tools import create_lead
            t1 = time.monotonic()
            lead_result = await create_lead(
                business_id=state["business_id"],
                customer=customer,
                entities=entities,
                db=db,
            )
            tool_results["lead"] = lead_result
            if state.get("agent_run_id"):
                await _log_tool_call(
                    state["agent_run_id"], "create_lead",
                    {"business_id": state["business_id"], "entities": entities},
                    lead_result, "success",
                    int((time.monotonic() - t1) * 1000), db,
                )
        except Exception as e:
            logger.error(f"create_lead failed: {e}")
            tool_results["lead"] = {"status": "error", "detail": str(e)}

    # ── 4. Send WhatsApp property cards ───────────────────────────────────────
    if customer:
        try:
            from app.tools.communication_tools import send_lead_whatsapp
            properties = tool_results.get("properties", {}).get("items", [])
            wa_result = await send_lead_whatsapp(customer=customer, properties=properties)
            tool_results["whatsapp"] = wa_result
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            tool_results["whatsapp"] = {"status": "error"}

    # ── 5. Team alert for hot leads ───────────────────────────────────────────
    if (
        customer
        and tool_results.get("lead", {}).get("score") == "hot"
        and settings.TWILIO_WHATSAPP_NUMBER
    ):
        try:
            from app.tools.communication_tools import notify_team_new_lead
            from app.models.customer import Lead
            from sqlalchemy import select
            lead_id = tool_results.get("lead", {}).get("lead_id")
            if lead_id:
                r = await db.execute(
                    select(Lead).where(Lead.id == uuid.UUID(lead_id))  # type: ignore[arg-type]
                )
                lead_obj = r.scalar_one_or_none()
                if lead_obj:
                    # Use business phone as team notification target
                    # In production: fetch from business.settings
                    pass  # team_phone not yet configured per-business
        except Exception as e:
            logger.error(f"Team alert failed: {e}")

    # ── Update customer preferences ───────────────────────────────────────────
    if db and customer and entities:
        try:
            from app.memory import update_customer_preferences
            await update_customer_preferences(customer, entities, db)
        except Exception as e:
            logger.error(f"Preference update failed: {e}")

    state["tool_results"] = {**state.get("tool_results", {}), **tool_results}
    return state


async def booking_agent_node(state: AgentState) -> AgentState:
    """
    Handles appointment_request:
    1. Get available calendar slots
    2. Create appointment (Calendar + DB)
    3. Update CRM lead stage
    4. Send WhatsApp confirmation
    """
    logger.info(f"📅 Booking Agent | entities={state.get('entities')}")
    db = _db(state)
    tool_results: dict = {}
    entities = state.get("entities", {})

    # ── 1. Get/create customer ────────────────────────────────────────────────
    customer = None
    if db:
        try:
            from app.tools.crm_tools import get_or_create_customer
            customer = await get_or_create_customer(
                business_id=state["business_id"],
                phone=state["customer_phone"],
                db=db,
                full_name=entities.get("customer_name"),
            )
        except Exception as e:
            logger.error(f"get_or_create_customer failed: {e}")

    # ── 2. Check calendar availability ───────────────────────────────────────
    try:
        from app.tools.calendar_tools import get_available_slots
        t0 = time.monotonic()
        slots_result = await get_available_slots(
            business_id=state["business_id"],
            preferred_datetime=entities.get("preferred_datetime"),
        )
        tool_results["calendar_slots"] = slots_result
        if state.get("agent_run_id") and db:
            await _log_tool_call(
                state["agent_run_id"], "get_available_slots",
                {"preferred_datetime": entities.get("preferred_datetime")},
                slots_result, "success", int((time.monotonic() - t0) * 1000), db,
            )
    except Exception as e:
        logger.error(f"get_available_slots failed: {e}")
        tool_results["calendar_slots"] = {"slots": [], "error": str(e)}

    # ── 3. Book the best available slot ──────────────────────────────────────
    slots = tool_results.get("calendar_slots", {}).get("slots", [])
    if slots and customer:
        try:
            from app.tools.calendar_tools import create_appointment
            t1 = time.monotonic()
            # Pick first slot (or preferred slot if datetime extracted)
            best_slot = slots[0]
            customer_name = customer.full_name or customer.phone
            appt_result = await create_appointment(
                business_id=state["business_id"],
                customer=customer,
                slot_start=best_slot["start"],
                title=f"Property Visit — {customer_name}",
                duration_minutes=60,
                description=(
                    f"Property requirements: {json.dumps(entities)}\n"
                    f"Conversation: {state['user_input'][:200]}"
                ),
                db=db,
            )
            tool_results["appointment"] = appt_result
            if state.get("agent_run_id") and db:
                await _log_tool_call(
                    state["agent_run_id"], "create_appointment",
                    {"slot": best_slot["start"], "customer": customer_name},
                    appt_result, "success", int((time.monotonic() - t1) * 1000), db,
                )
        except Exception as e:
            logger.error(f"create_appointment failed: {e}")
            tool_results["appointment"] = {"status": "error", "detail": str(e)}

    # ── 4. Update CRM lead stage → qualified ─────────────────────────────────
    if db:
        try:
            from app.tools.crm_tools import create_lead, update_lead_stage
            # Get or create lead
            lead_result = await create_lead(
                business_id=state["business_id"],
                customer=customer,
                entities=entities,
                db=db,
            )
            tool_results["lead"] = lead_result
            # Advance to QUALIFIED
            if lead_result.get("lead_id"):
                await update_lead_stage(
                    business_id=state["business_id"],
                    lead_id=lead_result["lead_id"],
                    stage="qualified",
                    note=f"Appointment booked for {tool_results.get('appointment', {}).get('start_label')}",
                    db=db,
                )
        except Exception as e:
            logger.error(f"CRM stage update failed: {e}")

    # ── 5. Send WhatsApp confirmation ─────────────────────────────────────────
    if customer and tool_results.get("appointment", {}).get("status") == "confirmed":
        try:
            from app.tools.communication_tools import send_appointment_confirmation
            appt = tool_results["appointment"]
            wa_result = await send_appointment_confirmation(
                customer=customer,
                appointment={
                    "date": appt.get("start_label", "").split(",")[1].strip()
                    if "," in appt.get("start_label", "") else appt.get("start_label", ""),
                    "time": appt.get("start_label", "").split(",")[0].strip()
                    if "," in appt.get("start_label", "") else appt.get("start_label", ""),
                    "location": "Our office (we'll send details)",
                    "meet_link": appt.get("meet_link"),
                },
            )
            tool_results["whatsapp"] = wa_result
        except Exception as e:
            logger.error(f"WhatsApp confirmation failed: {e}")

    state["tool_results"] = {**state.get("tool_results", {}), **tool_results}
    return state


async def support_agent_node(state: AgentState) -> AgentState:
    """
    Handles support / complaint / out_of_scope:
    Searches the knowledge base for answers (FAQs, policies, pricing).
    """
    logger.info(f"🛠️ Support Agent | intent={state['intent']}")
    db = _db(state)
    tool_results: dict = {}

    if db:
        try:
            from app.tools.search_tools import search_knowledge
            rag_result = await search_knowledge(
                query=state["user_input"],
                business_id=state["business_id"],
                db=db,
                top_k=5,
            )
            tool_results["knowledge"] = {
                "found": rag_result["found"],
                "context": rag_result["context"][:800],
            }
            if rag_result["context"]:
                state["business_context"] = (
                    state.get("business_context", "") + "\n\n" + rag_result["context"]
                )
            if state.get("agent_run_id"):
                await _log_tool_call(
                    state["agent_run_id"], "search_knowledge",
                    {"query": state["user_input"]},
                    {"found": rag_result["found"]}, "success", 0, db,
                )
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            tool_results["knowledge"] = {"found": False, "error": str(e)}

    state["tool_results"] = {**state.get("tool_results", {}), **tool_results}
    return state


async def responder_node(state: AgentState) -> AgentState:
    """
    Generate the final spoken/text response to the customer.
    Uses full context: intent, entities, tool results, business context.
    """
    llm = _llm(fast=True)

    mem = state.get("customer_memory", {})
    customer_name = (
        state.get("entities", {}).get("customer_name")
        or mem.get("full_name")
        or "there"
    )

    # Summarise what actions were taken
    actions_summary = []
    tr = state.get("tool_results", {})
    if tr.get("lead", {}).get("status") == "created":
        actions_summary.append(f"Lead created (score: {tr['lead'].get('score', '?')})")
    if tr.get("appointment", {}).get("status") == "confirmed":
        actions_summary.append(f"Appointment booked for {tr['appointment'].get('start_label', '?')}")
    if tr.get("whatsapp", {}).get("status") == "sent":
        actions_summary.append("WhatsApp message sent to customer")
    if tr.get("properties", {}).get("found"):
        actions_summary.append(f"Found {tr['properties']['count']} matching properties")

    system = """You are a warm, professional AI real estate assistant speaking to a customer on the phone.

Rules:
- Keep responses under 3 sentences for voice (conversational, not formal).
- Address the customer by first name if known.
- Confirm actions that were taken (appointment booked, properties found, etc.).
- If an appointment was booked, state the exact time clearly.
- If properties were found, briefly mention how many.
- If WhatsApp was sent, mention you've sent details there.
- Sound human, warm, and helpful — not robotic.
- In India, use ₹ and Lakhs for currency naturally."""

    prompt = f"""Customer name: {customer_name}
Customer said: "{state['user_input']}"
Intent: {state['intent']}
Entities extracted: {json.dumps(state.get('entities', {}), indent=2)}
Actions taken: {', '.join(actions_summary) if actions_summary else 'None yet'}
Business context available: {state.get('business_context', '')[:400]}

Generate a natural, conversational response (max 3 sentences for voice):"""

    try:
        resp = await llm.ainvoke([
            {"role": "system", "content": system},
            {"role": "human", "content": prompt},
        ])
        state["response"] = resp.content.strip()
    except Exception as e:
        logger.error(f"Responder LLM failed: {e}")
        state["response"] = (
            "Thank you for your enquiry. Our team will follow up with you shortly. "
            "Have a great day!"
        )

    state["next_action"] = "continue"
    logger.info(f"💬 Response: {state['response'][:120]}")
    return state


async def human_handoff_node(state: AgentState) -> AgentState:
    """
    Escalation node:
    1. Creates HumanHandoff DB record
    2. Notifies team via WhatsApp
    3. Responds to customer with hold message
    """
    logger.warning(f"🚨 Human handoff | reason: {state.get('escalation_reason')}")
    db = _db(state)

    # ── Get customer ──────────────────────────────────────────────────────────
    customer = None
    if db:
        try:
            from app.tools.crm_tools import get_or_create_customer
            customer = await get_or_create_customer(
                business_id=state["business_id"],
                phone=state["customer_phone"],
                db=db,
            )
        except Exception as e:
            logger.error(f"get_or_create_customer in handoff: {e}")

    # ── Summarise conversation for human context ───────────────────────────────
    history = state.get("conversation_history", [])
    summary_lines = [f"{m['role'].upper()}: {m['content']}" for m in history[-6:]]
    summary_lines.append(f"CUSTOMER: {state['user_input']}")
    conversation_summary = "\n".join(summary_lines)

    # ── Persist HumanHandoff ──────────────────────────────────────────────────
    if db:
        try:
            from app.models.integration import HumanHandoff
            handoff = HumanHandoff(
                business_id=uuid.UUID(state["business_id"]),
                conversation_id=uuid.UUID(state["conversation_id"]),
                trigger_reason=state.get("escalation_reason") or "requested",
                context_summary=conversation_summary,
                customer_intent=state.get("intent"),
                recommended_action="Call customer immediately",
            )
            db.add(handoff)
            await db.flush()
            logger.info(f"📋 HumanHandoff created: {handoff.id}")
        except Exception as e:
            logger.error(f"HumanHandoff creation failed: {e}")

    # ── Notify team ───────────────────────────────────────────────────────────
    team_phone = (settings.TEAM_WHATSAPP_PHONE or settings.TWILIO_WHATSAPP_NUMBER).strip()
    if customer and team_phone:
        try:
            from app.tools.communication_tools import notify_human_handoff
            await notify_human_handoff(
                team_phone=team_phone,
                customer=customer,
                reason=state.get("escalation_reason") or "Customer requested human",
                conversation_summary=conversation_summary,
                entities=state.get("entities", {}),
            )
        except Exception as e:
            logger.error(f"Team handoff notification failed: {e}")

    state["response"] = (
        "I completely understand. Let me connect you with one of our senior advisors "
        "right now — they have your full conversation details and will be with you "
        "in just a moment. Thank you for your patience."
    )
    state["next_action"] = "human_handoff"
    return state


# ── Routing ───────────────────────────────────────────────────────────────────

def route_by_intent(
    state: AgentState,
) -> Literal["lead_agent", "booking_agent", "support_agent", "human_handoff"]:
    if state.get("escalate"):
        return "human_handoff"
    intent = state.get("intent", "support")
    if intent in ("property_inquiry", "price_inquiry"):
        return "lead_agent"
    elif intent == "appointment_request":
        return "booking_agent"
    else:
        return "support_agent"


# ── Build Graph ───────────────────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("receptionist", receptionist_node)
    graph.add_node("intent_classifier", intent_classifier_node)
    graph.add_node("lead_agent", lead_agent_node)
    graph.add_node("booking_agent", booking_agent_node)
    graph.add_node("support_agent", support_agent_node)
    graph.add_node("responder", responder_node)
    graph.add_node("human_handoff", human_handoff_node)

    graph.set_entry_point("receptionist")
    graph.add_edge("receptionist", "intent_classifier")
    graph.add_conditional_edges(
        "intent_classifier",
        route_by_intent,
        {
            "lead_agent": "lead_agent",
            "booking_agent": "booking_agent",
            "support_agent": "support_agent",
            "human_handoff": "human_handoff",
        },
    )
    graph.add_edge("lead_agent", "responder")
    graph.add_edge("booking_agent", "responder")
    graph.add_edge("support_agent", "responder")
    graph.add_edge("responder", END)
    graph.add_edge("human_handoff", END)

    return graph.compile()


# ── Singleton ─────────────────────────────────────────────────────────────────

agent_graph = build_agent_graph()


# ── Public entry point ────────────────────────────────────────────────────────

async def process_customer_input(
    user_input: str,
    conversation_id: str,
    business_id: str,
    customer_phone: str,
    conversation_history: list[dict] | None = None,
    customer_memory: dict | None = None,
    db: AsyncSession | None = None,
    agent_id: str | None = None,
) -> dict:
    """
    Main entry point — called from the Twilio webhook handler.

    Creates an AgentRun record, runs the graph, finalises the record.
    Returns the agent's response and metadata.
    """
    t_start = time.monotonic()

    # ── Create AgentRun record ────────────────────────────────────────────────
    agent_run_id: str | None = None
    if db and agent_id:
        try:
            from app.models.conversation import AgentRun
            run = AgentRun(
                agent_id=uuid.UUID(agent_id),
                conversation_id=uuid.UUID(conversation_id),
                input_text=user_input,
                status="running",
            )
            db.add(run)
            await db.flush()
            agent_run_id = str(run.id)
        except Exception as e:
            logger.error(f"AgentRun creation failed: {e}")

    # ── Build initial state ───────────────────────────────────────────────────
    initial_state: AgentState = {
        "conversation_id": conversation_id,
        "business_id": business_id,
        "customer_phone": customer_phone,
        "agent_run_id": agent_run_id,
        "user_input": user_input,
        "conversation_history": conversation_history or [],
        "customer_memory": customer_memory or {},
        "business_context": "",
        "intent": "",
        "entities": {},
        "plan": [],
        "tool_results": {},
        "response": "",
        "escalate": False,
        "escalation_reason": "",
        "next_action": "continue",
        "_db": db,
    }

    # ── Run graph ─────────────────────────────────────────────────────────────
    result = await agent_graph.ainvoke(initial_state)

    latency_ms = int((time.monotonic() - t_start) * 1000)
    logger.info(f"⚡ Agent graph completed in {latency_ms}ms")

    # ── Finalise AgentRun ─────────────────────────────────────────────────────
    if db and agent_run_id:
        try:
            from sqlalchemy import select
            from app.models.conversation import AgentRun
            r = await db.execute(
                select(AgentRun).where(AgentRun.id == uuid.UUID(agent_run_id))
            )
            run = r.scalar_one_or_none()
            if run:
                run.status = "completed" if not result.get("escalate") else "escalated"
                run.intent = result.get("intent")
                run.output_text = result.get("response")
                run.latency_ms = latency_ms
                run.completed_at = datetime.now(timezone.utc)
                await db.flush()
        except Exception as e:
            logger.error(f"AgentRun finalise failed: {e}")

    return {
        "response": result["response"],
        "intent": result["intent"],
        "entities": result["entities"],
        "next_action": result["next_action"],
        "tool_results": result["tool_results"],
        "agent_run_id": agent_run_id,
        "latency_ms": latency_ms,
    }
