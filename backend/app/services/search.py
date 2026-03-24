import asyncio
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.concurrency import run_in_threadpool
from app.models.metadata import DocumentMetadata
from app.services.embeddings import get_embeddings, generate_sparse_embedding

logger = logging.getLogger(__name__)

async def hybrid_search(
    db: Session, 
    query: str, 
    limit: int = 25, 
    alpha: float = 0.4,
    batch_id: str = None
) -> List[Dict[str, Any]]:
    """
    Performs hybrid search using dense (OpenRouter) and sparse (SPLADE) embeddings.
    Combines results using Relative Score Fusion (RSF).
    """
    # 1. Generate query embeddings
    dense_task = get_embeddings([query])
    sparse_task = generate_sparse_embedding(query)
    
    # Run both in parallel
    dense_vec, sparse_query = await asyncio.gather(dense_task, sparse_task)
    
    if dense_vec.size == 0:
        return []
            
    dense_query_list = dense_vec[0].tolist()
    
    def run_db_searches():
        # 2. Dense Search (DiskANN)
        dense_expr = DocumentMetadata.dense_embedding.cosine_distance(dense_query_list)
        dense_query = db.query(DocumentMetadata, dense_expr)
        
        if batch_id:
            dense_query = dense_query.filter(DocumentMetadata.batch_id == batch_id)
            
        dense_res = dense_query.order_by(
            dense_expr
        ).limit(limit * 2).all()
        
        # 3. Sparse Search (GIN + Weighted Dot Product)
        sparse_res = []
        if sparse_query:
            clauses = []
            keys = []
            params: dict[str, Any] = {}
            for i, (token, weight) in enumerate(sparse_query.items()):
                key_param = f"k_{i}"
                val_param = f"v_{i}"
                clauses.append(f"coalesce((sparse_embedding->>:{key_param})::float, 0) * :{val_param}")
                params[key_param] = str(token)
                params[val_param] = float(weight)
                keys.append(str(token))

            score_sql = " + ".join(clauses)
            
            sparse_query_obj = db.query(DocumentMetadata, text(f"({score_sql})")).filter(
                text("sparse_embedding ?| :keys")
            )
            
            if batch_id:
                sparse_query_obj = sparse_query_obj.filter(DocumentMetadata.batch_id == batch_id)
                
            sparse_res = sparse_query_obj.params(keys=keys, **params).order_by(
                text(f"({score_sql}) DESC")
            ).limit(limit * 2).all()
            
        return dense_res, sparse_res

    dense_results, sparse_results = await run_in_threadpool(run_db_searches)

    # 4. Relative Score Fusion (RSF)
    dense_scores = {doc.id: 1.0 - (float(dist) / 2.0) for doc, dist in dense_results}
    sparse_scores = {doc.id: float(score) for doc, score in sparse_results}
    
    max_dense = max(dense_scores.values()) if dense_scores else 1.0
    max_sparse = max(sparse_scores.values()) if sparse_scores else 1.0
    
    max_dense = max_dense if max_dense > 0 else 1.0
    max_sparse = max_sparse if max_sparse > 0 else 1.0

    scores = {}
    doc_map = {}
    all_ids = set(dense_scores.keys()) | set(sparse_scores.keys())
    
    for res_list in (dense_results, sparse_results):
        for doc, _ in res_list:
            doc_map[doc.id] = doc
            
    for doc_id in all_ids:
        d_norm = dense_scores.get(doc_id, 0.0) / max_dense
        s_norm = sparse_scores.get(doc_id, 0.0) / max_sparse
        scores[doc_id] = (alpha * d_norm) + ((1.0 - alpha) * s_norm)
    
    # 5. Assembly
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:limit]
    
    return [{
        "id": str(doc_id),
        "filename": doc_map[doc_id].filename,
        "folder": doc_map[doc_id].cluster_label,
        "score": round(float(scores[doc_id]), 4)
    } for doc_id in sorted_ids if doc_id in doc_map]
