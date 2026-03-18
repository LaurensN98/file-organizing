from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "db"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    REDIS_URL: str = "redis://redis:6379/0"
    OPENROUTER_API_KEY: str = "dummy"
    INFERENCE_URL: str = "http://inference:80"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
