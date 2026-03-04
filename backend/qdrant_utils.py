import os
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from dotenv import load_dotenv
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "documents")

# Flag to track Qdrant availability
qdrant_available = False

# initializing Qdrant client
try:
    q_client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY if QDRANT_API_KEY else None
    )
    qdrant_available = True
except Exception as e:
    print(f"Warning: Could not connect to Qdrant: {e}")
    q_client = None


# initializing the qdrant collection
def init_qdrant(vector_size: int = 768):
    global qdrant_available
    if not q_client:
        print("Qdrant client not available, skipping initialization")
        return False
    
    try:
        #we are checking if the collection already exists, if not we create it
        #we named it collections because it is a list of collection objects

        collections = q_client.get_collections().collections
        print(collections) # Debugging line to print existing collections
        if not any(col.name == COLLECTION_NAME for col in collections):
            q_client.create_collection(
                collection_name=str(COLLECTION_NAME),
                vectors_config=VectorParams(size=vector_size, 
                                            distance=Distance.COSINE)
            )
            print(f"Created Qdrant collection: {COLLECTION_NAME}") # Debugging line to confirm creation

        else:
            print("Qdrant collection already exists.") # Debugging line to confirm existence
        qdrant_available = True
        return True
    except Exception as e:
        print(f"Warning: Could not initialize Qdrant collection: {e}")
        qdrant_available = False
        return False