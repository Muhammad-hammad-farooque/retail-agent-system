"""Tests for RAG pipeline — no OpenAI API calls, tests structure and FAQ content."""
import pytest
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
        from backend.rag.pipeline import RAGPipeline
        pipeline = RAGPipeline.__new__(RAGPipeline)
        assert hasattr(pipeline, "ingest_faq")
        assert hasattr(pipeline, "search")
        assert hasattr(pipeline, "build_context")

    def test_singleton_exists(self):
        from backend.rag.pipeline import rag_pipeline
        assert rag_pipeline is not None

    def test_build_context_empty_on_no_results(self):
        from unittest.mock import patch
        from backend.rag.pipeline import RAGPipeline

        pipeline = RAGPipeline()
        with patch.object(pipeline, "search", return_value=[]):
            result = pipeline.build_context("some query")
            assert result == ""

    def test_build_context_formats_correctly(self):
        from unittest.mock import patch
        from backend.rag.pipeline import RAGPipeline

        pipeline = RAGPipeline()
        mock_chunks = [
            {"content": "Q: Return policy?\nA: 7 days.", "category": "returns",
             "question": "Return policy?", "relevance_score": 0.95},
        ]
        with patch.object(pipeline, "search", return_value=mock_chunks):
            result = pipeline.build_context("return policy")
            assert "Relevant FAQ information" in result
            assert "Return policy?" in result
