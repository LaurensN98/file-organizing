from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@db:5432/rebels_db"
    REDIS_URL: str = "redis://redis:6379/0"
    EMBEDDING_API_KEY: str = "dummy"
    LLM_API_KEY: str = "dummy"

    class Config:
        env_file = ".env"

settings = Settings()
