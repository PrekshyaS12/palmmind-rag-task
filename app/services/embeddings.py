"""
Embedding generation (Gemini) + Pinecone vector storage.

"""
from google import genai
from google.genai import types
from pinecone import Pinecone, ServerlessSpec
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()

_genai_client = genai.Client(api_key=settings.google_api_key)
_pinecone_client = Pinecone(api_key=settings.pinecone_api_key)

def get_pinecone_index():
    existing_indexes = {idx["name"] for idx in _pinecone_client.list_indexes()}

    if settings.pinecone_index_name not in existing_indexes:
        _pinecone_client.create_index(
            name=settings.pinecone_index_name,
            dimension=settings.embedding_dim,
            metric="cosine",
            spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
        )

    return _pinecone_client.Index(settings.pinecone_index_name)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
def embed_texts(texts: list[str]) -> list[list[float]]:
    response = _genai_client.models.embed_content(
        model=settings.embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=settings.embedding_dim),
    )
    return [embedding.values for embedding in response.embeddings]


def upsert_chunks(document_id: str, chunk_ids: list[str], texts: list[str]) -> None:
    embeddings = embed_texts(texts)
    index = get_pinecone_index()

    vectors = [
        {
            "id": chunk_id,
            "values": embedding,
            "metadata": {"document_id": document_id, "text": text},
        }
        for chunk_id, embedding, text in zip(chunk_ids, embeddings, texts, strict=True)
    ]

    index.upsert(vectors=vectors)


def query_similar_chunks(query: str, top_k: int = 4) -> list[dict]:
    query_embedding = embed_texts([query])[0]
    index = get_pinecone_index()

    results = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)

    return [
        {
            "id": match["id"],
            "score": match["score"],
            "text": match["metadata"].get("text", ""),
            "document_id": match["metadata"].get("document_id", ""),
        }
        for match in results.get("matches", [])
    ]