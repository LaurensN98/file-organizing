import asyncio
import time
from app.core.database import SessionLocal
from app.services.search import hybrid_search

async def main():
    db = SessionLocal()
    start = time.time()
    try:
        results = await hybrid_search(db, query="invoice and receipts", limit=25)
        print(f"Latency: {time.time() - start:.3f}s. Found {len(results)} results")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
