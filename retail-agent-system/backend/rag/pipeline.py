import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List
from .faq_documents import FAQ_DOCUMENTS

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = "retail_faq"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


class RAGPipeline:
    def __init__(self):
        self._client = None
        self._collection = None
        self._embed_fn = None

    def _get_client(self):
        if self._client is None:
            self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        return self._client

    def _get_embed_fn(self):
        if self._embed_fn is None:
            self._embed_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=OPENAI_API_KEY,
                model_name="text-embedding-3-small",
            )
        return self._embed_fn

    def _get_collection(self):
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self._get_embed_fn(),
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def ingest_faq(self, force: bool = False) -> int:
        """Embed and store all FAQ documents into ChromaDB. Returns count ingested."""
        collection = self._get_collection()

        # Skip if already ingested and not forced
        if not force and collection.count() >= len(FAQ_DOCUMENTS):
            return 0

        # Clear existing if forcing re-ingest
        if force and collection.count() > 0:
            collection.delete(ids=[doc["id"] for doc in FAQ_DOCUMENTS])

        documents, ids, metadatas = [], [], []
        for doc in FAQ_DOCUMENTS:
            # Combine Q+A for richer embedding
            combined = f"Q: {doc['question']}\nA: {doc['answer']}"
            documents.append(combined)
            ids.append(doc["id"])
            metadatas.append({"category": doc["category"], "question": doc["question"]})

        collection.add(documents=documents, ids=ids, metadatas=metadatas)
        return len(documents)

    def search(self, query: str, top_k: int = 3) -> List[dict]:
        """Search FAQ for top-k relevant chunks matching the query."""
        collection = self._get_collection()
        if collection.count() == 0:
            self.ingest_faq()

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for doc, meta, dist in zip(docs, metas, distances):
            chunks.append({
                "content": doc,
                "category": meta.get("category", ""),
                "question": meta.get("question", ""),
                "relevance_score": round(1 - dist, 4),  # cosine: closer to 1 = more relevant
            })

        return chunks

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
