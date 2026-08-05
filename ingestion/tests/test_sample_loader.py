"""Tests for the sample loader metadata extraction.

Uses the real ISO 20022 and platform sample files shipped in the repo.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from epap_ingestion.sample_loader import (
    load_sample_file,
    load_samples,
    _stable_partition,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLES = REPO_ROOT / "data" / "samples"


def _fixed_clock():
    return datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)


def test_load_iso20022_pain001_extracts_metadata():
    msg = load_sample_file(
        SAMPLES / "pain001" / "icm-vpm-pain001-uk-001-09.xml",
        now_provider=_fixed_clock,
    )
    assert msg.message_type == "pain.001"
    assert msg.source_system == "icm-vpm"
    assert msg.message_id == "UK-EPAP-PAIN001-20260803-000001"
    # CreDtTm 2026-08-03T23:20:00 -> UTC partition components.
    assert msg.eventtime == datetime(2026, 8, 3, 23, 20, 0, tzinfo=timezone.utc)
    assert msg.header_extras["family"] == "iso"
    assert msg.header_extras["payload_size_bytes"] > 0


def test_load_iso20022_camt055_uses_assgnmt_id():
    msg = load_sample_file(
        SAMPLES / "camt055" / "icm-camt055-uk-001-08.xml", now_provider=_fixed_clock
    )
    assert msg.message_type == "camt.055"
    assert msg.message_id == "ICM-CAMT055-UK-001-08"  # from <Assgnmt><Id>
    # CreDtTm 2026-08-04T17:41:00Z
    assert msg.eventtime == datetime(2026, 8, 4, 17, 41, 0, tzinfo=timezone.utc)


def test_load_platform_message_extracts_source_and_business_id():
    msg = load_sample_file(
        SAMPLES / "plm" / "vpm_plm.xml", now_provider=_fixed_clock
    )
    assert msg.message_type == "vpm"
    assert msg.source_system == "VIRTUAL_ACCOUNT_ENGINE"
    assert msg.message_id == "VPM-SYN-2026-0001"
    assert msg.header_extras["correlation_id"] == "TRACE-SYN-VPM-0001"
    assert msg.header_extras["tenant_id"] == "TENANT-SYN-UK"
    assert msg.header_extras["schema_version"] == "vpm-plm-v1.0"


def test_load_samples_builds_envelopes_for_all_files():
    loaded = load_samples(SAMPLES, now_provider=_fixed_clock)
    assert len(loaded) == 10  # total sample files in the repo
    envelopes = [env for _, env in loaded]
    # All envelopes carry the contract fields with non-empty values.
    for env in envelopes:
        assert env.event_data
        assert env.header["source_system"]
        assert env.header["message_type"]
        assert env.header["message_id"]
        assert isinstance(env.kafkaoffset, int) and env.kafkaoffset >= 0
        assert len(env.year) == 4
        assert len(env.month) == 2
        assert len(env.day) == 2
        assert len(env.hour) == 2
        assert isinstance(env.partition, int)
        assert "payload_sha256" in env.header
        assert env.header["schema_version"] is not None


def test_load_samples_assigns_per_partition_offsets_monotonically():
    loaded = load_samples(SAMPLES, now_provider=_fixed_clock)
    by_partition: dict[int, list[int]] = {}
    for _, env in loaded:
        by_partition.setdefault(env.partition, []).append(env.kafkaoffset)
    for offsets in by_partition.values():
        assert offsets == list(range(len(offsets)))  # 0,1,2,... per partition


def test_load_samples_is_deterministic_across_runs():
    a = load_samples(SAMPLES, now_provider=_fixed_clock)
    b = load_samples(SAMPLES, now_provider=_fixed_clock)
    keys_a = [
        env.object_key(s.source_system, s.message_type, s.message_id)
        for s, env in a
    ]
    keys_b = [
        env.object_key(s.source_system, s.message_type, s.message_id)
        for s, env in b
    ]
    assert keys_a == keys_b


def test_stable_partition_is_deterministic():
    assert _stable_partition("VIRTUAL_ACCOUNT_ENGINE", 4) == _stable_partition(
        "VIRTUAL_ACCOUNT_ENGINE", 4
    )
    # Distinct sources should be able to land on different partitions.
    parts = {_stable_partition(s, 8) for s in [
        "icm", "icm-vpm", "cpo-psn", "VIRTUAL_ACCOUNT_ENGINE", "ISO_MAPPER"
    ]}
    assert len(parts) >= 2
