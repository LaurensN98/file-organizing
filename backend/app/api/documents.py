import logging
import asyncio
import os
import redis
from pathlib import Path
from typing import List, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.models.metadata import DocumentMetadata, UploadBatch
from app.core.database import get_db
from app.services.storage import secure_filename, save_upload_file
from app.services.search import hybrid_search
from app.tasks import process_upload_task
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...), 
    db: Session = Depends(get_db)
):
    """Handles multi-file uploads with streaming and offloaded processing."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    try:
        # 1. Create Batch
        batch = UploadBatch(status="PENDING")
        db.add(batch)
        await run_in_threadpool(db.commit)
        await run_in_threadpool(db.refresh, batch)
        
        # 2. Setup directory
        upload_dir = Path("/app/uploads") / str(batch.id)
        await run_in_threadpool(upload_dir.mkdir, parents=True, exist_ok=True)
        
        # 3. Stream files to disk concurrently
        save_tasks = []
        file_paths = []
        for file in files:
            safe_name = secure_filename(file.filename)
            dest = upload_dir / safe_name
            save_tasks.append(save_upload_file(file, dest))
            file_paths.append((safe_name, dest))
            
        sizes = await asyncio.gather(*save_tasks)
        
        # 4. Prepare task payload
        raw_files_data = []
        for i, (name, path) in enumerate(file_paths):
            raw_files_data.append({
                "filename": name,
                "path": str(path),
                "file_size_kb": round(sizes[i] / 1024, 2),
                "file_type": name.split('.')[-1] if '.' in name else 'unknown'
            })
            
        process_upload_task.delay(str(batch.id), raw_files_data)
        return {"batch_id": str(batch.id)}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Upload failed for batch {batch.id if 'batch' in locals() else 'unknown'}: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/results/{batch_id}")
def get_results(batch_id: str, db: Session = Depends(get_db)):
    """Fetch status and results of a processing batch."""
    batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    if batch.status in ["PENDING", "PROCESSING"]:
        return {"status": batch.status, "analysis": [], "summary": None}
    
    if batch.status == "FAILED":
        return {"status": "FAILED", "error": batch.error_message}

    # Format return data
    analysis = [{
        "id": str(doc.id),
        "filename": doc.filename,
        "folder": doc.cluster_label,
        "x": doc.x_coord,
        "y": doc.y_coord,
        "metadata": {
            "file_size_kb": doc.file_size_kb,
            "file_type": doc.file_type,
            "page_count": doc.page_count,
            "summary": doc.summary,
            "suggested_filename": doc.suggested_filename,
            "document_type": doc.document_type,
            "tags": doc.tags
        }
    } for doc in batch.documents]
    
    r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    has_zip = bool(r.get(f"batch_zip:{batch_id}"))
        
    return {
        "status": "SUCCESS",
        "analysis": analysis,
        "summary": batch.summary,
        "has_zip": has_zip
    }

@router.get("/download/{batch_id}")
def download_results(batch_id: str):
    """Download the organized ZIP for a specific batch."""
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
async def search_similar_docs(
    query: str, 
    limit: int = 25, 
    batch_id: str = None,
    db: Session = Depends(get_db)
):
    """Hybrid search endpoint using the search service."""
    results = await hybrid_search(db, query, limit, batch_id=batch_id)
    return results