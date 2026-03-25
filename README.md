# Neatly | Smart File Organization

## Project Overview

**Neatly** is an Intelligent Document Organization & Search platform designed to analyze unstructured file collections, automatically classify documents using unsupervised machine learning, and provide high-accuracy discovery with a **Hybrid Search** algorithm.

## Key Features

- **AI-Powered Labeling:** Automatically generates semantic folder names and dataset summaries using LLMs (MiMo v2 Flash).
- **Unsupervised Clustering:** Uses **UMAP** and **PCA** for dimensionality reduction and **HDBSCAN** for density-based document grouping.
- **Hybrid Search + Reranking:** A high-precision 2-stage retrieval pipeline. Combines **Dense Vector Search** (semantic) with **Sparse Retrieval** (SPLADE/Keyword-aware) via Relative Score Fusion (RSF), followed by a final **Reranking** pass using **DeepInfra (Llama-3-Nemotron)** to maximize relevance.
- **Interactive visualization:** Explore your document landscape through a dynamic 2D scatter plot with zooming and metadata inspection.
- **Asynchronous pipeline:** Scalable background processing using **Celery** and **Redis** for efficient large-scale file ingestion.
- **Automated Organization:** Delivers organized file structures back to the user as a streamed ZIP file.

## Supported File Types

The processing engine leverages **PyMuPDF (MuPDF)** and **LLM Vision** to support a wide range of document, image, and code formats:

- **Documents & eBooks**: PDF (`.pdf`), XPS (`.xps`), EPUB (`.epub`), MOBI (`.mobi`), FB2 (`.fb2`), CBZ (`.cbz`).
- **Images & Graphics**: 
    - **Standard Images**: PNG, JPG, JPEG, WebP (processed via Vision LLM).
    - **Vector Graphics**: SVG (natively parsed for text; automatically rasterized for Vision analysis if text-less).
- **Office Documents**: Word Documents (`.docx`).
- **Code & Plain Text**: Over 20+ text-based formats are supported using PyMuPDF's low-latency text engine, including:
    - **Web**: `.html`, `.css`, `.js`, `.ts`, `.tsx`, `.jsx`.
    - **Systems/Scripts**: `.py`, `.sh`, `.bash`, `.yml`, `.yaml`, `.json`, `.xml`.
    - **Languages**: `.c`, `.cpp`, `.h`, `.cs`, `.java`, `.go`, `.rs`, `.sql`.
    - **Docs**: `.md`, `.txt`, `.ini`, `.conf`.

## Implementation Status & Limitations

This is an active prototype. Please note the following implementation details:

- **Frontend Navigation:** The sidebar navigation links and footer options are currently placeholders and not fully functional.
- **Search:** The Hybrid Search is fully functional yet improvements need to be made for better file indexing.
- **PII Redaction:** The PII scrubbing hook is currently a placeholder and should be replaced with a service like Microsoft Presidio for enterprise use.

## System Architecture

### High-Level Data Flow

1. **Ingestion:** Files are uploaded via the **Next.js 15** frontend and initially processed by **FastAPI**.
2. **Asynchronous Task:** Ingestion triggers a **Celery** background worker to handle the heavy lifting:
    - **Universal Extraction:** Leverages **PyMuPDF** to parse 20+ file formats (EPUB, XPS, SVG, Source Code, etc.) with a **Vision Fallback** (rasterizing text-less SVGs for multimodal analysis).
    - **Multi-Vector Embedding:**
      - **Dense:** Generates semantic embeddings via OpenRouter (Qwen).
      - **Sparse:** Generates SPLADE embeddings via a local **Text Embeddings Inference (TEI)** service.
    - **Clustering:** Reduces dimensions with UMAP & PCA and groups documents with HDBSCAN (refined by `cluster_selection_epsilon` for fewer fractured clusters).
    - **Labeling:** LLMs analyze cluster centroids to generate concise folder names and a global summary via OpenRouter (MiMo v2 Flash).
- **Discovery:** Users can perform **Hybrid Search** with an automated **Reranking** step (via DeepInfra) for ultra-precise results or explore the interactive 2D map.

### Tech Stack

- **Frontend:** Next.js 15 (App Router), React 19, Tailwind CSS, Framer Motion, Recharts.
- **Backend:** FastAPI (Python 3.11), Celery, SQLAlchemy.
- **Inference Service:** HuggingFace Text Embeddings Inference (TEI) running SPLADE (naver/splade-cocondenser-ensembledistil).
- **Machine Learning:** UMAP-learn, PCA, HDBSCAN, Scikit-learn, PyMuPDF (fitz), pymupdf4llm.
- **Database:** TimescaleDB (PostgreSQL 16) with `pgvector` and `pgvectorscale` (DiskANN) for large-scale vector similarity search.
- **Reranking:** DeepInfra (nvidia/llama-nemotron-rerank-vl-1b-v2) for 2-stage retrieval precision.
- **Infrastructure:** Docker & Docker Compose, Redis (Task Queue), GitHub Actions (CI/CD).

## Directory Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── celery_app.py        # Celery configuration
│   │   ├── tasks.py             # Background ML pipeline tasks
│   │   ├── api/                 # API Endpoints (documents.py for Upload, Search, Results)
│   │   ├── services/
│   │   │   ├── processing.py    # Multi-format extraction (PyMuPDF + Vision)
│   │   │   ├── ml_engine.py     # Clustering, Reduction, AI Labeling
│   │   │   └── embeddings.py    # Dense & Sparse embedding clients
│   │   └── models/              # Pydantic & SQLAlchemy schema definitions
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js Pages & Layouts
│   │   ├── components/          # UI Components (ResultView, UploadZone)
│   │   └── lib/                 # API Clients & Utilities
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml           # Full multi-container orchestrator
```

## Getting Started

### Prerequisites

- Docker & Docker Compose
- OpenRouter API Key (for LLM and Dense Embeddings)
- DeepInfra API Key (for high-precision Reranking)

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/LaurensN98/file-organizing.git
   cd file-organizing
   ```

2. **Environment Setup:**
   Copy `.env.example` to `.env` in the root directory and fill in your keys:

   ```bash
   cp .env.example .env
   ```

   The `.env` file should look like this:

   ```env
   # Database Credentials
   POSTGRES_USER=neatly_admin
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_DB=db
   POSTGRES_HOST=db
   POSTGRES_PORT=5432

   # API Keys
   OPENROUTER_API_KEY=your_openrouter_key
   DEEPINFRA_API_KEY=your_deepinfra_key

   # Services URLs
   REDIS_URL=redis://redis:6379/0
   INFERENCE_URL=http://host.docker.internal:8081
   DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
   ```

3. **Start Local Inference Server (macOS Metal Accelerated):**
   To leverage native Apple Silicon performance for sparse embeddings, run TEI natively via Homebrew:

   ```bash
   brew install text-embeddings-inference
   text-embeddings-router --model-id naver/splade-cocondenser-ensembledistil --pooling splade --dtype float16 --port 8081
   ```

4. **Run Backend & Frontend:**
   In a separate terminal, start the main application stack:

   ```bash
   docker-compose up --build
   ```

### Access

- **Frontend:** [http://localhost:3000](http://localhost:3000)

## Production Readiness Matrix

| Feature              | Current Demo (Local)            | Production Standard (Target)                |
| :------------------- | :------------------------------ | :------------------------------------------ |
| **Hosting**          | Local Docker Compose            | OVHcloud (Amsterdam/France regions)         |
| **Embeddings & LLM** | OpenRouter + Local TEI (SPLADE) | Mistral via OVH AI Endpoints (EU Sovereign) |
| **Search Engine**    | Hybrid (Postgres + DiskANN)     | Scaled HA Cluster / Managed Timescale       |
| **Data Privacy**     | In-Memory + Metadata Storage    | Zero Data Retention (ZDR) + Signed DPA      |
| **Security**         | Internal AI Network             | HTTPS (TLS 1.3) + Private VPC               |
| **PII Handling**     | Placeholder Redaction           | Microsoft Presidio (Automated Redaction)    |

## Usage Costs & Efficiency (Estimated)

Neatly is designed for extreme cost-efficiency by leveraging high-performance, low-cost models via DeepInfra and OpenRouter. Below is a breakdown of the estimated costs per document and per search query.

### 1. Ingestion & Indexing (Per Document)
These costs are incurred once per document during the initial upload and processing phase.

| Task | Model | Avg. tokens | Cost per 1M tokens | Est. Cost / Doc |
| :--- | :--- | :--- | :--- | :--- |
| **Text Summarization** | MiMo v2 Flash | 5.5k (In) / 150 (Out) | $0.10 (In) / $0.30 (Out) | ~$0.000595 |
| **Image Vision** | Qwen 3.5 Flash | 2.5k (In) / 150 (Out) | $0.10 (In) / $0.40 (Out) | ~$0.00031 |
| **Embedding** | Qwen 8B | 150 (In) | $0.01 | ~$0.0000015 |

*   **Total Indexing Cost:** At most **$0.0005965 per document**.
*   **Efficiency:** You can index **~1,700 documents for $1.00**. In practice, this number is often much higher (3k+) as many documents are shorter than the 5.5k token maximum.

### 2. Search & Discovery (Per Query)
These costs are incurred when performing a search with the automated reranking stage enabled.

| Task | Model | Avg. tokens | Cost per 1M tokens | Est. Cost / Query |
| :--- | :--- | :--- | :--- | :--- |
| **Reranking** | Llama-3-Nemotron | 150 per doc (x25 docs) | $0.01 | ~$0.0000375 |

*   **Efficiency:** You can perform approximately **26,500 high-precision reranked searches for $1.00**.

---

## GDPR & Security Compliance
...

This architecture ensures **Data Minimization** through a multi-stage security pipeline:

- **In-Transit:** Files are processed in temporary secure storage. The moment AI analysis concludes, the raw upload directories are purged from the local hard disk volume.
- **At-Rest:** Only minimal metadata (filenames, cluster assignments, coordinates, statistics) and vector embeddings are stored in PostgreSQL. Raw document text is never persisted in the database.
- **Volatile Delivery:** Organized ZIP results are stored on a temporary volume with a strict 1-hour lifecycle. An automated Celery cleanup task physically deletes these archives when the Redis access token expires, guaranteeing zero long-term data retention.
- **Cloud Sovereignty:** While the platform is **designed for** OVHcloud (EU) to eliminate US-CLOUD Act exposure, current local prototypes utilize a hybrid model (Local SPLADE + External LLMs via OpenRouter). Production-grade compliance for EU public sector deployments requires switching to fully sovereign EU endpoints (e.g., Mistral via OVH AI).
