from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@db:5432/db"
    REDIS_URL: str = "redis://redis:6379/0"
    OPENROUTER_API_KEY: str = "dummy"
    # Deprecated keys, kept for compatibility if needed, or remove them
    EMBEDDING_API_KEY: str = "dummy"
    LLM_API_KEY: str = "dummy"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
