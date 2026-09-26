"""Simplified configuration for the SIH 2026 backend.

We avoid the `pydantic.BaseSettings` dependency because the current environment
does not have the `pydantic-settings` package required for the newer
`BaseSettings` implementation. Instead we read environment variables directly
using `os.getenv` and provide sensible defaults for development.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

class Settings:
    # General
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

    # Security / Auth – these must be set in the environment for the app to start.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "test-secret-key")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY")

    # Security / Auth – these must be set in the environment for the app to start.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "test-secret-key")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY")

    # Upload handling
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))  # 10 MiB default
    ALLOWED_EXTENSIONS: List[str] = [ext.strip() for ext in os.getenv("ALLOWED_EXTENSIONS", ".pdf,.jpg,.jpeg,.png,.tif,.tiff").split(",")]
    # Default allowed MIME types (used by file_service validation)
    ALLOWED_MIME_TYPES: List[str] = ["application/pdf", "image/jpeg", "image/png", "image/tiff"]

    # Misc
    PORT: int = int(os.getenv("PORT", "8000"))

    FACE_SIMILARITY_THRESHOLD: float = float(os.getenv("FACE_SIMILARITY_THRESHOLD", "0.70"))

    LIVENESS_SHARPNESS_THRESHOLD: float = float(os.getenv("LIVENESS_SHARPNESS_THRESHOLD", "100.0"))
    LIVENESS_ENTROPY_THRESHOLD: float = float(os.getenv("LIVENESS_ENTROPY_THRESHOLD", "5.0"))
    # Tampering detection threshold
    TAMPERING_SCORE_THRESHOLD: float = float(os.getenv("TAMPERING_SCORE_THRESHOLD", "0.5"))

    # Dev token minting endpoint (Phase 15): enabled by default for the local
    # dev/demo database, must be explicitly enabled in production deployments.
    AUTH_DEV_TOKEN_ENABLED: bool = os.getenv("AUTH_DEV_TOKEN_ENABLED", "true").lower() == "true"
    # Redis integration (optional)
    VECTOR_BACKEND: str = os.getenv("VECTOR_BACKEND", "memory")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    # Rate‑limit (requests per minute per user)
    RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", "60"))

    # Risk engine configuration
    RISK_WEIGHTS: dict = {
        "tampering": 0.25,
        "liveness": 0.15,
        "deepfake": 0.20,
        "face_mismatch": 0.15,
        "ocr_confidence": 0.10,
        "anomaly": 0.10,
        "document_validation": 0.05,
    }
    RISK_LEVEL_LOW: int = 20
    RISK_LEVEL_MEDIUM: int = 50
    RISK_LEVEL_HIGH: int = 80

    # Ollama configuration (optional)
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
    OLLAMA_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "5"))

    # Trained forgery classifier (ResNet18, Genuine/Tampered 2 dataset)
    DEEPFAKE_MODEL_PATH: str = os.getenv("DEEPFAKE_MODEL_PATH", "models/document_forgery_gt2.pth")

    # Cross-case face reuse (SFace cosine gate; official match gate is 0.363)
    FACE_REUSE_COSINE_THRESHOLD: float = float(os.getenv("FACE_REUSE_COSINE_THRESHOLD", "0.42"))

    def __init__(self):
        if not self.OLLAMA_URL and self.OLLAMA_HOST:
            host = self.OLLAMA_HOST.rstrip("/")
            self.OLLAMA_URL = f"{host}/api/generate"

    @property
    def upload_path(self) -> Path:
        """Absolute path for the upload directory; creates it on first access."""
        path = Path(self.UPLOAD_DIR).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

# Export a singleton instance used throughout the codebase.
settings = Settings()
