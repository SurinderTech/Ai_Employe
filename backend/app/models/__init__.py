"""Models package — import all for SQLAlchemy metadata."""
from app.models.user import User, UserRole  # noqa
from app.models.otp import OtpCode, OtpPurpose  # noqa
from app.models.business import Business, BusinessUser, BusinessStatus, BusinessUserRole  # noqa
from app.models.agent import Agent, AgentConfig, AgentType, AgentStatus  # noqa
from app.models.customer import Customer, Lead, LeadStatus, LeadScore  # noqa
from app.models.conversation import (  # noqa
    Conversation, Message, Call, CallEvent,
    AgentRun, ToolCall,
    ConversationChannel, ConversationStatus, MessageRole, CallStatus,
)
from app.models.appointment import Appointment, AppointmentStatus  # noqa
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk, DocumentStatus  # noqa
from app.models.integration import (  # noqa
    Integration, IntegrationCredential, HumanHandoff, AuditLog,
    IntegrationType, IntegrationStatus, HandoffStatus,
)

# Keep an audit trail model alias
from app.models.integration import AuditLog as audit  # noqa
