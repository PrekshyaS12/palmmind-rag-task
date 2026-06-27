"""
FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db.session import Base, engine
from app.routers import chat, ingestion

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(ingestion.router)
app.include_router(chat.router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}