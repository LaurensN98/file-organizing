import base64
import time
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List
import io
import zipfile
from app.services.processing import process_files
from app.services.ml_engine import clustering_pipeline, generate_dataset_summary
from app.models.metadata import DocumentMetadata
from app.core.database import SessionLocal

router = APIRouter()

async def save_metadata(organized_data: List[dict]):
    db = SessionLocal()
    try:
        for item in organized_data:
            meta = item.get("metadata", {})
            metadata = DocumentMetadata(
                filename=item["filename"],
                cluster_label=item["folder"],
                file_size_kb=meta.get("file_size_kb"),
                file_type=meta.get("file_type"),
                page_count=meta.get("page_count"),
                language=meta.get("language", "en"),
                x_coord=item.get("x"),
                y_coord=item.get("y")
            )
            db.add(metadata)
        db.commit()
    finally:
        db.close()

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_documents(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    start_time = time.time()
    logger.info(f"Starting upload of {len(files)} files")
    
    # Process files in memory
    t0 = time.time()
    processed_data = await process_files(files)
    t1 = time.time()
    logger.info(f"File processing took {t1 - t0:.2f}s")
    
    # ML Pipeline: Embed, Reduce, Cluster, Label
    t2 = time.time()
    organized_data = await clustering_pipeline(processed_data)
    t3 = time.time()
    logger.info(f"ML Pipeline took {t3 - t2:.2f}s")
    
    processing_time = round(time.time() - start_time, 2)
    
    # Calculate Stats
    t4 = time.time()
    total_files = len(organized_data)
    total_size_kb = sum(d["metadata"]["file_size_kb"] for d in organized_data)
    largest_file_kb = max(d["metadata"]["file_size_kb"] for d in organized_data) if organized_data else 0
    avg_size_kb = round(total_size_kb / total_files, 1) if total_files else 0
    unique_clusters = list(set(d["folder"] for d in organized_data))
    
    # Generate Semantic Summary
    dataset_description = await generate_dataset_summary(organized_data)
    t5 = time.time()
    logger.info(f"Stats & Summary took {t5 - t4:.2f}s")
    
    # Save metadata in background
    background_tasks.add_task(save_metadata, organized_data)
    
    # Zip organized files in memory
    t6 = time.time()
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for item in organized_data:
            zip_file.writestr(f"{item['folder']}/{item['filename']}", item['content'])
    
    zip_buffer.seek(0)
    zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode("utf-8")
    t7 = time.time()
    logger.info(f"Zipping took {t7 - t6:.2f}s")
    
    processing_time = round(time.time() - start_time, 2)
    logger.info(f"Total request processed in {processing_time}s")
    
    # Prepare response data 
    analysis_results = []
    for item in organized_data:
        analysis_results.append({
            "filename": item["filename"],
            "folder": item["folder"],
            "x": item.get("x", 0),
            "y": item.get("y", 0),
            "metadata": item.get("metadata", {})
        })

    return JSONResponse(content={
        "analysis": analysis_results,
        "zip_file": zip_base64,
        "summary": {
            "total_files": total_files,
            "total_size_kb": total_size_kb,
            "avg_size_kb": avg_size_kb,
            "largest_file_kb": largest_file_kb,
            "processing_time_sec": processing_time,
            "cluster_count": len(unique_clusters),
            "description": dataset_description
        }
    })
