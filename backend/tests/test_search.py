import asyncio
import time
import logging
from app.services.search import hybrid_search
from app.core.database import get_db_ctx

async def main():
    logging.basicConfig(level=logging.INFO) 

    with get_db_ctx() as db:
        start = time.time()
        results = await hybrid_search(db, query="invoice and receipts", limit=25, rerank=True)
        print(f"Latency: {time.time() - start:.3f}s. Found {len(results)} results")

if __name__ == "__main__":
    asyncio.run(main())
