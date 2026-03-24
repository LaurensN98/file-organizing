import os
import re
import asyncio
from pathlib import Path
from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool

def secure_filename(filename: str) -> str:
    """Sanitizes filenames to prevent directory traversal and remove invalid chars."""
    if not filename: return "unnamed_file"
    # Extract basename to strip any uploaded directory structure
    filename = os.path.basename(filename.replace("\\", "/"))
    # Replace genuinely invalid file characters depending on OS (Windows/Linux)
    filename = re.sub(r'[<>:"|?*]', '_', filename)
    return filename if filename else "unnamed_file"

async def save_upload_file(file: UploadFile, destination: Path) -> int:
    """Streams an UploadFile to a local destination and returns total bytes."""
    size = 0
    try:
        # Ensure parent directory exists (batch-level directory)
        async with asyncio.Lock(): # Guard for concurrent mkdir calls
             if not destination.parent.exists():
                 await run_in_threadpool(destination.parent.mkdir, parents=True, exist_ok=True)
            
        with open(destination, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024) # 1MB chunks
                if not chunk:
                    break
                size += len(chunk)
                # Offload the blocking disk write to the threadpool
                await run_in_threadpool(buffer.write, chunk)
        return size
    finally:
        await file.close()
