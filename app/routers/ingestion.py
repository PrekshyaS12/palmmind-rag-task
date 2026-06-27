"""
Document Ingestion API.

POST /documents/upload

"""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.models import ChunkingStrategy, ChunkMeta, Document, DocumentStatus
from app.db.session import get_db
from app.schemas.ingestion import DocumentUploadResponse
from app.services.chunking import chunk_text
from app.services.embeddings import upsert_chunks
from app.services.extraction import SUPPORTED_CONTENT_TYPES, extract_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["ingestion"])

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    chunking_strategy: ChunkingStrategy = Query(
        default=ChunkingStrategy.RECURSIVE_SENTENCE,
        description="Chunking strategy to apply: fixed_size or recursive_sentence",
    ),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file.content_type}'. Upload a PDF or TXT file.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 10 MB limit.",
        )

    document = Document(
        filename=file.filename or "unnamed",
        content_type=file.content_type,
        chunking_strategy=chunking_strategy,
        status=DocumentStatus.PROCESSING,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        text = extract_text(file_bytes, file.content_type)
        chunks = chunk_text(text, chunking_strategy)

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Chunking produced no chunks from the extracted text.",
            )

        chunk_records = [
            ChunkMeta(document_id=document.id, chunk_index=i, text=chunk_text_value)
            for i, chunk_text_value in enumerate(chunks)
        ]
        db.add_all(chunk_records)
        db.flush()  

        upsert_chunks(
            document_id=document.id,
            chunk_ids=[c.id for c in chunk_records],
            texts=[c.text for c in chunk_records],
        )

        document.status = DocumentStatus.READY
        document.chunk_count = len(chunk_records)
        db.commit()

    except HTTPException:
        document.status = DocumentStatus.FAILED
        db.commit()
        raise
    except Exception as exc:
        document.status = DocumentStatus.FAILED
        db.commit()
        logger.exception("Document ingestion failed for document_id=%s", document.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document.",
        ) from exc

    db.refresh(document)
    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
        chunk_count=document.chunk_count,
        chunking_strategy=document.chunking_strategy,
    )