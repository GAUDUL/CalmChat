from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.database import Base, engine
from app.routers import stt, chat, tts, profile, metrics, users

Base.metadata.create_all(bind=engine)


def ensure_runtime_schema():
    # create_all() does not add columns to an existing table, so keep local/dev DBs usable
    # after introducing device-based identity.
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "device_key" in user_columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN device_key VARCHAR(100) NULL"))
        connection.execute(text("CREATE UNIQUE INDEX ix_users_device_key ON users (device_key)"))


ensure_runtime_schema()

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
app.include_router(users.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
