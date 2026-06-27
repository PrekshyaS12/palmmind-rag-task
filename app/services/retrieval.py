"""
Custom RAG logic — written by hand, no RetrievalQAChain.

"""
from google import genai
from google.genai import types

from app.config import get_settings
from app.services.embeddings import query_similar_chunks

settings = get_settings()
client = genai.Client(api_key=settings.google_api_key)

SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question using ONLY "
    "the context below. If the answer isn't in the context, say you "
    "don't know — do not make things up."
)


def build_context(chunks: list[dict]) -> str:
 
    if not chunks:
        return "No relevant context was found."
    return "\n\n".join(f"- {chunk['text']}" for chunk in chunks)


def _history_to_gemini_contents(chat_history: list[dict[str, str]]) -> list[types.Content]:
    """Gemini expects roles 'user'/'model' (not 'assistant'), so we
    convert our stored history into that shape."""
    contents = []
    for turn in chat_history:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=turn["content"])]))
    return contents


def answer_question(question: str, chat_history: list[dict[str, str]]) -> str:
    retrieved_chunks = query_similar_chunks(question, top_k=6)
    context = build_context(retrieved_chunks)

    contents = _history_to_gemini_contents(chat_history)
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=question)]))

    response = client.models.generate_content(
        model=settings.chat_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=f"{SYSTEM_PROMPT}\n\nContext:\n{context}",
        ),
    )
    return response.text