from typing import List, Union, Tuple
from backend.embeddings import embed_text
from backend.qdrant_utils import q_client, COLLECTION_NAME
from google import genai


# Gemini client for generating final answers (RAG generation)
llm = genai.Client()


def _extract_chunk_from_result(result: Union[tuple, object]) -> str:
    """
    Extract the text chunk from a Qdrant search result.
    Compatible with ScoredPoint objects.
    """

    # Case 1: Modern Qdrant → result is ScoredPoint object
    if hasattr(result, "payload"):
        return result.payload.get("text", "") # type: ignore

    # Fallback for unexpected formats (less likely now, but safe)
    if isinstance(result, tuple) and len(result) >= 2 and isinstance(result[1], dict) and 'text' in result[1]:
        return result[1].get("text", "")

    # This WARNING is now mainly for debugging unexpected formats or an empty list being passed.
    # print("WARNING: Unknown result format in _extract_chunk_from_result:", result)
    return ""


def search_query(query: str, top_k: int = 5) -> dict:
    
    # 1) Embed the user query
    query_vector = embed_text(query)

    raw_result = None
    try:
        # 2) Search in Qdrant (query_points returns an object with a .points attribute)
        raw_result = q_client.query_points(
            collection_name=COLLECTION_NAME,  # type: ignore
            query=query_vector,
            limit=top_k
        )
    except AttributeError:
        # Fallback to old method 'search'
        raw_result = q_client.search( #type: ignore
            collection_name=COLLECTION_NAME,  # type: ignore
            query_vector=query_vector,
            limit=top_k
        )
    except Exception as e:
        print(f"Qdrant error: {e}")
        return {
            "answer": "Error while searching the database.",
            "chunks_used": []
        }

    # --- CRITICAL FIX: EXTRACT THE LIST OF POINTS ---
    final_results_list = []
    
    # Prioritize extracting the list of points via the attribute discovered in test.py
    if hasattr(raw_result, 'points'):
        final_results_list = raw_result.points
    elif isinstance(raw_result, list):
        # Fallback for if an older client returned a list directly
        final_results_list = raw_result
    elif isinstance(raw_result, tuple) and len(raw_result) >= 1 and isinstance(raw_result[0], list):
        # Fallback for the common tuple return format: ([list], metadata)
        final_results_list = raw_result[0]
    else:
        # If all else fails, use the raw result (likely empty or failed)
        final_results_list = raw_result


    if not final_results_list:
        return {
            "answer": "No relevant information found.",
            "chunks_used": []
        }

    # -----------------------------
    # 3) Extract chunks
    # -----------------------------
    retrieved_chunks: List[str] = [
        _extract_chunk_from_result(r)
        for r in final_results_list # Iterate over the correctly unpacked list
    ]

    retrieved_chunks = [c for c in retrieved_chunks if c.strip()]

    if not retrieved_chunks:
        return {
            "answer": "Found results, but no readable text chunks were extracted.",
            "chunks_used": []
        }

    context = "\n\n".join(retrieved_chunks)

    # -----------------------------
    # 4) Generate final answer using Gemini LLM
    # -----------------------------
    prompt = f"""
    You are a helpful assistant. Answer strictly using the context.
    
    Context:
    {context}
    
    Question:
    {query}
    
    If answer is not present in the context, reply:
    "I don't have enough information from the stored documents."
    """

    response = llm.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return {
        "answer": response.text,
        "chunks_used": retrieved_chunks
    }