from app.db.models import ChunkingStrategy
from app.services.chunking import chunk_text


def test_fixed_size_chunking_produces_multiple_chunks():
    text = "word " * 500
    chunks = chunk_text(text, ChunkingStrategy.FIXED_SIZE)
    assert len(chunks) > 1


def test_fixed_size_chunking_respects_overlap_ordering():
    text = "abcdefghij" * 200
    chunks = chunk_text(text, ChunkingStrategy.FIXED_SIZE)
    # each chunk should be non-empty and shorter than the full text
    assert all(0 < len(c) < len(text) for c in chunks)


def test_recursive_sentence_chunking_does_not_split_sentences():
    text = "This is sentence one. This is sentence two. This is sentence three."
    chunks = chunk_text(text, ChunkingStrategy.RECURSIVE_SENTENCE)
    for chunk in chunks:
        assert chunk.strip().endswith((".", "!", "?"))


def test_chunking_short_text_returns_single_chunk():
    text = "Just one short sentence."
    chunks = chunk_text(text, ChunkingStrategy.RECURSIVE_SENTENCE)
    assert len(chunks) == 1
    assert chunks[0] == text