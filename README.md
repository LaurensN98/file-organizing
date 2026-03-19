# Neatly | Smart File Organization

## Project Overview

**Neatly** is an Intelligent Document Organization & Search platform designed to analyze unstructured file collections, automatically classify documents using unsupervised machine learning, and provide high-accuracy discovery with a **Hybrid Search** algorithm.

## Key Features

- **AI-Powered Labeling:** Automatically generates semantic folder names and dataset summaries using LLMs (MiMo v2 Flash).
- **Unsupervised Clustering:** Uses **UMAP** and **PCA** for dimensionality reduction and **HDBSCAN** for density-based document grouping.
- **Hybrid Search:** Combines **Dense Vector Search** (semantic) with **Sparse Retrieval** (SPLADE/Keyword-aware) via Relative Score Fusion (RSF) with alpha-weighting to prioritize exact keyword matching.
- **Interactive visualization:** Explore your document landscape through a dynamic 2D scatter plot with zooming and metadata inspection.
- **Asynchronous pipeline:** Scalable background processing using **Celery** and **Redis** for efficient large-scale file ingestion.
- **Automated Organization:** Delivers organized file structures back to the user as a streamed ZIP file.

## Supported File Types

The processing engine currently supports the following document and image formats:

- **Documents:** PDF (`.pdf`), Word (`.docx`), and Plain Text (`.txt`).
- **Images (OCR):** PNG, JPG, JPEG, and WebP.
- **Scalability:** Large documents are sampled (first few pages/paragraphs) to ensure rapid response times during clustering.

## Implementation Status & Limitations

This is an active prototype. Please note the following implementation details:

- **Frontend Navigation:** The sidebar navigation links and footer options are currently placeholders and not fully functional.
- **Search:** The Hybrid Search is fully functional yet improvements need to be made for better file indexing.
- **PII Redaction:** The PII scrubbing hook is currently a placeholder and should be replaced with a service like Microsoft Presidio for enterprise use.

## System Architecture

### High-Level Data Flow

1. **Ingestion:** Files are uploaded via the **Next.js 15** frontend and initially processed by **FastAPI**.
2. **Asynchronous Task:** Ingestion triggers a **Celery** background worker to handle the heavy lifting:
   - **OCR & Extraction:** Processes images (OCR), PDFs, and Word docs into clean text snippets.
   - **Multi-Vector Embedding:**
     - **Dense:** Generates semantic embeddings via OpenRouter (Qwen).
     - **Sparse:** Generates SPLADE embeddings via a local **Text Embeddings Inference (TEI)** service.
   - **Clustering:** Reduces dimensions with UMAP & PCA and groups documents with HDBSCAN.
   - **Labeling:** LLMs analyze cluster centroids to generate concise folder names and a global summary via OpenRouter (MiMo v2 Flash).
3. **Storage:** Metadata and vectors are stored in **TimescaleDB (PostgreSQL)** using `pgvector` and `pgvectorscale`.
4. **Discovery:** Users can perform **Hybrid Search** across the processed dataset or explore the interactive 2D map.

### Tech Stack

- **Frontend:** Next.js 15 (App Router), React 19, Tailwind CSS, Framer Motion, Recharts.
- **Backend:** FastAPI (Python 3.11), Celery, SQLAlchemy.
- **Inference Service:** HuggingFace Text Embeddings Inference (TEI) running SPLADE (naver/splade-cocondenser-ensembledistil).
- **Machine Learning:** UMAP-learn, PCA, HDBSCAN, Scikit-learn, LangDetect.
- **Database:** TimescaleDB (PostgreSQL 16) with `pgvector` and `pgvectorscale` for vector similarity search.
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
│   │   │   ├── processing.py    # OCR, PDF/Doc parsing, Language detection
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

   # Services URLs
   REDIS_URL=redis://redis:6379/0
   INFERENCE_URL=http://inference:7997/v1
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

## GDPR & Security Compliance

This architecture ensures **Data Minimization** through a multi-stage security pipeline:

- **In-Transit:** Files are processed in temporary secure storage. The moment AI analysis concludes, the raw upload directories are purged from the local hard disk volume.
- **At-Rest:** Only minimal metadata (filenames, cluster assignments, coordinates, statistics) and vector embeddings are stored in PostgreSQL. Raw document text is never persisted in the database.
- **Volatile Delivery:** Organized ZIP results are stored on a temporary volume with a strict 1-hour lifecycle. An automated Celery cleanup task physically deletes these archives when the Redis access token expires, guaranteeing zero long-term data retention.
- **Cloud Sovereignty:** While the platform is **designed for** OVHcloud (EU) to eliminate US-CLOUD Act exposure, current local prototypes utilize a hybrid model (Local SPLADE + External LLMs via OpenRouter). Production-grade compliance for EU public sector deployments requires switching to fully sovereign EU endpoints (e.g., Mistral via OVH AI).
