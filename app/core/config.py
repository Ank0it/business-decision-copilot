"""
Application Configuration

Centralized configuration management for the Business Decision Copilot.

Responsibilities:
- Load environment variables
- Validate required settings
- Expose typed configuration values
- Build commonly used paths

Python: 3.11+
"""

from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------

load_dotenv()


# ---------------------------------------------------------------------
# Project Paths
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
DOCUMENT_DIR = DATA_DIR / "documents"
CHROMA_DIR = DATA_DIR / "chroma"

DATABASE_DIR = BASE_DIR / "app" / "database"
DATABASE_PATH = DATABASE_DIR / "ecommerce.db"

PROMPT_DIR = BASE_DIR / "prompts"

LOG_DIR = BASE_DIR / "logs"


# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------


class Settings(BaseSettings):
    """
    Global application settings.

    Values are loaded from:
    1. .env
    2. System environment variables
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------------------------------------------------------
    # Application
    # ---------------------------------------------------------

    APP_NAME: str = "Business Decision Copilot"

    APP_VERSION: str = "1.0.0"

    DEBUG: bool = False

    HOST: str = "127.0.0.1"

    PORT: int = 8000

    # ---------------------------------------------------------
    # Gemini
    # ---------------------------------------------------------

    GEMINI_API_KEY: str = Field(...)

    GEMINI_MODEL: str = "gemini-2.5-flash"

    TEMPERATURE: float = 0.2

    MAX_OUTPUT_TOKENS: int = 2048

    # ---------------------------------------------------------
    # Embeddings
    # ---------------------------------------------------------

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    CHUNK_SIZE: int = 600

    CHUNK_OVERLAP: int = 120

    TOP_K: int = 4

    # ---------------------------------------------------------
    # Database
    # ---------------------------------------------------------

    DATABASE_URL: str = f"sqlite:///{DATABASE_PATH}"

    SQL_QUERY_TIMEOUT: int = 30

    # ---------------------------------------------------------
    # Retrieval
    # ---------------------------------------------------------

    RETRIEVAL_SCORE_THRESHOLD: float = 0.45

    # ---------------------------------------------------------
    # Logging
    # ---------------------------------------------------------

    LOG_LEVEL: str = "INFO"

    # ---------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------

    ENABLE_SQL_VALIDATION: bool = True

    ENABLE_CITATIONS: bool = True


# ---------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Prevents reloading environment variables throughout
    the application.
    """
    return Settings()


settings = get_settings()


# ---------------------------------------------------------------------
# Create Required Directories
# ---------------------------------------------------------------------

DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

CHROMA_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR.mkdir(parents=True, exist_ok=True)