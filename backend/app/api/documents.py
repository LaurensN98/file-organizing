import logging
import base64
import asyncio
import os
from pathlib import Path
from typing import List, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.concurrency import run_in_threadpool
import httpx
from app.services.embeddings import get_embeddings, generate_sparse_embedding

from app.services.processing import process_files
from app.models.metadata import DocumentMetadata, UploadBatch
from app.core.database import SessionLocal
from app.tasks import process_upload_task
from pgvector.sqlalchemy import Vector
from sqlalchemy import text

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload")
def upload_documents(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    db = SessionLocal()
    try:
        # 1. Create Batch first to get ID for directory naming
        batch = UploadBatch(status="PENDING")
        db.add(batch)
        db.commit()
        db.refresh(batch)
        
        # 2. Setup storage directory
        upload_dir = Path("/app/uploads") / str(batch.id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        raw_files_data = []
        import re
        
        def secure_filename(filename: str) -> str:
            # Prevent path traversal while preserving directory structures and spaces
            if not filename: return "unnamed_file"
            
            # Remove any path traversal constructs
            filename = filename.replace("..\\", "").replace("../", "")
            
            # Normalize slashes
            filename = filename.replace("\\", "/")
            
            # Strip leading slashes to prevent absolute path injection
            while filename.startswith("/"):
                filename = filename[1:]
                
            # Replace genuinely invalid file characters depending on OS (Windows/Linux)
            filename = re.sub(r'[<>:"|?*]', '_', filename)
            
            return filename if filename else "unnamed_file"
        for file in files:
            # Save file to shared volume using secured filename
            safe_name = secure_filename(file.filename or "unnamed")
            file_path = upload_dir / safe_name
            # Ensure subdirectories exist if filename contains paths
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            content = file.file.read()
            with open(file_path, "wb") as f:
                f.write(content)
                
            raw_files_data.append({
                "filename": safe_name,
                "path": str(file_path)
            })
        process_upload_task.delay(str(batch.id), raw_files_data)
        return {"batch_id": str(batch.id)}
    except Exception as e:
        db.rollback()
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="File upload failed")
    finally:
        db.close()

@router.get("/results/{batch_id}")
def get_results(batch_id: str):
    db = SessionLocal()
    try:
        batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        if batch.status in ["PENDING", "PROCESSING"]:
            return {
                "status": batch.status,
                "analysis": [],
                "summary": None,
                "zip_file": None
            }
        
        if batch.status == "FAILED":
            return {
                "status": "FAILED",
                "error": batch.error_message,
                "analysis": [],
                "summary": None,
                "zip_file": None
            }

        analysis_results = [{
            "id": str(doc.id),
            "filename": doc.filename,
            "folder": doc.cluster_label,
            "x": doc.x_coord,
            "y": doc.y_coord,
            "metadata": {
                "file_size_kb": doc.file_size_kb,
                "file_type": doc.file_type,
                "page_count": doc.page_count,
                "language": doc.language
            }
        } for doc in batch.documents]
        # Check if the ZIP file path exists in Redis
        import redis
        from app.core.config import settings
        r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        zip_path = r.get(f"batch_zip:{batch_id}")
            
        return {
            "status": "SUCCESS",
            "analysis": analysis_results,
            "summary": batch.summary,
            "has_zip": bool(zip_path)
        }
    finally:
        db.close()

@router.get("/download/{batch_id}")
def download_results(batch_id: str):
    import redis
    from app.core.config import settings
    r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    zip_path = r.get(f"batch_zip:{batch_id}")
    
    if not zip_path or not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="ZIP file not found or expired")
        
    return FileResponse(
        path=zip_path, 
        filename="organized_documents.zip", 
        media_type="application/zip"
    )

@router.post("/vector-search")
async def search_similar_docs(query: str, limit: int = 25):
    """
    Performs hybrid search using dense (OpenRouter) and sparse (SPLADE) embeddings.
    Combines results using Reciprocal Rank Fusion (RRF).
    """
    db = SessionLocal()
    try:
        
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
            dense_res = db.query(DocumentMetadata, dense_expr).order_by(
                dense_expr
            ).limit(limit * 2).all()
            
            # 3. Sparse Search (GIN + Weighted Dot Product)
            sparse_res = []
            if sparse_query:
                # Construct a weighted dot product score: Σ (doc_weight * query_weight)
                clauses = []
                keys = []
                params: dict[str, Any] = {}
                for i, (token, weight) in enumerate(sparse_query.items()):
                    # Cast to float because JSONB stores values as numbers/strings
                    key_param = f"k_{i}"
                    val_param = f"v_{i}"
                    clauses.append(f"coalesce((sparse_embedding->>:{key_param})::float, 0) * :{val_param}")
                    params[key_param] = str(token)
                    params[val_param] = float(weight)
                    keys.append(str(token))
    
                score_sql = " + ".join(clauses)
                
                # Using the GIN index for filtering (?, ?|, ?&) and the calculated score for ordering
                sparse_res = db.query(DocumentMetadata, text(f"({score_sql})")).filter(
                    text("sparse_embedding ?| :keys")
                ).params(keys=keys, **params).order_by(
                    text(f"({score_sql}) DESC")
                ).limit(limit * 2).all()
                
            return dense_res, sparse_res

        dense_results, sparse_results = await run_in_threadpool(run_db_searches)

        # 4. Relative Score Fusion (RSF)
        # Convert dense distances to similarities (0 to 1). Cosine distance ranges from 0 to 2.
        dense_scores = {doc.id: 1.0 - (float(dist) / 2.0) for doc, dist in dense_results}
        sparse_scores = {doc.id: float(score) for doc, score in sparse_results}
        
        # Normalize against the max score in the result set to equalize Dense and Sparse bounds
        max_dense = max(dense_scores.values()) if dense_scores else 1.0
        max_sparse = max(sparse_scores.values()) if sparse_scores else 1.0
        
        max_dense = max_dense if max_dense > 0 else 1.0
        max_sparse = max_sparse if max_sparse > 0 else 1.0

        # Alpha determines the balance. We heavily favor sparse (0.7) for superior keyword fidelity.
        alpha = 0.4 
        
        scores = {}
        doc_map = {}
        all_ids = set(dense_scores.keys()) | set(sparse_scores.keys())
        
        # Build the document map
        for res_list in (dense_results, sparse_results):
            for doc, _ in res_list:
                doc_map[doc.id] = doc
                
        # Calculate final hybrid score
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
    finally:
        db.close()