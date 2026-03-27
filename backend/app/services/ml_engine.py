import logging
import warnings
import time
import re
import numpy as np
import umap
from sklearn.cluster import HDBSCAN
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
import asyncio
from typing import List, Dict, Any, Coroutine, Union, Tuple
from app.core.openai_client import openai_client
from app.services.embeddings import get_embeddings, generate_sparse_embeddings


# Configure logging
logger = logging.getLogger(__name__)


# Suppress UMAP UserWarnings
warnings.filterwarnings("ignore", category=UserWarning, module="umap")


def _get_doc_signal(d: Dict[str, Any]) -> str:
    """Combines filename and summary/text into a single embedding signal."""
    meta = d.get("metadata", {})
    summary = meta.get("summary", "")
    
    # 1. Clean the filename (strip extension, replace symbols with spaces)
    raw_filename = d.get("filename", "unnamed")
    clean_name = raw_filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
    
    if summary:
        tags_list = meta.get("tags", [])
        tags_str = ", ".join(tags_list) if tags_list else ""
        doc_type = meta.get("document_type", "")
        
        components = [clean_name]
        if doc_type: components.append(doc_type)
        if tags_str: components.append(tags_str)
        components.append(summary)
        return " - ".join(components).strip()
    
    raw_text = d.get('text', '') or ''
    return f"{clean_name} - {raw_text[:8000]}".strip()


def _worker_run_clustering(embeddings: np.ndarray, n_samples: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Synchronous worker for dimensionality reduction and clustering.
    Optimized for high recall (minimizing 'unsorted' noise).
    """
    init_mode = "random" if n_samples < 15 else "spectral"
    
    # 1. Dimensionality Reduction for Clustering
    if n_samples < 50:
         # CRITICAL FIX: L2-normalize embeddings before PCA to preserve cosine relationships
         normalized_embeddings = normalize(embeddings, norm='l2')
         n_components_pca = min(n_samples - 1, 10)
         pca = PCA(n_components=n_components_pca, random_state=42)
         embeddings_for_clustering = pca.fit_transform(normalized_embeddings)
    else:
         # CRITICAL FIX: Dynamically scale n_neighbors to prevent global topology distortion
         n_neighbors_cluster = min(n_samples - 1, 15)
         reducer_cluster = umap.UMAP(
            n_neighbors=n_neighbors_cluster,
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
         n_neighbors_viz = min(n_samples - 1, 15)
         reducer_viz = umap.UMAP(
            n_neighbors=n_neighbors_viz,
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
        min_samples=1,                  
        cluster_selection_method='leaf', 
        cluster_selection_epsilon=0.5,
        metric='euclidean', 
        allow_single_cluster=True, 
        n_jobs=1 
    )
    
    cluster_labels = clusterer.fit_predict(embeddings_for_clustering)
    
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
    for s in samples[:5]:
        filename = s.get("filename", "Unknown")
        excerpt = (s.get("text") or "")[:1000]
        sample_blocks.append(f"{filename} | {excerpt}")

    prompt += "\n---\n".join(sample_blocks)
    
    try:
        logger.info(f"Generating label for cluster with {len(samples)} documents...")
        response = await openai_client.chat.completions.create(
            model="xiaomi/mimo-v2-flash", 
            extra_body={
                "provider": {
                    "sort": "throughput", 
                    "preferred_min_throughput": {
                        'p90': 25, 
                    }
                }
            },
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=20,
            temperature=0.1,
        )
        content = response.choices[0].message.content
        if content:
            # Clean up markdown and common artifacts safely
            clean_content = content.replace('*', '').replace('#', '').replace('"', '').replace("'", "").strip()
            
            # If AI returned "Folder: Name", extract "Name"
            if ":" in clean_content:
                parts = clean_content.split(":")
                if len(parts) > 1 and len(parts[-1].strip()) > 1:
                    clean_content = parts[-1].strip()
            
            # FINAL GUARD: If cleaning made it empty, or it's still empty, use raw content or fallback
            final_label = clean_content if len(clean_content) > 1 else content.strip()
            
            if not final_label or final_label.lower() == "none":
                final_label = "Miscellaneous"
                
            logger.info(f"Final Label processed: {final_label}")
            return final_label
            
        return "Miscellaneous"
    except Exception as e:
        logger.error(f"Labeling error: {e}")
        return "Miscellaneous"


async def generate_dataset_summary(cluster_data: List[Dict[str, Any]]) -> str:
    """Generate a 1-3 sentence summary of the entire dataset based on cluster samples."""
    if not cluster_data:
        return "A collection of documents."
        
    sample_texts = [
        f"[Group: {item['category']}]: {item['text'][:300]}..." 
        for item in cluster_data[:15]
    ]

    prompt = (
        "Analyze these document snippets, which have been grouped into logical categories. "
        "Provide a single, professional 1-3 sentence summary of what this entire collection represents. "
        "Refer to the themes found in the groups. Do not use markdown.\n\n"
        "Document Groups:\n" + "\n".join(sample_texts)
    )

    try:
        logger.info("Generating dataset summary...")
        response = await openai_client.chat.completions.create(
            model="xiaomi/mimo-v2-flash",
            messages=[{"role": "user", "content": prompt}],
            extra_body={
                "provider": {
                    "sort": "throughput", 
                    "preferred_min_throughput": {
                        'p90': 25, 
                    }
                }
            },
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
    if not processed_data:
        return [], "No data."

    texts = [_get_doc_signal(d) for d in processed_data]

    n_samples = len(texts)
    logger.info(f"Number of samples for ML processing: {n_samples}")

    t0 = time.time()
    
    # 2. Execute Both Embedding Models Concurrently
    logger.info(f"Generating Dense and Sparse embeddings concurrently for {n_samples} docs...")
    
    try:
        embeddings, all_sparse_embeddings = await asyncio.gather(
            get_embeddings(texts),
            generate_sparse_embeddings(texts, batch_size=32)
        )
        logger.info(f"Both embedding sets generated successfully in {time.time() - t0:.2f}s")
    except Exception as e:
        logger.error(f"Failed during concurrent embedding generation: {e}")
        raise

    # For tiny datasets, return immediately to avoid HDBSCAN/UMAP errors
    if n_samples < 2:
        logger.info("Tiny dataset detected, skipping complex clustering.")
        for i, d in enumerate(processed_data):
            d["folder"] = "Miscellaneous"
            d["x"], d["y"] = 0.0, 0.0
            # Safety check: if embeddings is a numpy array, it has .tolist()
            d["dense_embedding"] = embeddings[i].tolist() if i < len(embeddings) else None
            d["sparse_embedding"] = all_sparse_embeddings[i] if i < len(all_sparse_embeddings) else {}
        return processed_data, "An organized collection of documents."

    # 2 & 3. Reduction & Clustering (CPU Bound - Offload to Thread)
    t1 = time.time()
    
    # Ensure embeddings are a NumPy array to prevent shape/slice errors in worker
    np_embeddings = np.array(embeddings)
    
    cluster_labels, embeddings_for_viz = await asyncio.to_thread(
        _worker_run_clustering, np_embeddings, n_samples
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
        cluster_samples = [
            {"filename": processed_data[idx]["filename"], "text": (processed_data[idx].get("text") or "")}
            for idx in indices[:8]
        ]

        # Data for summary task (take up to 2 snippets of this cluster for more variety)
        category_name: Union[int, str] = cluster_id if cluster_id != -1 else "Miscellaneous"
        summary_sampling_data.extend([
            {
                "category": category_name,
                "text": f"{s.get('filename', 'Unknown')} | {str(s.get('text', ''))[:300]}..."
            }
            for s in cluster_samples[:2]
        ])

        if cluster_id == -1:
            cluster_names[cluster_id] = "Miscellaneous"
        else:
            label_tasks.append(get_cluster_label(cluster_samples))
            cluster_ids_for_tasks.append(cluster_id)
    
    # Fire Labeling AND Summary together
    all_ai_tasks = label_tasks + [generate_dataset_summary(summary_sampling_data)]
    raw_results = await asyncio.gather(*all_ai_tasks, return_exceptions=True)
    
    # Check for exceptions in gather
    cleaned_results: List[Any] = []
    for r in list(raw_results):
        if isinstance(r, Exception):
            logger.error(f"AI Task failed: {r}")
            cleaned_results.append("Miscellaneous Error")
        else:
            cleaned_results.append(r)
    
    # Summary is the last task, labels are everything before
    final_summary_raw = cleaned_results[-1] if cleaned_results else "No summary."
    final_summary: str = str(final_summary_raw)
    dataset_summary: str = final_summary
    
    # Extract labels (everything but the last element which is the summary)
    raw_labels = [cleaned_results[i] for i in range(len(cleaned_results) - 1)] if len(cleaned_results) > 1 else []
    labels: List[str] = [str(r) for r in raw_labels]
    
    logger.info(f"Summary result: {final_summary[:100]}...")
    
    # 5. Build final map with standardized INT keys
    # Clusters with the same AI name will naturally collapse into the same folder in the UI.
    final_cluster_names = {-1: "Miscellaneous"}
    
    for cid_raw, label_raw in zip(cluster_ids_for_tasks, labels):
        cid = int(cid_raw)
        raw_name = str(label_raw).strip()
        
        # Only use a generic fallback if the result is truly empty or 'none'
        if not raw_name or raw_name.lower() in ["none", "null", ""] or len(raw_name) < 1:
            name = f"Cluster {cid}"
        else:
            name = raw_name
            
        final_cluster_names[cid] = name
        
    logger.info(f"Final mapping generated: {final_cluster_names}")
    logger.info(f"Labeling & Summary took {time.time() - t3:.2f}s")

    # 6. Final mapping of results (folders, coords, embeddings) directly to processed_data by index
    for i, d in enumerate(processed_data):
        # Explicitly cast to int for robust dict lookup
        cluster_id = int(cluster_labels[i])
        
        # Standardize folder name with multi-level fallback
        folder_name = final_cluster_names.get(cluster_id, "Miscellaneous")
        d["folder"] = folder_name if folder_name and str(folder_name).strip() else "Miscellaneous"
        
        # Add 2D visualization embeddings for coordinates
        if n_samples > 3:
            coords_row = np.asarray(embeddings_for_viz)[i]
            d["x"] = float(coords_row[0])
            d["y"] = float(coords_row[1])
        else:
            # Dummy coords for tiny datasets to prevent UI crash
            d["x"] = float(i)
            d["y"] = float(i)
        
        # Store both dense and sparse embeddings for persistence 
        dense_emb = embeddings[i] if i < len(embeddings) else None
        if dense_emb is not None and hasattr(dense_emb, "tolist"):
            d["dense_embedding"] = dense_emb.tolist()
        else:
            d["dense_embedding"] = dense_emb
        
        sparse_vec = all_sparse_embeddings[i] if i < len(all_sparse_embeddings) else {}
        if not sparse_vec:
            logger.warning(f"Sparse embedding for {d.get('filename', 'unnamed')} is EMPTY")
        d["sparse_embedding"] = sparse_vec
        
    return processed_data, dataset_summary
