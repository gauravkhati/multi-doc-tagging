# syntax=docker/dockerfile:1.7

# -------- Base image --------
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system deps
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
 && rm -rf /var/lib/apt/lists/*

# Create app user and dirs
WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (exclude secrets via .dockerignore)
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Default environment (override in compose or env)
ENV PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true

# Streamlit config to trust the remote origin
ENV STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Healthcheck (optional simple curl)
HEALTHCHECK CMD curl --fail http://localhost:${PORT}/_stcore/health || exit 1

# Entrypoint: run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
