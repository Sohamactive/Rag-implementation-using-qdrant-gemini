## Gemini-Qdrant RAG Backend

This is a production-ready RAG (Retrieval-Augmented Generation) backend built with FastAPI. It uses Google Gemini Embeddings for high-quality semantic search and Qdrant as the vector database.

The pipeline is non-blocking, designed for concurrent requests, and optimized for indexing large documents.

## ⚙️ Setup and Installation

```
python -m venv .venv
.venv/scripts/activate
pip install -r requirements.txt
fastapi dev backend/main.py
```
Create a .env file in the root of your project directory and set your access keys and database URL.
```
# Gemini API Key (Required for embedding and generation)
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"

# Qdrant Vector Database Connection
QDRANT_URL="http://localhost:6333"
QDRANT_API_KEY="" # Use only if your Qdrant instance requires it
QDRANT_COLLECTION="rag_documents_768"
```

