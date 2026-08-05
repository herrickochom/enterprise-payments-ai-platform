"""Command-line interface for the EPAP ingestion services.

Usage::

    python -m epap_ingestion.cli ingest-samples [--num-partitions N]
    python -m epap_ingestion.cli list-raw
    python -m epap_ingestion.cli ensure-buckets

The CLI connects to MinIO using configuration from the environment (see
``IngestionConfig``) and lands sample payment messages into the Raw layer
as immutable event envelopes.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from minio import Minio

from epap_ingestion.config import IngestionConfig, ALL_BUCKETS
from epap_ingestion.raw_ingestor import RawIngestor
from epap_ingestion.sample_loader import load_samples


def _build_minio_client(cfg: IngestionConfig) -> Minio:
    return Minio(
        endpoint=cfg.endpoint,
        access_key=cfg.access_key,
        secret_key=cfg.secret_key,
        region=cfg.region,
        secure=cfg.secure,
    )


def cmd_ensure_buckets(cfg: IngestionConfig) -> int:
    client = _build_minio_client(cfg)
    created, existing = [], []
    for bucket in ALL_BUCKETS:
        if client.bucket_exists(bucket):
            existing.append(bucket)
        else:
            client.make_bucket(bucket)
            created.append(bucket)
    print("Bucket bootstrap complete.")
    for b in created:
        print(f"  created:   {b}")
    for b in existing:
        print(f"  existing:  {b}")
    return 0


def cmd_ingest_samples(cfg: IngestionConfig, num_partitions: int) -> int:
    samples_dir = cfg.samples_path
    if not samples_dir.is_dir():
        print(f"ERROR: samples directory not found: {samples_dir}", file=sys.stderr)
        return 2

    client = _build_minio_client(cfg)
    ingestor = RawIngestor(client, cfg.raw_bucket)

    loaded = load_samples(
        samples_dir,
        num_partitions=num_partitions,
        now_provider=lambda: datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc),
    )
    result = ingestor.write_samples(loaded)

    print(f"Ingested {result.objects_written} raw event(s) into {result.bucket}")
    for sample, envelope in loaded:
        key = envelope.object_key(
            sample.source_system, sample.message_type, sample.message_id
        )
        print(
            f"  [{envelope.partition}/{envelope.kafkaoffset}] "
            f"{sample.message_type:<10} {sample.source_system:<22} "
            f"{envelope.eventtime}  {key}"
        )
    print(f"Total objects written: {result.objects_written}")
    return 0


def cmd_list_raw(cfg: IngestionConfig) -> int:
    client = _build_minio_client(cfg)
    if not client.bucket_exists(cfg.raw_bucket):
        print(f"Bucket {cfg.raw_bucket} does not exist.", file=sys.stderr)
        return 2
    print(f"Objects in {cfg.raw_bucket}:")
    count = 0
    for obj in client.list_objects(cfg.raw_bucket, recursive=True):
        print(f"  {obj.size:>8} bytes  {obj.object_name}")
        count += 1
    print(f"Total objects: {count}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epap-ingestion",
        description="Enterprise Payments AI Platform - raw layer ingestion.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ensure-buckets", help="Create the medallion buckets if missing.")

    ingest = sub.add_parser(
        "ingest-samples", help="Ingest sample payment data into the raw layer."
    )
    ingest.add_argument(
        "--num-partitions",
        type=int,
        default=4,
        help="Number of simulated Kafka partitions (default: 4).",
    )

    sub.add_parser("list-raw", help="List objects in the raw bucket.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = IngestionConfig.from_env()
    if args.command == "ensure-buckets":
        return cmd_ensure_buckets(cfg)
    if args.command == "ingest-samples":
        return cmd_ingest_samples(cfg, args.num_partitions)
    if args.command == "list-raw":
        return cmd_list_raw(cfg)
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
