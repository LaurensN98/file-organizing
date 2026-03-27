import os
import logging
import asyncio
import json
import time
import base64
import fitz 
import pymupdf4llm
import zipfile
import datetime
import shutil

from typing import List, Dict, Tuple, Optional, Any
from app.services.privacy import scrub_pii
from app.core.openai_client import openai_client
from app.celery_app import celery_app
from app.core.database import get_db_ctx
from app.models.metadata import UploadBatch, DocumentMetadata
from app.services.storage import get_unique_name
from app.services.ml_engine import clustering_pipeline
from app.core.redis_client import redis_client


# Configure logging
logger = logging.getLogger(__name__)


# Base directory for uploads
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")


# Suppress fitz warnings
logging.getLogger("fitz").setLevel(logging.ERROR)


# Extensions that PyMuPDF handles natively as documents
PYMUPDF_DOC_EXTENSIONS = {
    ".pdf", ".xps", ".epub", ".mobi", ".fb2", ".cbz", ".svg",
    ".docx", ".pptx", ".xlsx", ".hwp", ".hwpx"
}


# Extensions that should be opened as text by PyMuPDF
PYMUPDF_TXT_EXTENSIONS = {
    ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".xml", ".html", ".css", 
    ".sql", ".md", ".sh", ".bash", ".yml", ".yaml", ".ini", ".conf", ".c", ".cpp", 
    ".h", ".cs", ".java", ".go", ".rs", ".rb", ".php"
}


def extract_text_with_pymupdf_sync(content: bytes, extension: str, is_text_file: bool = False) -> Tuple[str, int, Optional[bytes]]:
    """Generic PyMuPDF extractor for PDFs, eBooks, SVGs, and Text files."""
    try:
        # For text files, we specify the filetype="txt"
        filetype = "txt" if is_text_file else extension.strip(".")
        
        doc = fitz.open(stream=content, filetype=filetype)
        page_count = len(doc)
        
        # Use pymupdf4llm for markdown extraction if it's a standard document
        # For text files or simple SVGs, standard extraction might be cleaner
        if not is_text_file and extension.lower() in {
            ".pdf", ".epub", ".mobi", ".docx", ".pptx", ".xlsx", ".hwp", ".hwpx"
        }:
            md_text = pymupdf4llm.to_markdown(doc)
        else:
            # Join text from all pages
            md_text = "\n".join(page.get_text() for page in doc)
        
        # SVG Special Handling: If it's an SVG and we have no text, 
        # or it's a very small amount of text, rasterize it.
        rasterized_image = None
        if extension.lower() == ".svg" and (not md_text or len(md_text.strip()) < 50):
            try:
                page = doc[0]
                pix = page.get_pixmap(dpi=300)
                rasterized_image = pix.tobytes("png")
                logger.info("SVG rasterized as no significant text was found.")
            except Exception as e:
                logger.error(f"SVG rasterization failed: {e}")
                
        doc.close()
        return md_text, page_count, rasterized_image
        
    except Exception as e:
        logger.error(f"PyMuPDF ({extension}) extraction failed: {e}")
        return "", 0, None


async def extract_metadata_and_summary(text: str) -> dict:
    """Use Gemini Flash to analyze document text and return key metadata."""
    fallback = {
        "summary": "No summary available.",
        "suggested_filename": "unnamed_document",
        "document_type": "unknown",
        "tags": []
    }

    if not text or len(text.strip()) < 100:
        return fallback

    # 1. Truncation Strategy
    max_chars = 15000
    if len(text) > max_chars:
        front_text = text[:12000]
        back_text = text[-3000:]
        trunc_text = front_text + "\n\n...[DOCUMENT TRUNCATED]...\n\n" + back_text
    else:
        trunc_text = text
    
    # 2. Forcing JSON Schema
    prompt = f"""
    You are an expert data librarian categorizing documents for a vector database.
    Analyze the following document content and extract key metadata.
    
    You MUST respond with a raw JSON object containing EXACTLY these four keys:
    1. "summary": A single, cohesive paragraph of about 100-150 words (under 200 words) summarizing the core topics and entities. No lists.
    2. "suggested_filename": A highly descriptive file name using snake_case (e.g., q3_financial_report_2024). Do not include file extensions.
    3. "document_type": A 1-to-3 word category (e.g., Legal Contract, Invoice, Research Paper).
    4. "tags": An array of 3 to 5 highly relevant string keywords.
    
    CONTENT:
    {trunc_text}
    """
    
    try:
        response = await openai_client.chat.completions.create(
            model="xiaomi/mimo-v2-flash",
            messages=[{"role": "user", "content": prompt}],
            extra_body={
                "provider": {
                    "sort": "throughput", 
                    "preferred_min_throughput": {
                        'p90': 25, 
                    }
                }
            },
            max_tokens=600, 
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content.strip()
        if raw_content.startswith("```json"):
            raw_content = raw_content.strip("```json").strip("```").strip()
            
        return json.loads(raw_content)
    except Exception as e:
        logger.error(f"Metadata extraction error: {e}")
        return fallback


async def extract_description_from_image(content: bytes, mime_type: str) -> dict:
    """Use Qwen 3.5 Flash to describe the image content and extract structured metadata."""
    base64_image = base64.b64encode(content).decode('utf-8')
    
    fallback = {
        "summary": "An image file.",
        "suggested_filename": "uploaded_image",
        "document_type": "Image",
        "tags": []
    }

    prompt = """
    You are an expert data librarian. Analyze the following image.
    
    You MUST respond with a raw JSON object containing EXACTLY these four keys:
    1. "summary": A single, cohesive paragraph of about 100-150 words (under 200 words) summarizing the core topics and entities. No lists.
    2. "suggested_filename": A highly descriptive file name using snake_case. Do not include file extensions.
    3. "document_type": A category (e.g., Photograph, Screenshot, Invoice, Chart).
    4. "tags": 3 to 5 relevant keywords.
    """
    
    try:
        response = await openai_client.chat.completions.create(
            model="qwen/qwen3.5-flash-02-23",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content.strip()
        if raw_content.startswith("```json"):
            raw_content = raw_content.strip("```json").strip("```").strip()
            
        return json.loads(raw_content)
    except Exception as e:
        logger.error(f"Image Vision Error: {e}")
        return fallback


def _worker_analyze_text(text: str, filename: str, path: Optional[str], file_data: dict, page_count: Optional[int]) -> Dict:
    """Shared logic for Scrubbing. Runs in a separate thread."""
    scrubbed_text = scrub_pii(text)
    
    # Robust fallback calculation for size and type if not provided in file_data
    file_size_kb = file_data.get('file_size_kb', 0)
    if not file_size_kb and path and os.path.exists(path):
        file_size_kb = round(os.path.getsize(path) / 1024, 2)
        
    file_type = file_data.get('file_type', 'unknown')
    if file_type == 'unknown' and '.' in filename:
        file_type = filename.split('.')[-1]
    
    res = {
        "filename": filename,
        "path": path,
        "text": scrubbed_text,
        "metadata": {
            "file_size_kb": file_size_kb,
            "file_type": file_type,
            "page_count": page_count
        }
    }
    
    # CRITICAL: Preserve content bytes for in-memory files to prevent loss during zipping
    if not path and "content" in file_data:
        res["content"] = file_data["content"]
        
    return res


def _helper_read_file(p: str) -> bytes:
    """Synchronous file reader for offloading to threads."""
    try:
        with open(p, "rb") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Read error for {p}: {e}")
        return b""


def _worker_process_document_cpu(file_data: dict) -> Dict:
    """Handles parsing + Scrubbing. Runs in a thread."""
    path = file_data.get('path')
    content = b""
    if path:
        content = _helper_read_file(path)
    else:
        content = file_data.get('content', b"")
        
    filename = file_data.get('filename', 'unnamed')
    _, ext = os.path.splitext(filename.lower())
    
    text = ""
    page_count = None
    rasterized_img = None

    # 1. Generic PyMuPDF Handled Documents
    if ext in PYMUPDF_DOC_EXTENSIONS:
        text, page_count, rasterized_img = extract_text_with_pymupdf_sync(content, ext)
    
    # 3. Text/Code Files Handled by PyMuPDF
    elif ext in PYMUPDF_TXT_EXTENSIONS:
        text, page_count, _ = extract_text_with_pymupdf_sync(content, ext, is_text_file=True)
        
    # 4. Global Fallback
    else:
        try: text = content.decode("utf-8")[:15000]
        except: text = ""

    result = _worker_analyze_text(text, filename, path, file_data, page_count)
    if rasterized_img:
        result["rasterized_image"] = rasterized_img
        
    return result


async def process_single_file(file_data: dict) -> Dict:
    """Main entry point for processing a single file."""
    filename = file_data.get('filename', 'unnamed')
    file_type = file_data.get('file_type', 'unknown')
    path = file_data.get('path')

    # Images (Direct Vision Path)
    if filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        content = await asyncio.to_thread(_helper_read_file, path) if path else file_data.get('content', b"")
        mime_type = f"image/{file_type if file_type != 'jpg' else 'jpeg'}"
        llm_data = await extract_description_from_image(content, mime_type) if content else {}
        
        result = await asyncio.to_thread(_worker_analyze_text, llm_data.get("summary", ""), filename, path, file_data, None)
        result["metadata"].update({
            "summary": llm_data.get("summary", ""),
            "suggested_filename": llm_data.get("suggested_filename", ""),
            "document_type": llm_data.get("document_type", ""),
            "tags": llm_data.get("tags", [])
        })
        return result

    # All other "Documents" (including SVGs)
    else:
        result = await asyncio.to_thread(_worker_process_document_cpu, file_data)
        
        # If we have a rasterized image (from a text-less SVG), use Vision LLM
        if result.get("rasterized_image"):
            llm_data = await extract_description_from_image(result["rasterized_image"], "image/png")
            result["metadata"].update({
                "summary": llm_data.get("summary", ""),
                "suggested_filename": llm_data.get("suggested_filename", ""),
                "document_type": llm_data.get("document_type", ""),
                "tags": llm_data.get("tags", [])
            })
            # Remove image bytes before returning to avoid heavy payload in Celery
            del result["rasterized_image"]
        else:
            text = result.get("text", "")
            # Only summarize if there's enough content to be meaningful
            if len(text) > 200:
                llm_data = await extract_metadata_and_summary(text)
                result["metadata"].update({
                    "summary": llm_data.get("summary", ""),
                    "suggested_filename": llm_data.get("suggested_filename", ""),
                    "document_type": llm_data.get("document_type", ""),
                    "tags": llm_data.get("tags", [])
                })
        return result


async def process_files(files_to_process: List[Dict]) -> List[Dict]:
    """Parallel process files with concurrency capping and error isolation."""
    sem = asyncio.Semaphore(30)
    
    async def _safe_process(f: Dict) -> Dict:
        async with sem:
            try:
                return await process_single_file(f)
            except Exception as e:
                filename = f.get('filename', 'unnamed')
                logger.error(f"Error processing file {filename}: {e}")
                # Return a valid fallback dictionary to prevent breaking the entire batch gather
                return {
                    "filename": filename,
                    "path": f.get('path'),
                    "content": f.get('content'),
                    "text": "",
                    "metadata": {
                        "file_size_kb": f.get('file_size_kb', 0),
                        "file_type": filename.split('.')[-1] if '.' in filename else 'unknown',
                        "page_count": 0,
                        "error": str(e)
                    }
                }
            
    tasks = [_safe_process(f) for f in files_to_process]
    results = await asyncio.gather(*tasks)
    return list(results)


def _create_zip_archive(zip_path: str, organized_data: List[Dict[str, Any]]):
    """Synchronous worker for zip creation to avoid blocking the event loop."""
    used_arcnames = set()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:
        for item in organized_data:
            folder = item.get("folder", "Miscellaneous")
            orig_filename = item["filename"]
            
            # Check for collisions in the same folder using shared utility
            arcname = get_unique_name(orig_filename, used_arcnames, folder=folder)
            used_arcnames.add(arcname)
            
            if item.get("path") and os.path.exists(item["path"]):
                zip_file.write(item["path"], arcname=arcname)
            elif item.get("content"):
                zip_file.writestr(arcname, item["content"])


async def run_processing_pipeline(batch_id: str, files_data: List[Dict]):
    with get_db_ctx() as db:
        batch = db.get(UploadBatch, batch_id)
        if not batch:
            logger.error(f"Batch {batch_id} not found")
            return

        try:
            batch.status = "PROCESSING"
            db.commit()

            # 1. Initial Processing (Text extraction, Document summarization, PII scrubbing)
            t_start = time.time()
            processed_data = await process_files(files_data)
            logger.info(f"File processing completed in {time.time() - t_start:.2f}s for {len(files_data)} files")

            # 2. ML Pipeline: Embed, Reduce, Cluster, Label
            organized_data: List[Dict[str, Any]]
            dataset_description: str
            organized_data, dataset_description = await clustering_pipeline(processed_data)
            
            # 3. Calculate Stats
            total_files = len(organized_data)
            total_size_kb = sum(d["metadata"]["file_size_kb"] for d in organized_data)
            unique_folders = sorted(list(set(d["folder"] for d in organized_data)))
            
            logger.info(f"Organized data count: {total_files}")
            logger.info(f"Unique folders found: {unique_folders}")

            # 4. Zip organized files to disk (Offloaded to thread to keep Event Loop responsive)
            zip_filename = f"batch_{batch_id}_organized.zip"
            zip_path = os.path.join(UPLOAD_DIR, zip_filename)
            
            await asyncio.to_thread(_create_zip_archive, zip_path, organized_data)
            
            redis_client.setex(f"batch_zip:{batch_id}", 3600, zip_path)
            
            # Schedule physical file cleanup to match the 1-hour Redis TTL
            celery_app.send_task("cleanup_zip_task", args=[zip_path], countdown=3600)
            
            # 5. Save structured results to Database session
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
                    summary=meta.get("summary"),
                    suggested_filename=meta.get("suggested_filename"),
                    document_type=meta.get("document_type"),
                    tags=meta.get("tags")
                )
                db.add(metadata)
            
            # 6. Finalize Batch Status and Total Duration
            # replacement for deprecated utcnow()
            now = datetime.datetime.now(datetime.timezone.utc)
            # Ensure batch.created_at is offset-aware for the subtraction
            created_at = batch.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=datetime.timezone.utc)
            
            elapsed = (now - created_at).total_seconds()
            
            batch.status = "SUCCESS"
            batch.summary = {
                "total_files": total_files,
                "total_size_kb": total_size_kb,
                "processing_time_sec": round(elapsed, 2),
                "cluster_count": len(unique_folders),
                "description": dataset_description
            }
            
            db.commit()
            
            # Clean up the raw files off the disk physically ONLY after commit succeeds
            try:
                raw_files_dir = os.path.join(UPLOAD_DIR, batch_id)
                if os.path.exists(raw_files_dir):
                    shutil.rmtree(raw_files_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up raw files for batch {batch_id}: {e}")
                
        except Exception as e:
            db.rollback()
            logger.error(f"Task failed for batch {batch_id}: {e}")
            batch.status = "FAILED"
            batch.error_message = str(e)
            db.commit()
