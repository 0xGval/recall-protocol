from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://recall:recall@localhost:5432/recall"
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    min_similarity: float = 0.55
    duplicate_threshold: float = 0.92
    auto_duplicate_threshold: float = 0.97
    min_content_length: int = 80

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
