import json
import httpx
from typing import AsyncGenerator
from app.config import settings


def build_prompt(query: str, chunks: list[dict], chat_history: list[dict] | None = None) -> str:
    context_parts = []
    for i, chunk in enumerate(chunks):
        source = chunk.get("filename", f"Source {i + 1}")
        context_parts.append(f"[{i + 1}] Source: {source}\n{chunk['content']}")

    context = "\n\n---\n\n".join(context_parts)

    history = ""
    if chat_history:
        lines = []
        for msg in chat_history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        history = "\n".join(lines) + "\n\n"

    return f"""You are an AI assistant that answers questions based solely on the provided context.

RULES:
- Answer ONLY using information from the context below.
- If the context does not contain the answer, say "I don't have enough information to answer that."
- Cite sources using the format [1], [2] referencing the source numbers.
- Be concise and factual.

CONTEXT:
{context}

{history}Question: {query}

Answer:"""


async def generate_stream(
    query: str, chunks: list[dict], chat_history: list[dict] | None = None
) -> AsyncGenerator[str, None]:
    prompt = build_prompt(query, chunks, chat_history)

    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream(
            "POST",
            f"{settings.ollama_url}/api/generate",
            json={
                "model": settings.llm_model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 1024,
                },
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                except json.JSONDecodeError:
                    continue
