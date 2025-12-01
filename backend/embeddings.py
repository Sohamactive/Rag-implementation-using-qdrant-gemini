#this file is for embedding text using Google Gemini Embedding API

import os
from typing import List, Union
from dotenv import load_dotenv

from google import genai
from google.genai import types


load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

'''
print("GEMINI_API_KEY:", API_KEY)  # Debugging line to check if the key is loaded
if not API_KEY:
    raise ValueError("GEMINI_API_KEY missing in .env")
'''



client = genai.Client(api_key=API_KEY)

# Common settings
MODEL = "gemini-embedding-001"
EMBED_DIM = 768 # recommended: 768 / 1536 / 3072





# Embed a single text (query)
def embed_text(text: str) -> List[float]:


    """
    Embed a single user query. Returns a list[float].
    Uses task_type=RETRIEVAL_QUERY to optimize for queries.
    """

    result = client.models.embed_content(
        model=MODEL,
        contents=[text],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBED_DIM,
        ),
    )

    vec = result.embeddings[0].values #type:ignore

    return vec #type:ignore







# Embed multiple text chunks (batched for Gemini limit 100)
def embed_chunks(chunks: List[str]) -> List[List[float]]:


    """
    Embeds large documents by batching into <=100 chunks per request.
    Gemini API LIMIT: max 100 items per embed_content call.
    """


    all_vectors = []
    batch_size = 50

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        result = client.models.embed_content(
            model=MODEL,
            contents=batch, # type: ignore
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=EMBED_DIM,
            ),
        )

        for emb in result.embeddings: #type:ignore
            all_vectors.append(emb.values)   # extract list of floats

    return all_vectors
























# from fastembed import TextEmbedding
# from typing import List
# embedding_model = TextEmbedding()
# def embed_text(text: str) -> List[float]:
#     vectors = embedding_model.embed([text])
#     vector_list = []
#     for vec in vectors:
#         if hasattr(vec, "tolist"):
#             vector_list.append(vec.tolist())
#         else:
#             vector_list.append(vec)
#     return vector_list[0]
# def embed_chunks(chunks: List[str]) -> List[List[float]]:
#     vectors = embedding_model.embed(chunks)
#     vector_list = []
#     for vec in vectors:
#         if hasattr(vec, "tolist"):
#             vector_list.append(vec.tolist())
#         else:
#             vector_list.append(vec)
#     return vector_list
