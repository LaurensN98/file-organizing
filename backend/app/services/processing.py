import io
from typing import List, Dict
from fastapi import UploadFile
import PyPDF2
from docx import Document
from app.services.privacy import scrub_pii

async def extract_text_from_pdf(content: bytes) -> str:
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
    text = ""
    # Read only first 3 pages
    num_pages = min(len(pdf_reader.pages), 3)
    for i in range(num_pages):
        text += pdf_reader.pages[i].extract_text() or ""
    return text

async def extract_text_from_docx(content: bytes) -> str:
    doc = Document(io.BytesIO(content))
    text = ""
    # Simplified approach for docx: just get first few paragraphs or pages if possible
    # For now, let's just take a slice of paragraphs to simulate "first 3 pages"
    paragraphs = doc.paragraphs[:50] 
    for para in paragraphs:
        text += para.text + "\n"
    return text

async def process_files(files: List[UploadFile]) -> List[Dict]:
    processed_files = []
    for file in files:
        content = await file.read()
        filename = file.filename
        
        text = ""
        if filename.endswith(".pdf"):
            text = await extract_text_from_pdf(content)
        elif filename.endswith(".docx"):
            text = await extract_text_from_docx(content)
        else:
            # Fallback for plain text or skip
            try:
                text = content.decode("utf-8")[:2000] # Limit size
            except:
                text = ""

        # Scrub PII
        scrubbed_text = scrub_pii(text)
        
        processed_files.append({
            "filename": filename,
            "content": content,
            "text": scrubbed_text
        })
    return processed_files
