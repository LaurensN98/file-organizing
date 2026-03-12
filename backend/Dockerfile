# --- STAGE 1: Builder ---
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install to a specific prefix to make copying easier
RUN pip install --user --no-cache-dir -r requirements.txt


# --- STAGE 2: Runner ---
FROM python:3.11-slim AS runner

# 1. Create a non-privileged user
RUN groupadd -g 999 python && \
    useradd -r -u 999 -g python python

WORKDIR /app

# 2. Install runtime dependencies and 'chown' the app directory
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* && \
    chown python:python /app

# 3. Copy installed packages from builder
COPY --from=builder /root/.local /home/python/.local
ENV PATH=/home/python/.local/bin:$PATH
ENV NUMBA_CACHE_DIR=/tmp

# 4. Copy code and ensure the 'python' user owns it
COPY --chown=python:python . .

# 5. SWITCH TO NON-ROOT USER
USER python

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]