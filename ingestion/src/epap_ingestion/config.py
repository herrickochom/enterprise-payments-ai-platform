"""Environment-driven configuration for the ingestion services.

All connection values are read from environment variables (or a `.env` file
loaded via python-dotenv). Host-side processes target MinIO on localhost;
in-network Docker containers use the internal service name (`minio:9000`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


# --- Medallion bucket names (DNS-compatible, prefixed with epap-) ------------
RAW_BUCKET = "epap-raw"
STAGING_BUCKET = "epap-staging"
BRONZE_BUCKET = "epap-bronze"
SILVER_BUCKET = "epap-silver"
GOLD_BUCKET = "epap-gold"
DATA_PRODUCTS_BUCKET = "epap-data-products"
ARCHIVE_BUCKET = "epap-archive"
AI_INTELLIGENCE_BUCKET = "epap-ai-intelligence"

ALL_BUCKETS: tuple[str, ...] = (
    RAW_BUCKET,
    STAGING_BUCKET,
    BRONZE_BUCKET,
    SILVER_BUCKET,
    GOLD_BUCKET,
    DATA_PRODUCTS_BUCKET,
    ARCHIVE_BUCKET,
    AI_INTELLIGENCE_BUCKET,
)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class IngestionConfig:
    """Connection configuration for MinIO and the ingestion process."""

    endpoint: str  # host:port, e.g. "localhost:9000"
    access_key: str
    secret_key: str
    region: str
    secure: bool
    raw_bucket: str

    # Sample data source
    samples_dir: Path

    @classmethod
    def from_env(cls, repo_root: Path | None = None) -> "IngestionConfig":
        """Build configuration from environment variables / .env file.

        Loads `.env` from the repository root (or the provided path) so that
        host-side scripts can be run without exporting variables manually.
        """
        repo_root = repo_root or Path(__file__).resolve().parents[3]
        load_dotenv(repo_root / ".env")
        # Fall back to the docker .env if a root .env is absent.
        load_dotenv(repo_root / "infrastructure" / "docker" / ".env", override=False)

        external = os.getenv("MINIO_EXTERNAL_ENDPOINT", "http://localhost:9000")
        # MinIO Python client expects host:port without scheme.
        endpoint = external.replace("http://", "").replace("https://", "")

        return cls(
            endpoint=endpoint,
            access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
            secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
            region=os.getenv("MINIO_REGION", "eu-west-2"),
            secure=_env_bool("MINIO_USE_SSL", False),
            raw_bucket=os.getenv("MINIO_RAW_BUCKET", RAW_BUCKET),
            samples_dir=Path(os.getenv("SAMPLES_DIR", "data/samples")),
        )

    @property
    def samples_path(self) -> Path:
        """Absolute path to the sample data directory."""
        if self.samples_dir.is_absolute():
            return self.samples_dir
        # Resolve relative to repo root (four levels up from this module).
        repo_root = Path(__file__).resolve().parents[3]
        return repo_root / self.samples_dir
