"""
LLM Client

Centralized interface for interacting with the configured
Large Language Model (ZhipuAI GLM).

Responsibilities:
- Initialize the ZhipuAI client
- Standardize generation parameters
- Provide a reusable text generation interface
- Handle API errors consistently
"""

from __future__ import annotations

from zhipuai import ZhipuAI

from app.core.config import settings


class LLMClient:
    """
    Wrapper around the ZhipuAI SDK.

    All services should use this class instead of interacting
    with the SDK directly.
    """

    def __init__(self) -> None:
        self._client = None
        self.model = settings.ZHIPU_MODEL
        self.temperature = settings.TEMPERATURE
        self.max_output_tokens = settings.MAX_OUTPUT_TOKENS

    @property
    def client(self):
        if self._client is None:
            api_key = settings.ZHIPU_API_KEY
            if not api_key:
                raise RuntimeError(
                    "ZHIPU_API_KEY is not configured. "
                    "Set it in your environment or .env file."
                )
            self._client = ZhipuAI(api_key=api_key)
        return self._client

    def generate(self, prompt: str) -> str:
        """
        Generate a text response from the configured model.

        Args:
            prompt:
                Complete prompt sent to GLM.

        Returns:
            Generated response text.

        Raises:
            RuntimeError:
                If generation fails.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_output_tokens,
            )

            content = response.choices[0].message.content

            if not content:
                raise RuntimeError("Model returned an empty response.")

            return content.strip()

        except Exception as exc:
            raise RuntimeError(
                f"ZhipuAI generation failed: {exc}"
            ) from exc


# ---------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------

llm = LLMClient()