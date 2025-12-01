import uuid
from typing import List
from pypdf import PdfReader

from backend.embeddings import embed_chunks
from backend.qdrant_utils import q_client, COLLECTION_NAME


# 1. Extract text from a PDF file
def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text() or ""   # SAFER
        text += page_text + "\n"

    return text


# 2. Clean the extracted text
def clean_text(text: str) -> str:
    text = text.replace("\t", " ")
    text = text.replace("\xa0", " ")
    text = " ".join(text.split())
    return text


#currenlty using count based chunkng

# 3. Split text into chunks
def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    words = text.split(" ")
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += (chunk_size - overlap)

    return chunks




# 4. Upload vectors + payload to Qdrant
def upload_to_qdrant(chunks, vectors, batch_size=50):
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        batch_vectors = vectors[i:i+batch_size]

        points = []
        for text, vector in zip(batch_chunks, batch_vectors):
            points.append({
                "id": str(uuid.uuid4()),
                "vector": vector,
                "payload": {"text": text}
            })

        q_client.upsert(
            collection_name=COLLECTION_NAME,   # type: ignore
            points=points
        )


# 5. Main function → called by FastAPI
def process_pdf(file_path: str):
    raw_text = extract_text_from_pdf(file_path)
    cleaned = clean_text(raw_text)

    chunks = chunk_text(cleaned)
    chunks = [c for c in chunks if c.strip()]  # no empty chunks

    vectors = embed_chunks(chunks)

    # SAFETY CHECK
    if len(vectors) != len(chunks):
        raise ValueError(f"Mismatch: {len(chunks)} chunks but {len(vectors)} vectors")

    upload_to_qdrant(chunks, vectors)

    print(f"Uploaded {len(chunks)} chunks successfully.")

    return {"chunks_uploaded": len(chunks)}


print("the collection name is :", COLLECTION_NAME)