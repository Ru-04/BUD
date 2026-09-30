import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config, db  # Load backend-only environment before configuring CORS.
from app.identity import optional_owner
from app.routes.memory import router as memory_router
from app.routes.preferences import router as preferences_router
from app.routes.speak import router as speak_router
from app.routes.transcribe import router as transcribe_router
from app.schemas import ChatRequest, ChatResponse
from app.services.chat import chat
from app.services.groq import ProviderError, get_provider


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="BUD", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-Owner-Token"],
)
app.include_router(preferences_router)
app.include_router(memory_router)
app.include_router(transcribe_router)
app.include_router(speak_router)


CHAT_VALIDATION_MESSAGE = "Provide a valid session UUID, a message of 1-4000 characters, and at most 6 completed history pairs (24000 characters total)."


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    message = CHAT_VALIDATION_MESSAGE if request.url.path == "/api/chat" else (
        "Invalid request: check the request body, headers (e.g. X-Owner-Token) and path parameters."
    )
    return JSONResponse(status_code=422, content={"error": {"code": "INVALID_REQUEST", "message": message}})


@app.exception_handler(ProviderError)
async def provider_error(request: Request, exc: ProviderError):
    return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}})


@app.post("/api/chat", response_model=ChatResponse)
async def post_chat(payload: ChatRequest, request: Request, provider=Depends(get_provider), owner_token_hash: str | None = Depends(optional_owner)):
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        return JSONResponse(status_code=415, content={"error": {"code": "CONTENT_TYPE", "message": "Use application/json."}})
    return await chat(payload, provider, owner_token_hash)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
