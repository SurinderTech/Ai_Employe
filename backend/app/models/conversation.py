"""Conversation, Message, Call, CallEvent, AgentRun, ToolCall models."""
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, JSON, ForeignKey, Text, Float, Boolean, Integer, DateTime, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import GUID as PGUUID
from app.database.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class ConversationChannel(str, enum.Enum):
    PHONE = "phone"
    WHATSAPP = "whatsapp"
    WEB = "web"
    EMAIL = "email"


class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    ABANDONED = "abandoned"


class MessageRole(str, enum.Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    SYSTEM = "system"
    HUMAN = "human"


class CallStatus(str, enum.Enum):
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"


# ── Conversation ──────────────────────────────────────────────────────────────

class Conversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversations"

    business_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(), ForeignKey("customers.id", ondelete="SET NULL")
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(), ForeignKey("agents.id", ondelete="SET NULL")
    )
    channel: Mapped[ConversationChannel] = mapped_column(
        PgEnum(ConversationChannel, name="conversation_channel"), default=ConversationChannel.PHONE
    )
    status: Mapped[ConversationStatus] = mapped_column(
        PgEnum(ConversationStatus, name="conversation_status"), default=ConversationStatus.ACTIVE
    )
    summary: Mapped[str | None] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(100))
    sentiment: Mapped[str | None] = mapped_column(String(50))
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped["Customer"] = relationship(back_populates="conversations")  # noqa
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", order_by="Message.created_at")
    calls: Mapped[list["Call"]] = relationship(back_populates="conversation")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="conversation")


# ── Message ───────────────────────────────────────────────────────────────────

class Message(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(
        PgEnum(MessageRole, name="message_role")
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(String(500))
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


# ── Call ──────────────────────────────────────────────────────────────────────

class Call(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "calls"

    business_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(), ForeignKey("conversations.id", ondelete="SET NULL")
    )
    # Twilio fields
    twilio_call_sid: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    from_number: Mapped[str] = mapped_column(String(30))
    to_number: Mapped[str] = mapped_column(String(30))
    direction: Mapped[str] = mapped_column(String(20), default="inbound")  # inbound / outbound
    status: Mapped[CallStatus] = mapped_column(
        PgEnum(CallStatus, name="call_status"), default=CallStatus.INITIATED
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    recording_url: Mapped[str | None] = mapped_column(String(500))
    transcript: Mapped[str | None] = mapped_column(Text)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversation: Mapped["Conversation"] = relationship(back_populates="calls")
    events: Mapped[list["CallEvent"]] = relationship(back_populates="call", order_by="CallEvent.created_at")


class CallEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "call_events"

    call_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("calls.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(100))  # speech_detected, silence, dtmf, etc.
    data: Mapped[dict] = mapped_column(JSON, default=dict)

    call: Mapped["Call"] = relationship(back_populates="events")


# ── Agent Run (Observability) ─────────────────────────────────────────────────

class AgentRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_runs"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("agents.id", ondelete="CASCADE"), index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(), ForeignKey("conversations.id", ondelete="SET NULL")
    )
    input_text: Mapped[str | None] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(100))
    plan: Mapped[dict | None] = mapped_column(JSON)
    output_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="running")  # running, completed, failed, escalated
    error: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    agent: Mapped["Agent"] = relationship(back_populates="agent_runs")  # noqa
    conversation: Mapped["Conversation"] = relationship(back_populates="agent_runs")
    tool_calls: Mapped[list["ToolCall"]] = relationship(back_populates="agent_run", order_by="ToolCall.created_at")


class ToolCall(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tool_calls"

    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100))
    input_args: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, success, error
    error: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)

    agent_run: Mapped["AgentRun"] = relationship(back_populates="tool_calls")
