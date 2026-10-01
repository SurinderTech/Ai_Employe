"""Conversations and AgentRuns API — for the dashboard logs view."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database.session import get_db
from app.models.conversation import Conversation, Message, AgentRun, ToolCall, ConversationStatus
from app.models.user import User
from app.security.auth import get_current_user

router = APIRouter()


@router.get("")
async def list_conversations(
    business_id: uuid.UUID,
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Conversation)
        .where(Conversation.business_id == business_id)
        .order_by(desc(Conversation.created_at))
        .limit(limit)
    )
    if status:
        query = query.where(Conversation.status == ConversationStatus(status))

    result = await db.execute(query)
    convs = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "channel": c.channel.value,
            "status": c.status.value,
            "intent": c.intent,
            "summary": c.summary,
            "ended_at": c.ended_at.isoformat() if c.ended_at else None,
            "created_at": c.created_at.isoformat(),
        }
        for c in convs
    ]


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return [
        {
            "id": str(m.id),
            "role": m.role.value,
            "content": m.content,
            "timestamp": m.created_at.isoformat(),
        }
        for m in result.scalars().all()
    ]


@router.get("/{conversation_id}/agent-runs")
async def get_agent_runs(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return all agent runs for a conversation — each run has its tool calls.
    This powers the Agent Execution Log in the dashboard.
    """
    runs_result = await db.execute(
        select(AgentRun)
        .where(AgentRun.conversation_id == conversation_id)
        .order_by(AgentRun.created_at)
    )
    runs = runs_result.scalars().all()

    output = []
    for run in runs:
        # Load tool calls for this run
        tc_result = await db.execute(
            select(ToolCall)
            .where(ToolCall.agent_run_id == run.id)
            .order_by(ToolCall.created_at)
        )
        tool_calls = [
            {
                "tool_name": tc.tool_name,
                "status": tc.status,
                "input_args": tc.input_args,
                "output": tc.output,
                "latency_ms": tc.latency_ms,
                "timestamp": tc.created_at.isoformat(),
            }
            for tc in tc_result.scalars().all()
        ]
        output.append({
            "id": str(run.id),
            "status": run.status,
            "input_text": run.input_text,
            "intent": run.intent,
            "output_text": run.output_text,
            "latency_ms": run.latency_ms,
            "tokens_in": run.tokens_in,
            "tokens_out": run.tokens_out,
            "cost_usd": run.cost_usd,
            "tool_calls": tool_calls,
            "created_at": run.created_at.isoformat(),
        })

    return output


@router.get("/agent-runs/recent")
async def recent_agent_runs(
    business_id: uuid.UUID,
    limit: int = Query(20, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Most recent agent runs across all conversations for a business.
    Powers the Agent Execution Log on the dashboard overview.
    """
    result = await db.execute(
        select(AgentRun)
        .join(Conversation, Conversation.id == AgentRun.conversation_id)
        .where(Conversation.business_id == business_id)
        .order_by(desc(AgentRun.created_at))
        .limit(limit)
    )
    runs = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "status": r.status,
            "intent": r.intent,
            "input_text": r.input_text[:100] if r.input_text else None,
            "output_text": r.output_text[:100] if r.output_text else None,
            "latency_ms": r.latency_ms,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]
