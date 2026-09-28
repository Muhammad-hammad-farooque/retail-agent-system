"""Tests for the FAQ search pipeline (FastEmbed embeddings, pgvector or in-memory store)."""
import copy
import hashlib
import importlib.util
import re

import numpy as np
import pytest
from sqlalchemy import create_engine, text

from backend.rag import pipeline as P
from backend.rag.faq_documents import FAQ_DOCUMENTS


class TestFAQDocuments:

    def test_faq_count(self):
        assert len(FAQ_DOCUMENTS) >= 25, "Should have at least 25 FAQ documents"

    def test_faq_structure(self):
        required_keys = {"id", "question", "answer", "category"}
        for doc in FAQ_DOCUMENTS:
            assert required_keys.issubset(doc.keys()), f"Missing keys in {doc.get('id')}"

    def test_faq_ids_unique(self):
        ids = [doc["id"] for doc in FAQ_DOCUMENTS]
        assert len(ids) == len(set(ids)), "FAQ IDs must be unique"

    def test_faq_no_empty_answers(self):
        for doc in FAQ_DOCUMENTS:
            assert doc["answer"].strip(), f"Empty answer in {doc['id']}"

    def test_faq_no_empty_questions(self):
        for doc in FAQ_DOCUMENTS:
            assert doc["question"].strip(), f"Empty question in {doc['id']}"

    def test_faq_categories_valid(self):
        valid_categories = {
            "general", "returns", "payment", "delivery",
            "loyalty", "warranty", "complaints", "discounts", "account"
        }
        for doc in FAQ_DOCUMENTS:
            assert doc["category"] in valid_categories, f"Invalid category: {doc['category']} in {doc['id']}"

    def test_faq_covers_return_policy(self):
        questions = [d["question"].lower() for d in FAQ_DOCUMENTS]
        assert any("return" in q for q in questions)

    def test_faq_covers_loyalty(self):
        questions = [d["question"].lower() for d in FAQ_DOCUMENTS]
        assert any("loyalty" in q for q in questions)

    def test_faq_covers_delivery(self):
        questions = [d["question"].lower() for d in FAQ_DOCUMENTS]
        assert any("deliver" in q for q in questions)

    def test_faq_covers_warranty(self):
        questions = [d["question"].lower() for d in FAQ_DOCUMENTS]
        assert any("warrant" in q for q in questions)

    def test_faq_covers_payment(self):
        questions = [d["question"].lower() for d in FAQ_DOCUMENTS]
        assert any("payment" in q for q in questions)


class TestRAGPipelineStructure:

    def test_pipeline_has_required_methods(self):
        pipeline = P.RAGPipeline.__new__(P.RAGPipeline)
        assert hasattr(pipeline, "ingest_faq")
        assert hasattr(pipeline, "search")
        assert hasattr(pipeline, "build_context")

    def test_singleton_exists(self):
        assert P.rag_pipeline is not None

    def test_build_context_empty_on_no_results(self):
        from unittest.mock import patch

        pipeline = P.RAGPipeline()
        with patch.object(pipeline, "search", return_value=[]):
            assert pipeline.build_context("some query") == ""

    def test_build_context_formats_correctly(self):
        from unittest.mock import patch

        pipeline = P.RAGPipeline()
        mock_chunks = [
            {"content": "Q: Return policy?\nA: 7 days.", "category": "returns",
             "question": "Return policy?", "relevance_score": 0.95},
        ]
        with patch.object(pipeline, "search", return_value=mock_chunks):
            result = pipeline.build_context("return policy")
            assert "Relevant FAQ information" in result
            assert "Return policy?" in result


# ── Pipeline with a fake embedder (fast, no model download) ──────────────────

class FakeEmbedder:
    """Deterministic bag-of-words vectors: texts sharing words are similar."""

    def _vec(self, text_):
        v = np.zeros(P.EMBEDDING_DIM)
        for word in re.findall(r"[a-z]+", text_.lower()):
            v[int(hashlib.md5(word.encode()).hexdigest(), 16) % P.EMBEDDING_DIM] += 1
        return v / (np.linalg.norm(v) or 1)

    def passages(self, texts):
        return np.array([self._vec(t) for t in texts])

    def query(self, q):
        return self._vec(q)


@pytest.fixture
def sqlite_engine():
    return create_engine("sqlite://")


def test_falls_back_to_memory_without_pgvector(sqlite_engine):
    rag = P.RAGPipeline(engine=sqlite_engine, embedder=FakeEmbedder())
    assert rag.store_name == "memory"
    assert rag.last_embedded == len(FAQ_DOCUMENTS)


def test_pgvector_not_available_on_sqlite(sqlite_engine):
    assert P.PgVectorStore.available(sqlite_engine) is False


def test_search_returns_ranked_chunks(sqlite_engine):
    rag = P.RAGPipeline(engine=sqlite_engine, embedder=FakeEmbedder())
    # The fake embedder only counts words, so query with the FAQ's own text
    chunks = rag.search(P._document_text(FAQ_DOCUMENTS[1]), top_k=3)
    assert len(chunks) == 3
    assert chunks[0]["question"] == "What is the return policy?"
    assert chunks[0]["category"] == "returns"
    assert chunks[0]["content"].startswith("Q: What is the return policy?")
    scores = [c["relevance_score"] for c in chunks]
    assert scores == sorted(scores, reverse=True)


def test_ingest_does_not_re_embed_unless_forced(sqlite_engine):
    rag = P.RAGPipeline(engine=sqlite_engine, embedder=FakeEmbedder())
    assert rag.ingest_faq() == len(FAQ_DOCUMENTS)
    assert rag.ingest_faq() == 0
    assert rag.ingest_faq(force=True) == len(FAQ_DOCUMENTS)


def test_content_hash_tracks_text_and_model(monkeypatch):
    doc = dict(FAQ_DOCUMENTS[0])
    original = P._content_hash(doc)
    assert P._content_hash(dict(doc, answer=doc["answer"] + "!")) != original
    monkeypatch.setattr(P, "EMBEDDING_MODEL", "another/model")
    assert P._content_hash(doc) != original


def test_pgvector_literal_format():
    assert P._to_pgvector([0.5, -0.25]) == "[0.5000000,-0.2500000]"


# ── search_faq tool ──────────────────────────────────────────────────────────

def test_search_faq_reports_failures_plainly(monkeypatch):
    from tests.helpers import call_tool
    from backend.tools import customer_tools

    def broken(*args, **kwargs):
        raise RuntimeError("model missing")

    monkeypatch.setattr(customer_tools.rag_pipeline, "search", broken)
    result = call_tool(customer_tools.search_faq, "return policy")
    assert "FAQ SEARCH UNAVAILABLE" in result
    assert "do not guess" in result


def test_search_faq_formats_results(monkeypatch):
    from tests.helpers import call_tool
    from backend.tools import customer_tools

    monkeypatch.setattr(customer_tools.rag_pipeline, "search", lambda q, top_k=3: [
        {"content": "Q: What is the return policy?\nA: 7 days.", "category": "returns",
         "question": "What is the return policy?", "relevance_score": 0.79},
    ])
    result = call_tool(customer_tools.search_faq, "return policy")
    assert "FAQ Results for: 'return policy'" in result
    assert "(relevance: 0.79)" in result
    assert "7 days" in result


# ── Real model: retrieval quality (downloads ~67 MB once) ────────────────────

# Worded differently from the FAQs on purpose. The agent writes FAQ queries in
# English (see customer_service_agent), so Roman Urdu isn't expected here.
QUALITY_SET = [
    ("can I give back something I bought last week?", "faq_002"),
    ("I want to swap my shirt for a bigger size", "faq_003"),
    ("do you take JazzCash or credit cards?", "faq_004"),
    ("will you bring my order to my house?", "faq_005"),
    ("how do I earn points when I shop?", "faq_006"),
    ("how can I use my points for a discount?", "faq_007"),
    ("my TV stopped working after 3 months, is it covered?", "faq_008"),
    ("where is my parcel?", "faq_010"),
    ("when will I get my money back?", "faq_012"),
    ("I'm a university student, any discount?", "faq_013"),
    ("the product arrived broken", "faq_016"),
    ("can you pay in monthly installments?", "faq_019"),
    ("I left my loyalty card at home", "faq_021"),
    ("what time do you open on sunday?", "faq_001"),
    ("can I hold an item and pick it up later?", "faq_023"),
    ("do you handle orders for companies?", "faq_028"),
    ("return policy", "faq_002"),
    ("warranty on electronic items", "faq_008"),
    ("how to register a complaint", "faq_015"),
]


@pytest.fixture(scope="module")
def real_rag():
    return P.RAGPipeline(engine=create_engine("sqlite://"))


def test_real_model_finds_the_right_faq(real_rag):
    ids = {d["question"]: d["id"] for d in FAQ_DOCUMENTS}
    misses = []
    for query, want in QUALITY_SET:
        got = [ids[c["question"]] for c in real_rag.search(query, top_k=3)]
        if want not in got:
            misses.append(f"{query!r}: want {want}, got {got}")
    # search_faq passes the top 3 to the agent, so that's what has to contain the answer
    assert len(misses) <= 1, "\n".join(misses)


# ── Real pgvector (runs when the optional `pgserver` package is installed) ───

@pytest.mark.skipif(importlib.util.find_spec("pgserver") is None,
                    reason="pip install pgserver to run against a real Postgres with pgvector")
def test_pgvector_store_end_to_end(tmp_path):
    import pgserver
    server = pgserver.get_server(str(tmp_path), cleanup_mode="stop")
    try:
        engine = create_engine(server.get_uri())
        embedder = FakeEmbedder()
        rag = P.RAGPipeline(engine=engine, embedder=embedder)
        assert rag.store_name == "pgvector"
        assert rag.last_embedded == len(FAQ_DOCUMENTS)

        # A redeploy (new pipeline, same database) embeds nothing
        assert P.RAGPipeline(engine=engine, embedder=embedder).last_embedded == 0

        # Editing one FAQ and removing another touches only those
        docs = copy.deepcopy(FAQ_DOCUMENTS)
        docs[1]["answer"] += " Accessories must be included."
        del docs[-1]
        store = P.PgVectorStore(engine)
        assert store.sync(docs, embedder) == 1
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM faq_embeddings")).scalar() == len(docs)

        # Same ranking as the in-memory store
        memory = P.MemoryStore()
        memory.sync(docs, embedder)
        q = embedder.query("What is the return policy?")
        assert [r["doc"]["id"] for r in store.search(q, 3)] == [r["doc"]["id"] for r in memory.search(q, 3)]
    finally:
        server.cleanup()
