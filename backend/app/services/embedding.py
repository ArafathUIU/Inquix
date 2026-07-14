import httpx
from app.config import settings


async def get_embedding(text: str) -> list[float]:
    provider = settings.embed_provider
    if provider == "jina" and settings.jina_api_key:
        try:
            return await _embed_jina(text)
        except Exception as e:
            print(f"Jina embedding failed, falling back to Ollama: {e}")
    return await _embed_ollama(text)


async def _embed_jina(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.jina.ai/v1/embeddings",
            headers={
                "Authorization": f"Bearer {settings.jina_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "jina-embeddings-v2-base-en",
                "input": [text[:8000]],
            },
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]


async def _embed_ollama(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.ollama_url}/api/embeddings",
            json={"model": settings.embedding_model, "prompt": text[:8000]},
        )
        response.raise_for_status()
        return response.json()["embedding"]


async def ensure_models():
    import asyncio

    if settings.llm_provider != "ollama" and settings.embed_provider != "ollama":
        print("Cloud providers configured, skipping Ollama model checks")
        return

    for attempt in range(12):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.ollama_url}/api/tags")
                response.raise_for_status()
                available = {m["name"] for m in response.json().get("models", [])}

            needed = set()
            if settings.embed_provider == "ollama":
                needed.add(settings.embedding_model)
            if settings.llm_provider == "ollama":
                needed.add(settings.llm_model)
                needed.add(settings.vision_model)
            missing = needed - available

            if missing:
                print(f"Pulling models: {missing}")
                async with httpx.AsyncClient(timeout=600.0) as client:
                    for model in missing:
                        print(f"Pulling {model}...")
                        await client.post(
                            f"{settings.ollama_url}/api/pull",
                            json={"name": model, "stream": False},
                        )
                        print(f"{model} ready.")
            return
        except Exception as e:
            if attempt < 11:
                print(f"Waiting for Ollama ({attempt + 1}/12): {e}")
                await asyncio.sleep(5)
            else:
                print(f"Warning: Could not connect to Ollama: {e}")
