from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AIvising API"
    env: str = "dev"
    cors_origins_raw: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    retrieval_top_k: int = 4
    retrieval_max_context_chars: int = 1800
    conversation_context_messages: int = 6
    llm_temperature: float = 0.2

    @property
    def cors_origins(self) -> List[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
