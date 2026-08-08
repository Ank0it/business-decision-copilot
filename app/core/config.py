"""
Application configuration.

All environment-sensitive configuration is centralized here.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root:
# business-decision-copilot/
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------------------------------------------------------
    # Application
    # ---------------------------------------------------------

    APP_NAME: str = "Business Decision Copilot"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # ---------------------------------------------------------
    # LLM
    # ---------------------------------------------------------

    ZHIPU_API_KEY: str = ""
    ZHIPU_MODEL: str = "glm-4.5-flash"
    TEMPERATURE: float = 0.1
    MAX_OUTPUT_TOKENS: int = 2048

    # ---------------------------------------------------------
    # Database
    # ---------------------------------------------------------

    DATABASE_PATH: Path = BASE_DIR / "app" / "database" / "ecommerce.db"

    # ---------------------------------------------------------
    # Dataset
    # ---------------------------------------------------------

    DATASET_PATH: Path = BASE_DIR / "data" / "dataset"

    # ---------------------------------------------------------
    # Documents
    # ---------------------------------------------------------

    DOCUMENTS_PATH: Path = BASE_DIR / "data" / "documents"

    # ---------------------------------------------------------
    # Prompts
    # ---------------------------------------------------------

    PROMPT_DIR: Path = BASE_DIR / "prompts"

    # ---------------------------------------------------------
    # Vector database
    # ---------------------------------------------------------

    CHROMA_DIR: Path = BASE_DIR / "data" / "chroma"

    CHROMA_COLLECTION: str = "business_documents"

    # ---------------------------------------------------------
    # Retrieval
    # ---------------------------------------------------------

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    RETRIEVAL_TOP_K: int = 3

    # Chroma returns distances.
    # Lower distance = better match.
    RETRIEVAL_DISTANCE_THRESHOLD: float = 0.75

    # ---------------------------------------------------------
    # SQL
    # ---------------------------------------------------------

    SQL_QUERY_TIMEOUT: int = 30

    # ---------------------------------------------------------
    # CORS
    # ---------------------------------------------------------

    ALLOW_ORIGINS: str = "*"


settings = Settings()