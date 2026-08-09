"""
Business Decision Copilot Benchmark Evaluator

Evaluates the Business Decision Copilot against the required
benchmark datasets.

Benchmark Categories
---------------------
1. RAG
2. Text2SQL
3. Hybrid
4. Refusal

Outputs
-------
- Routing Accuracy (measured independently)
- RAG Accuracy
- SQL Accuracy
- Hybrid Accuracy
- Refusal Accuracy
- Citation Coverage
- Overall Accuracy
- LLM Call Count
- Failure Classification
- Model/Application Success Rate
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.constants import QueryType
from app.models.request import BusinessRequest
from app.services.business_service import business_service
from app.services.router import router


BENCHMARK_DIR = Path(__file__).parent


class LLMCallTracker:
    """Benchmark-local LLM call counter.

    Temporarily monkeypatches the LLM singleton to count calls
    without changing production behavior.
    """

    def __init__(self) -> None:
        self.total = 0
        self.by_category: dict[str, int] = {}
        self._original_generate = None
        self._current_category = None

    def set_category(self, category: str) -> None:
        self._current_category = category

    def start(self) -> None:
        import app.utils.llm as llm_module

        self._original_generate = llm_module.llm.generate
        llm_module.llm.generate = self._counting_generate

    def stop(self) -> None:
        import app.utils.llm as llm_module

        if self._original_generate is not None:
            llm_module.llm.generate = self._original_generate

    def _counting_generate(self, prompt: str) -> str:
        self.total += 1
        if self._current_category is not None:
            key = self._current_category
            self.by_category[key] = self.by_category.get(key, 0) + 1
        return self._original_generate(prompt)


class BenchmarkEvaluator:

    FAILURE_TYPES = [
        "EXTERNAL_API_FAILURE",
        "MODEL_FAILURE",
        "PARSER_FAILURE",
        "APPLICATION_FAILURE",
    ]

    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []

        self.metrics = {
            "rag": {"correct": 0, "total": 0},
            "sql": {"correct": 0, "total": 0},
            "hybrid": {"correct": 0, "total": 0},
            "refusal": {"correct": 0, "total": 0},
            "citations": {"correct": 0, "total": 0},
        }

        self.routing = {
            "correct": 0,
            "total": 0,
            "unknown": 0,
        }

        self.failure_counts: dict[str, int] = {k: 0 for k in self.FAILURE_TYPES}

        self.llm_tracker = LLMCallTracker()
        self.failures: list[dict[str, Any]] = []

    # -----------------------------------------------------

    def load_json(self, filename: str):

        path = BENCHMARK_DIR / filename

        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # -----------------------------------------------------

    def _classify_exception(self, exc: Exception) -> tuple[str, str]:
        """Classify an exception into a benchmark failure type."""

        msg = str(exc)
        cause = exc.__cause__
        cause_type = type(cause).__name__ if cause else ""

        if "Connection error" in msg:
            return "EXTERNAL_API_FAILURE", msg
        if cause and isinstance(cause, (ConnectionError, OSError)):
            return "EXTERNAL_API_FAILURE", msg
        if "timeout" in msg.lower() or "timed out" in msg.lower():
            return "EXTERNAL_API_FAILURE", msg
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            return "EXTERNAL_API_FAILURE", msg
        if "rate limit" in msg.lower():
            return "EXTERNAL_API_FAILURE", msg

        if "Model returned an empty response" in msg:
            return "MODEL_FAILURE", msg

        if isinstance(exc, json.JSONDecodeError):
            return "PARSER_FAILURE", msg
        if "ParserError" in cause_type:
            return "PARSER_FAILURE", msg
        if "invalid JSON" in msg.lower() or "json" in msg.lower():
            return "PARSER_FAILURE", msg

        return "APPLICATION_FAILURE", msg

    # -----------------------------------------------------

    def evaluate_file(
        self,
        filename: str,
        category: str,
    ) -> None:

        benchmark = self.load_json(filename)

        print(f"\nEvaluating {category.upper()}")

        self.llm_tracker.set_category(category)

        for sample in benchmark:

            self.metrics[category]["total"] += 1
            self.routing["total"] += 1

            expected_route = category
            predicted_route = None
            routing_correct = False
            routing_unknown = False
            routing_error = None

            # Step 1: Evaluate routing independently
            try:
                decision = router.classify(sample["question"])
                predicted_route = decision.route.value
                routing_correct = predicted_route == expected_route
                if routing_correct:
                    self.routing["correct"] += 1

            except Exception as exc:
                routing_unknown = True
                self.routing["unknown"] += 1
                failure_type, routing_error = self._classify_exception(exc)
                self.failure_counts[failure_type] = (
                    self.failure_counts.get(failure_type, 0) + 1
                )

            # Step 2: Execute pipeline
            pipeline_passed = False
            pipeline_failure_type = None
            pipeline_error = None

            if routing_unknown:
                pipeline_passed = False
            else:
                try:
                    response = business_service.ask(sample["question"])

                    if category == "rag":
                        pipeline_passed = self._evaluate_rag(
                            response,
                            sample,
                        )

                    elif category == "sql":
                        pipeline_passed = self._evaluate_sql(
                            response,
                            sample,
                        )

                    elif category == "hybrid":
                        pipeline_passed = self._evaluate_hybrid(
                            response,
                            sample,
                        )

                    else:
                        pipeline_passed = self._evaluate_refusal(
                            response,
                            sample,
                        )

                    if pipeline_passed:
                        self.metrics[category]["correct"] += 1
                    else:
                        pipeline_failure_type = "MODEL_FAILURE"
                        self.failure_counts["MODEL_FAILURE"] = (
                            self.failure_counts.get("MODEL_FAILURE", 0) + 1
                        )
                        pipeline_error = self._describe_failure(
                            response, category, sample
                        )

                except Exception as exc:
                    pipeline_passed = False
                    pipeline_failure_type, pipeline_error = (
                        self._classify_exception(exc)
                    )
                    self.failure_counts[pipeline_failure_type] = (
                        self.failure_counts.get(pipeline_failure_type, 0) + 1
                    )

            passed = routing_correct and pipeline_passed

            record = {
                "id": sample["id"],
                "question": sample["question"],
                "expected_category": expected_route,
                "predicted_route": predicted_route,
                "routing_correct": routing_correct,
                "routing_unknown": routing_unknown,
                "routing_error": routing_error,
                "pipeline_passed": pipeline_passed,
                "pipeline_failure_type": pipeline_failure_type,
                "passed": passed,
                "error": pipeline_error if pipeline_error is not None else routing_error,
            }

            self.results.append(record)

            if not passed:
                self.failures.append(record)

            status = "PASS" if passed else "FAIL"
            if routing_unknown:
                status += " (router unknown)"
            elif not routing_correct:
                status += " (routing wrong)"
            elif not pipeline_passed:
                status += " (pipeline failed)"

            print(
                f"  {sample['id']} : "
                f"{status}"
            )

    # -----------------------------------------------------

    def _describe_failure(
        self,
        response,
        category: str,
        sample,
    ) -> str:
        """Return a short description of why a case failed."""

        if category == "rag":
            return (
                f"answer missing keywords: {sample['expected_answer_contains']}"
            )

        if category == "sql":
            sql = getattr(response, "generated_sql", None) or ""
            return (
                f"SQL missing keywords: {sample['expected_sql_contains']}; "
                f"got: {sql[:120]}"
            )

        if category == "hybrid":
            return (
                f"answer missing keywords: {sample['expected_keywords']}"
            )

        if category == "refusal":
            reason = getattr(response, "refusal_reason", None)
            return (
                f"expected refusal, got query_type={getattr(response, 'query_type', None)}, "
                f"refusal_reason={reason}"
            )

        return "unknown failure"

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

        sql = getattr(response, "generated_sql", None)

        if not sql:
            return False

        sql = sql.upper()

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

        return response.refusal_reason is not None

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

        routing_evaluable = self.routing["total"] - self.routing["unknown"]
        routing_accuracy = (
            (self.routing["correct"] / routing_evaluable) * 100
            if routing_evaluable > 0
            else None
        )

        external_api_failures = self.failure_counts["EXTERNAL_API_FAILURE"]
        eligible = total_tests - external_api_failures
        model_app_success_rate = (
            (passed / eligible) * 100
            if eligible > 0
            else None
        )

        print("-" * 60)
        print(
            f"Overall Accuracy  : {(passed / total_tests) * 100:.1f}% "
            f"({passed}/{total_tests})"
        )
        if routing_accuracy is not None:
            print(
                f"Routing Accuracy  : {routing_accuracy:.1f}% "
                f"({self.routing['correct']}/{routing_evaluable})"
            )
        else:
            print("Routing Accuracy  : N/A (no evaluable cases)")
        print(
            f"Routing Unknown    : {self.routing['unknown']}"
        )
        if model_app_success_rate is not None:
            print(
                f"Model/App Success  : {model_app_success_rate:.1f}% "
                f"({passed}/{eligible})"
            )
        else:
            print("Model/App Success  : N/A")
        print(
            f"Total LLM Calls   : {self.llm_tracker.total}"
        )
        print("=" * 60)

        if self.failures:
            print("\nFAILED CASES:")
            for failure in self.failures:
                detail = failure.get("error", "unknown")
                ftype = failure.get("pipeline_failure_type") or failure.get("routing_error", "unknown")
                print(f"  {failure['id']}: [{ftype}] {detail}")

    # -----------------------------------------------------

    def run(self):

        self.llm_tracker.start()

        try:
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
            self.save_results()

        finally:
            self.llm_tracker.stop()

    # -----------------------------------------------------

    def save_results(self) -> None:
        """Persist benchmark results to benchmark/results.json."""
        from datetime import datetime, timezone

        output_path = BENCHMARK_DIR / "results.json"

        total_tests = len(self.results)
        passed = sum(result["passed"] for result in self.results)

        routing_evaluable = self.routing["total"] - self.routing["unknown"]
        routing_accuracy = (
            (self.routing["correct"] / routing_evaluable) * 100
            if routing_evaluable > 0
            else None
        )

        external_api_failures = self.failure_counts["EXTERNAL_API_FAILURE"]
        eligible = total_tests - external_api_failures
        model_app_success_rate = (
            (passed / eligible) * 100
            if eligible > 0
            else None
        )

        payload = {
            "provider": "ZhipuAI",
            "model": "glm-4.5-flash",
            "benchmark_date": datetime.now(timezone.utc).isoformat(),
            "total_cases": total_tests,
            "passed": passed,
            "failed": total_tests - passed,
            "overall_accuracy": round((passed / total_tests) * 100, 2)
            if total_tests
            else 0.0,
            "routing": {
                "total": self.routing["total"],
                "correct": self.routing["correct"],
                "unknown": self.routing["unknown"],
                "accuracy": round(routing_accuracy, 2)
                if routing_accuracy is not None
                else None,
            },
            "model_application_success_rate": round(model_app_success_rate, 2)
            if model_app_success_rate is not None
            else None,
            "total_llm_calls": self.llm_tracker.total,
            "llm_calls_by_category": self.llm_tracker.by_category,
            "metrics": {
                metric: {
                    "correct": values["correct"],
                    "total": values["total"],
                    "accuracy": round(
                        (values["correct"] / values["total"]) * 100, 2
                    )
                    if values["total"]
                    else 0.0,
                }
                for metric, values in self.metrics.items()
            },
            "failure_counts": self.failure_counts,
            "failures": self.failures,
            "case_results": self.results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {output_path}")


# ---------------------------------------------------------


if __name__ == "__main__":

    BenchmarkEvaluator().run()
