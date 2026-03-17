import asyncio
import base64
import io
import zipfile
import logging
import time
from typing import List, Dict
from app.celery_app import celery_app
from app.services.processing import process_files
from app.services.ml_engine import clustering_pipeline, generate_dataset_summary
from app.models.metadata import DocumentMetadata, UploadBatch
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

async def run_processing_pipeline(batch_id: str, files_data: List[Dict]):
    db = SessionLocal()
    try:
        batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
        if not batch:
            logger.error(f"Batch {batch_id} not found")
            return

        batch.status = "PROCESSING"
        db.commit()

        # Decode base64 contents back to bytes for processing
        for item in files_data:
            if isinstance(item.get("content"), str):
                item["content"] = base64.b64decode(item["content"])

        start_time = time.time()
        
        # 1. ML Pipeline: Embed, Reduce, Cluster, Label
        # files_data already contains the 'content' and 'filename'
        organized_data, dataset_description = await clustering_pipeline(files_data)
        
        # 2. Calculate Stats
        total_files = len(organized_data)
        total_size_kb = sum(d["metadata"]["file_size_kb"] for d in organized_data)
        largest_file_kb = max(d["metadata"]["file_size_kb"] for d in organized_data) if organized_data else 0
        avg_size_kb = round(total_size_kb / total_files, 1) if total_files else 0
        unique_clusters = list(set(d["folder"] for d in organized_data))
        
        # 3. Zip organized files in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for item in organized_data:
                # item['content'] is already bytes
                zip_file.writestr(f"{item['folder']}/{item['filename']}", item['content'])
        
        zip_buffer.seek(0)
        zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode("utf-8")
        
        processing_time = round(time.time() - start_time, 2)
        
        # 4. Save Results
        batch.summary = {
            "total_files": total_files,
            "total_size_kb": total_size_kb,
            "avg_size_kb": avg_size_kb,
            "largest_file_kb": largest_file_kb,
            "processing_time_sec": processing_time,
            "cluster_count": len(unique_clusters),
            "description": dataset_description
        }
        batch.zip_base64 = zip_base64
        batch.status = "SUCCESS"
        
        for item in organized_data:
            meta = item.get("metadata", {})
            metadata = DocumentMetadata(
                batch_id=batch.id,
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
    except Exception as e:
        db.rollback()
        logger.error(f"Task failed for batch {batch_id}: {e}")
        batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
        if batch:
            batch.status = "FAILED"
            batch.error_message = str(e)
            db.commit()
    finally:
        db.close()

@celery_app.task(name="process_upload_task")
def process_upload_task(batch_id: str, files_data: List[Dict]):
    """ Celery task wrapper to run the async pipeline. """
    asyncio.run(run_processing_pipeline(batch_id, files_data))
