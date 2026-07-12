FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/
COPY data/ ./data/
# Tests, scripts, etc. aren't strictly needed for prod runtime, but copying everything is fine
# or we can explicitly copy what we need

# Install dependencies via uv
RUN uv pip install --system -e .

# Expose backend port
EXPOSE 8000

# Start the FastAPI app via uvicorn
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
