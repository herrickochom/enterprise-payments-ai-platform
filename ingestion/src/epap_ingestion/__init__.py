"""EPAP Ingestion package.

Host-side ingestion services for the Enterprise Payments AI Platform.

Responsibilities:
    - Land source payment messages into the Raw layer of MinIO as immutable
      event envelopes (see `epap_ingestion.envelope.RawEventEnvelope`).

The ingestion layer does NOT transform source data. It preserves the original
payload, message identifiers, correlation identifiers and event timestamps,
satisfying the Raw layer governance rules defined in `.clinerules`.
"""

from epap_ingestion.envelope import RawEventEnvelope
from epap_ingestion.config import IngestionConfig

__all__ = ["RawEventEnvelope", "IngestionConfig"]
__version__ = "0.1.0"
