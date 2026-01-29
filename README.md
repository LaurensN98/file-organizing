# Case Study: Intelligent Document Management System

## 🚀 Project Overview
This project is an Intelligent Document Organization Endpoint designed to analyze unstructured folders, classify documents using unsupervised machine learning, and provide actionable insights.

It is architected with a "Privacy by Design" philosophy, utilizing Zero Data Retention (ZDR) principles and EU-Sovereign infrastructure patterns suitable for Dutch public sector clients.

## 🏗️ System Architecture

### High-Level Data Flow
1. **Upload:** User uploads multiple files or folders via Next.js Frontend (drag-and-drop).
2. **Ingestion & Parallel Processing:** FastAPI receives files -> Processes images (OCR), PDFs, and Docs concurrently using `asyncio`.
3. **Processing (ML Pipeline):**
    - **OCR:** Images are described using Multimodal LLM (Gemini Flash via OpenRouter).
    - **Embed:** External Embedding API (Qwen via OpenRouter/Nebius) via standard HTTPS requests.
    - **Reduce:** UMAP (10D for clustering, 2D for visualization).
    - **Cluster:** HDBSCAN (Density-based clustering).
    - **Label:** LLM (Google Gemini via OpenRouter) generates concise folder names based on cluster centroids.
4. **Output A (Interactive Map):** A semantic 2D scatter plot visualizes the document landscape with zooming and metadata inspection.
5. **Output B (Stream):** Organized files are zipped in RAM and streamed back to the user immediately.
6. **Output C (Insight):** Enhanced metadata (language, file size, cluster) is stored in PostgreSQL.

### Tech Stack
- **Frontend:** Next.js 16 (App Router), React 19, TailwindCSS, Recharts.
- **Backend:** FastAPI (Python 3.11), AsyncOpenAI.
- **ML & Data:** umap-learn, hdbscan, scikit-learn, langdetect.
- **Database:** PostgreSQL (Metadata storage).
- **Async/Queue:** Redis & Celery (Background metadata processing).
- **Infrastructure:** Docker & Docker Compose.

## ⚖️ Production Readiness Matrix
A comparison between this demonstration implementation and the target production architecture.

| Feature | 🛠️ Demo Implementation (Local) | 🏢 Production Standard (Target) |
| :--- | :--- | :--- |
| **Hosting** | Local Docker Compose | OVHcloud (Amsterdam/France regions) |
| **Embeddings & LLM** | OpenRouter (Qwen / Gemini) | Mistral 7B via OVH AI Endpoints (EU Sovereign) |
| **Data Privacy** | In-Memory Processing (RAM) | Zero Data Retention (ZDR) + Signed DPA |
| **Security** | HTTP (Localhost) | HTTPS (TLS 1.3) + Private VPC |
| **PII Handling** | `scrub_pii()` hook (Placeholder) | Microsoft Presidio (Automated Redaction) |
| **Concurrency** | AsyncIO + BackgroundTasks | Celery Workers + Redis Cluster |

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
│   │   │   ├── processing.py    # File reading, OCR, LangDetect
│   │   │   ├── ml_engine.py     # Embeddings, UMAP, HDBSCAN, LLM Labeling
│   │   │   └── privacy.py       # PII Scrubbing hooks
│   │   └── models/              # Pydantic & SQLAlchemy models
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js Pages
│   │   ├── components/
│   │   │   └── ResultsView.tsx  # Interactive Scatter Plot
│   ├── Dockerfile
│   └── package.json
└── docker-compose.yml
```

### 2. Key Libraries & Versions
- **Backend:** `fastapi`, `uvicorn`, `python-multipart`, `sqlalchemy`, `psycopg2-binary`, `celery`, `redis`, `langdetect`.
- **ML Core:** `umap-learn`, `hdbscan`, `scikit-learn`, `numpy`.
- **API Client:** `openai` (Standard SDK used for both Embeddings and LLM calls).
- **Frontend:** `next` (v16), `react` (v19), `lucide-react`, `axios`, `recharts`.

### 3. ML Pipeline Logic (`ml_engine.py`)
- **Text Extraction:** Read `pages[0:3]` of PDFs/Docx. Use Gemini Vision for Images.
- **Vectorization (API):** Batch send text chunks to the Embedding API (Qwen).
- **Dimensionality Reduction:** UMAP to 2 dimensions (visualization) and 10 dimensions (clustering).
- **Clustering:** HDBSCAN with `min_cluster_size=2`.
- **Naming:** Select 3 files near the centroid -> LLM Prompt (Gemini) -> "Generate a concise folder name".

### 4. Privacy Features (Implementation Details)
- **Zero-Write:** Use `io.BytesIO` for all file handling. Do not write uploaded files to disk.
- **Consent:** Frontend must include a checkbox: "I agree to the Privacy Policy and understand data is processed in the EU."
- **Scrubber Hook:** Include a placeholder function `scrub_pii(text)` in the processing pipeline to demonstrate where GDPR redaction would occur.

## 🏃‍♂️ Getting Started

### Prerequisites
- Docker & Docker Compose
- API Key (OpenRouter) compatible with Qwen and Gemini endpoints.

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
   OPENROUTER_API_KEY=your_key_here
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
- **At-Rest:** Only metadata (filenames, cluster IDs, coordinates, language) is stored in Postgres. File content is never persisted.
- **Sovereignty:** Designed for OVHcloud Amsterdam/France regions to ensure no US-CLOUD Act exposure.
