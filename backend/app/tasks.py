import asyncio
import os
import base64
import io
import zipfile
import logging
import time
import datetime
import shutil
import redis
from app.core.config import settings
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

        # 1. Initial Processing (Text extraction, PII scrubbing)
        t_start = time.time()
        processed_data = await process_files(files_data)
        logger.info(f"File processing completed in {time.time() - t_start:.2f}s for {len(files_data)} files")

        # 2. ML Pipeline: Embed, Reduce, Cluster, Label
        organized_data, dataset_description = await clustering_pipeline(processed_data)
        
        # 2.1 Calculate Stats
        total_files = len(organized_data)
        total_size_kb = sum(d["metadata"]["file_size_kb"] for d in organized_data)
        largest_file_kb = max(d["metadata"]["file_size_kb"] for d in organized_data) if organized_data else 0
        avg_size_kb = round(total_size_kb / total_files, 1) if total_files else 0
        unique_clusters = list(set(d["folder"] for d in organized_data))
        
        # 3. Zip organized files to disk with collision handling
        zip_path = f"/app/uploads/batch_{batch_id}_organized.zip"
        used_arcnames = set()
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
            for item in organized_data:
                folder = item.get("folder", "Miscellaneous")
                orig_filename = item["filename"]
                
                # Check for collisions in the same folder
                arcname = f"{folder}/{orig_filename}"
                cnt = 1
                while arcname in used_arcnames:
                    # Rename if collision exists: file.pdf -> file(1).pdf
                    name_parts = orig_filename.rsplit('.', 1)
                    if len(name_parts) > 1:
                        new_name = f"{name_parts[0]}({cnt}).{name_parts[1]}"
                    else:
                        new_name = f"{orig_filename}({cnt})"
                    arcname = f"{folder}/{new_name}"
                    cnt += 1
                
                used_arcnames.add(arcname)
                
                if item.get("path") and os.path.exists(item["path"]):
                    zip_file.write(item["path"], arcname=arcname)
                elif item.get("content"):
                    zip_file.writestr(arcname, item["content"])
        
        # Redis client to flag completion (no heavy payload)
        redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.setex(f"batch_zip:{batch_id}", 3600, zip_path)
        
        # Schedule physical file cleanup to match the 1-hour Redis TTL
        cleanup_zip_task.apply_async((zip_path,), countdown=3600)
        

        # 4. Save structured results to Database session
        for item in organized_data:
            meta = item.get("metadata", {})
            metadata = DocumentMetadata(
                batch_id=batch.id,
                filename=item["filename"],
                cluster_label=item["folder"],
                file_size_kb=meta.get("file_size_kb"),
                file_type=meta.get("file_type"),
                page_count=meta.get("page_count"),
                x_coord=item.get("x"),
                y_coord=item.get("y"),
                dense_embedding=item.get("dense_embedding"),
                sparse_embedding=item.get("sparse_embedding"),
                # LLM Metadata
                summary=meta.get("summary"),
                suggested_filename=meta.get("suggested_filename"),
                document_type=meta.get("document_type"),
                tags=meta.get("tags")
            )
            db.add(metadata)
        
        # 5. Finalize Batch Status and Total Duration (includes DB transaction time)
        elapsed = (datetime.datetime.utcnow() - batch.created_at).total_seconds()
        
        batch.status = "SUCCESS"
        batch.summary = {
            "total_files": total_files,
            "total_size_kb": total_size_kb,
            "avg_size_kb": avg_size_kb,
            "largest_file_kb": largest_file_kb,
            "processing_time_sec": round(elapsed, 2),
            "cluster_count": len(unique_clusters),
            "description": dataset_description
        }
        
        db.commit()
        
        # Clean up the raw files off the disk physically ONLY after commit succeeds
        try:
            shutil.rmtree(f"/app/uploads/{batch_id}")
        except Exception as e:
            logger.warning(f"Failed to clean up raw files for batch {batch_id}: {e}")
            
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

@celery_app.task(name="cleanup_zip_task")
def cleanup_zip_task(zip_path: str):
    """ Deletes a ZIP result file from disk after use or TTL. """
    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
            logger.info(f"Successfully cleaned up expired ZIP result: {zip_path}")
        else:
            logger.warning(f"Cleanup task found no file at: {zip_path}")
    except Exception as e:
        logger.error(f"Failed to cleanup ZIP result {zip_path}: {e}")

