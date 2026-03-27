import logging
import asyncio
import os
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.models.metadata import UploadBatch
from app.core.database import get_db
from app.services.storage import secure_filename, save_upload_file, get_unique_name
from app.services.search import hybrid_search
from app.tasks import process_upload_task
from app.core.redis_client import redis_client


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
        db.commit()
        db.refresh(batch)
        
        # 2. Setup directory
        upload_dir = Path("/app/uploads") / str(batch.id)
        await run_in_threadpool(upload_dir.mkdir, parents=True, exist_ok=True)
        
        # 3. Stream files to disk concurrently
        save_tasks = []
        file_paths = []
        used_names = set()

        for file in files:
            safe_name = secure_filename(file.filename)
            # Ensure unique name within this batch
            unique_name = get_unique_name(safe_name, used_names)
            used_names.add(unique_name)
            
            dest = upload_dir / unique_name
            save_tasks.append(save_upload_file(file, dest))
            file_paths.append((unique_name, dest))
            
        sizes = await asyncio.gather(*save_tasks)
        
        # 4. Prepare task payload
        raw_files_data = []
        for i, (name, path) in enumerate(file_paths):
            p = Path(name)
            raw_files_data.append({
                "filename": name,
                "path": str(path),
                "file_size_kb": round(sizes[i] / 1024, 2),
                "file_type": p.suffix.lower().replace(".", "") or 'unknown'
            })
            
        process_upload_task.delay(str(batch.id), raw_files_data)
        return {"batch_id": str(batch.id)}
        
    except Exception as e:
        # Update the already committed batch safely
        db.rollback()
        if 'batch' in locals():
            try:
                batch.status = "FAILED"
                batch.error_message = str(e)
                db.add(batch)
                db.commit()
            except Exception:
                pass # Give up if DB is totally dead
        logger.error(f"Upload failed for batch {batch.id if 'batch' in locals() else 'unknown'}: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/results/{batch_id}")
def get_results(batch_id: str, db: Session = Depends(get_db)):
    """Fetch status and results of a processing batch."""
    batch = db.get(UploadBatch, batch_id)
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
    
    has_zip = bool(redis_client.get(f"batch_zip:{batch_id}"))
        
    return {
        "status": "SUCCESS",
        "analysis": analysis,
        "summary": batch.summary,
        "has_zip": has_zip
    }


@router.get("/download/{batch_id}")
def download_results(batch_id: str):
    """Download the organized ZIP for a specific batch."""
    zip_path = redis_client.get(f"batch_zip:{batch_id}")
    
    if not zip_path or not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="ZIP file not found or expired")
        
    return FileResponse(
        path=zip_path, 
        filename="organized_documents.zip", 
        media_type="application/zip"
    )


@router.get("/vector-search")
async def search_similar_docs(
    query: str, 
    limit: int = 25, 
    batch_id: str = None,
    rerank: bool = False,
    db: Session = Depends(get_db)
):
    """Hybrid search endpoint using the search service."""
    results = await hybrid_search(db, query, limit, batch_id=batch_id, rerank=rerank)
    return results
    