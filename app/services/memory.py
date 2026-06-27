"""
Chat memory, backed by Redis.

"""
import json

import redis

from app.config import get_settings

settings = get_settings()

_redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True,
)


def _key(session_id: str) -> str:
    return f"chat:{session_id}"


def get_history(session_id: str) -> list[dict[str, str]]:
    raw = _redis_client.get(_key(session_id))
    if not raw:
        return []
    return json.loads(raw)


def append_turn(session_id: str, role: str, content: str) -> None:
    history = get_history(session_id)
    history.append({"role": role, "content": content})

    max_messages = settings.chat_memory_max_turns * 2  
    history = history[-max_messages:]

    _redis_client.set(
        _key(session_id),
        json.dumps(history),
        ex=settings.chat_memory_ttl_seconds,
    )


def clear_history(session_id: str) -> None:
    _redis_client.delete(_key(session_id))