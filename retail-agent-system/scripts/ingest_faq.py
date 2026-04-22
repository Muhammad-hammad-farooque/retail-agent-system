"""Ingest FAQ documents into ChromaDB. Run once after setting OPENAI_API_KEY."""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backend.rag.pipeline import rag_pipeline
from backend.rag.faq_documents import FAQ_DOCUMENTS


def main():
    print(f"Ingesting {len(FAQ_DOCUMENTS)} FAQ documents into ChromaDB...")
    count = rag_pipeline.ingest_faq(force=True)
    print(f"Ingested {count} documents.")

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
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Set OPENAI_API_KEY in .env before running this script.")
        sys.exit(1)
    main()
