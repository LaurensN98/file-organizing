# PR: Backend Service-Oriented Refactor & Search Optimization

## Summary
This PR represents a major architectural overhaul of the backend, transitioning from tight task-based coupling to a more modular service-oriented layer. Key improvements include a unified document processing pipeline, optimized ML clustering with concurrent execution, and a high-performance hybrid search engine with reranking support.

## Key Changes

### 🏗️ Backend Architecture & Core
- **Consolidated Clients**: Moved `DeepInfra`, `OpenAI`, and `Redis` clients from the service layer to `app.core` for better lifecycle management.
- **Improved Lifespan Management**: Standardized `lifespan` in `main.py` to ensure all async clients and database pools are gracefully disposed on shutdown.
- **Robust Database Access**: Implemented `get_db_ctx()` context manager for safer, thread-safe database sessions across sync/async boundaries.

### 📄 Document Processing Pipeline
- **Unified Extraction**: Integrated `fitz` (PyMuPDF) and `pymupdf4llm` to handle a wide range of document types (PDFs, eBooks, SVGs, etc.) with consistent markdown output.
- **Vision-First Processing**: Added a dedicated vision path using `qwen3.5-flash-02-23` for analyzing images and text-less SVGs.
- **LLM-Enabled Metadata**: Integrated `mimo-v2-flash` for high-throughput extraction of document summaries, suggested filenames, types, and tags.
- **Service Isolation**: Extracted `run_processing_pipeline` into a dedicated service module, simplifying `tasks.py` to a thin wrapper.

### 🧠 ML & Embedding Optimization
- **Signal Boosting**: Refined embedding logic to use a composite signal of filename, summary, and tags, significantly improving clustering accuracy compared to raw text.
- **Concurrent Execution**: Parallelized dense/sparse embedding generation and AI labelling using `asyncio.gather`.
- **HDBSCAN Fine-tuning**: Optimized clustering parameters (`cluster_selection_epsilon`, `min_cluster_size`) to reduce 'Miscellaneous' noise and produce better defined folders.
- **Dataset Awareness**: Added automated dataset-wide summary generation to provide immediate context for bulk uploads.

### 🔍 Search & Retrieval
- **Optimized Hybrid Search**: Implemented `Relative Score Fusion (RSF)` to combine dense and sparse results with user-tunable `alpha`.
- **Reranking Integration**: Added support for deep reranking via `nvidia/llama-nemotron-rerank-vl-1b-v2` through DeepInfra.
- **Performance Gains**: Pruned sparse queries for GIN indices and moved heavy retrieval logic to a modular, performant service layer.
- **API Improvements**: Standardized `/vector-search` as a `GET` endpoint for better caching and semantic alignment.

### 🎨 Frontend & Experience
- **Search Modes**: Introduced "FAST" (Hybrid) vs "DEEP" (Reranked) toggles in the `ResultView` with animated Framer Motion components.
- **Polished UI**: Enhanced `FileUpload` and `ResultView` with high-fidelity transitions and better state handling during large batch processing.

## Testing Performed
- Validated full batch processing pipeline with mixed document types (PDF, Image, SVG).
- Benchmarked hybrid search latency with/without reranking.
- Verified ZIP archival and cleanup tasks in Celery.
- Manual UI testing of the new search toggle and animated transitions.
