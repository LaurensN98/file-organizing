import logging
import asyncio
import httpx
import numpy as np
import traceback
from typing import List, Dict, Any
from app.core.config import settings
from app.services.openai_client import client

# Configure logging
logger = logging.getLogger(__name__)

# Create a semaphore to limit concurrent API calls to OpenRouter (e.g., 5 at a time)
MAX_CONCURRENT_EMBEDDING_BATCHES = 15
embedding_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EMBEDDING_BATCHES)

MAX_CONCURRENT_SPLADE_BATCHES = 10
splade_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SPLADE_BATCHES)

async def _fetch_sparse_batch(client_http: httpx.AsyncClient, batch: List[str], batch_idx: int, total_batches: int) -> List[Dict[str, float]]:
    """Helper to fetch a single sparse embedding batch with semaphore limits."""
    # Strip and strictly truncate to 1500 characters (~300 tokens)
    safe_batch = [t[:1500] if t.strip() else "[Empty]" for t in batch]
    
    async with splade_semaphore:
        try:
            logger.info(f"Processing SPLADE batch {batch_idx}/{total_batches}...")
            response = await client_http.post(
                f"{settings.INFERENCE_URL}/embed_sparse",
                json={"inputs": safe_batch},
                timeout=120.0  # High timeout for CPU-bound SPLADE
            )
            
            if response.status_code != 200:
                logger.error(f"SPLADE batch error: {response.text}")
                return [{} for _ in safe_batch]
                
            data = response.json()
            return [{str(item["index"]): float(item["value"]) for item in embedding} for embedding in data]
                
        except Exception:
            logger.exception(f"SPLADE batch {batch_idx} failed or timed out")
            return [{} for _ in safe_batch]

async def generate_sparse_embeddings(texts: List[str], batch_size: int = 32) -> List[Dict[str, float]]:
    """Fetch sparse embeddings in parallel batches to optimize throughput on GPU/Metal."""
    if not texts:
        return []
        
    async with httpx.AsyncClient(timeout=20.0) as client_http:
        total_batches = (len(texts) - 1) // batch_size + 1
        
        tasks = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_idx = (i // batch_size) + 1
            tasks.append(_fetch_sparse_batch(client_http, batch, batch_idx, total_batches))
            
        results = await asyncio.gather(*tasks)
    
    # Flatten the results
    return [emb for batch_result in results for emb in batch_result]

async def generate_sparse_embedding(text: str) -> Dict[str, float]:
    """Singular version for compatibility with existing code."""
    res = await generate_sparse_embeddings([text])
    return res[0] if res else {}

async def _fetch_embedding_batch(batch: List[str], batch_idx: int) -> List[List[float]]:
    """Internal helper to fetch a single batch of embeddings with error handling."""
    async with embedding_semaphore:
        try:
            response = await client.embeddings.create(
                input=batch,
                model="qwen/qwen3-embedding-8b"
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            error_details = getattr(e, "body", str(e))
            logger.error(f"Embedding error in batch {batch_idx}: {error_details}")
            # Returning None entries prevents silent misalignment for downstream documents.
            return [None] * len(batch)

async def get_embeddings(texts: List[str]) -> np.ndarray:
    """Fetch embeddings from OpenRouter using Qwen model in parallel batches."""
    if not texts:
        return np.array([])
    
    batch_size = 50 
    tasks = []
    for i in range(0, len(texts), batch_size):
        tasks.append(_fetch_embedding_batch(texts[i:i + batch_size], i // batch_size))
    
    results = await asyncio.gather(*tasks)
    
    # Flatten the results
    all_embeddings = [emb for batch_result in results for emb in batch_result]
    return np.array(all_embeddings)

