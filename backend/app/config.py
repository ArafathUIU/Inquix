from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://inquix:inquix@localhost:5432/inquix"
    ollama_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    llm_model: str = "qwen2.5:3b"
    upload_dir: str = "/data/uploads"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
