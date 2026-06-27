"""
Chunking strategies.

Two strategies are implemented, selectable by the caller:

1. fixed_size           - splits text into fixed-length character windows
                           with overlap. Simple, predictable, fast.
2. recursive_sentence   - splits on sentence boundaries first, then packs
                           sentences together up to a max size. Produces
                           chunks that don't cut sentences in half, which
                           usually improves retrieval quality at a small
                           extra cost.

"""
import re

from app.db.models import ChunkingStrategy

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str, strategy: ChunkingStrategy) -> list[str]:
    if strategy == ChunkingStrategy.FIXED_SIZE:
        return _chunk_fixed_size(text)
    if strategy == ChunkingStrategy.RECURSIVE_SENTENCE:
        return _chunk_recursive_sentence(text)
    raise ValueError(f"Unknown chunking strategy: {strategy}")


def _chunk_fixed_size(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """Fixed-length character windows with overlap so context isn't lost at chunk boundaries."""
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == text_length:
            break
        start = end - overlap

    return chunks


def _chunk_recursive_sentence(text: str, max_chunk_size: int = 1000) -> list[str]:
    """Splits text into sentences, then packs consecutive sentences into chunks up to max_chunk_size so we never cut a sentence
    in half."""
    sentences = _SENTENCE_SPLIT_RE.split(text)

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        candidate = f"{current} {sentence}".strip() if current else sentence

        if len(candidate) <= max_chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = sentence if len(sentence) <= max_chunk_size else sentence[:max_chunk_size]

    if current:
        chunks.append(current)

    return chunks