# EPAP Ingestion

Host-side ingestion services for the Enterprise Payments AI Platform. Lands
source payment messages into the **Raw layer** of MinIO as immutable event
envelopes.

## Raw Event Envelope

Every ingested message is wrapped in an envelope whose field set and order
implement the ingestion contract:

```
{|event_data|header|kafkaoffset|eventtime|year|month|day|hour|partition|}
```

| Field         | Type | Description                                                              |
|---------------|------|--------------------------------------------------------------------------|
| `event_data`  | str  | Original, untransformed payload (ISO 20022 XML / platform XML).          |
| `header`      | dict | Message metadata: source system, message type, message id, correlation, hashes, audit stamps. |
| `kafkaoffset` | int  | Kafka offset (simulated for sample data; per-partition landing position). |
| `eventtime`   | str  | Event timestamp (ISO-8601 UTC). Derived from `<CreDtTm>` (ISO 20022) or file mtime (platform). |
| `year`        | str  | Partition component derived from `eventtime`.                           |
| `month`       | str  | Partition component derived from `eventtime`.                           |
| `day`         | str  | Partition component derived from `eventtime`.                          |
| `hour`        | str  | Partition component derived from `eventtime`.                           |
| `partition`   | int  | Kafka partition (simulated; CRC32 of source system modulo N).           |

**Serialization:** each envelope is a self-contained JSON object (one object
per raw event). JSON is used instead of a literal pipe-delimited line because
`event_data` is XML containing newlines that would collide with a pipe
delimiter. JSON preserves the exact field set/order above while being
delimiter-safe and queryable by downstream Staging/Bronze consumers. See
`docs/adr/ADR-003-raw-ingestion-event-envelope.md`.

## Raw Layer Object Layout

```
epap-raw/<source_system>/<message_type>/year=YYYY/month=MM/day=DD/hour=HH/partition=N/<message_id>_<kafkaoffset>.json
```

Hive-style partitioning by `year/month/day/hour` + `partition` enables
time/partition pruning by downstream consumers, while keeping every event
individually addressable and immutable.

## Setup

```bash
# 1. Start MinIO + bucket bootstrap (from infrastructure/docker/)
docker compose up -d minio minio-init

# 2. Install the ingestion package (editable) from ingestion/
python -m pip install -e ".[test]"

# 3. Configure (optional; defaults target localhost:9000)
cp .env.example .env   # at repo root
```

## Usage

```bash
# Create the medallion buckets (also done by the minio-init container)
python -m epap_ingestion ensure-buckets

# Ingest the sample ISO 20022 / platform messages into the raw layer
python -m epap_ingestion ingest-samples --num-partitions 4

# List the landed raw objects
python -m epap_ingestion list-raw
```

## Tests

```bash
cd ingestion
python -m pytest -q
```

Unit tests cover the envelope contract and the sample loader metadata
extraction (ISO 20022 + platform payloads), and run without a live MinIO.
