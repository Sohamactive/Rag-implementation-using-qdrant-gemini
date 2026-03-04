import os
import asyncio
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.ingest import process_pdf
from backend.search import search_query
from backend.qdrant_utils import init_qdrant
from backend.chat import chat, chat_stream, clear_history, get_conversation_history, advanced_chat

app = FastAPI()

# Serve frontend static files (CSS, JS)
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


@app.on_event("startup")
async def startup_event():
    await asyncio.to_thread(init_qdrant, vector_size=768)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -- Pages --

@app.get("/")
async def index():
    return FileResponse("frontend/index.html")


# -- Upload --

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    file_location = f"data/uploads/{file.filename}"
    file_content = await file.read()

    await asyncio.to_thread(
        lambda: (
            os.makedirs(os.path.dirname(file_location), exist_ok=True),
            open(file_location, "wb").write(file_content)
        )
    )

    result = await asyncio.to_thread(process_pdf, file_location)
    await asyncio.to_thread(os.remove, file_location)

    return {"status": "success", "details": result}


# -- Search --

@app.post("/search")
async def rag_search(q: str = Form(...), k: int = Form(5)):
    result = await asyncio.to_thread(search_query, q, top_k=k)
    return result


# -- Chat --

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    top_k: int = 5
    advanced: bool = False


@app.post("/chat/message")
async def chat_message(request: ChatRequest):
    if request.advanced:
        result = await asyncio.to_thread(
            advanced_chat, request.message, request.session_id, request.top_k
        )
    else:
        result = await asyncio.to_thread(
            chat, request.message, request.session_id, request.top_k
        )
    return result


@app.get("/chat/stream")
async def chat_stream_endpoint(
    message: str, session_id: str = "default", top_k: int = 5
):
    async def generate():
        for chunk in chat_stream(message, session_id, top_k):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    history = get_conversation_history(session_id)
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": msg.content}
        for i, msg in enumerate(history)
    ]
    return {"session_id": session_id, "messages": messages}


@app.delete("/chat/history/{session_id}")
async def delete_chat_history(session_id: str):
    clear_history(session_id)
    return {"status": "success", "message": f"History cleared for session {session_id}"}
