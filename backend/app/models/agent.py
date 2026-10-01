"""Agent and AgentConfig models — the AI employee configuration."""
import uuid
import enum
from sqlalchemy import String, Boolean, JSON, ForeignKey, Text, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import GUID as PGUUID
from app.database.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class AgentType(str, enum.Enum):
    RECEPTIONIST = "receptionist"
    LEAD = "lead"
    BOOKING = "booking"
    SUPPORT = "support"
    ORCHESTRATOR = "orchestrator"


class AgentStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class Agent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agents"

    business_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[AgentType] = mapped_column(
        PgEnum(AgentType, name="agent_type"), default=AgentType.RECEPTIONIST
    )
    status: Mapped[AgentStatus] = mapped_column(
        PgEnum(AgentStatus, name="agent_status"), default=AgentStatus.DRAFT
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Assigned phone number (Twilio)
    phone_number: Mapped[str | None] = mapped_column(String(30))

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="agents")  # noqa
    config: Mapped["AgentConfig"] = relationship(back_populates="agent", uselist=False)
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="agent")  # noqa


class AgentConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_configs"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("agents.id", ondelete="CASCADE"), unique=True
    )
    # LLM
    llm_provider: Mapped[str] = mapped_column(String(50), default="gemini")
    llm_model: Mapped[str] = mapped_column(String(100), default="gemini-1.5-pro")
    temperature: Mapped[float] = mapped_column(default=0.3)
    system_prompt: Mapped[str | None] = mapped_column(Text)

    # Voice
    voice_id: Mapped[str | None] = mapped_column(String(100))  # TTS voice name
    language: Mapped[str] = mapped_column(String(10), default="en-IN")
    stt_provider: Mapped[str] = mapped_column(String(50), default="google")

    # Behavior
    max_call_duration_seconds: Mapped[int] = mapped_column(default=600)
    silence_timeout_seconds: Mapped[int] = mapped_column(default=5)
    escalation_triggers: Mapped[list] = mapped_column(JSON, default=list)
    allowed_tools: Mapped[list] = mapped_column(JSON, default=list)
    
    # Greeting and persona
    greeting_message: Mapped[str | None] = mapped_column(Text)
    persona: Mapped[dict] = mapped_column(JSON, default=dict)

    agent: Mapped["Agent"] = relationship(back_populates="config")
