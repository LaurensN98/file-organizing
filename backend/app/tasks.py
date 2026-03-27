import asyncio
import os
from typing import List, Dict
from app.celery_app import celery_app
from app.services.processing import run_processing_pipeline
import logging


logger = logging.getLogger(__name__)


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
