import os
import logging
import asyncio
import json
import time
import base64
import httpx
import fitz # PyMuPDF
import pymupdf4llm
from typing import List, Dict, Tuple, Optional, Any
from app.services.privacy import scrub_pii
from app.services.openai_client import client
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

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
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            md_text = "\n".join(text_parts)
        
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
        response = await client.chat.completions.create(
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
        response = await client.chat.completions.create(
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
    
    return {
        "filename": filename,
        "path": path,
        "text": scrubbed_text,
        "metadata": {
            "file_size_kb": file_size_kb,
            "file_type": file_type,
            "page_count": page_count
        }
    }


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
    """Parallel process files with concurrency capping."""
    sem = asyncio.Semaphore(30)
    
    async def _safe_process(f: Dict) -> Dict:
        async with sem:
            return await process_single_file(f)
            
    tasks = [_safe_process(f) for f in files_to_process]
    results = await asyncio.gather(*tasks)
    return list(results)