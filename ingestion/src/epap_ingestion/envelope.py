"""Raw event envelope for the Raw layer.

Implements the ingestion envelope format:

    {|event_data|header|kafkaoffset|eventtime|year|month|day|hour|partition|}

The pipe notation defines the field set and order of the immutable raw event
record. Each ingested source message is wrapped in this envelope before being
landed into the MinIO ``epap-raw`` bucket.

Fields (in order):
    event_data  : str   The original, untransformed source payload (ISO 20022
                        XML text). Preserved verbatim (Raw rule: "Do not
                        transform source data").
    header      : dict  Message metadata headers. Carries the source system,
                        message type, business message identifier, correlation
                        identifiers and content hashes for auditability.
    kafkaoffset : int   Kafka offset of the event (simulated for sample data
                        as the monotonic landing position of the event).
    eventtime   : str   Event timestamp in ISO-8601 (UTC). The temporal anchor
                        used to derive the partition components.
    year        : str   Partition component derived from eventtime (YYYY).
    month       : str   Partition component derived from eventtime (MM).
    day         : str   Partition component derived from eventtime (DD).
    hour        : str   Partition component derived from eventtime (HH).
    partition   : int   Kafka partition number (simulated for sample data;
                        derived from the source system for deterministic
                        distribution).

Serialization decision (see ADR-003):
    The envelope is serialised as a JSON object (one object per raw event).
    JSON is chosen over a literal pipe-delimited line because ``event_data``
    contains XML with embedded newlines that would collide with a pipe
    delimiter. JSON preserves the exact field set/order above while being
    delimiter-safe and queryable by downstream Staging/Bronze consumers.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def _to_iso_utc(dt: datetime) -> str:
    """Return an ISO-8601 UTC timestamp string with 'Z' suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RawEventEnvelope:
    """Immutable raw event record landed into the Raw layer.

    Field order matches the ingestion format contract:

        {|event_data|header|kafkaoffset|eventtime|year|month|day|hour|partition|}
    """

    event_data: str
    header: dict[str, Any]
    kafkaoffset: int
    eventtime: str
    year: str
    month: str
    day: str
    hour: str
    partition: int

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def build(
        cls,
        *,
        payload: str,
        header: dict[str, Any],
        kafkaoffset: int,
        eventtime: datetime,
        partition: int,
    ) -> "RawEventEnvelope":
        """Construct an envelope, deriving the time-partition components.

        ``eventtime`` is normalised to UTC and used to derive ``year``,
        ``month``, ``day`` and ``hour`` so that partition paths are always
        consistent with the event timestamp.
        """
        ts = _to_iso_utc(eventtime)
        utc = (
            eventtime.astimezone(timezone.utc)
            if eventtime.tzinfo
            else eventtime.replace(tzinfo=timezone.utc)
        )
        envelope_header = dict(header)
        # Enrich the header with audit content hashes (do not touch payload).
        envelope_header.setdefault(
            "payload_sha256",
            hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        )
        return cls(
            event_data=payload,
            header=envelope_header,
            kafkaoffset=kafkaoffset,
            eventtime=ts,
            year=f"{utc.year:04d}",
            month=f"{utc.month:02d}",
            day=f"{utc.day:02d}",
            hour=f"{utc.hour:02d}",
            partition=partition,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_json(self) -> str:
        """Serialise the envelope to a compact JSON string.

        The key order in the output mirrors the format contract so that the
        on-disk representation reads in the documented field order.
        """
        return json.dumps(
            {
                "event_data": self.event_data,
                "header": self.header,
                "kafkaoffset": self.kafkaoffset,
                "eventtime": self.eventtime,
                "year": self.year,
                "month": self.month,
                "day": self.day,
                "hour": self.hour,
                "partition": self.partition,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def to_bytes(self) -> bytes:
        """UTF-8 encoded JSON bytes of the envelope (for object storage)."""
        return self.to_json().encode("utf-8")

    @classmethod
    def from_json(cls, text: str) -> "RawEventEnvelope":
        """Reconstruct an envelope from its JSON serialisation."""
        data = json.loads(text)
        return cls(
            event_data=data["event_data"],
            header=data["header"],
            kafkaoffset=data["kafkaoffset"],
            eventtime=data["eventtime"],
            year=data["year"],
            month=data["month"],
            day=data["day"],
            hour=data["hour"],
            partition=data["partition"],
        )

    # ------------------------------------------------------------------
    # Storage key helpers
    # ------------------------------------------------------------------
    def object_key(
        self, source_system: str, message_type: str, message_id: str
    ) -> str:
        """Build the Hive-style partitioned object key for the raw bucket.

        Layout::

            <source_system>/<message_type>/year=YYYY/month=MM/day=DD/hour=HH/partition=N/<message_id>_<kafkaoffset>.json

        Partition components are derived from the event timestamp, enabling
        time-based partition pruning by downstream consumers.
        """
        safe_message_id = message_id.replace("/", "_")
        return (
            f"{source_system}/{message_type}/"
            f"year={self.year}/month={self.month}/day={self.day}/hour={self.hour}/"
            f"partition={self.partition}/"
            f"{safe_message_id}_{self.kafkaoffset}.json"
        )

    header: dict[str, Any]
    kafkaoffset: int
    eventtime: str
    year: str
    month: str
    day: str
    hour: str
    partition: int
