"""
Memory — loads and persists agent memory from the database.

Three kinds:
  1. Customer memory  — preferences, past interactions (from Customer.preferences)
  2. Conversation memory — messages in this conversation (from Message table)
  3. Business context — loaded via RAG (delegated to search_tools)
"""
from __future__ import annotations
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.logging import logger
from app.models.customer import Customer
from app.models.conversation import Conversation, Message, MessageRole


async def load_customer_memory(
    business_id: str,
    phone: str,
    db: AsyncSession,
) -> dict:
    """
    Load customer memory: name, past preferences, tags, notes.
    Returns a dict that goes into AgentState.customer_memory.
    """
    result = await db.execute(
        select(Customer).where(
            Customer.business_id == uuid.UUID(business_id),
            Customer.phone == phone,
        )
    )
    customer = result.scalar_one_or_none()

    if not customer:
        return {"is_new": True, "phone": phone}

    return {
        "is_new": False,
        "customer_id": str(customer.id),
        "full_name": customer.full_name,
        "phone": customer.phone,
        "email": customer.email,
        "preferences": customer.preferences or {},
        "tags": customer.tags or [],
        "notes": customer.notes,
        "crm_id": customer.crm_id,
    }


async def load_conversation_history(
    conversation_id: str,
    db: AsyncSession,
    limit: int = 20,
) -> list[dict]:
    """
    Load the last N messages from this conversation for the agent's context window.
    Returns a list of {role, content} dicts.
    """
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == uuid.UUID(conversation_id))
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    # Reverse so oldest first
    return [
        {"role": m.role.value, "content": m.content}
        for m in reversed(messages)
    ]


async def save_message(
    conversation_id: str,
    role: MessageRole,
    content: str,
    db: AsyncSession,
    metadata: dict | None = None,
) -> Message:
    """Persist a single message turn to the database."""
    msg = Message(
        conversation_id=uuid.UUID(conversation_id),
        role=role,
        content=content,
        metadata=metadata or {},
    )
    db.add(msg)
    await db.flush()
    return msg


async def update_customer_preferences(
    customer: Customer,
    entities: dict,
    db: AsyncSession,
) -> None:
    """
    Merge newly extracted entities into customer.preferences.
    This is how the AI builds long-term customer memory.
    """
    prefs = customer.preferences or {}
    for key in ("location", "property_type", "bedrooms", "budget"):
        val = entities.get(key)
        if val:
            prefs[key] = val
    customer.preferences = prefs
    await db.flush()
    logger.info(f"🧠 Customer preferences updated: {prefs}")
