"""
Document Ingestion API.

POST /documents/upload
GET  /documents/{document_id}
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import verify_api_key
from app.db.models import ChunkingStrategy, ChunkMeta, Document, DocumentStatus
from app.db.session import SessionLocal, get_db
from app.schemas.ingestion import DocumentUploadResponse
from app.services.chunking import chunk_text
from app.services.embeddings import upsert_chunks
from app.services.extraction import SUPPORTED_CONTENT_TYPES, extract_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["ingestion"])

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def process_document(
    document_id: str,
    file_bytes: bytes,
    content_type: str,
    chunking_strategy: ChunkingStrategy,
) -> None:
    """
    Runs after the response has already been sent. Opens its own DB session
    since the request-scoped session from Depends(get_db) is closed by then.
    """
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            logger.error("Background processing: document_id=%s no longer exists", document_id)
            return

        text = extract_text(file_bytes, content_type)
        chunks = chunk_text(text, chunking_strategy)

        if not chunks:
            document.status = DocumentStatus.FAILED
            db.commit()
            logger.error("Chunking produced no chunks for document_id=%s", document_id)
            return

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

    except Exception:
        db.rollback()
        document = db.get(Document, document_id)
        if document is not None:
            document.status = DocumentStatus.FAILED
            db.commit()
        logger.exception("Background document processing failed for document_id=%s", document_id)
    finally:
        db.close()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_api_key)],
)
async def upload_document(
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(
        process_document,
        document.id,
        file_bytes,
        file.content_type,
        chunking_strategy,
    )

    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
        chunk_count=document.chunk_count,
        chunking_strategy=document.chunking_strategy,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentUploadResponse,
    dependencies=[Depends(verify_api_key)],
)
def get_document_status(document_id: str, db: Session = Depends(get_db)) -> DocumentUploadResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No document found with id={document_id}.",
        )

    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
        chunk_count=document.chunk_count,
        chunking_strategy=document.chunking_strategy,
    )