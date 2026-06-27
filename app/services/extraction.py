"""
Text extraction for uploaded files.

"""
import io

from fastapi import HTTPException, status
from pypdf import PdfReader

SUPPORTED_CONTENT_TYPES = {"application/pdf", "text/plain"}

def extract_text(file_bytes: bytes, content_type: str) -> str:
    """Extract raw text from a PDF or TXT file's bytes."""
    if content_type == "application/pdf":
        return _extract_pdf_text(file_bytes)
    if content_type == "text/plain":
        return _extract_txt_text(file_bytes)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported content type '{content_type}'. Only PDF and TXT are supported.",
    )


def _extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages_text).strip()

    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No extractable text found in PDF (it may be a scanned/image-only document).",
        )
    return text


def _extract_txt_text(file_bytes: bytes) -> str:
    try:
        text = file_bytes.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TXT file is not valid UTF-8 text.",
        ) from exc

    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="TXT file is empty.",
        )
    return text