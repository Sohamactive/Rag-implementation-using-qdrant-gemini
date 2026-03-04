"""
Chat module using LangChain for conversational RAG with memory.
"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document

from backend.qdrant_utils import q_client, COLLECTION_NAME
from backend.embeddings import embed_text

load_dotenv()

# Initialize Gemini LLM - using gemini-2.0-flash-lite for better availability
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.7,
    convert_system_message_to_human=True
)

# Store for conversation histories (in production, use Redis or database)
conversation_store: Dict[str, List[BaseMessage]] = {}


def get_conversation_history(session_id: str) -> List[BaseMessage]:
    """Get conversation history for a session."""
    if session_id not in conversation_store:
        conversation_store[session_id] = []
    return conversation_store[session_id]


def add_to_history(session_id: str, human_msg: str, ai_msg: str):
    """Add a message pair to conversation history."""
    history = get_conversation_history(session_id)
    history.append(HumanMessage(content=human_msg))
    history.append(AIMessage(content=ai_msg))
    # Keep only last 10 exchanges (20 messages) to prevent context overflow
    if len(history) > 20:
        conversation_store[session_id] = history[-20:]


def clear_history(session_id: str):
    """Clear conversation history for a session."""
    if session_id in conversation_store:
        del conversation_store[session_id]


def retrieve_documents(query: str, top_k: int = 5) -> List[Document]:
    """
    Retrieve relevant documents from Qdrant.
    Returns LangChain Document objects.
    """
    # Embed the query
    query_vector = embed_text(query)
    
    try:
        # Search in Qdrant
        results = q_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k
        )
        
        # Extract points from result
        points = results.points if hasattr(results, 'points') else results
        
        # Convert to LangChain documents
        documents = []
        for point in points:
            if hasattr(point, 'payload'):
                text = point.payload.get('text', '')
                metadata = {
                    'score': point.score if hasattr(point, 'score') else 0,
                    'id': str(point.id) if hasattr(point, 'id') else '',
                    **{k: v for k, v in point.payload.items() if k != 'text'}
                }
                if text.strip():
                    documents.append(Document(page_content=text, metadata=metadata))
        
        return documents
        
    except Exception as e:
        print(f"Error retrieving documents: {e}")
        return []


def format_docs(docs: List[Document]) -> str:
    """Format documents into a context string."""
    if not docs:
        return "No relevant documents found."
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


# RAG prompt template with conversation history
RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful AI assistant that answers questions based on the provided context from uploaded documents.

Guidelines:
- Answer questions accurately based on the context provided
- If the context doesn't contain relevant information, say so clearly
- Be conversational and helpful
- Reference specific parts of the documents when relevant
- If asked about previous conversation, refer to the chat history

Context from documents:
{context}"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}")
])


def chat(
    question: str,
    session_id: str = "default",
    top_k: int = 5,
    retrieval_query: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a chat message with RAG and conversation history.
    
    Args:
        question: The user's question (saved in history)
        session_id: Unique identifier for the conversation session
        top_k: Number of documents to retrieve
        retrieval_query: Optional rewritten query for better retrieval
    
    Returns:
        Dictionary with answer and metadata
    """
    try:
        # Get conversation history
        history = get_conversation_history(session_id)
        
        # Retrieve relevant documents (use rewritten query if provided)
        search_query = retrieval_query if retrieval_query else question
        docs = retrieve_documents(search_query, top_k=top_k)
        context = format_docs(docs)
        
        # Create the chain
        chain = RAG_PROMPT | llm | StrOutputParser()
        
        # Generate response
        response = chain.invoke({
            "context": context,
            "chat_history": history,
            "question": question
        })
        
        # Add to conversation history
        add_to_history(session_id, question, response)
        
        # Prepare chunks for frontend display
        chunks_used = [
            {
                "text": doc.page_content,
                "score": doc.metadata.get('score', 0)
            }
            for doc in docs
        ]
        
        return {
            "answer": response,
            "chunks_used": chunks_used,
            "session_id": session_id,
            "history_length": len(get_conversation_history(session_id)) // 2
        }
        
    except Exception as e:
        print(f"Chat error: {e}")
        return {
            "answer": f"Sorry, I encountered an error: {str(e)}",
            "chunks_used": [],
            "session_id": session_id,
            "error": str(e)
        }


def chat_stream(
    question: str,
    session_id: str = "default",
    top_k: int = 5
):
    """
    Stream chat responses for real-time output.
    Yields chunks of the response as they're generated.
    """
    try:
        # Get conversation history
        history = get_conversation_history(session_id)
        
        # Retrieve relevant documents
        docs = retrieve_documents(question, top_k=top_k)
        context = format_docs(docs)
        
        # Create streaming chain
        chain = RAG_PROMPT | llm
        
        # Collect full response for history
        full_response = ""
        
        # Stream the response
        for chunk in chain.stream({
            "context": context,
            "chat_history": history,
            "question": question
        }):
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            full_response += content
            yield content
        
        # Add complete exchange to history
        add_to_history(session_id, question, full_response)
        
    except Exception as e:
        yield f"Error: {str(e)}"


# Standalone question generator for better retrieval
CONDENSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Given a chat history and a follow-up question, rephrase the follow-up question 
to be a standalone question that captures all necessary context.
If the question is already standalone or there's no relevant history, return it as-is."""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "Follow-up question: {question}\n\nStandalone question:")
])


def get_standalone_question(question: str, session_id: str) -> str:
    """
    Convert a follow-up question into a standalone question using chat history.
    This improves retrieval for conversational queries.
    """
    history = get_conversation_history(session_id)
    
    if not history:
        return question
    
    try:
        chain = CONDENSE_PROMPT | llm | StrOutputParser()
        standalone = chain.invoke({
            "chat_history": history[-6:],  # Use last 3 exchanges
            "question": question
        })
        return standalone.strip()
    except:
        return question


def advanced_chat(
    question: str,
    session_id: str = "default",
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Advanced chat with query rewriting for better contextual understanding.
    """
    # Convert to standalone question for better retrieval
    standalone_question = get_standalone_question(question, session_id)
    
    # Use the rewritten query for retrieval, but keep original for history
    result = chat(question, session_id, top_k, retrieval_query=standalone_question)
    
    # Include the rewritten question in response
    if standalone_question != question:
        result["rewritten_query"] = standalone_question
    
    return result
