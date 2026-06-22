from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import stt, chat, tts, profile, metrics

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Elderly Companion AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 운영 환경에서는 React Native 앱 도메인으로 제한
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stt.router)
app.include_router(chat.router)
app.include_router(tts.router)
app.include_router(profile.router)
app.include_router(metrics.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
