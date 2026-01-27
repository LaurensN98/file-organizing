import os
import numpy as np
import umap
from sklearn.cluster import HDBSCAN
from openai import OpenAI
from typing import List, Dict

# Initialize client for OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", "dummy-key"),
)

async def get_embeddings(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.array([])
    
    # Using Qwen embedding model via OpenRouter
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

async def get_cluster_label(texts: List[str]) -> str:
    """Ask LLM to name the cluster based on sample texts."""
    prompt = f"Based on the following document snippets, generate a concise (1-3 words) folder name that categorizes them:\n\n"
    prompt += "\n---\n".join([t[:500] for t in texts[:3]])
    
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            extra_body={
                "provider": {
                    "order": ["nebius"],
                }
            }
        )
        return response.choices[0].message.content.strip().replace('"', '')
    except Exception as e:
        print(f"Labeling error: {e}")
        return "Unclassified"

async def clustering_pipeline(processed_data: List[Dict]) -> List[Dict]:
    if not processed_data:
        return []

    texts = [d["text"] for d in processed_data if d["text"].strip()]
    if len(texts) < 2:
        # Not enough data to cluster
        for d in processed_data:
            d["folder"] = "Misc"
        return processed_data

    # 1. Embeddings
    embeddings = await get_embeddings(texts)
    
    # 2. Reduction (UMAP)
    # Reducing to 5 dimensions for clustering, enough to keep structure
    reducer = umap.UMAP(n_neighbors=min(len(texts)-1, 15), n_components=min(len(texts)-1, 5), random_state=42)
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
            # Get samples for this cluster
            indices = [i for i, l in enumerate(cluster_labels) if l == cluster_id]
            sample_texts = [texts[i] for i in indices]
            cluster_names[cluster_id] = await get_cluster_label(sample_texts)

    # Assign folders to processed_data
    text_to_folder = {}
    for i, label in enumerate(cluster_labels):
        text_to_folder[texts[i]] = cluster_names[label]

    for d in processed_data:
        d["folder"] = text_to_folder.get(d["text"], "Misc")
        
    return processed_data
