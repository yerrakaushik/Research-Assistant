"""
rag_engine.py – builds an in-memory FAISS index from paper abstracts
and runs semantic search to retrieve relevant context chunks.
"""

from typing import List, Dict
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    _FAISS_AVAILABLE = True
except ImportError:
    _FAISS_AVAILABLE = False

_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None and _FAISS_AVAILABLE:
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def build_index(papers: List[Dict]):
    """
    Embeds paper abstracts and builds a FAISS index.
    Returns (index, chunks) where chunks[i] corresponds to index vector i.
    """
    if not _FAISS_AVAILABLE:
        return None, []

    model = _get_model()
    chunks = []
    for p in papers:
        chunks.append(f"Title: {p['title']}\nAbstract: {p['abstract']}")

    if not chunks:
        return None, []

    embeddings = model.encode(chunks, normalize_embeddings=True)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product (cosine on normalized vectors)
    index.add(np.array(embeddings, dtype=np.float32))
    return index, chunks


def query_rag(question: str, papers: List[Dict], top_k: int = 4) -> str:
    """
    Queries the RAG index and returns the top-k relevant paper contexts as a string.
    Falls back to joining all abstracts if FAISS is unavailable.
    """
    if not _FAISS_AVAILABLE or not papers:
        # Fallback: return all abstracts truncated
        context = "\n\n".join(
            f"[{p['title']}]: {p['abstract'][:300]}" for p in papers[:5]
        )
        return context

    model = _get_model()
    index, chunks = build_index(papers)

    if index is None:
        return ""

    q_emb = model.encode([question], normalize_embeddings=True)
    distances, indices = index.search(np.array(q_emb, dtype=np.float32), top_k)

    results = []
    for idx in indices[0]:
        if idx < len(chunks):
            results.append(chunks[idx])

    return "\n\n---\n\n".join(results)
