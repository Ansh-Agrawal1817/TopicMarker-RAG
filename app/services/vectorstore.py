from pinecone import Pinecone, ServerlessSpec
from app.config import settings
# from langchain.vectorstores import Pinecone as PineconeStore
# from langchain.embeddings.openai import OpenAIEmbeddings
# from langchain_pinecone import PineconeVectorStore
# from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone as PineconeStore
# from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings


# Instantiate Pinecone client
pc = Pinecone(api_key=settings.pinecone_api_key)

_index = None

def init_pinecone():
    global _index
    index_name = settings.pinecone_index_name

    try:
        # Check if index already exists
        existing_indexes = [index.name for index in pc.list_indexes()]
        if index_name not in existing_indexes:
            pc.create_index(
                name=index_name,
                dimension=1536,  # ✅ Update this to match your actual embedding dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
    except Exception as e:
        # Check if it's an "already exists" error (status code 409)
        if hasattr(e, 'status') and e.status != 409:
            raise  # Re-raise if it's not an "already exists" error
        elif not hasattr(e, 'status'):
            raise  # Re-raise if it doesn't have a status attribute

    # Get the index using the new API
    _index = pc.Index(index_name)



def embed_and_store(chunks, namespace: str = "default"):
    init_pinecone()
    embeddings = OpenAIEmbeddings()
    PineconeStore.from_texts(
        chunks,
        embedding=embeddings,
        index_name=settings.pinecone_index_name,
        namespace=namespace,
    )
    print("✅ Stored in Pinecone.")

def upsert_embeddings(vectors: list[dict]):
    """
    vectors: list of dicts like:
    {
        'id': str,
        'values': [float, ...],  # your embedding
        'metadata': { 'text': str, 'source_url': str, ... }
    }
    """
    if not _index:
        raise RuntimeError("Pinecone index not initialized.")
    _index.upsert(vectors=vectors)

def query_similar(vector: list[float], top_k: int = 2):
    """
    Returns top_k most similar items to the input vector.
    Each result has: id, text (from metadata), score.
    """
    if not _index:
        raise RuntimeError("Pinecone index not initialized.")

    res = _index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=True
    )

    return [
        {
            "id": match["id"],
            "score": match["score"],
            "metadata": match["metadata"]
        }
        for match in res.get("matches", [])
        if "metadata" in match and "text" in match["metadata"]
    ]
