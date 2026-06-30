from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.config import settings
from app.database import Base, engine
from app.routers import chat, metrics, profile, stt, tts, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Elderly Companion AI Backend")

app.add_middleware(
    CORSMiddleware,
    # Set CORS_ALLOW_ORIGINS to a comma-separated allowlist in production.
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stt.router)
app.include_router(chat.router)
app.include_router(tts.router)
app.include_router(profile.router)
app.include_router(metrics.router)
app.include_router(users.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
