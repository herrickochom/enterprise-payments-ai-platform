# MinIO Object Storage

MinIO is the S3-compatible object storage for the Enterprise Payments AI Platform.
It provides the physical storage substrate for the medallion lakehouse
(Raw → Staging → Bronze → Silver → Gold → Data Products → AI Intelligence).

## Services

| Service      | Container    | Purpose                                            | Ports            |
|--------------|--------------|----------------------------------------------------|------------------|
| `minio`      | `minio`      | S3 API + object storage                            | 9000 (S3), 9001 (Console) |
| `minio-init` | `minio-init` | Idempotent bucket bootstrap (runs once per `up`)   | -                |

## Bucket Layout

Buckets follow the medallion architecture defined in `.clinerules`. Bucket names
are DNS-compatible (lowercase, hyphen-separated) and prefixed with `epap-`.

| Bucket                  | Layer             | Purpose                                                              |
|-------------------------|-------------------|----------------------------------------------------------------------|
| `epap-raw`              | Raw               | Immutable source payloads + event envelope (source evidence).        |
| `epap-staging`          | Staging           | Parsed, schema-validated, technically enriched data.                |
| `epap-bronze`           | Bronze            | Standardised technical datasets (normalised, typed, QC'd).           |
| `epap-silver`           | Silver            | Trusted, source-independent canonical payment domain models.        |
| `epap-gold`             | Gold              | Dimensional, analytics-ready governed data products (star schema).  |
| `epap-data-products`    | Data Products     | Published, SLA-backed data products with ownership + lineage.        |
| `epap-archive`          | Archive           | Long-term retention / cold storage of raw evidence.                  |
| `epap-ai-intelligence`  | AI Intelligence   | AI artefacts (embeddings, knowledge docs, agent outputs, NOT raw).  |

> Per platform governance, AI must not directly reason over uncontrolled raw
> data. `epap-ai-intelligence` holds derived AI artefacts only; AI agents
> consume governed Silver/Gold data.

## Raw Layer Partitioning

Raw events are written with Hive-style partitioning derived from the event
envelope time components (`year`, `month`, `day`, `hour`) plus the Kafka
`partition`. The object key layout is:

```
epap-raw/<source_system>/<message_type>/year=YYYY/month=MM/day=DD/hour=HH/partition=N/<message_id>_<kafkaoffset>.json
```

This enables partition pruning by time and partition for downstream
Staging/Bronze consumers while preserving immutable, individually-addressable
source evidence.

## Running

From `infrastructure/docker/`:

```bash
# Boot MinIO + the bucket bootstrap service only
docker compose up -d minio minio-init

# Verify buckets were created
docker compose logs minio-init
docker compose exec minio mc ls local
```

Console UI: http://localhost:9001 (credentials from `.env`, default
`minioadmin` / `minioadmin`).

## Configuration

All connection values live in `infrastructure/docker/.env`. Host-side Python
services (e.g. ingestion) use `MINIO_EXTERNAL_ENDPOINT=http://localhost:9000`,
while in-network containers use `MINIO_ENDPOINT=minio:9000`.
