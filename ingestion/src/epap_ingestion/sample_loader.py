"""Sample data loader.

Reads ISO 20022 and platform (PLM/PMN) sample files from ``data/samples``
and builds immutable :class:`RawEventEnvelope` records for the Raw layer.

Metadata extraction is namespace-agnostic so that both ISO 20022
(``urn:iso:std:iso:20022:...``) and platform (``urn:epap:...``) payloads are
handled uniformly. The loader never transforms the source payload - it only
reads metadata to populate the envelope ``header`` and partition components.

Event time resolution:
    - ISO 20022 messages: ``<CreDtTm>`` (creation date-time) parsed as UTC.
    - Platform messages (PLM/PMN): no in-message timestamp; falls back to the
      file modification time (a reasonable proxy for the landing time of an
      immutable source artefact).

Simulated Kafka coordinates:
    - ``partition``: deterministically derived from the source system
      (stable CRC32 modulo a configurable partition count).
    - ``kafkaoffset``: a monotonic, per-partition landing position assigned in
      sorted-file order (offsets restart at 0 within each partition).
"""

from __future__ import annotations

import re
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree

from epap_ingestion.envelope import RawEventEnvelope

ISO_NAMESPACE_MARKER = "urn:iso:std:iso:20022"
EPAP_NAMESPACE_MARKER = "urn:epap"

# ISO 20022 messages that carry the business id under <GrpHdr><MsgId>.
_ISO_MSGID_CANDIDATES = ("MsgId",)  # pain.001/002, pacs.008
_PLATFORM_BUSINESS_IDS = ("VpmId", "CpoId", "PmnId", "IcmnId", "PsnId")
_PLATFORM_ROOT_PREFIXES = {
    "VpmPlm": "vpm",
    "CpoPlm": "cpo",
    "PmnPlm": "pmn",
    "IcmnPlm": "icmn",
    "PsnPlm": "psn",
}


def _local_name(tag: str) -> str:
    """Strip the ``{namespace}`` prefix from an ElementTree tag."""
    return tag.split("}", 1)[1] if "}" in tag else tag


def _find_local(elem: ElementTree.Element, name: str) -> ElementTree.Element | None:
    """Depth-first search for the first element with the given local name."""
    for el in elem.iter():
        if _local_name(el.tag) == name:
            return el
    return None


def _text(el: ElementTree.Element | None) -> str | None:
    return (el.text or "").strip() if el is not None and el.text else None


def _detect_message_type(root: ElementTree.Element) -> tuple[str, str]:
    """Return (message_type, family) where family is 'iso' or 'platform'."""
    ns_match = re.search(r"\{(.*?)\}", root.tag)
    namespace = ns_match.group(1) if ns_match else ""
    root_local = _local_name(root.tag)

    if namespace.startswith(ISO_NAMESPACE_MARKER):
        # e.g. urn:iso:std:iso:20022:tech:xsd:pain.001.001.09 -> pain.001
        msg_type = namespace.rsplit(":", 1)[-1]
        parts = msg_type.split(".")
        if len(parts) >= 2:
            msg_type = ".".join(parts[:2])  # drop version -> pain.001
        return msg_type, "iso"

    if namespace.startswith(EPAP_NAMESPACE_MARKER) or root_local in _PLATFORM_ROOT_PREFIXES:
        return _PLATFORM_ROOT_PREFIXES.get(root_local, root_local.lower()), "platform"

    return root_local.lower(), "unknown"


def _parse_iso_datetime(raw: str) -> datetime:
    """Parse an ISO-8601 date-time, normalising to an aware UTC datetime."""
    text = raw.strip().replace(" ", "T")
    dt = datetime.fromisoformat(text)  # Python 3.11+ accepts trailing 'Z'
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _stable_partition(source_system: str, num_partitions: int) -> int:
    """Deterministic partition assignment from the source system."""
    digest = zlib.crc32(source_system.encode("utf-8")) & 0xFFFFFFFF
    return digest % num_partitions


@dataclass(frozen=True)
class SampleMessage:
    """A single loaded sample message ready for envelope construction."""

    payload: str
    source_system: str
    message_type: str
    message_id: str
    eventtime: datetime
    file_name: str
    header_extras: dict[str, Any]


def load_sample_file(
    path: Path,
    *,
    num_partitions: int = 4,
    now_provider: Callable[[], datetime] | None = None,
) -> SampleMessage:
    """Load a single sample file and extract its raw-layer metadata.

    ``now_provider`` allows tests to inject a deterministic clock; it is only
    used to populate the audit ``ingested_at`` header value.
    """
    payload = path.read_text(encoding="utf-8")
    # NOTE: the raw payload is preserved verbatim for `event_data` (Raw rule:
    # "Do not transform source data"). Metadata extraction parses a copy with
    # leading whitespace / BOM stripped, because some source files begin with
    # whitespace before the XML declaration, which the parser rejects.
    parseable = payload.lstrip("\ufeff").lstrip()
    root = ElementTree.fromstring(parseable)
    message_type, family = _detect_message_type(root)

    # --- Message identifier -------------------------------------------------
    message_id = None
    if family == "iso":
        for candidate in _ISO_MSGID_CANDIDATES:
            message_id = _text(_find_local(root, candidate))
            if message_id:
                break
        if not message_id:
            # camt.029 / camt.055 carry the business id under <Assgnmt><Id>,
            # nested below the document root element. Find Assgnmt depth-first,
            # then locate the first <Id> within it.
            assgnmt = _find_local(root, "Assgnmt")
            if assgnmt is not None:
                message_id = _text(_find_local(assgnmt, "Id"))
    else:  # platform
        for business_id in _PLATFORM_BUSINESS_IDS:
            message_id = _text(_find_local(root, business_id))
            if message_id:
                break
    if not message_id:
        message_id = path.stem

    # --- Source system ------------------------------------------------------
    if family == "platform":
        source_system = _text(_find_local(root, "XSourceSystem")) or "UNKNOWN"
    else:
        # Derive the operational source from the filename prefix that
        # precedes the message-type token (icm-vpm-pain001-... -> icm-vpm).
        token = message_type.replace(".", "")  # pain.001 -> pain001
        stem = path.stem.lower()
        idx = stem.find(token)
        if idx > 0:
            source_system = path.stem[: idx].rstrip("-").lower() or "iso20022"
        else:
            source_system = "iso20022"

    # --- Event time ---------------------------------------------------------
    created = _text(_find_local(root, "CreDtTm"))
    if created:
        eventtime = _parse_iso_datetime(created)
    else:
        # Platform messages carry no timestamp; use file mtime as the landing
        # time proxy for the immutable source artefact.
        eventtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    # --- Header extras ------------------------------------------------------
    schema_version = _text(_find_local(root, "SchemaVersion"))
    if not schema_version:
        # ElementTree places xmlns in the root tag (not .attrib), so derive
        # the schema version from the namespace. For ISO 20022 this is e.g.
        # "camt.055.001.08"; for platform payloads "vpm:v1" -> "v1".
        ns_match = re.search(r"\{(.*?)\}", root.tag)
        namespace = ns_match.group(1) if ns_match else ""
        if namespace:
            schema_version = namespace.rsplit(":", 1)[-1] or None

    header_extras: dict[str, Any] = {
        "family": family,
        "file_name": path.name,
        "payload_size_bytes": len(payload.encode("utf-8")),
        "schema_version": schema_version,
    }
    trace = _text(_find_local(root, "XTraceId")) or _text(_find_local(root, "TraceId"))
    if trace:
        header_extras["correlation_id"] = trace
    tenant = _text(_find_local(root, "XTenantId")) or _text(_find_local(root, "TenantId"))
    if tenant:
        header_extras["tenant_id"] = tenant

    clock = now_provider or (lambda: datetime.now(tz=timezone.utc))
    header_extras["ingested_at"] = clock().astimezone(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    return SampleMessage(
        payload=payload,
        source_system=source_system,
        message_type=message_type,
        message_id=message_id,
        eventtime=eventtime,
        file_name=path.name,
        header_extras=header_extras,
    )


def load_samples(
    samples_dir: Path,
    *,
    num_partitions: int = 4,
    now_provider: Callable[[], datetime] | None = None,
) -> list[tuple[SampleMessage, RawEventEnvelope]]:
    """Load every sample file and build its raw event envelope.

    Returns a list of ``(SampleMessage, RawEventEnvelope)`` pairs in sorted
    file order. Kafka offsets are assigned monotonically per partition so the
    landing order is deterministic and reproducible.
    """
    files = sorted(p for p in samples_dir.rglob("*.xml") if p.is_file())
    loaded: list[tuple[SampleMessage, RawEventEnvelope]] = []
    per_partition_offset: dict[int, int] = {}

    for path in files:
        sample = load_sample_file(
            path, num_partitions=num_partitions, now_provider=now_provider
        )
        partition = _stable_partition(sample.source_system, num_partitions)
        kafkaoffset = per_partition_offset.get(partition, 0)
        per_partition_offset[partition] = kafkaoffset + 1

        header = {
            "source_system": sample.source_system,
            "message_type": sample.message_type,
            "message_id": sample.message_id,
            **sample.header_extras,
        }
        envelope = RawEventEnvelope.build(
            payload=sample.payload,
            header=header,
            kafkaoffset=kafkaoffset,
            eventtime=sample.eventtime,
            partition=partition,
        )
        loaded.append((sample, envelope))

    return loaded
