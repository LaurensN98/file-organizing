import io
import os
import base64
import asyncio
import logging
import time
from typing import List, Dict
from fastapi import UploadFile
import PyPDF2
from docx import Document
from app.services.privacy import scrub_pii
from langdetect import detect, LangDetectException
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Suppress PyPDF2 warnings
logging.getLogger("PyPDF2").setLevel(logging.ERROR)

# Initialize async client for OCR/Vision
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", "dummy-key"),
)

async def extract_text_from_pdf(content: bytes) -> tuple[str, int]:
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
    text = ""
    total_pages = len(pdf_reader.pages)
    num_pages = min(total_pages, 3)
    for i in range(num_pages):
        text += pdf_reader.pages[i].extract_text() or ""
    return text, total_pages

async def extract_text_from_docx(content: bytes) -> tuple[str, int | None]:
    doc = Document(io.BytesIO(content))
    text = ""
    paragraphs = doc.paragraphs[:50] 
    for para in paragraphs:
        text += para.text + "\n"
    
    try:
        pages = doc.part.package.app_properties.pages
    except:
        pages = None
        
    return text, pages

async def extract_description_from_image(content: bytes, mime_type: str) -> str:
    """Use Gemini Flash to describe the image content."""
    base64_image = base64.b64encode(content).decode('utf-8')
    
    try:
        response = await client.chat.completions.create(
            model="google/gemini-3-flash-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe the content of this image in detail for indexing purposes. Include any visible text."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

async def process_single_file(file_data: dict) -> Dict:
    content = file_data['content']
    filename = file_data['filename']
    file_size_kb = file_data['file_size_kb']
    file_type = file_data['file_type']
    
    text = ""
    page_count = None

    if filename.lower().endswith(".pdf"):
        try:
            text, page_count = await extract_text_from_pdf(content)
        except:
            text = ""
    elif filename.lower().endswith(".docx"):
        try:
            text, page_count = await extract_text_from_docx(content)
        except:
            text = ""
    elif filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        try:
            mime_type = f"image/{file_type if file_type != 'jpg' else 'jpeg'}"
            text = await extract_description_from_image(content, mime_type)
        except:
            text = ""
    else:
        try:
            text = content.decode("utf-8")[:2000]
        except:
            text = ""

    scrubbed_text = scrub_pii(text)
    
    language = "unk"
    if len(scrubbed_text.strip()) > 50:
        try:
            language = detect(scrubbed_text)
        except LangDetectException:
            language = "unk"
    
    return {
        "filename": filename,
        "content": content,
        "text": scrubbed_text,
        "metadata": {
            "file_size_kb": file_size_kb,
            "file_type": file_type,
            "page_count": page_count,
            "language": language
        }
    }

async def process_files(files: List[UploadFile]) -> List[Dict]:
    seen_filenames = {}

    # Pre-read all files (IO bound, but fast for memory) and prepare unique names
    files_to_process = []
    
    for file in files:
        content = await file.read()
        original_filename = file.filename
        base_name = original_filename.split("/")[-1].split("\\")[-1]
        
        if base_name in seen_filenames:
            seen_filenames[base_name] += 1
            name_part, ext = os.path.splitext(base_name)
            filename = f"{name_part}-{seen_filenames[base_name]}{ext}"
        else:
            seen_filenames[base_name] = 0
            filename = base_name
        
        file_size_kb = len(content) // 1024
        file_type = filename.split('.')[-1].lower() if '.' in filename else "unknown"
        
        files_to_process.append({
            "filename": filename,
            "content": content,
            "file_size_kb": file_size_kb,
            "file_type": file_type
        })

    # Create tasks for parallel processing
    logger.info(f"Processing {len(files_to_process)} files concurrently...")
    t0 = time.time()
    tasks = [process_single_file(f) for f in files_to_process]
    
    # Run all tasks concurrently
    processed_files = await asyncio.gather(*tasks)
    logger.info(f"Parallel processing finished in {time.time() - t0:.2f}s")
    
    return processed_files
