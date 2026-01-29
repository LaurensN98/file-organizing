import os
import logging
import warnings
import asyncio
import time
import numpy as np
import umap
from sklearn.cluster import HDBSCAN
from openai import AsyncOpenAI
from typing import List, Dict

# Configure logging
logger = logging.getLogger(__name__)

# Suppress UMAP UserWarnings
warnings.filterwarnings("ignore", category=UserWarning, module="umap")

# Initialize client for OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", "dummy-key"),
)

async def get_embeddings(texts: List[str]) -> np.ndarray:
    """Fetch embeddings from OpenRouter using Qwen model in parallel batches."""
    if not texts:
        return np.array([])
    
    batch_size = 25 # Smaller batches for more concurrency
    
    async def fetch_batch(batch: List[str], batch_idx: int):
        try:
            response = await client.embeddings.create(
                input=batch,
                model="qwen/qwen3-embedding-8b",
                extra_body={
                    "provider": {
                        "order": ["nebius"],
                    }
                }
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Embedding error in batch {batch_idx}: {e}")
            return [np.random.rand(1536).tolist() for _ in range(len(batch))]

    tasks = []
    for i in range(0, len(texts), batch_size):
        tasks.append(fetch_batch(texts[i:i + batch_size], i // batch_size))
    
    results = await asyncio.gather(*tasks)
    
    # Flatten the results
    all_embeddings = [emb for batch_result in results for emb in batch_result]
    return np.array(all_embeddings)

async def get_cluster_label(texts: List[str]) -> str:
    """Generate a concise folder name using Google Gemini via OpenRouter."""
    # Construct a prompt with the first few documents
    prompt = "Based on the following document snippets, generate a concise (1-3 words) folder name that categorizes them. "
    prompt += "Do not use markdown formatting, bolding (like **), or special characters. Output only the plain text name:\n\n"
    prompt += "\n---\n".join([t[:500] for t in texts[:3]])
    
    try:
        response = await client.chat.completions.create(
            model="google/gemini-3-flash-preview", 
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=20
        )
        content = response.choices[0].message.content
        if content:
            # Clean up markdown and quotes
            return content.strip().replace('"', '').replace('*', '').replace('_', '').replace('#', '')
        return "Unclassified"
    except Exception as e:
        logger.error(f"Labeling error: {e}")
        return "Unclassified"

async def generate_dataset_summary(organized_data: List[Dict]) -> str:
    """Generate a 1-3 sentence summary of the entire dataset."""
    if not organized_data:
        return "No documents processed."
        
    # Sample 1 document from each cluster to give the LLM good variety
    unique_clusters = set(d["folder"] for d in organized_data)
    sample_texts = []
    
    for cluster in unique_clusters:
        # Find first doc in this cluster
        for d in organized_data:
            if d["folder"] == cluster and d["text"].strip():
                sample_texts.append(f"[{cluster}]: {d['text'][:300]}")
                break
    
    if not sample_texts:
        return "A collection of documents."

    prompt = "Analyze the following document snippets (categorized by cluster). "
    prompt += "Write a brief, 1-3 sentence description of what this entire dataset represents (e.g., 'A collection of legal contracts and financial invoices regarding...'). "
    prompt += "Do not use markdown. Keep it professional and concise:\n\n"
    prompt += "\n".join(sample_texts[:10]) # Limit to 10 samples to fit context

    try:
        response = await client.chat.completions.create(
            model="google/gemini-3-flash-preview",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Summary generation error: {e}")
        return "An organized collection of documents."

async def clustering_pipeline(processed_data: List[Dict]) -> List[Dict]:
    """
    Core ML Pipeline:
    1. Embed text (Qwen/OpenRouter)
    2. Reduce dimensions (UMAP)
    3. Cluster (HDBSCAN)
    4. Label clusters (Gemini/OpenRouter)
    """
    if not processed_data:
        return []

    texts = [d["text"] for d in processed_data if d["text"].strip()]
    n_samples = len(texts)

    if n_samples < 2:
        for d in processed_data:
            d["folder"] = "Misc"
        return processed_data

    # 1. Embeddings
    t0 = time.time()
    embeddings = await get_embeddings(texts)
    logger.info(f"Embeddings generated in {time.time() - t0:.2f}s")
    
    # 2. Dimensionality Reduction (UMAP)
    # Adjust parameters for small datasets to prevent spectral initialization errors
    t1 = time.time()
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

    logger.info(f"UMAP reduction took {time.time() - t1:.2f}s")
    
    # 3. Clustering (HDBSCAN)
    t2 = time.time()
    clusterer = HDBSCAN(
        min_cluster_size=2,
        cluster_selection_epsilon=0.5, 
        metric='euclidean',
        )
    # Use the higher dimensional embeddings for better clustering
    cluster_labels = clusterer.fit_predict(embeddings_for_clustering)
    logger.info(f"HDBSCAN clustering took {time.time() - t2:.2f}s")
    
    # 4. Labeling Clusters (Parallelized)
    t3 = time.time()
    unique_clusters = set(cluster_labels)
    cluster_names = {}
    
    label_tasks = []
    cluster_ids_for_tasks = []

    for cluster_id in unique_clusters:
        if cluster_id == -1:
            cluster_names[cluster_id] = "Unsorted"
        else:
            # Get samples for this cluster to generate a label
            indices = [i for i, l in enumerate(cluster_labels) if l == cluster_id]
            sample_texts = [texts[i] for i in indices]
            
            # Create a task for labeling
            label_tasks.append(get_cluster_label(sample_texts))
            cluster_ids_for_tasks.append(cluster_id)
    
    # Run labeling tasks concurrently
    if label_tasks:
        labels = await asyncio.gather(*label_tasks)
        for cid, label in zip(cluster_ids_for_tasks, labels):
            cluster_names[cid] = label
    logger.info(f"Cluster labeling took {time.time() - t3:.2f}s")

    # Map texts back to folder names and coords
    text_to_folder = {}
    text_to_coords = {}
    
    for i, label in enumerate(cluster_labels):
        text = texts[i]
        text_to_folder[text] = cluster_names[label]
        # Use the 2D visualization embeddings for coordinates
        if n_samples > 3:
            text_to_coords[text] = {"x": float(embeddings_for_viz[i][0]), "y": float(embeddings_for_viz[i][1])}
        else:
            # Dummy coords for tiny datasets to prevent UI crash
            text_to_coords[text] = {"x": float(i), "y": float(i)}

    for d in processed_data:
        d["folder"] = text_to_folder.get(d["text"], "Misc")
        coords = text_to_coords.get(d["text"], {"x": 0.0, "y": 0.0})
        d["x"] = coords["x"]
        d["y"] = coords["y"]
        
    return processed_data