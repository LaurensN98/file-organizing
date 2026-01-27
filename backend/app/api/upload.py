from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List
import io
import zipfile
from app.services.processing import process_files
from app.services.ml_engine import clustering_pipeline
from fastapi.responses import StreamingResponse
from app.models.metadata import DocumentMetadata
from sqlalchemy.orm import Session
from app.core.database import SessionLocal

router = APIRouter()

async def save_metadata(organized_data: List[dict]):
    db = SessionLocal()
    try:
        for item in organized_data:
            metadata = DocumentMetadata(
                filename=item["filename"],
                cluster_name=item["folder"],
                # x_coord/y_coord could be added if clustering_pipeline returned them
            )
            db.add(metadata)
        db.commit()
    finally:
        db.close()

@router.post("/upload")
async def upload_documents(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    # Process files in memory
    processed_data = await process_files(files)
    
    # ML Pipeline: Embed, Reduce, Cluster, Label
    organized_data = await clustering_pipeline(processed_data)
    
    # Save metadata in background
    background_tasks.add_task(save_metadata, organized_data)
    
    # Zip organized files in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for item in organized_data:
            zip_file.writestr(f"{item['folder']}/{item['filename']}", item['content'])
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=organized_documents.zip"}
    )
