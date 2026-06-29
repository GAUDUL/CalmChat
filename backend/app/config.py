from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    # General
    app_name: str = "Calm Chat"
    env: str = "development"

    # Database (MySQL)
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

    # Vector DB (RAG)
    vector_db_path: str = "./data/chroma_db"
    vector_db_collection: str = "user_profiles"
    rag_update_interval_minutes: int = 60  # 프로파일 문서 자동 갱신 주기 (논의 필요했던 값)
    rag_top_k: int = 5

    # LLM provider: "anthropic" | "openai" | "gemini" | "local"  -> 팀 합의 후 결정
    llm_provider: Literal["anthropic", "openai", "gemini", "local"] = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # STT (Whisper)
    whisper_model_size: str = "base"  # tiny/base/small/medium/large
    whisper_finetuned_checkpoint: str = ""  # 사투리 파인튜닝 체크포인트 경로 (있으면 우선 사용)

    # TTS
    tts_engine: str = "placeholder"  # 모델 선정 논의 필요 -> 실제 엔진명으로 교체
    elevenlabs_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
