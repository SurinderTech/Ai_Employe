"""Knowledge base models for RAG pipeline."""
import uuid
import enum
from sqlalchemy import String, JSON, ForeignKey, Text, Integer, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import GUID as PGUUID
from pgvector.sqlalchemy import Vector
from app.database.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class KnowledgeDocument(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_documents"

    business_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_url: Mapped[str | None] = mapped_column(String(500))
    file_type: Mapped[str | None] = mapped_column(String(50))  # pdf, csv, txt, docx
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[DocumentStatus] = mapped_column(
        PgEnum(DocumentStatus, name="document_status"), default=DocumentStatus.PENDING
    )
    chunk_count: Mapped[int] = mapped_column(default=0)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)

    business: Mapped["Business"] = relationship(back_populates="knowledge_documents")  # noqa
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="document")


class KnowledgeChunk(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer)
    # 768-dim for text-embedding-004
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)

    document: Mapped["KnowledgeDocument"] = relationship(back_populates="chunks")
