"""
Zero to GEO — Application Configuration

Pillar weights and all tunable parameters live here.
Change weights in one place; the scoring engine picks them up automatically.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    # ---- Application ----
    app_name: str = "Zero to GEO"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_debug: bool = True

    # ---- Server ----
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # ---- Database ----
    database_url: str = "sqlite:///./zero_to_geo.db"

    # ---- CORS ----
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    # ---- Crawling ----
    crawl_timeout_seconds: int = 15
    crawl_max_pages: int = 5
    crawl_respect_robots: bool = True
    crawl_user_agent: str = "ZeroToGEO/0.1 (+https://zerotogeo.com/bot)"

    # ---- Optional LLM (not required for MVP) ----
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # ---- Security ----
    secret_key: str = "change-this-in-production"

    model_config = {"env_file": ".env", "extra": "ignore"}


class ScoringWeights:
    """
    GEO pillar weights. Must sum to 1.0.
    Stored here so they can be adjusted without touching analysis code.
    """

    ENTITY_CLARITY: float = 0.15
    LOCAL_SIGNALS: float = 0.15
    STRUCTURED_DATA: float = 0.15
    CONTENT: float = 0.20
    AUTHORITY: float = 0.15
    CITATION_READINESS: float = 0.20

    @classmethod
    def as_dict(cls) -> dict:
        return {
            "entity_clarity": cls.ENTITY_CLARITY,
            "local_signals": cls.LOCAL_SIGNALS,
            "structured_data": cls.STRUCTURED_DATA,
            "content": cls.CONTENT,
            "authority": cls.AUTHORITY,
            "citation_readiness": cls.CITATION_READINESS,
        }

    @classmethod
    def validate(cls) -> None:
        total = sum(cls.as_dict().values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"ScoringWeights must sum to 1.0, got {total:.4f}"
            )


class GeoScoreClassification:
    """GEO score classification thresholds."""

    THRESHOLDS = [
        (90, 100, "Excellent"),
        (75, 89, "Strong"),
        (60, 74, "Good Foundation"),
        (40, 59, "Needs Work"),
        (0, 39, "Poor"),
    ]

    @classmethod
    def classify(cls, score: float) -> str:
        for low, high, label in cls.THRESHOLDS:
            if low <= round(score) <= high:
                return label
        return "Unknown"


# Validate weights at import time so misconfiguration fails fast.
ScoringWeights.validate()

settings = Settings()
