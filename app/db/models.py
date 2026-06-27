"""
ORM models.

"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class DocumentStatus(str, enum.Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ChunkingStrategy(str, enum.Enum):
    FIXED_SIZE = "fixed_size"
    RECURSIVE_SENTENCE = "recursive_sentence"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    chunking_strategy: Mapped[ChunkingStrategy] = mapped_column(Enum(ChunkingStrategy), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PROCESSING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    chunks: Mapped[list["ChunkMeta"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class ChunkMeta(Base):
   
    __tablename__ = "chunk_meta"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)  
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="chunks")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    interview_date: Mapped[str] = mapped_column(String, nullable=False)  
    interview_time: Mapped[str] = mapped_column(String, nullable=False)  
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)