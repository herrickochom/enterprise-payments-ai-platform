"""Raw layer ingestor.

Writes immutable :class:`RawEventEnvelope` records into the MinIO raw bucket
(``epap-raw``) using Hive-style partitioned object keys. Objects are written
idempotently: re-ingesting the same event overwrites the same key (same
partition + offset) without creating duplicates.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Iterable

from minio import Minio

from epap_ingestion.envelope import RawEventEnvelope
from epap_ingestion.sample_loader import SampleMessage


@dataclass(frozen=True)
class IngestionResult:
    """Summary of a raw-layer ingestion run."""

    bucket: str
    objects_written: int
    object_keys: list[str]


class RawIngestor:
    """Writes raw event envelopes to MinIO as immutable objects."""

    def __init__(self, client: Minio, raw_bucket: str):
        self._client = client
        self._bucket = raw_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the raw bucket if it does not exist (defensive)."""
        try:
            self._client.make_bucket(self._bucket)
        except Exception:
            # Bucket already exists or is owned by another principal.
            pass

    def write_envelope(
        self,
        envelope: RawEventEnvelope,
        *,
        source_system: str,
        message_type: str,
        message_id: str,
    ) -> str:
        """Write a single envelope to the raw bucket. Returns the object key."""
        object_key = envelope.object_key(source_system, message_type, message_id)
        data = envelope.to_bytes()
        stream = io.BytesIO(data)
        self._client.put_object(
            bucket_name=self._bucket,
            object_name=object_key,
            data=stream,
            length=len(data),
            content_type="application/json",
            metadata={
                "x-amz-meta-source-system": source_system,
                "x-amz-meta-message-type": message_type,
                "x-amz-meta-message-id": message_id,
                "x-amz-meta-eventtime": envelope.eventtime,
                "x-amz-meta-kafkaoffset": str(envelope.kafkaoffset),
                "x-amz-meta-partition": str(envelope.partition),
            },
        )
        return object_key

    def write_samples(
        self, loaded: Iterable[tuple[SampleMessage, RawEventEnvelope]]
    ) -> IngestionResult:
        """Write a batch of loaded sample envelopes. Returns a summary."""
        keys: list[str] = []
        for sample, envelope in loaded:
            key = self.write_envelope(
                envelope,
                source_system=sample.source_system,
                message_type=sample.message_type,
                message_id=sample.message_id,
            )
            keys.append(key)
        return IngestionResult(
            bucket=self._bucket, objects_written=len(keys), object_keys=keys
        )
