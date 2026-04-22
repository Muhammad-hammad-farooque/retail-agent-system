"""Evaluation framework — runs test cases and scores agent/guardrail performance."""
import time
from dataclasses import dataclass, field
from typing import List, Optional
from .test_cases import INPUT_GUARDRAIL_CASES, OUTPUT_GUARDRAIL_CASES, RAG_QUALITY_CASES


@dataclass
class EvalResult:
    test_id: str
    category: str
    input: str
    expected: str
    actual: str
    passed: bool
    latency_ms: float = 0.0
    notes: str = ""


@dataclass
class EvalReport:
    results: List[EvalResult] = field(default_factory=list)

    @property
    def total(self): return len(self.results)

    @property
    def passed(self): return sum(1 for r in self.results if r.passed)

    @property
    def failed(self): return self.total - self.passed

    @property
    def score(self): return (self.passed / self.total * 100) if self.total else 0

    def by_category(self):
        cats = {}
        for r in self.results:
            cats.setdefault(r.category, []).append(r)
        return cats

    def print_summary(self):
        print("\n" + "=" * 60)
        print("EVALUATION REPORT")
        print("=" * 60)
        print(f"Total Tests : {self.total}")
        print(f"Passed      : {self.passed}")
        print(f"Failed      : {self.failed}")
        print(f"Score       : {self.score:.1f}%")
        print("\nBy Category:")
        for cat, results in self.by_category().items():
            cat_passed = sum(1 for r in results if r.passed)
            print(f"  {cat:<30} {cat_passed}/{len(results)}")
        if self.failed > 0:
            print("\nFailed Tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  [{r.test_id}] {r.input[:50]}")
                    print(f"    Expected: {r.expected}")
                    print(f"    Actual  : {r.actual}")
        print("=" * 60)


class GuardrailEvaluator:

    def run(self) -> EvalReport:
        report = EvalReport()
        report.results.extend(self._eval_input_guardrails())
        report.results.extend(self._eval_output_guardrails())
        return report

    def _eval_input_guardrails(self) -> List[EvalResult]:
        from backend.guardrails.input_guardrails import check_input
        results = []
        for i, (query, should_pass) in enumerate(INPUT_GUARDRAIL_CASES):
            start = time.perf_counter()
            result = check_input(query)
            latency = (time.perf_counter() - start) * 1000
            passed = result["allowed"] == should_pass
            results.append(EvalResult(
                test_id=f"INPUT-{i+1:02d}",
                category="input_guardrail",
                input=query,
                expected="PASS" if should_pass else "BLOCK",
                actual="PASS" if result["allowed"] else f"BLOCK: {result['reason'][:40]}",
                passed=passed,
                latency_ms=round(latency, 2),
            ))
        return results

    def _eval_output_guardrails(self) -> List[EvalResult]:
        from backend.guardrails.output_guardrails import check_output
        results = []
        for i, (response, expect_approval, expect_block, expect_mask) in enumerate(OUTPUT_GUARDRAIL_CASES):
            start = time.perf_counter()
            result = check_output(response)
            latency = (time.perf_counter() - start) * 1000

            approval_ok = result["requires_approval"] == expect_approval
            block_ok = result["blocked"] == expect_block
            mask_ok = (result["response"] != response) == expect_mask
            passed = approval_ok and block_ok and mask_ok

            results.append(EvalResult(
                test_id=f"OUTPUT-{i+1:02d}",
                category="output_guardrail",
                input=response[:50],
                expected=f"approval={expect_approval} block={expect_block} mask={expect_mask}",
                actual=f"approval={result['requires_approval']} block={result['blocked']} mask={result['response'] != response}",
                passed=passed,
                latency_ms=round(latency, 2),
            ))
        return results


class RAGEvaluator:

    def run(self) -> EvalReport:
        from backend.rag.pipeline import rag_pipeline
        from backend.rag.faq_documents import FAQ_DOCUMENTS
        report = EvalReport()

        # Test 1: FAQ document count
        count_ok = len(FAQ_DOCUMENTS) >= 25
        report.results.append(EvalResult(
            test_id="RAG-01",
            category="rag_pipeline",
            input="FAQ document count",
            expected=">=25",
            actual=str(len(FAQ_DOCUMENTS)),
            passed=count_ok,
        ))

        # Test 2: All required categories present
        cats = {d["category"] for d in FAQ_DOCUMENTS}
        required = {"returns", "payment", "delivery", "loyalty", "warranty"}
        missing = required - cats
        report.results.append(EvalResult(
            test_id="RAG-02",
            category="rag_pipeline",
            input="FAQ category coverage",
            expected=str(required),
            actual=str(cats),
            passed=len(missing) == 0,
            notes=f"Missing: {missing}" if missing else "",
        ))

        # Test 3: build_context returns non-empty string for retail queries
        from unittest.mock import patch
        mock_chunk = [{"content": "Q: Test\nA: Answer", "category": "general",
                       "question": "Test", "relevance_score": 0.9}]
        with patch.object(rag_pipeline, "search", return_value=mock_chunk):
            ctx = rag_pipeline.build_context("test query")
            report.results.append(EvalResult(
                test_id="RAG-03",
                category="rag_pipeline",
                input="build_context output",
                expected="non-empty string with 'Relevant FAQ'",
                actual=ctx[:60] if ctx else "EMPTY",
                passed=bool(ctx) and "Relevant FAQ" in ctx,
            ))

        # Test 4: build_context returns empty for no results
        with patch.object(rag_pipeline, "search", return_value=[]):
            ctx = rag_pipeline.build_context("gibberish query xyz")
            report.results.append(EvalResult(
                test_id="RAG-04",
                category="rag_pipeline",
                input="build_context with no results",
                expected="empty string",
                actual=repr(ctx),
                passed=ctx == "",
            ))

        return report


class FullEvaluator:
    """Run all evaluators and produce a combined report."""

    def run(self) -> EvalReport:
        print("Running guardrail evaluation...")
        guardrail_report = GuardrailEvaluator().run()

        print("Running RAG evaluation...")
        rag_report = RAGEvaluator().run()

        combined = EvalReport()
        combined.results = guardrail_report.results + rag_report.results
        return combined
