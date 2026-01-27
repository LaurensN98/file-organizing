# Case Study: Intelligent Document Management System

## 🚀 Project Overview
This project is an Intelligent Document Organization Endpoint designed to analyze unstructured folders, classify documents using unsupervised machine learning, and provide actionable insights.

It is architected with a "Privacy by Design" philosophy, utilizing Zero Data Retention (ZDR) principles and EU-Sovereign infrastructure patterns suitable for Dutch public sector clients.

## 🏗️ System Architecture

### High-Level Data Flow
1. **Upload:** User uploads a folder (multiple files) via Next.js Frontend.
2. **Ingestion:** FastAPI receives files -> Reads only the first 3 pages (proxy) in memory (io.BytesIO).
3. **Processing (ML Pipeline):**
    - **Embed:** External Embedding API (e.g., Mistral/GPT-OSS) via standard HTTP requests.
    - **Reduce:** UMAP (Uniform Manifold Approximation and Projection).
    - **Cluster:** HDBSCAN (Density-based clustering).
    - **Label:** LLM (via EU-hosted Mistral) generates folder names based on cluster centroids.
4. **Output A (Stream):** Organized files are zipped in RAM and streamed back to the user immediately.
5. **Output B (Insight):** Metadata and cluster coordinates are stored in PostgreSQL for future custom visualization.

### Tech Stack
- **Frontend:** Next.js 14 (App Router), TailwindCSS.
- **Backend:** FastAPI (Python 3.11).
- **ML & Data:** umap-learn, hdbscan, scikit-learn, openai (SDK for API calls).
- **Database:** PostgreSQL (Metadata storage).
- **Async/Queue:** Redis & Celery (Background metadata processing).
- **Infrastructure:** Docker & Docker Compose.

## ⚖️ Production Readiness Matrix
A comparison between this demonstration implementation and the target production architecture.

| Feature | 🛠️ Demo Implementation (Local) | 🏢 Production Standard (Target) |
| :--- | :--- | :--- |
| **Hosting** | Local Docker Compose | OVHcloud (Amsterdam/France regions) |
| **Embeddings & LLM** | API (Mistral/GPT-OSS) | Mistral 7B via OVH AI Endpoints (EU Sovereign) |
| **Data Privacy** | In-Memory Processing (RAM) | Zero Data Retention (ZDR) + Signed DPA |
| **Security** | HTTP (Localhost) | HTTPS (TLS 1.3) + Private VPC |
| **PII Handling** | `scrub_pii()` hook (Placeholder) | Microsoft Presidio (Automated Redaction) |
| **Concurrency** | FastAPI BackgroundTasks | Celery Workers + Redis Cluster |

## 📂 Implementation Guide (For Developers/Agents)

### 1. Directory Structure
Ensure the project follows this strict structure:
```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── api/                 # Endpoints
│   │   ├── core/                # Config & Security
│   │   ├── services/
│   │   │   ├── processing.py    # File reading (PDF/Docx text extraction)
│   │   │   ├── ml_engine.py     # API-based Embeddings, UMAP, HDBSCAN logic
│   │   │   └── privacy.py       # PII Scrubbing hooks
│   │   └── models/              # Pydantic & SQLAlchemy models
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js Pages
│   │   ├── components/
│   │   │   └── Dashboard.tsx    # Stats view
│   ├── Dockerfile
│   └── package.json
└── docker-compose.yml
```

### 2. Key Libraries & Versions
- **Backend:** `fastapi`, `uvicorn`, `python-multipart`, `sqlalchemy`, `psycopg2-binary`, `celery`, `redis`.
- **ML Core:** `umap-learn`, `hdbscan`, `scikit-learn`, `numpy`.
- **API Client:** `openai` (Standard SDK used for both Embeddings and LLM calls).
- **Frontend:** `next`, `react`, `lucide-react`, `axios`, `framer-motion` (for basic UI transitions).

### 3. ML Pipeline Logic (`ml_engine.py`)
- **Text Extraction:** Read `pages[0:3]` of PDFs/Docx to reduce token usage.
- **Vectorization (API):** Batch send text chunks to the Embedding API (e.g., `mistral-embed`). Do not use local transformers.
- **Dimensionality Reduction:** UMAP to 2 dimensions (for future plotting) and 10 dimensions (for clustering).
- **Clustering:** HDBSCAN with `min_cluster_size=2` (adjust based on dataset size).
- **Naming:** Select 3 files near the centroid -> LLM Prompt -> "Generate a concise folder name".

### 4. Privacy Features (Implementation Details)
- **Zero-Write:** Use `io.BytesIO` for all file handling. Do not write uploaded files to disk.
- **Consent:** Frontend must include a checkbox: "I agree to the Privacy Policy and understand data is processed in the EU."
- **Scrubber Hook:** Include a placeholder function `scrub_pii(text)` in the processing pipeline to demonstrate where GDPR redaction would occur.

## 🏃‍♂️ Getting Started

### Prerequisites
- Docker & Docker Compose
- API Key (Mistral or OVHcloud) compatible with Embedding and Chat endpoints.

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd document-management-system
   ```

2. **Environment Setup:**
   Create a `.env` file in `./backend`:
   ```env
   DATABASE_URL=postgresql://user:password@db:5432/rebels_db
   EMBEDDING_API_KEY=your_key_here
   LLM_API_KEY=your_key_here
   REDIS_URL=redis://redis:6379/0
   ```

3. **Run with Docker:**
   ```bash
   docker-compose up --build
   ```

### Access
- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

## 🛡️ GDPR & Security Compliance
This architecture ensures **Data Minimization**:
- **In-Transit:** Files are processed in volatile memory.
- **At-Rest:** Only metadata (filenames, cluster IDs, coordinates) is stored in Postgres. File content is never persisted.
- **Sovereignty:** Designed for OVHcloud Amsterdam/France regions to ensure no US-CLOUD Act exposure.