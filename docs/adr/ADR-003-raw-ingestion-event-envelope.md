# ADR-003: Raw Ingestion Event Envelope

## Metadata
- **Number:** ADR-003
- **Title:** Raw Ingestion Event Envelope
- **Status:** Proposed
- **Date:** 2026-08-04

## Context

The Raw layer must hold immutable source evidence that preserves the original
payload, message identifiers, correlation identifiers and event timestamps,
with complete audit history (per `.clinerules` Raw layer rules).

Payment sources arrive as event streams. The platform needs a consistent raw
landing format that:

1. Carries the original payload verbatim (no transformation).
2. Captures the Kafka-style coordinates (`kafkaoffset`, `partition`) that
   locate the event within its source stream, so downstream stages can
   replay, deduplicate and reason about ordering.
3. Records the event timestamp and its derived time-partition components
   (`year`, `month`, `day`, `hour`) for physical partitioning of the raw lake.
4. Carries a metadata `header` (source system, message type, message id,
   correlation id, content hashes, audit stamps).

The ingestion contract requested for sample-data landing is expressed as:

```
{|event_data|header|kafkaoffset|eventtime|year|month|day|hour|partition|}
```

The pipe notation defines the **field set and order** of the raw event record.

## Decision

Adopt a single raw event envelope with the exact field set/order above:

- `event_data`: the original, untransformed source payload.
- `header`: a metadata dictionary (source system, message type, message id,
  correlation id, payload content hash, payload size, schema version, audit
  `ingested_at`).
- `kafkaoffset`: integer Kafka offset. For sample data it is simulated as the
  monotonic, per-partition landing position of the event (reproducible, in
  sorted-file order).
- `eventtime`: ISO-8601 UTC timestamp. For ISO 20022 messages it is parsed
  from `<CreDtTm>`; for platform (PLM/PMN) messages that carry no timestamp
  it falls back to the immutable source artefact's modification time.
- `year`, `month`, `day`, `hour`: partition components derived from
  `eventtime` (always consistent with the event timestamp).
- `partition`: integer Kafka partition. For sample data it is simulated via
  a deterministic CRC32 of the source system modulo a configurable partition
  count, giving stable distribution across partitions.

### Physical serialisation

Each raw event is serialised as a **self-contained JSON object** (one object
per event) and stored as a single object in the `epap-raw` MinIO bucket. The
JSON key order mirrors the contract so the on-disk representation reads in the
documented field order.

The object key is Hive-style partitioned:

```
epap-raw/<source_system>/<message_type>/year=YYYY/month=MM/day=DD/hour=HH/partition=N/<message_id>_<kafkaoffset>.json
```

### Why JSON and not a literal pipe-delimited line

The contract is written with pipe delimiters, but `event_data` is XML that
contains newlines and could contain pipe characters. A literal
pipe-delimited single-line record would therefore be ambiguous and require
base64 encoding of the payload, hurting raw-layer inspectability. JSON
preserves the exact field set/order, is delimiter-safe, self-describing and
directly queryable by the Staging/Bronze layers without decoding. The pipe
notation is treated as the field-order specification, not the physical
serialisation.

## Alternatives Considered

- **Literal pipe-delimited line per event**
  - Pros: Compact; matches the literal notation.
  - Cons: XML payloads contain newlines/pipes, forcing base64 of
    `event_data`; reduces raw inspectability; brittle parsing for downstream.

- **Avro/Parquet per micro-batch file**
  - Pros: Columnar efficiency for analytics; schema evolution.
  - Cons: Raw layer should be maximally faithful and individually addressable
    source evidence; columnar formats are better suited to Bronze/Silver.
    Micro-batching also complicates per-event audit/replay of a single offset.

- **One file per event with raw payload only (no envelope)**
  - Pros: Simplest; no envelope overhead.
  - Cons: Loses Kafka coordinates, correlation and audit metadata that the
    Staging layer needs; violates the requirement to land a structured event
    record.

## Consequences

Benefits
- Immutable, individually-addressable source evidence with full lineage and
  Kafka coordinates for replay/deduplication.
- Time-based partition pruning via `year/month/day/hour` plus `partition`.
- Deterministic, reproducible landing for sample data (stable partitions and
  per-partition offsets).
- Clean handoff to Staging: the envelope is self-describing JSON that the
  Staging parser can read directly.

Trade-offs
- One object per event produces many small objects at scale; a future
  optimisation is micro-batch compaction (multiple events per object per
  partition-hour) once volumes grow, while keeping the envelope schema.
- Simulated Kafka coordinates for sample data must be replaced by real
  broker offsets when a live Kafka source is integrated.

Operational considerations
- Raw objects are immutable; re-ingestion overwrites the same
  `partition/offset` key (idempotent) rather than creating duplicates.
- `payload_sha256` in the header supports integrity checks and
  deduplication detection in Staging.
- DLP: raw payloads may contain PII; access to `epap-raw` is restricted via
  RBAC and audit-logged (see ADR-006 DLP & Security).

## Future ADRs
- ADR-009: Kafka source integration and live offset management (replacing
  simulated coordinates).
- ADR-010: Raw layer retention, compaction and archival to `epap-archive`.
