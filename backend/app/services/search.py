import asyncio
import time
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, select, func, Float, String, cast
from sqlalchemy.dialects.postgresql import ARRAY
from fastapi.concurrency import run_in_threadpool
from app.models.metadata import DocumentMetadata
from app.services.embeddings import get_embeddings, generate_sparse_embedding
from app.core.deepinfra_client import deepinfra_client


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
    stmt = select(
        DocumentMetadata.id,
        DocumentMetadata.filename,
        DocumentMetadata.cluster_label,
        DocumentMetadata.summary,
        dense_expr.label("distance")
    )
    if batch_id:
        stmt = stmt.where(DocumentMetadata.batch_id == batch_id)
    stmt = stmt.order_by(dense_expr).limit(search_limit * 2)
    dense_res = db.execute(stmt).all()
        
    # Sparse Search (Optimized for GIN Index)
    sparse_res = []
    if sparse_query:
        # 1. Prune and Filter
        top_k_sparse = 50
        sorted_tokens = sorted(
            (it for it in sparse_query.items() if it[1] >= 0.05), 
            key=lambda x: x[1], reverse=True
        )[:top_k_sparse]

        if sorted_tokens:
            keys = [str(token) for token, _ in sorted_tokens]
            
            # 2. Build the Dot Product Expression
            score_expr = sum(
                float(weight) * func.coalesce(DocumentMetadata.sparse_embedding[token].astext.cast(Float), 0)
                for token, weight in sorted_tokens
            ).label("sparse_score")

            # 3. Create and Execute the Statement
            stmt = select(
                DocumentMetadata.id,
                DocumentMetadata.filename,
                DocumentMetadata.cluster_label,
                DocumentMetadata.summary,
                score_expr
            ).where(
                DocumentMetadata.sparse_embedding.has_any(cast(keys, ARRAY(String)))
            )

            if batch_id:
                stmt = stmt.where(DocumentMetadata.batch_id == batch_id)

            stmt = stmt.order_by(score_expr.desc()).limit(search_limit * 2)
            sparse_res = db.execute(stmt).all()
            
    return dense_res, sparse_res


def _relative_score_fusion(
    dense_results: List[Any], 
    sparse_results: List[Any], 
    alpha: float, 
    search_limit: int
) -> Tuple[List[str], Dict[str, float], Dict[str, Any]]:
    """Merges and normalizes dense and sparse search results using Relative Score Fusion."""
    dense_scores = {row[0]: 1.0 - (float(row[4]) / 2.0) for row in dense_results}
    sparse_scores = {row[0]: float(row[4]) for row in sparse_results}
    
    max_dense = max(dense_scores.values()) if dense_scores else 1.0
    max_sparse = max(sparse_scores.values()) if sparse_scores else 1.0

    # Fast dictionary comprehension to merge both lists into a map
    doc_map = {row[0]: row for res_list in (dense_results, sparse_results) for row in res_list}
            
    # Calculate fusion scores in a single dictionary comprehension directly from the set union
    all_ids = set(dense_scores.keys()) | set(sparse_scores.keys())
    scores = {
        doc_id: (alpha * (dense_scores.get(doc_id, 0.0) / max_dense)) + 
                ((1.0 - alpha) * (sparse_scores.get(doc_id, 0.0) / max_sparse))
        for doc_id in all_ids
    }

    
    # Sort and slice
    top_candidate_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:search_limit]
    
    return top_candidate_ids, scores, doc_map


async def _apply_reranking(
    query: str,
    top_candidate_ids: List[str],
    doc_map: Dict[str, Any],
    scores: Dict[str, float],
    rerank_limit: int = 15
) -> None:
    """Uses DeepInfra LLM to rerank top candidates, mutating the scores dictionary in-place."""
    t2 = time.perf_counter()
    candidates_to_rerank = top_candidate_ids[:rerank_limit]
    
    try:
        # Enrich context for the reranker
        documents_to_rerank = [
            f"File: {doc_map[doc_id].filename}\nSummary: {doc_map[doc_id].summary or 'No summary.'}"
            for doc_id in candidates_to_rerank
        ]
        
        # DeepInfra call
        rerank_response = await deepinfra_client.rerank(
            model="nvidia/llama-nemotron-rerank-vl-1b-v2",
            queries=[query],
            documents=documents_to_rerank
        )
        
        rerank_scores = rerank_response.get("scores", [])
        scores.update({
            doc_id: score + 10.0 
            for doc_id, score in zip(candidates_to_rerank, rerank_scores)
        })
        
        t_rerank = time.perf_counter() - t2
        logger.info(f"Reranking completed in {t_rerank:.3f}s for {len(candidates_to_rerank)} candidates")
    except Exception as e:
        logger.error(f"Reranking failed, falling back to hybrid scores: {e}")


async def hybrid_search(
    db: Session, 
    query: str, 
    limit: int = 25, 
    alpha: float = 0.4,
    batch_id: str = None,
    rerank: bool = False
) -> List[Dict[str, Any]]:
    """
    Performs hybrid search followed by a reranking step using DeepInfra's LLama-nemotron-rerank.
    """
    # 1. Increase candidate pool for reranking
    search_limit = limit * 2 if rerank else limit
    
    # 2. Generate query embeddings
    t0 = time.perf_counter()
    dense_task = get_embeddings([query])
    sparse_task = generate_sparse_embedding(query)
    
    dense_vec, sparse_query = await asyncio.gather(dense_task, sparse_task)
    t_embeddings = time.perf_counter() - t0
    logger.info(f"Embeddings generated in {t_embeddings:.3f}s")
    
    if dense_vec.size == 0:
        return []
            
    dense_query_list = dense_vec[0].tolist()
    
    # 3. DB Searches (Dense + Sparse)
    t1 = time.perf_counter()
    dense_results, sparse_results = await run_in_threadpool(
        _run_db_searches_sync, 
        db, 
        dense_query_list, 
        sparse_query, 
        batch_id, 
        search_limit
    )
    t_db = time.perf_counter() - t1
    logger.info(f"DB search completed in {t_db:.3f}s. Dense: {len(dense_results)}, Sparse: {len(sparse_results)}")

    # 4. Relative Score Fusion
    top_candidate_ids, scores, doc_map = _relative_score_fusion(
        dense_results, sparse_results, alpha, search_limit
    )
    
    # 5. Optional Reranking Step
    if rerank and top_candidate_ids:
        await _apply_reranking(query, top_candidate_ids, doc_map, scores)

    # Final assembly
    final_ids = sorted(top_candidate_ids, key=lambda x: scores[x], reverse=True)[:limit]
    
    return [{
        "id": str(doc_id),
        "filename": doc_map[doc_id].filename,
        "folder": doc_map[doc_id].cluster_label,
        "score": round(float(scores[doc_id]), 4)
    } for doc_id in final_ids if doc_id in doc_map]
