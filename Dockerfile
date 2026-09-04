# Multi-stage Dockerfile for GCP Cloud Run and local containerized deployment
# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python ADK Backend Runtime
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install Python dependencies using uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev

# Copy backend code
COPY backend/ ./backend/
COPY tally_connector.py run.py ./

# Copy compiled frontend assets from Stage 1 into backend static folder
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Setup uploads directory
RUN mkdir -p /app/uploads

ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

CMD ["sh", "-c", "uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT}"]

