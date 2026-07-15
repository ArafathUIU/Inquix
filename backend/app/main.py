from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.types import ASGIApp, Scope, Receive, Send
from app.database import engine, Base
from app.services.embedding import ensure_models
from app.routers import health, kb, documents, chat, audio, tts


class CORSMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        origin = "*"
        for header, value in scope.get("headers", []):
            if header == b"origin":
                origin = value.decode()
                break

        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                headers = list(headers)
                headers.append((b"access-control-allow-origin", origin.encode()))
                headers.append((b"access-control-allow-credentials", b"true"))
                headers.append((b"access-control-allow-methods", b"DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"))
                headers.append((b"access-control-allow-headers", b"*"))
                headers.append((b"access-control-max-age", b"600"))
                message["headers"] = headers
            await send(message)

        if scope["method"] == "OPTIONS":
            await send_with_cors({
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-length", b"0")],
            })
            await send({"type": "http.response.body", "body": b""})
            return

        await self.app(scope, receive, send_with_cors)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        await ensure_models()
    except Exception as e:
        print(f"Warning: Could not verify Ollama models: {e}")
    yield
    await engine.dispose()


app = FastAPI(title="Inquix API", version="0.1.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(kb.router, prefix="/api", tags=["kb"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(audio.router, prefix="/api", tags=["audio"])
app.include_router(tts.router, prefix="/api", tags=["tts"])


@app.get("/")
async def root():
    return {"name": "Inquix API", "version": "0.1.0"}
