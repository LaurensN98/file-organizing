import os
import re
import shutil
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
    return filename or "unnamed_file"


def get_unique_name(filename: str, existing_names: set, folder: str = "") -> str:
    """Returns a unique name by appending (n) if a collision exists in existing_names."""
    p = Path(filename)
    # Prefix with folder if provided for ZIP contexts (folder/filename)
    candidate = f"{folder}/{p.name}" if folder else p.name
    
    counter = 1
    while candidate in existing_names:
        new_filename = f"{p.stem}({counter}){p.suffix}"
        candidate = f"{folder}/{new_filename}" if folder else new_filename
        counter += 1
    return candidate


async def save_upload_file(file: UploadFile, destination: Path) -> int:
    """Streams an UploadFile to a local destination using optimized shutil buffer."""
    try:
        if not destination.parent.exists():
            await run_in_threadpool(destination.parent.mkdir, parents=True, exist_ok=True)
            
        def _block_write():
            # This entirely runs inside ONE background worker thread
            with open(destination, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            return destination.stat().st_size
                
        # Send the entire transfer to the thread pool ONCE
        size = await run_in_threadpool(_block_write)
        return size
    finally:
        await file.close()
