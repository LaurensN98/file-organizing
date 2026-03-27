import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import documents
from app.core.database import init_db, engine
from app.core.deepinfra_client import deepinfra_client
from app.core.openai_client import openai_client
from app.core.inference_client import local_inference_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    deepinfra_key = os.getenv("DEEPINFRA_API_KEY", "")
    print(f"DEBUG: OPENROUTER_API_KEY loaded: {openrouter_key[:5]}... (len={len(openrouter_key)})")
    print(f"DEBUG: DEEPINFRA_API_KEY loaded: {deepinfra_key[:5]}... (len={len(deepinfra_key)})")
    init_db()
    yield
    # --- Shutdown ---
    # 1. Close the AI clients
    await deepinfra_client.aclose()
    await openai_client.close()
    await local_inference_client.aclose()
    
    # 2. Close the Database connection pool
    engine.dispose()


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
    