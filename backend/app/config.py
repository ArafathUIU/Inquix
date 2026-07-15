from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://inquix:inquix@localhost:5432/inquix"
    ollama_url: str = "http://localhost:11434"

    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5:3b"
    groq_api_key: str = ""

    gemini_api_key: str = ""

    embed_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    jina_api_key: str = ""

    openai_api_key: str = ""

    openai_llm_model: str = "gpt-4o-2024-11-20"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_tts_model: str = "tts-1-hd"
    openai_tts_voice: str = "alloy"
    openai_whisper_model: str = "whisper-1"

    vision_model: str = "llava-phi3:3.8b"
    web_search_threshold: float = 0.65
    tts_provider: str = "kokoro"
    tts_voice: str = "af_heart"

    upload_dir: str = "/data/uploads"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    similarity_threshold: float = 0.45

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
