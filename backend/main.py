import os
import asyncio # <-- NEW: Required for non-blocking I/O tasks
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from backend.ingest import process_pdf
from backend.search import search_query
from backend.qdrant_utils import init_qdrant # <-- NEW: Import collection initialization

app = FastAPI()


# --- SERVER LIFECYCLE ---
@app.on_event("startup")
async def startup_event():
    """Initializes the Qdrant collection when the FastAPI server starts."""
    # Run the synchronous init_qdrant() in a background thread 
    # to avoid blocking the Uvicorn startup thread.
    # We use vector_size=768 as defined in embeddings.py
    await asyncio.to_thread(init_qdrant, vector_size=768) 
# --------------------------

# Enable communication between frontend and backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "RAG Backend Running Successfully"}

# Upload endpoint (Now fully Non-Blocking)
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    
    file_location = f"data/uploads/{file.filename}"
    file_content = await file.read() # Asynchronous file read

    # FIX 1: Synchronous file writing and directory creation wrapped in to_thread
    # This prevents blocking the server while writing the file to disk.
    await asyncio.to_thread(
        lambda: (
            os.makedirs(os.path.dirname(file_location), exist_ok=True),
            open(file_location, "wb").write(file_content)
        )
    )

    # FIX 2: Run the heavy, synchronous ingestion process (process_pdf) in a thread.
    # This includes PDF parsing, chunking, and synchronous upserting/embedding.
    result = await asyncio.to_thread(process_pdf, file_location)

    # FIX 3: Run the synchronous file deletion (os.remove) in a thread.
    await asyncio.to_thread(os.remove, file_location)
    
    return {"status": "success", "details": result}

# Final Search endpoint (Now fully Non-Blocking)
@app.post("/search")
async def rag_search(q: str = Form(...), k: int = Form(5)):
    # FIX: Run the synchronous search_query (Gemini embedding + Qdrant search) in a thread.
    # This is essential for the search endpoint's stability.
    result = await asyncio.to_thread(search_query, q, top_k=k)
    return result