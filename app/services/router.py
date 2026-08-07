"""
Query Router Service

Classifies incoming business questions into one of the
supported execution routes.

Routes:
- rag
- sql
- hybrid
- refusal
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.core.constants import QueryType
from app.core.prompts import prompts
from app.utils.llm import llm


# ==========================================================
# Router Result
# ==========================================================

@dataclass(slots=True)
class RoutingDecision:
    """
    Structured routing result.
    """

    route: QueryType

    reason: str


# ==========================================================
# Router
# ==========================================================

class QueryRouter:
    """
    Uses the LLM to determine the execution route
    for an incoming business question.
    """

    def __init__(self) -> None:
        self.router_prompt = prompts.router()

    def classify(self, question: str) -> RoutingDecision:
        """
        Classify an incoming question.

        Parameters
        ----------
        question:
            User's business question.

        Returns
        -------
        RoutingDecision
        """

        final_prompt = (
            f"{self.router_prompt}\n\n"
            "User Question:\n"
            f"{question}\n\n"
            "Return ONLY the JSON object."
        )

        response = llm.generate(final_prompt)

        return self._parse_response(response)

    # ------------------------------------------------------

    def _parse_response(self, response: str) -> RoutingDecision:
        """
        Parse and validate the router JSON.
        """

        try:
            data = json.loads(response)

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Router returned invalid JSON:\n{response}"
            ) from exc

        route = data.get("route")
        reason = data.get("reason")

        if route is None:
            raise ValueError("Router response missing 'route'.")

        if reason is None:
            raise ValueError("Router response missing 'reason'.")

        try:
            route = QueryType(route.lower())

        except ValueError as exc:
            raise ValueError(
                f"Unsupported route returned: {route}"
            ) from exc

        return RoutingDecision(
            route=route,
            reason=reason.strip(),
        )


# ==========================================================
# Singleton
# ==========================================================

router = QueryRouter()