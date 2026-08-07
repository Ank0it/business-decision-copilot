"""
LLM Client

Centralized interface for interacting with the configured
Large Language Model (Google Gemini).

Responsibilities:
- Initialize the Gemini client
- Standardize generation parameters
- Provide a reusable text generation interface
- Handle API errors consistently
"""

from __future__ import annotations

from google import genai
from google.genai import types

from app.core.config import settings


class LLMClient:
    """
    Wrapper around the Google GenAI SDK.

    All services should use this class instead of interacting
    with the SDK directly.
    """

    def __init__(self) -> None:
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

        self.model = settings.GEMINI_MODEL

        self.generation_config = types.GenerateContentConfig(
            temperature=settings.TEMPERATURE,
            max_output_tokens=settings.MAX_OUTPUT_TOKENS,
        )

    def generate(self, prompt: str) -> str:
        """
        Generate a text response from the configured model.

        Args:
            prompt:
                Complete prompt sent to Gemini.

        Returns:
            Generated response text.

        Raises:
            RuntimeError:
                If generation fails.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self.generation_config,
            )

            if not response.text:
                raise RuntimeError("Model returned an empty response.")

            return response.text.strip()

        except Exception as exc:
            raise RuntimeError(
                f"LLM generation failed: {exc}"
            ) from exc


# ---------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------

llm = LLMClient()