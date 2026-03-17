import os
import logging
import warnings
import asyncio
import time
import numpy as np
import umap
from sklearn.cluster import HDBSCAN
from openai import AsyncOpenAI
from typing import List, Dict, Tuple, Any

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Suppress UMAP UserWarnings
warnings.filterwarnings("ignore", category=UserWarning, module="umap")

# Initialize client for OpenRouter 
# Adding headers can help with certain 401 "User not found" edge cases on OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Neatly AI Organizer",
    }
)

async def get_embeddings(texts: List[str]) -> np.ndarray:
    """Fetch embeddings from OpenRouter using Qwen model in parallel batches."""
    if not texts:
        return np.array([])
    
    batch_size = 50 
    
    async def fetch_batch(batch: List[str], batch_idx: int):
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
            return [np.random.rand(1536).tolist() for _ in range(len(batch))]

    tasks = []
    for i in range(0, len(texts), batch_size):
        tasks.append(fetch_batch(texts[i:i + batch_size], i // batch_size))
    
    results = await asyncio.gather(*tasks)
    
    # Flatten the results
    all_embeddings = [emb for batch_result in results for emb in batch_result]
    return np.array(all_embeddings)

def _worker_run_clustering(embeddings: np.ndarray, n_samples: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Synchronous worker for CPU-intensive UMAP and HDBSCAN tasks.
    Runs in a separate thread.
    """
    # 2. Dimensionality Reduction (UMAP)
    # Adjust parameters for small datasets to prevent spectral initialization errors
    init_mode = "random" if n_samples < 15 else "spectral"
    n_neighbors = min(n_samples - 1, 15)
    
    # Reduction for Clustering (High dim)
    n_components_cluster = min(n_samples - 2, 5) if n_samples > 10 else min(n_samples - 1, 5)
    
    if n_samples <= 3:
         # Skip reduction for tiny datasets
         embeddings_for_clustering = embeddings
         embeddings_for_viz = embeddings[:, :2] if embeddings.shape[1] >= 2 else embeddings
    else:
         # 2a. Clustering Reduction (e.g. 10D)
         reducer_cluster = umap.UMAP(
            n_neighbors=n_neighbors,
            n_components=n_components_cluster,
            min_dist=0.0, 
            metric='cosine',
            random_state=42,
            init=init_mode
        )
         embeddings_for_clustering = reducer_cluster.fit_transform(embeddings)
         
         # 2b. Visualization Reduction (2D)
         reducer_viz = umap.UMAP(
            n_neighbors=n_neighbors,
            n_components=2,
            min_dist=0.0, 
            metric='cosine',
            random_state=42,
            init=init_mode
        )
         embeddings_for_viz = reducer_viz.fit_transform(embeddings)

    # 3. Clustering (HDBSCAN)
    clusterer = HDBSCAN(
        min_cluster_size=2,
        cluster_selection_epsilon=0.5, 
        metric='euclidean',
        )
    # Use the higher dimensional embeddings for better clustering
    cluster_labels = clusterer.fit_predict(embeddings_for_clustering)
    
    return cluster_labels, embeddings_for_viz

async def get_cluster_label(texts: List[str]) -> str:
    """Generate a concise folder name using Google Gemini via OpenRouter."""
    # Filter for quality text snippets to send to the LLM
    clean_texts = [t.strip() for t in texts if len(t.strip()) > 20]
    if not clean_texts:
        return "Miscellaneous"

    prompt = (
        "Analyze these document excerpts and provide a single, concise folder name (1-3 words) "
        "that accurately describes the collection. Avoid generic words like 'Documents' or 'Files'.\n\n"
        "Examples: 'Financial Reports', 'Legal Contracts', 'Resume Applications', 'Product Manuals'.\n\n"
        "Document Excerpts:\n"
    )
    # Give the model a diverse look at the cluster
    prompt += "\n---\n".join([t[:800] for t in clean_texts[:5]])
    
    try:
        logger.info(f"Generating label for cluster with {len(clean_texts)} documents...")
        response = await client.chat.completions.create(
            model="qwen/qwen3.5-27b", 
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=20,
            temperature=0.1,
        )
        content = response.choices[0].message.content
        if content:
            # Clean up markdown and quotes
            return content.strip().replace('"', '').replace('*', '').replace('_', '').replace('#', '')
        return "Miscellaneous"
    except Exception as e:
        logger.error(f"Labeling error: {e}")
        return "Miscellaneous"

async def generate_dataset_summary(cluster_data: List[Dict[str, Any]]) -> str:
    """Generate a 1-3 sentence summary of the entire dataset based on cluster samples."""
    if not cluster_data:
        return "A collection of documents."
        
    sample_texts = []
    for item in cluster_data[:15]: # Up to 15 different clusters/docs
        sample_texts.append(f"[Group: {item['category']}]: {item['text'][:300]}...")

    prompt = (
        "Analyze these document snippets, which have been grouped into logical categories. "
        "Provide a single, professional 1-3 sentence summary of what this entire collection represents. "
        "Refer to the themes found in the groups. Do not use markdown.\n\n"
        "Document Groups:\n" + "\n".join(sample_texts)
    )

    try:
        response = await client.chat.completions.create(
            model="qwen/qwen3.5-27b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250
        )
        content = response.choices[0].message.content
        return content.strip() if content else "An organized collection of documents."
    except Exception as e:
        logger.error(f"Summary generation error: {e}")
        return "An organized collection of documents."

async def clustering_pipeline(processed_data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
    """
    Core ML Pipeline:
    Returns (organized_data, dataset_summary)
    """
    if not processed_data:
        return [], "No data."

    texts = [d["text"] for d in processed_data if d["text"].strip()]
    n_samples = len(texts)
    logger.info(f"Number of samples: {n_samples}")

    if n_samples < 2:
        for d in processed_data:
            d["folder"] = "Misc"
        return processed_data, "A collection of documents."

    # 1. Embeddings (I/O Bound - Async)
    t0 = time.time()
    embeddings = await get_embeddings(texts)
    logger.info(f"Embeddings generated in {time.time() - t0:.2f}s")
    
    # 2 & 3. Reduction & Clustering (CPU Bound - Offload to Thread)
    t1 = time.time()
    
    cluster_labels, embeddings_for_viz = await asyncio.to_thread(
        _worker_run_clustering, embeddings, n_samples
    )

    logger.info(f"UMAP & HDBSCAN took {time.time() - t1:.2f}s")
    
    # 4. Labeling & Summary (Concurrent "Mega-Burst")
    t3 = time.time()
    unique_clusters = set(cluster_labels)
    cluster_names = {}
    
    label_tasks = []
    cluster_ids_for_tasks = []
    summary_sampling_data = []

    for cluster_id in unique_clusters:
        indices = [i for i, l in enumerate(cluster_labels) if l == cluster_id]
        sample_texts = [texts[i] for i in indices]
        
        # Data for summary task (take up to 2 snippets of this cluster for more variety)
        category_name = cluster_id if cluster_id != -1 else "Unsorted"
        for stext in sample_texts[:2]:
            summary_sampling_data.append({
                "category": category_name,
                "text": stext
            })

        if cluster_id == -1:
            cluster_names[cluster_id] = "Unsorted"
        else:
            label_tasks.append(get_cluster_label(sample_texts))
            cluster_ids_for_tasks.append(cluster_id)
    
    # Fire Labeling AND Summary together
    all_ai_tasks = label_tasks + [generate_dataset_summary(summary_sampling_data)]
    raw_results = await asyncio.gather(*all_ai_tasks)
    
    # Casting/Slicing with explicit typing to satisfy static analysis
    dataset_summary: str = str(raw_results[-1]) if raw_results else "A collection of documents."
    labels: List[str] = [str(r) for r in raw_results[:-1]]
    
    for cid, label in zip(cluster_ids_for_tasks, labels):
        cluster_names[cid] = label
        
    logger.info(f"AI Concurrent Burst took {time.time() - t3:.2f}s")

    # Map texts back to folder names and coords
    text_to_folder = {}
    text_to_coords = {}
    
    for i, label in enumerate(cluster_labels):
        text = texts[i]
        text_to_folder[text] = cluster_names[label]
        # Use the 2D visualization embeddings for coordinates
        if n_samples > 3:
            # Force conversion to numpy array to satisfy type checker if needed, 
            # though it should already be one. 
            coords_row = np.asarray(embeddings_for_viz)[i]
            text_to_coords[text] = {"x": float(coords_row[0]), "y": float(coords_row[1])}
        else:
            # Dummy coords for tiny datasets to prevent UI crash
            text_to_coords[text] = {"x": float(i), "y": float(i)}

    for d in processed_data:
        d["folder"] = text_to_folder.get(d["text"], "Misc")
        coords = text_to_coords.get(d["text"], {"x": 0.0, "y": 0.0})
        d["x"] = coords["x"]
        d["y"] = coords["y"]
        
    return processed_data, dataset_summary
