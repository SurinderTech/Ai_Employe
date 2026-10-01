"""Base mixin for all models — UUID PK, timestamps.
Uses SQLAlchemy's cross-database Uuid type so this works with
both SQLite (local dev) and PostgreSQL (production).
"""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, func, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator, CHAR

# Cross-database UUID type — stores as native UUID on Postgres,
# as CHAR(36) on SQLite. This avoids the PGUUID dialect dependency.
class GUID(TypeDecorator):
    """Platform-independent GUID type. Uses Postgres UUID natively,
    CHAR(36) otherwise."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return str(value)
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
