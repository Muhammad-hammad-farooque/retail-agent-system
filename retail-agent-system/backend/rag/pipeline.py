"""FAQ semantic search: local embeddings (FastEmbed) stored in pgvector.

Embeddings are made on the CPU with FastEmbed, so no API key or rate limit is
involved. Vectors are kept in a pgvector table when the database supports it
(Neon does), so they survive redeploys and only changed FAQs are re-embedded.
Where pgvector isn't installed (local Windows Postgres, SQLite in tests) the
same search runs in memory; with ~30 FAQs that is instant either way.
"""
import hashlib
import logging
import os
from typing import List, Optional

import numpy as np
from sqlalchemy import text

from .faq_documents import FAQ_DOCUMENTS

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
TABLE = "faq_embeddings"


def _document_text(doc: dict) -> str:
    # Question and answer together give a richer embedding than either alone
    return f"Q: {doc['question']}\nA: {doc['answer']}"


def _content_hash(doc: dict) -> str:
    # Includes the model name, so switching models re-embeds everything
    return hashlib.sha256(f"{EMBEDDING_MODEL}\n{_document_text(doc)}".encode()).hexdigest()


def _to_pgvector(vector) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in vector) + "]"


class Embedder:
    def __init__(self):
        self._model = None

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding
            # FASTEMBED_CACHE_PATH points at the copy baked into the Docker image
            self._model = TextEmbedding(EMBEDDING_MODEL, cache_dir=os.getenv("FASTEMBED_CACHE_PATH"))
        return self._model

    def passages(self, texts: List[str]) -> np.ndarray:
        return np.array(list(self._load().passage_embed(texts)))

    def query(self, query: str) -> np.ndarray:
        return np.array(next(iter(self._load().query_embed(query))))


class MemoryStore:
    name = "memory"

    def __init__(self):
        self._docs: List[dict] = []
        self._matrix: Optional[np.ndarray] = None

    def sync(self, docs: List[dict], embedder: Embedder) -> int:
        self._docs = list(docs)
        self._matrix = embedder.passages([_document_text(d) for d in docs])
        return len(docs)

    def search(self, query_vector: np.ndarray, top_k: int) -> List[dict]:
        # Vectors are normalized, so the dot product is the cosine similarity
        scores = self._matrix @ query_vector
        best = np.argsort(-scores)[:top_k]
        return [
            {"doc": self._docs[i], "score": float(scores[i])}
            for i in best
        ]


class PgVectorStore:
    name = "pgvector"

    def __init__(self, engine):
        self._engine = engine

    @classmethod
    def available(cls, engine) -> bool:
        if engine.dialect.name != "postgresql":
            return False
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            return True
        except Exception as exc:
            logger.info("pgvector not available (%s); FAQ search will run in memory", exc.__class__.__name__)
            return False

    def sync(self, docs: List[dict], embedder: Embedder) -> int:
        """Embed only FAQs that are new or changed; remove deleted ones."""
        with self._engine.begin() as conn:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {TABLE} (
                    id           TEXT PRIMARY KEY,
                    category     TEXT NOT NULL,
                    question     TEXT NOT NULL,
                    content      TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    embedding    vector({EMBEDDING_DIM}) NOT NULL
                )
            """))
            stored = dict(conn.execute(text(f"SELECT id, content_hash FROM {TABLE}")).fetchall())

            changed = [d for d in docs if stored.get(d["id"]) != _content_hash(d)]
            if changed:
                vectors = embedder.passages([_document_text(d) for d in changed])
                for doc, vector in zip(changed, vectors):
                    conn.execute(text(f"""
                        INSERT INTO {TABLE} (id, category, question, content, content_hash, embedding)
                        VALUES (:id, :category, :question, :content, :hash, CAST(:embedding AS vector))
                        ON CONFLICT (id) DO UPDATE SET
                            category = EXCLUDED.category, question = EXCLUDED.question,
                            content = EXCLUDED.content, content_hash = EXCLUDED.content_hash,
                            embedding = EXCLUDED.embedding
                    """), {
                        "id": doc["id"], "category": doc["category"], "question": doc["question"],
                        "content": _document_text(doc), "hash": _content_hash(doc),
                        "embedding": _to_pgvector(vector),
                    })

            removed = set(stored) - {d["id"] for d in docs}
            for doc_id in removed:
                conn.execute(text(f"DELETE FROM {TABLE} WHERE id = :id"), {"id": doc_id})
        return len(changed)

    def search(self, query_vector: np.ndarray, top_k: int) -> List[dict]:
        with self._engine.connect() as conn:
            rows = conn.execute(text(f"""
                SELECT id, category, question, content,
                       1 - (embedding <=> CAST(:q AS vector)) AS score
                FROM {TABLE}
                ORDER BY embedding <=> CAST(:q AS vector)
                LIMIT :k
            """), {"q": _to_pgvector(query_vector), "k": top_k}).fetchall()
        return [
            {"doc": {"id": r.id, "category": r.category, "question": r.question}, "content": r.content,
             "score": float(r.score)}
            for r in rows
        ]


class RAGPipeline:
    def __init__(self, engine=None, embedder: Optional[Embedder] = None):
        self._engine = engine
        self._embedder = embedder or Embedder()
        self._store = None
        self.last_embedded = 0

    def _get_store(self):
        if self._store is None:
            engine = self._engine
            if engine is None:
                from ..database import engine
            store = PgVectorStore(engine) if PgVectorStore.available(engine) else MemoryStore()
            self.last_embedded = store.sync(FAQ_DOCUMENTS, self._embedder)
            logger.info("FAQ search ready (%s store, %d FAQs embedded now)", store.name, self.last_embedded)
            self._store = store
        return self._store

    @property
    def store_name(self) -> str:
        return self._get_store().name

    def ingest_faq(self, force: bool = False) -> int:
        """Make sure every FAQ is embedded. Returns how many were embedded by this call."""
        if self._store is not None and not force:
            return 0
        self._store = None
        self._get_store()
        return self.last_embedded

    def search(self, query: str, top_k: int = 3) -> List[dict]:
        """Return the top_k FAQ chunks most similar to the query."""
        store = self._get_store()
        results = store.search(self._embedder.query(query), top_k)
        return [
            {
                "content": r.get("content") or _document_text(r["doc"]),
                "category": r["doc"]["category"],
                "question": r["doc"]["question"],
                "relevance_score": round(r["score"], 4),
            }
            for r in results
        ]

    def build_context(self, query: str, top_k: int = 3) -> str:
        """Return a formatted context string to inject into the agent prompt."""
        chunks = self.search(query, top_k=top_k)
        if not chunks:
            return ""
        lines = ["Relevant FAQ information:"]
        for i, chunk in enumerate(chunks, 1):
            lines.append(f"\n[{i}] {chunk['content']}")
        return "\n".join(lines)


# Singleton instance
rag_pipeline = RAGPipeline()
