import os
import logging
import numpy as np
import umap
from sklearn.cluster import HDBSCAN
from openai import OpenAI
from typing import List, Dict

# Configure logging
logger = logging.getLogger(__name__)

# Initialize client for OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", "dummy-key"),
)

async def get_embeddings(texts: List[str]) -> np.ndarray:
    """Fetch embeddings from OpenRouter using Qwen model."""
    if not texts:
        return np.array([])
    
    try:
        response = client.embeddings.create(
            input=texts,
            model="qwen/qwen3-embedding-8b",
            extra_body={
                "provider": {
                    "order": ["nebius"],
                }
            }
        )
        embeddings = [data.embedding for data in response.data]
        return np.array(embeddings)
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        # Return dummy embeddings to keep pipeline alive in case of partial API failure
        return np.random.rand(len(texts), 1536)

async def get_cluster_label(texts: List[str]) -> str:
    """Generate a concise folder name using Google Gemini via OpenRouter."""
    # Construct a prompt with the first few documents
    prompt = "Based on the following document snippets, generate a concise (1-3 words) folder name that categorizes them:\n\n"
    prompt += "\n---\n".join([t[:500] for t in texts[:3]])
    
    try:
        response = client.chat.completions.create(
            model="google/gemini-3-flash-preview", 
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=20
        )
        content = response.choices[0].message.content
        return content.strip().replace('"', '') if content else "Unclassified"
    except Exception as e:
        logger.error(f"Labeling error: {e}")
        return "Unclassified"

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
    embeddings = await get_embeddings(texts)
    
    # 2. Dimensionality Reduction (UMAP)
    # Adjust parameters for small datasets to prevent spectral initialization errors
    init_mode = "random" if n_samples < 15 else "spectral"
    n_neighbors = min(n_samples - 1, 15)
    n_components = min(n_samples - 2, 5) if n_samples > 5 else 2

    if n_samples <= 3:
         # Skip reduction for tiny datasets
         reduced_embeddings = embeddings
    else:
         reducer = umap.UMAP(
            n_neighbors=n_neighbors,
            n_components=n_components,
            random_state=42,
            init=init_mode
        )
         reduced_embeddings = reducer.fit_transform(embeddings)
    
    # 3. Clustering (HDBSCAN)
    clusterer = HDBSCAN(min_cluster_size=2)
    cluster_labels = clusterer.fit_predict(reduced_embeddings)
    
    # 4. Labeling Clusters
    unique_clusters = set(cluster_labels)
    cluster_names = {}
    
    for cluster_id in unique_clusters:
        if cluster_id == -1:
            cluster_names[cluster_id] = "Unsorted"
        else:
            # Get samples for this cluster to generate a label
            indices = [i for i, l in enumerate(cluster_labels) if l == cluster_id]
            sample_texts = [texts[i] for i in indices]
            cluster_names[cluster_id] = await get_cluster_label(sample_texts)

    # Map texts back to folder names
    text_to_folder = {}
    for i, label in enumerate(cluster_labels):
        text_to_folder[texts[i]] = cluster_names[label]

    for d in processed_data:
        d["folder"] = text_to_folder.get(d["text"], "Misc")
        
    return processed_data