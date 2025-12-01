import os
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from dotenv import load_dotenv
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION")

q_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

def init_qdrant(vector_size: int = 768):
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

init_qdrant()
# print(QDRANT_URL)
# print(QDRANT_API_KEY)
# print(COLLECTION_NAME)