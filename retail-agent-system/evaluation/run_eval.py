"""Run the full evaluation suite. Usage: python -m evaluation.run_eval"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from evaluation.evaluator import FullEvaluator


def main():
    print("=" * 60)
    print("RETAIL AGENT SYSTEM — EVALUATION SUITE")
    print("=" * 60)
    evaluator = FullEvaluator()
    report = evaluator.run()
    report.print_summary()
    # Exit with error code if score < 80%
    sys.exit(0 if report.score >= 80 else 1)


if __name__ == "__main__":
    main()
