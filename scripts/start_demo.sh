#!/bin/bash
set -e

echo "======================================"
echo "    Starting TinyBI Local Demo        "
echo "======================================"

# 1. Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed!"
    echo "To run this application fully locally with GPU acceleration, please install Ollama:"
    echo "👉 https://ollama.com/download"
    echo ""
    echo "Once installed, run this script again."
    exit 1
fi

echo "✅ Ollama is installed."

# 2. Pull the necessary models via host's Ollama
echo "📥 Ensuring required models are pulled (this may take a moment if not cached)..."
ollama pull ibm/granite4.1:3b
ollama pull qwen3-embedding:0.6b

echo "✅ Models are ready."

# 3. Start the application via Docker Compose
echo "🚀 Booting up the TinyBI Docker containers..."
docker compose up --build -d backend frontend

echo ""
echo "======================================"
echo "🎉 TinyBI is running!"
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000/docs"
echo "======================================"
echo "Use 'docker compose logs -f' to view live logs."
echo "Use 'docker compose down' to stop."
