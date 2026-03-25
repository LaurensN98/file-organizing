import asyncio
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, literal_column
from fastapi.concurrency import run_in_threadpool
from app.models.metadata import DocumentMetadata
from app.services.embeddings import get_embeddings, generate_sparse_embedding
from app.services.deepinfra_client import deepinfra_client

logger = logging.getLogger(__name__)

def _run_db_searches_sync(
    db: Session, 
    dense_query_list: List[float], 
    sparse_query: Dict[str, float], 
    batch_id: str, 
    search_limit: int
) -> Tuple[List[Any], List[Any]]:
    """Synchronous database searches for dense and sparse embeddings."""
    # Dense Search
    dense_expr = DocumentMetadata.dense_embedding.cosine_distance(dense_query_list)
    dense_query = db.query(
        DocumentMetadata.id,
        DocumentMetadata.filename,
        DocumentMetadata.cluster_label,
        DocumentMetadata.summary,
        dense_expr
    )
    if batch_id:
        dense_query = dense_query.filter(DocumentMetadata.batch_id == batch_id)
    dense_res = dense_query.order_by(dense_expr).limit(search_limit * 2).all()
        
    # Sparse Search
    sparse_res = []
    if sparse_query:
        # Optimization: prune sparse_query to top 50 tokens by weight
        top_k_sparse = 50
        sorted_tokens = sorted(sparse_query.items(), key=lambda item: item[1], reverse=True)[:top_k_sparse]

        clauses, keys, params = [], [], {}
        for i, (token, weight) in enumerate(sorted_tokens):
            if weight < 0.05: # Skip negligible tokens to save DB computation
                continue
            key_param, val_param = f"k_{i}", f"v_{i}"
            clauses.append(f"coalesce((sparse_embedding->>:{key_param})::float, 0) * :{val_param}")
            params[key_param], params[val_param] = str(token), float(weight)
            keys.append(str(token))

        if clauses:
            score_sql = " + ".join(clauses)
            sparse_query_obj = db.query(
                DocumentMetadata.id,
                DocumentMetadata.filename,
                DocumentMetadata.cluster_label,
                DocumentMetadata.summary,
                text(f"({score_sql})")
            ).filter(text("sparse_embedding ?| :keys"))
            if batch_id:
                sparse_query_obj = sparse_query_obj.filter(DocumentMetadata.batch_id == batch_id)
            sparse_res = sparse_query_obj.params(keys=keys, **params).order_by(text(f"({score_sql}) DESC")).limit(search_limit * 2).all()
            
    return dense_res, sparse_res


async def hybrid_search(
    db: Session, 
    query: str, 
    limit: int = 25, 
    alpha: float = 0.4,
    batch_id: str = None,
    rerank: bool = True
) -> List[Dict[str, Any]]:
    """
    Performs hybrid search followed by a reranking step using DeepInfra's LLama-nemotron-rerank.
    """
    # 1. Increase candidate pool for reranking
    search_limit = limit * 2 if rerank else limit
    
    # 2. Generate query embeddings
    dense_task = get_embeddings([query])
    sparse_task = generate_sparse_embedding(query)
    
    dense_vec, sparse_query = await asyncio.gather(dense_task, sparse_task)
    
    if dense_vec.size == 0:
        return []
            
    dense_query_list = dense_vec[0].tolist()
    
    # Executing DB logic in a threadpool to avoid blocking event loop
    dense_results, sparse_results = await run_in_threadpool(
        _run_db_searches_sync, 
        db, 
        dense_query_list, 
        sparse_query, 
        batch_id, 
        search_limit
    )

    # Relative Score Fusion
    dense_scores = {row[0]: 1.0 - (float(row[4]) / 2.0) for row in dense_results}
    sparse_scores = {row[0]: float(row[4]) for row in sparse_results}
    
    max_dense = max(dense_scores.values()) if dense_scores else 1.0
    max_sparse = max(sparse_scores.values()) if sparse_scores else 1.0

    scores = {}
    doc_map = {}
    for res_list in (dense_results, sparse_results):
        for row in res_list:
            doc_map[row[0]] = row
            
    # Calculate fusion scores for sorting candidates
    all_ids = list(set(dense_scores.keys()) | set(sparse_scores.keys()))
    for doc_id in all_ids:
        d_norm = dense_scores.get(doc_id, 0.0) / (max_dense or 1.0)
        s_norm = sparse_scores.get(doc_id, 0.0) / (max_sparse or 1.0)
        scores[doc_id] = (alpha * d_norm) + ((1.0 - alpha) * s_norm)
    
    # Select top candidates for final results or reranking
    top_candidate_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:search_limit]
    
    # 2. Optional Reranking Step
    if rerank and top_candidate_ids:
        try:
            # 2. Enrich context for the VL-reranker
            # Combining filename and summary provides a more complete 'document image' for the model.
            documents_to_rerank = [
                f"File: {doc_map[doc_id].filename}\nSummary: {doc_map[doc_id].summary or 'No summary.'}"
                for doc_id in top_candidate_ids
            ]
            
            # DeepInfra call
            rerank_response = await deepinfra_client.rerank(
                model="nvidia/llama-nemotron-rerank-vl-1b-v2",
                queries=[query],
                documents=documents_to_rerank
            )
            
            # DeepInfra returns a score for each document in the order provided
            rerank_scores = rerank_response.get("scores", [])
            for idx, doc_id in enumerate(top_candidate_ids):
                if idx < len(rerank_scores):
                    # Combine original score with reranker score (or just use reranker score)
                    # Often rerankers provide a high-quality global score (0 to 1) 
                    scores[doc_id] = rerank_scores[idx]
        except Exception as e:
            logger.error(f"Reranking failed, falling back to hybrid scores: {e}")

    # Final assembly
    final_ids = sorted(top_candidate_ids, key=lambda x: scores[x], reverse=True)[:limit]
    
    return [{
        "id": str(doc_id),
        "filename": doc_map[doc_id].filename,
        "folder": doc_map[doc_id].cluster_label,
        "score": round(float(scores[doc_id]), 4)
    } for doc_id in final_ids if doc_id in doc_map]
