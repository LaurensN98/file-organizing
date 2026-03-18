from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import documents
from app.core.database import init_db
from contextlib import asynccontextmanager
import os
from app.services.embeddings import close_http_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    key = os.getenv("OPENROUTER_API_KEY", "")
    print(f"DEBUG: OPENROUTER_API_KEY loaded: {key[:5]}... (len={len(key)})")
    init_db()
    yield
    # Shutdown (if needed)
    await close_http_client()

app = FastAPI(
    title="Neatly",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to Neatly"}