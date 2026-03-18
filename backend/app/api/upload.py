import logging
import base64
import asyncio
import os
from pathlib import Path
from typing import List, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
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
        for file in files:
            # Save file to shared volume
            file_path = upload_dir / (file.filename or "unnamed")
            # Ensure subdirectories exist if filename contains paths
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            content = file.file.read()
            with open(file_path, "wb") as f:
                f.write(content)
                
            raw_files_data.append({
                "filename": file.filename,
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
            
        return {
            "status": "SUCCESS",
            "analysis": analysis_results,
            "summary": batch.summary,
            "zip_file": batch.zip_base64
        }
    finally:
        db.close()

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
            dense_res = db.query(DocumentMetadata).order_by(
                DocumentMetadata.dense_embedding.cosine_distance(dense_query_list)
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
                    # Using coalesce to handle missing tokens gracefully
                    key_param = f"k_{i}"
                    val_param = f"v_{i}"
                    clauses.append(f"coalesce((sparse_embedding->>:{key_param})::float, 0) * :{val_param}")
                    params[key_param] = str(token)
                    params[val_param] = float(weight)
                    keys.append(str(token))
    
                score_sql = " + ".join(clauses)
                
                # Using the GIN index for filtering (?, ?|, ?&) and the calculated score for ordering
                sparse_res = db.query(DocumentMetadata).filter(
                    text("sparse_embedding ?| :keys")
                ).params(keys=keys, **params).order_by(
                    text(f"({score_sql}) DESC")
                ).limit(limit * 2).all()
                
            return dense_res, sparse_res

        dense_results, sparse_results = await run_in_threadpool(run_db_searches)

        # 4. RRF (Reciprocal Rank Fusion)
        k = 60
        scores = {doc.id: 1.0 / (k + rank + 1) for rank, doc in enumerate(dense_results)}
        for rank, doc in enumerate(sparse_results):
            scores[doc.id] = scores.get(doc.id, 0.0) + 1.0 / (k + rank + 1)
            
        # 5. Assembly
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:limit]
        
        # Mapping for result objects
        doc_map = {doc.id: doc for res_list in (dense_results, sparse_results) for doc in res_list}
        
        return [{
            "id": str(doc_id),
            "filename": doc_map[doc_id].filename,
            "folder": doc_map[doc_id].cluster_label,
            "score": round(float(scores[doc_id]), 4)
        } for doc_id in sorted_ids if doc_id in doc_map]
    finally:
        db.close()