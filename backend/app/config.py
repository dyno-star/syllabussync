from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://syllabussync:devpassword@localhost:5432/syllabussync"
    hf_api_token: str = ""
    anthropic_api_key: str = ""
    backend_cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
