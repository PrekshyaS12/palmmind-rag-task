import pytest
from fastapi import HTTPException

from app.services.extraction import extract_text


def test_extract_txt_returns_decoded_text():
    result = extract_text(b"Hello world", "text/plain")
    assert result == "Hello world"


def test_extract_txt_rejects_empty_file():
    with pytest.raises(HTTPException) as exc_info:
        extract_text(b"", "text/plain")
    assert exc_info.value.status_code == 422


def test_extract_rejects_unsupported_content_type():
    with pytest.raises(HTTPException) as exc_info:
        extract_text(b"some bytes", "image/png")
    assert exc_info.value.status_code == 400


def test_extract_txt_rejects_invalid_utf8():
    with pytest.raises(HTTPException) as exc_info:
        extract_text(b"\xff\xfe\x00\x01", "text/plain")
    assert exc_info.value.status_code == 400