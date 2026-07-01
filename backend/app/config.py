from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # General
    app_name: str = "Calm Chat"
    env: str = "development"
    cors_allow_origins: str = "*"

    # Database
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_db: str = "elderly_companion"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )

    # Vector DB / profile retrieval
    vector_db_path: str = "./data/chroma_db"
    vector_db_profile_collection: str = "user_profiles"
    vector_db_conversation_collection: str = "user_conversations"
    rag_update_interval_minutes: int = 60
    rag_top_k: int = 5

    rag_time_decay_alpha: float = 0.05   # 최근일수록 중요
    rag_min_score: float = 0.2           # 필터 컷
    rag_max_context: int = 8             # 최종 context 수

    # LLM provider
    llm_provider: Literal["anthropic", "openai", "gemini", "local"] = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    danger_confirmation_timeout_seconds: float = 4.0

    # STT
    whisper_model_size: str = "base"
    whisper_finetuned_checkpoint: str = ""

    # TTS
    elevenlabs_api_key: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
