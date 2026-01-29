from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload
from app.core.database import init_db
from contextlib import asynccontextmanager
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    key = os.getenv("OPENROUTER_API_KEY", "")
    print(f"DEBUG: OPENROUTER_API_KEY loaded: {key[:5]}... (len={len(key)})")
    init_db()
    yield
    # Shutdown (if needed)

app = FastAPI(
    title="Intelligent Document Management System",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to Intelligent Document Management System"}