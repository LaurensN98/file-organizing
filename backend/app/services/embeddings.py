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
MAX_CONCURRENT_EMBEDDING_BATCHES = 5
embedding_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EMBEDDING_BATCHES)

# Shared client to be reused
_client_http = None

def get_http_client():
    global _client_http
    if _client_http is None or _client_http.is_closed:
        _client_http = httpx.AsyncClient(timeout=20.0)
    return _client_http

async def generate_sparse_embeddings(texts: List[str], batch_size: int = 4) -> List[Dict[str, float]]:
    """Fetch sparse embeddings in small batches to avoid timeouts on CPU."""
    all_results = []
    
    client_http = get_http_client()
    for i in range(0, len(texts), batch_size):
        batch = [t if t.strip() else "[Empty]" for t in texts[i : i + batch_size]]
        try:
            logger.info(f"Processing SPLADE batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}...")
            response = await client_http.post(
                f"{settings.INFERENCE_URL}/embed_sparse",
                json={"inputs": batch},
                timeout=120.0  # High timeout for CPU-bound SPLADE
            )
            
            if response.status_code != 200:
                logger.error(f"SPLADE batch error: {response.text}")
                all_results.extend([{} for _ in batch])
                continue
                
            data = response.json()
            # TEI returns a list of sparse embeddings (one for each input string)
            for embedding in data:
                all_results.append({str(item["index"]): float(item["value"]) for item in embedding})
                
        except Exception:
            logger.exception("SPLADE batch failed or timed out")
            all_results.extend([{} for _ in batch])
            
    return all_results

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
            # Fallback to random embeddings to prevent total pipeline failure
            # Dimension for qwen3-embedding-8b is 4096
            return [np.random.rand(4096).tolist() for _ in range(len(batch))]

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

