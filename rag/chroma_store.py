import os
import re
import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "syllabus_chunks"

os.makedirs(CHROMA_DIR, exist_ok=True)

client = chromadb.PersistentClient(path=CHROMA_DIR)

#Default embedding model (works offline) but better for RAG:
# Chroma provides default embedding function fallback.
# We’ll use SentenceTransformer embeddings if available (optional)
try:
    sentence_model = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
except Exception:
    sentence_model = None

def get_collection():
    if sentence_model:
        return client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=sentence_model
        )
    return client.get_or_create_collection(name=COLLECTION_NAME)

def clean_text(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    return t

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120):
    """
    Very stable chunker for PDF syllabus text.
    """
    text = clean_text(text)
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks

def index_syllabus_to_chroma(syllabus_text: str, filename: str):
    collection = get_collection()

    # clear old syllabus (only keep latest)
    # If you want multiple syllabus support, remove this delete step.
    try:
        collection.delete(where={})
    except Exception:
        pass

    chunks = chunk_text(syllabus_text)

    ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas
    )

    return len(chunks)

def rag_search(query: str, top_k: int = 5):
    collection = get_collection()

    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    final = []
    for d, m in zip(docs, metas):
        final.append({"text": d, "meta": m})

    return final
