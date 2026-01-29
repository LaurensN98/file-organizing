# Case Study: Intelligent Document Management System

## Project Overview
This project is an Intelligent Document Organization Endpoint designed to analyze unstructured folders, classify documents using unsupervised machine learning, and provide actionable insights.

It is architected with a "Privacy by Design" philosophy, utilizing Zero Data Retention (ZDR) principles and EU-Sovereign infrastructure patterns suitable for Dutch public sector clients.

## System Architecture

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

## Production Improvements
To transition from this prototype to a production-grade enterprise solution, the following enhancements are recommended:

*   **EU Hosting & Sovereign AI:** Deploy exclusively on EU-based cloud providers (e.g., OVHcloud, Scaleway) and use EU-hosted LLM endpoints to ensure immunity from the US CLOUD Act.
*   **Private VPC:** Isolate the infrastructure within a Virtual Private Cloud (VPC) with strict firewall rules, ensuring no public internet access to the database or internal services.
*   **Encrypted Object Store:** Replace in-memory processing with a secure, S3-compatible object store (e.g., MinIO) featuring server-side encryption (SSE) for temporary file handling.
*   **DPA Agreements:** Establish formal Data Processing Agreements (DPAs) with all third-party AI subprocessors to legally guarantee data privacy and usage limitations.
*   **AI Rate Limiting:** Implement robust rate limiting and circuit breakers on LLM API calls to prevent cost overruns and ensure service stability during high load.
*   **HTTPS/SSL:** Enforce end-to-end encryption using TLS 1.3 with valid SSL certificates (e.g., via Let's Encrypt or a managed load balancer).
*   **Celery & Redis Cluster:** Scale background processing by deploying multiple Celery workers across nodes and using a high-availability Redis cluster for the task queue.
*   **Advanced PII Redaction:** Integrate enterprise-grade PII detection (like Microsoft Presidio) to automatically redact sensitive information (names, SSNs) before sending text to AI models.

## Getting Started

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

## GDPR & Security Compliance
This architecture ensures **Data Minimization**:
- **In-Transit:** Files are processed in volatile memory.
- **At-Rest:** Only metadata (filenames, cluster IDs, coordinates, language) is stored in Postgres. File content is never persisted.
- **Sovereignty:** Designed for OVHcloud Amsterdam/France regions to ensure no US-CLOUD Act exposure.