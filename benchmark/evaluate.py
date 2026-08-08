"""
Business Decision Copilot Benchmark Evaluator

Evaluates the Business Decision Copilot against the required
benchmark datasets.

Benchmark Categories
--------------------
1. RAG
2. Text2SQL
3. Hybrid
4. Refusal

Outputs
-------
- Routing Accuracy
- RAG Accuracy
- SQL Accuracy
- Hybrid Accuracy
- Refusal Accuracy
- Citation Coverage
- Overall Accuracy
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.request import BusinessRequest
from app.services.business_service import business_service


BENCHMARK_DIR = Path(__file__).parent


class BenchmarkEvaluator:

    def __init__(self) -> None:

        self.results: list[dict[str, Any]] = []

        self.metrics = {
            "rag": {"correct": 0, "total": 0},
            "sql": {"correct": 0, "total": 0},
            "hybrid": {"correct": 0, "total": 0},
            "refusal": {"correct": 0, "total": 0},
            "routing": {"correct": 0, "total": 0},
            "citations": {"correct": 0, "total": 0},
        }

    # -----------------------------------------------------

    def load_json(self, filename: str):

        path = BENCHMARK_DIR / filename

        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # -----------------------------------------------------

    def evaluate_file(
        self,
        filename: str,
        category: str,
    ) -> None:

        benchmark = self.load_json(filename)

        print(f"\nEvaluating {category.upper()}")

        for sample in benchmark:

            self.metrics[category]["total"] += 1
            self.metrics["routing"]["total"] += 1

            request = BusinessRequest(
                question=sample["question"]
            )

            response = business_service.ask(request.question)

            record = {
                "id": sample["id"],
                "question": sample["question"],
                "passed": False,
            }

            # -----------------------------
            # Routing
            # -----------------------------

            if response.query_type == category:

                self.metrics["routing"]["correct"] += 1

            # -----------------------------
            # Category checks
            # -----------------------------

            if category == "rag":

                passed = self._evaluate_rag(
                    response,
                    sample,
                )

            elif category == "sql":

                passed = self._evaluate_sql(
                    response,
                    sample,
                )

            elif category == "hybrid":

                passed = self._evaluate_hybrid(
                    response,
                    sample,
                )

            else:

                passed = self._evaluate_refusal(
                    response,
                    sample,
                )

            if passed:

                self.metrics[category]["correct"] += 1

            record["passed"] = passed

            self.results.append(record)

            print(
                f"{sample['id']} : "
                f"{'PASS' if passed else 'FAIL'}"
            )

    # -----------------------------------------------------

    def _evaluate_rag(
        self,
        response,
        sample,
    ) -> bool:

        expected = sample["expected_answer_contains"]

        answer = response.answer.lower()

        ok = all(
            keyword.lower() in answer
            for keyword in expected
        )

        if response.citations:

            self.metrics["citations"]["correct"] += 1

        self.metrics["citations"]["total"] += 1

        return ok

    # -----------------------------------------------------

    def _evaluate_sql(
        self,
        response,
        sample,
    ) -> bool:

        sql = response.generated_sql.upper()

        return all(
            keyword.upper() in sql
            for keyword in sample["expected_sql_contains"]
        )

    # -----------------------------------------------------

    def _evaluate_hybrid(
        self,
        response,
        sample,
    ) -> bool:

        text = response.answer.lower()

        return all(
            keyword.lower() in text
            for keyword in sample["expected_keywords"]
        )

    # -----------------------------------------------------

    def _evaluate_refusal(
        self,
        response,
        sample,
    ) -> bool:

        return response.refused

    # -----------------------------------------------------

    def report(self):

        print("\n")
        print("=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)

        for metric, values in self.metrics.items():

            total = values["total"]

            if total == 0:
                continue

            score = (
                values["correct"] / total
            ) * 100

            print(
                f"{metric.title():15}"
                f"{score:.1f}% "
                f"({values['correct']}/{total})"
            )

        total_tests = len(self.results)

        passed = sum(
            result["passed"]
            for result in self.results
        )

        overall = (passed / total_tests) * 100

        print("-" * 60)
        print(
            f"Overall Accuracy : {overall:.1f}%"
        )
        print("=" * 60)

    # -----------------------------------------------------

    def run(self):

        self.evaluate_file(
            "rag.json",
            "rag",
        )

        self.evaluate_file(
            "sql.json",
            "sql",
        )

        self.evaluate_file(
            "hybrid.json",
            "hybrid",
        )

        self.evaluate_file(
            "refusal.json",
            "refusal",
        )

        self.report()


# ---------------------------------------------------------


if __name__ == "__main__":

    BenchmarkEvaluator().run()