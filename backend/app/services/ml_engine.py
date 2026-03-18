import os
import logging
import warnings
import time
import numpy as np
import umap
from sklearn.cluster import HDBSCAN
from sklearn.decomposition import PCA
import base64
import asyncio
from typing import List, Dict, Tuple, Any
from app.core.config import settings
from app.services.openai_client import client
from app.services.embeddings import get_embeddings, generate_sparse_embeddings

# Configure logging
logger = logging.getLogger(__name__)

# Suppress UMAP UserWarnings
warnings.filterwarnings("ignore", category=UserWarning, module="umap")


def _worker_run_clustering(embeddings: np.ndarray, n_samples: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Synchronous worker for dimensionality reduction and clustering.
    """
    init_mode = "random" if n_samples < 15 else "spectral"
    n_neighbors = min(n_samples - 1, 15) 
    
    # 1. Dimensionality Reduction for Clustering
    if n_samples < 50:
         # Use PCA for small datasets
         n_components_pca = min(n_samples - 1, 10)
         pca = PCA(n_components=n_components_pca, random_state=42)
         embeddings_for_clustering = pca.fit_transform(embeddings)
    else:
         # Use UMAP for datasets >= 50
         reducer_cluster = umap.UMAP(
            n_neighbors=15,
            n_components=15,
            min_dist=0.0, 
            metric='cosine',
            random_state=42,
            init=init_mode,
            n_jobs=1 
        )
         embeddings_for_clustering = reducer_cluster.fit_transform(embeddings)
         
    # 2. Dimensionality Reduction for Visualization
    if n_samples <= 3:
         embeddings_for_viz = embeddings[:, :2] if embeddings.shape[1] >= 2 else embeddings
    else:
         reducer_viz = umap.UMAP(
            n_neighbors=n_neighbors,
            n_components=2,
            min_dist=0.0, 
            metric='cosine',
            random_state=42,
            init=init_mode,
            n_jobs=1 
        )
         embeddings_for_viz = reducer_viz.fit_transform(embeddings)

    # 3. Clustering (HDBSCAN)
    clusterer = HDBSCAN(
        min_cluster_size=2, 
        min_samples=2,                  
        cluster_selection_method='leaf', 
        metric='euclidean',
        n_jobs=1 
    )
    
    cluster_labels = clusterer.fit_predict(embeddings_for_clustering)
    
    # # 4. Post-processing: force-assign any remaining noise (-1) to the nearest cluster.
    # unique_labels = set(cluster_labels)
    # if -1 in unique_labels:
    #     # We have at least one valid cluster to map noise into
    #     valid_labels = [l for l in unique_labels if l != -1]
        
    #     # Calculate centroids for each valid cluster
    #     cluster_centers = {
    #         l: np.mean(embeddings_for_clustering[cluster_labels == l], axis=0)
    #         for l in valid_labels
    #     }
        
    #     for i, label in enumerate(cluster_labels):
    #         if label == -1:
    #             point = embeddings_for_clustering[i]
    #             # Find the nearest valid cluster based on Euclidean distance
    #             nearest_label = min(
    #                 valid_labels, 
    #                 key=lambda l: np.linalg.norm(point - cluster_centers[l])
    #             )
    #             cluster_labels[i] = nearest_label
    return cluster_labels, embeddings_for_viz

async def get_cluster_label(samples: List[Dict[str, str]]) -> str:
    """Generate a concise folder name by analyzing filenames and content snippets."""
    if not samples:
        return "Miscellaneous"

    prompt = (
        "Analyze the following sample documents (formatted as 'Filename | Text Excerpt') which all belong to the same cluster. "
        "Find the common denominator that unifies all these samples. "
        "Provide ONLY a single, general umbrella folder name (1-3 words) that accurately captures the entire collection. "
        "Do not return JSON. Do not return markdown. Do not explain. Return ONLY the folder title.\n\n"
        "Examples: 'Financial Reports', 'Legal Contracts', 'Resume Applications', 'Product Manuals'.\n\n"
        "Cluster Samples:\n"
    )
    
    # Give the model a diverse look at the cluster
    sample_blocks = []
    for s in samples[:8]:
        filename = s.get("filename", "Unknown")
        excerpt = (s.get("text") or "")[:800]
        sample_blocks.append(f"{filename} | {excerpt}")

    prompt += "\n---\n".join(sample_blocks)
    
    try:
        logger.info(f"Generating label for cluster with {len(samples)} documents...")
        response = await client.chat.completions.create(
            model="xiaomi/mimo-v2-flash", 
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=20,
            temperature=0.1,
        )
        content = response.choices[0].message.content
        if content:
            logger.info(f"Raw Label result: {content[:100]}...")

            # Clean up markdown, quotes, and common JSON artifacts
            clean_content = content.strip().replace('"', '').replace("'", "").replace('{', '').replace('}', '').replace('*', '').replace('_', '').replace('#', '')
            if ":" in clean_content and len(clean_content.split(":")) > 1:
                # Handle cases like "Folder: Name"
                clean_content = clean_content.split(":")[-1].strip()
                
            return clean_content
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
        logger.info("Generating dataset summary...")
        response = await client.chat.completions.create(
            model="xiaomi/mimo-v2-flash",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250
        )
        content = response.choices[0].message.content
        if content:
            return content.strip()
        return "An organized collection of documents."
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

    # Combine filename and text for maximum signal in both clustering and search
    texts = [f"Filename: {d['filename']} | {d.get('text') or ''}".strip() for d in processed_data]
    n_samples = len(texts)
    logger.info(f"Number of samples for ML processing: {n_samples}")

    # For tiny datasets, we still want to proceed to get embeddings, but clustering will be trivial
    if n_samples < 2:
        logger.info("Tiny dataset detected, skipping complex clustering.")

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
        
        # Build structured samples for labeling
        cluster_samples = []
        for idx in indices[:8]:
            doc = processed_data[idx]
            cluster_samples.append({
                "filename": doc["filename"],
                "text": (doc.get("text") or "")
            })

        # Data for summary task (take up to 2 snippets of this cluster for more variety)
        category_name = cluster_id if cluster_id != -1 else "Unsorted"
        for s in cluster_samples[:2]:
            summary_sampling_data.append({
                "category": category_name,
                "text": f"{s['filename']} | {s['text'][:300]}..."
            })

        if cluster_id == -1:
            cluster_names[cluster_id] = "Unsorted"
        else:
            label_tasks.append(get_cluster_label(cluster_samples))
            cluster_ids_for_tasks.append(cluster_id)
    
    # Fire Labeling AND Summary together
    all_ai_tasks = label_tasks + [generate_dataset_summary(summary_sampling_data)]
    raw_results = await asyncio.gather(*all_ai_tasks, return_exceptions=True)
    
    # Check for exceptions in gather
    cleaned_results: List[Any] = []
    # Use a copy to avoid slicing issues if needed, or just index safely
    for r in list(raw_results):
        if isinstance(r, Exception):
            logger.error(f"AI Task failed: {r}")
            cleaned_results.append("Miscellaneous Error")
        else:
            cleaned_results.append(r)
    
    # Ensure dataset_summary is a string for logging
    final_summary = str(cleaned_results[-1]) if len(cleaned_results) > 0 else "No summary."
    dataset_summary: str = final_summary
    # Labels represent all results except the last one (summary)
    labels: List[str] = [str(r) for idx, r in enumerate(cleaned_results) if idx < len(cleaned_results) - 1]
    
    logger.info(f"Summary result: {final_summary[:100]}...")
    
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

    # Generate sparse embeddings in batches to avoid timeouts on CPU
    logger.info(f"Generating sparse embeddings for {n_samples} documents...")
    all_sparse_embeddings = await generate_sparse_embeddings(texts, batch_size=32)
    logger.info(f"Sparse embeddings successfully generated.")

    # Final mapping of results (folders, coords, embeddings) to processed_data
    for i, d in enumerate(processed_data):
        combined_text = texts[i]
        d["folder"] = text_to_folder.get(combined_text, "Misc")
        coords = text_to_coords.get(combined_text, {"x": 0.0, "y": 0.0})
        d["x"] = coords["x"]
        d["y"] = coords["y"]
        
        # Store both dense and sparse embeddings for persistence 
        d["dense_embedding"] = embeddings[i].tolist() if i < len(embeddings) else None
        d["sparse_embedding"] = all_sparse_embeddings[i]
        
    return processed_data, dataset_summary
