"""Embed the FAQ documents and test a few searches.

Optional: the backend embeds FAQs automatically on the first search. Useful to
warm up the store (pgvector when the database has it, otherwise in memory) or to
check retrieval after editing faq_documents.py. Needs no API key.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backend.rag.pipeline import rag_pipeline
from backend.rag.faq_documents import FAQ_DOCUMENTS


def main():
    print(f"Embedding {len(FAQ_DOCUMENTS)} FAQ documents...")
    count = rag_pipeline.ingest_faq(force=True)
    print(f"Store: {rag_pipeline.store_name}; embedded {count} documents now "
          "(pgvector only re-embeds new or changed FAQs).")

    # Test a sample search
    print("\nTesting search: 'return policy'")
    results = rag_pipeline.search("return policy", top_k=3)
    for r in results:
        print(f"  [{r['relevance_score']:.2f}] {r['question']}")

    print("\nTesting search: 'loyalty points'")
    results = rag_pipeline.search("loyalty points how to use", top_k=3)
    for r in results:
        print(f"  [{r['relevance_score']:.2f}] {r['question']}")

    print("\nFAQ ingestion complete!")


if __name__ == "__main__":
    main()
