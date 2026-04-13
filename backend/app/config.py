from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Knowledge Assistant API"
    env: str = "dev"
    cors_origins_raw: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    llm_provider: str = "mock"
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = ""

    @property
    def cors_origins(self) -> List[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
