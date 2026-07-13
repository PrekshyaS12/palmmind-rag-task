"""
Centralized application configuration.

"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    api_key: str

    # App
    app_name: str = "Prekshya RAG Service"

    # Gemini
    google_api_key: str
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768
    chat_model: str = "gemini-2.5-flash"

    # Pinecone
    pinecone_api_key: str
    pinecone_index_name: str = "palmmind-rag"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    # Database
    database_url: str = "sqlite:///./app_data.db"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    chat_memory_ttl_seconds: int = 86400
    chat_memory_max_turns: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()