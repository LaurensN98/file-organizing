import logging
import base64
import asyncio
from typing import List, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import httpx

from app.services.processing import process_files
from app.models.metadata import DocumentMetadata, UploadBatch
from app.core.database import SessionLocal
from app.tasks import process_upload_task
from pgvector.sqlalchemy import Vector
from sqlalchemy import text

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    try:
        processed_data = await process_files(files)
        
        serializable_data = []
        for item in processed_data:
            serializable_item = item.copy()
            serializable_item["content"] = base64.b64encode(item["content"]).decode("utf-8")
            serializable_data.append(serializable_item)
            
    except Exception as e:
        logger.error(f"Initial processing failed: {e}")
        raise HTTPException(status_code=500, detail="File processing failed")

    db = SessionLocal()
    try:
        batch = UploadBatch(status="PENDING")
        db.add(batch)
        db.commit()
        db.refresh(batch)
        
        process_upload_task.delay(str(batch.id), serializable_data)
        
        return {"batch_id": str(batch.id)}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to initiate batch: {e}")
        raise HTTPException(status_code=500, detail="Failed to start processing")
    finally:
        db.close()

@router.get("/results/{batch_id}")
async def get_results(batch_id: str):
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

        analysis_results = []
        for doc in batch.documents:
            analysis_results.append({
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
            })
            
        return {
            "status": "SUCCESS",
            "analysis": analysis_results,
            "summary": batch.summary,
            "zip_file": batch.zip_base64
        }
    finally:
        db.close()

@router.post("/vector-search")
async def search_similar_docs(query: str, limit: int = 50):
    """
    Performs hybrid search using dense (OpenRouter) and sparse (SPLADE) embeddings.
    Combines results using Reciprocal Rank Fusion (RRF).
    """
    db = SessionLocal()
    try:
        from app.services.ml_engine import get_embeddings, generate_sparse_embedding
        
        # 1. Generate query embeddings
        dense_task = get_embeddings([query])
        sparse_task = generate_sparse_embedding(query)
        
        # Run both in parallel
        dense_vec, sparse_query = await asyncio.gather(dense_task, sparse_task)
        
        if dense_vec.size == 0:
             return []
             
        dense_query_list = dense_vec[0].tolist()
        
        # 2. Dense Search (DiskANN)
        dense_results = db.query(DocumentMetadata).order_by(
            DocumentMetadata.dense_embedding.cosine_distance(dense_query_list)
        ).limit(limit * 2).all()
        
        # 3. Sparse Search (GIN)
        sparse_results = []
        if sparse_query:
            keys = list(sparse_query.keys())
            sparse_results = db.query(DocumentMetadata).filter(
                text("sparse_embedding ?| :keys")
            ).params(keys=keys).limit(limit * 2).all()

        # 4. RRF
        k = 60
        scores: dict[Any, float] = {}
        for rank, doc in enumerate(dense_results):
            scores[doc.id] = scores.get(doc.id, 0.0) + 1.0 / (k + rank + 1)
        for rank, doc in enumerate(sparse_results):
            scores[doc.id] = scores.get(doc.id, 0.0) + 1.0 / (k + rank + 1)
            
        # 5. Assembly
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:limit]
        
        # Mapping for result objects
        doc_map = {}
        for doc in dense_results:
            doc_map[doc.id] = doc
        for doc in sparse_results:
            doc_map[doc.id] = doc
        
        results = []
        for doc_id in sorted_ids:
            doc = doc_map.get(doc_id)
            if doc:
                results.append({
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "folder": doc.cluster_label,
                    "score": round(float(scores[doc_id]), 4)
                })
        return results
    finally:
        db.close()