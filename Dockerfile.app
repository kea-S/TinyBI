# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
# Override the API base URL to an empty string so the production build
# knows to send API requests to the exact same host/port serving the UI.
ENV VITE_API_BASE_URL=""
RUN npm run build

# Stage 2: Build Python Backend
FROM python:3.13-slim
WORKDIR /app

# Install required system packages for building C-extensions (like DuckDB/SQLite)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for ultra-fast python dependency management
RUN pip install uv

# Copy python dependency manifests
COPY pyproject.toml requirements.txt ./
# Install dependencies into a virtual environment
RUN uv venv && uv pip install -r requirements.txt

# Copy backend source code
COPY src/ ./src/

# Copy seed database and vector index files
COPY data/ ./data/

# Copy the built React assets from the frontend builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose the internal container port
EXPOSE 8000

# Run FastAPI via uvicorn
CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
