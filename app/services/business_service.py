"""
Business Service

Central orchestration layer for the Business Decision Copilot.

Responsibilities:
- Route incoming business questions.
- Execute the correct pipeline.
- Return a unified BusinessResponse.
"""

from __future__ import annotations

from app.core.constants import ConfidenceLevel, QueryType
from app.models.response import (
    BusinessInsight,
    BusinessResponse,
    Citation,
)
from app.models.sql import SQLValidationResult
from app.services.hybrid import hybrid_service
from app.services.rag import rag_service
from app.services.refusal import refusal_service
from app.services.router import router
from app.services.sql_executor import sql_executor
from app.services.sql_generator import sql_generator
from app.services.sql_validator import sql_validator


class BusinessService:
    """
    Coordinates all business intelligence pipelines.
    """

    def ask(self, question: str) -> BusinessResponse:
        """
        Process a business question.

        Parameters
        ----------
        question:
            Natural language business question.

        Returns
        -------
        BusinessResponse
        """

        decision = router.classify(question)

        if decision.route is QueryType.RAG:
            return self._handle_rag(question)

        if decision.route is QueryType.SQL:
            return self._handle_sql(question)

        if decision.route is QueryType.HYBRID:
            return self._handle_hybrid(question)

        return self._handle_refusal(decision.reason)

    # ---------------------------------------------------------
    # RAG Pipeline
    # ---------------------------------------------------------

    def _handle_rag(self, question: str) -> BusinessResponse:
        """
        Execute the RAG pipeline and normalize the result.
        """

        result = rag_service.answer(question)

        if result.get("refuse"):
            return BusinessResponse(
                query_type=QueryType.RAG,
                answer="I cannot answer this question based on available documents.",
                refusal_reason=result.get("reason"),
                confidence=ConfidenceLevel.LOW,
                confidence_notes="No relevant documents found.",
            )

        citations = self._build_citations(result.get("citations", []))

        return BusinessResponse(
            query_type=QueryType.RAG,
            answer=result.get("answer", ""),
            citations=citations,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_notes=result.get("confidence_notes"),
        )

    # ---------------------------------------------------------
    # SQL Pipeline
    # ---------------------------------------------------------

    def _handle_sql(self, question: str) -> BusinessResponse:
        """
        Execute the Text2SQL pipeline and normalize the result.
        """

        generated = sql_generator.generate(question)

        if hasattr(generated, "refuse") and generated.refuse:
            return BusinessResponse(
                query_type=QueryType.SQL,
                answer="I cannot generate SQL for this request.",
                refusal_reason=generated.reason,
                confidence=ConfidenceLevel.LOW,
                confidence_notes="SQL generation refused.",
            )

        validation = sql_validator.validate(generated.sql)

        if not validation.valid:
            return BusinessResponse(
                query_type=QueryType.SQL,
                answer="The generated SQL did not pass safety validation.",
                generated_sql=generated.sql,
                sql_validation=validation,
                refusal_reason=validation.reason,
                confidence=ConfidenceLevel.LOW,
                confidence_notes="SQL validation failed.",
            )

        execution = sql_executor.execute(generated.sql)

        answer = (
            f"Query returned {execution.row_count} rows."
            if execution.row_count > 0
            else "Query executed successfully but returned no rows."
        )

        return BusinessResponse(
            query_type=QueryType.SQL,
            answer=answer,
            generated_sql=generated.sql,
            sql_validation=validation,
            sql_result=execution,
            confidence=ConfidenceLevel.HIGH,
            confidence_notes="SQL executed successfully against the database.",
        )

    # ---------------------------------------------------------
    # Hybrid Pipeline
    # ---------------------------------------------------------

    def _handle_hybrid(self, question: str) -> BusinessResponse:
        """
        Execute the Hybrid pipeline and normalize the result.
        """

        result = hybrid_service.answer(question)

        if result.get("refuse"):
            return BusinessResponse(
                query_type=QueryType.HYBRID,
                answer="I cannot provide a recommendation for this request.",
                refusal_reason=result.get("reason"),
                confidence=ConfidenceLevel.LOW,
                confidence_notes="Hybrid pipeline refused.",
            )

        insight = BusinessInsight(
            policy_summary=result.get("policy_summary"),
            data_summary=result.get("data_summary"),
            recommendation=result.get("recommendation"),
            next_steps=result.get("next_steps", []),
        )

        return BusinessResponse(
            query_type=QueryType.HYBRID,
            answer=result.get("recommendation", ""),
            business_insight=insight,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_notes=result.get("confidence_notes"),
        )

    # ---------------------------------------------------------
    # Refusal
    # ---------------------------------------------------------

    def _handle_refusal(self, reason: str) -> BusinessResponse:
        """
        Build a refusal response.
        """

        return BusinessResponse(
            query_type=QueryType.REFUSAL,
            answer="I cannot process this request.",
            refusal_reason=reason,
            confidence=ConfidenceLevel.LOW,
            confidence_notes="Request refused by routing policy.",
        )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _build_citations(
        raw_citations: list[object],
    ) -> list[Citation]:
        """
        Normalize citations from RAG/LLM output into Citation models.
        """

        citations: list[Citation] = []

        for item in raw_citations:
            if isinstance(item, dict):
                citations.append(
                    Citation(
                        source=item.get("source", "unknown"),
                        chunk_id=item.get("chunk_id"),
                        score=item.get("score"),
                    )
                )
            elif isinstance(item, str):
                citations.append(
                    Citation(
                        source=item,
                        chunk_id=None,
                        score=None,
                    )
                )

        return citations


business_service = BusinessService()