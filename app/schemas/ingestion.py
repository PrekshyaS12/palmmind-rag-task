from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import ChunkingStrategy, DocumentStatus


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus
    chunk_count: int
    chunking_strategy: ChunkingStrategy


class DocumentInfo(BaseModel):
    id: str
    filename: str
    content_type: str
    chunking_strategy: ChunkingStrategy
    chunk_count: int
    status: DocumentStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ChunkPreview(BaseModel):
    chunk_index: int
    text: str = Field(..., description="Truncated preview of chunk text")