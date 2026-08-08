"""
Parser Utilities

Provides helper functions for safely parsing and validating
JSON responses returned by the LLM.

Responsibilities:
- Parse JSON returned by Gemini
- Validate required fields
- Raise consistent exceptions
"""

from __future__ import annotations

import json
from typing import Any


class ParserError(ValueError):
    """
    Raised when an LLM response cannot be parsed or validated.
    """


class JSONParser:
    """
    Utility class for parsing LLM JSON responses.
    """

    @staticmethod
    def parse_json(response: str) -> dict[str, Any]:
        """
        Parse a JSON string into a Python dictionary.

        Args:
            response:
                Raw LLM response.

        Returns:
            Parsed dictionary.

        Raises:
            ParserError:
                If the response is not valid JSON.
        """

        if not response or not response.strip():
            raise ParserError("Received an empty response from the LLM.")

        try:
            data = json.loads(response)

        except json.JSONDecodeError as exc:
            raise ParserError(
                f"Invalid JSON returned by the LLM:\n{response}"
            ) from exc

        if not isinstance(data, dict):
            raise ParserError(
                "Expected a JSON object as the top-level response."
            )

        return data

    @staticmethod
    def require_fields(
        data: dict[str, Any],
        required_fields: list[str],
    ) -> None:
        """
        Validate that all required fields exist.

        Args:
            data:
                Parsed JSON dictionary.

            required_fields:
                List of required keys.

        Raises:
            ParserError:
                If one or more required fields are missing.
        """

        missing = [
            field
            for field in required_fields
            if field not in data
        ]

        if missing:
            raise ParserError(
                f"Missing required field(s): {', '.join(missing)}"
            )

    @staticmethod
    def validate_allowed_keys(
        data: dict[str, Any],
        allowed_keys: list[str],
    ) -> None:
        """
        Ensure no unexpected keys are returned.

        Args:
            data:
                Parsed JSON dictionary.

            allowed_keys:
                Allowed JSON keys.

        Raises:
            ParserError:
                If unexpected keys are found.
        """

        unexpected = [
            key
            for key in data.keys()
            if key not in allowed_keys
        ]

        if unexpected:
            raise ParserError(
                "Unexpected field(s): "
                + ", ".join(unexpected)
            )

    @staticmethod
    def parse_and_validate(
        response: str,
        required_fields: list[str],
        allowed_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Parse JSON and validate required/allowed fields.

        Args:
            response:
                Raw LLM response.

            required_fields:
                Required keys.

            allowed_keys:
                Optional whitelist of allowed keys.

        Returns:
            Validated dictionary.
        """

        data = JSONParser.parse_json(response)

        JSONParser.require_fields(
            data,
            required_fields,
        )

        if allowed_keys is not None:
            JSONParser.validate_allowed_keys(
                data,
                allowed_keys,
            )

        return data


# ==========================================================
# Singleton
# ==========================================================

parser = JSONParser()