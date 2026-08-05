"""Unit tests for the raw event envelope contract.

These tests validate the field set/order of:

    {|event_data|header|kafkaoffset|eventtime|year|month|day|hour|partition|}

and run without a live MinIO.
"""

from datetime import datetime, timezone

from epap_ingestion.envelope import RawEventEnvelope


def test_envelope_field_order_matches_contract():
    """JSON serialisation keys must follow the documented field order."""
    envelope = RawEventEnvelope.build(
        payload="<payload/>",
        header={"source_system": "iso", "message_id": "M1"},
        kafkaoffset=7,
        eventtime=datetime(2026, 8, 3, 23, 20, 0, tzinfo=timezone.utc),
        partition=2,
    )
    import json

    keys = list(json.loads(envelope.to_json()).keys())
    assert keys == [
        "event_data",
        "header",
        "kafkaoffset",
        "eventtime",
        "year",
        "month",
        "day",
        "hour",
        "partition",
    ]


def test_envelope_derives_time_partition_components_from_eventtime():
    envelope = RawEventEnvelope.build(
        payload="x",
        header={},
        kafkaoffset=0,
        eventtime=datetime(2026, 8, 3, 23, 20, 0, tzinfo=timezone.utc),
        partition=1,
    )
    assert envelope.year == "2026"
    assert envelope.month == "08"
    assert envelope.day == "03"
    assert envelope.hour == "23"
    assert envelope.eventtime == "2026-08-03T23:20:00Z"


def test_envelope_normalises_naive_eventtime_to_utc():
    envelope = RawEventEnvelope.build(
        payload="x",
        header={},
        kafkaoffset=0,
        eventtime=datetime(2026, 1, 2, 3, 4, 5),  # naive
        partition=0,
    )
    assert envelope.eventtime == "2026-01-02T03:04:05Z"
    assert envelope.hour == "03"


def test_envelope_preserves_payload_verbatim():
    payload = "<Doc>\n  <Id>A</Id>\n</Doc>\n"
    envelope = RawEventEnvelope.build(
        payload=payload,
        header={"message_id": "A"},
        kafkaoffset=3,
        eventtime=datetime(2026, 8, 4, 9, 0, 0, tzinfo=timezone.utc),
        partition=0,
    )
    # event_data must be the original payload, unmodified.
    assert envelope.event_data == payload
    # Round-trip through JSON must preserve it too.
    assert RawEventEnvelope.from_json(envelope.to_json()).event_data == payload


def test_envelope_header_includes_payload_sha256():
    import hashlib

    payload = "abc"
    envelope = RawEventEnvelope.build(
        payload=payload,
        header={"message_id": "A"},
        kafkaoffset=0,
        eventtime=datetime(2026, 8, 4, tzinfo=timezone.utc),
        partition=0,
    )
    assert envelope.header["payload_sha256"] == hashlib.sha256(b"abc").hexdigest()


def test_envelope_object_key_is_hive_partitioned():
    envelope = RawEventEnvelope.build(
        payload="x",
        header={},
        kafkaoffset=42,
        eventtime=datetime(2026, 8, 3, 14, 0, 0, tzinfo=timezone.utc),
        partition=3,
    )
    key = envelope.object_key("iso20022", "pain.001", "MSG-1")
    assert key == (
        "iso20022/pain.001/year=2026/month=08/day=03/hour=14/partition=3/MSG-1_42.json"
    )


def test_envelope_object_key_sanitises_message_id_slashes():
    envelope = RawEventEnvelope.build(
        payload="x",
        header={},
        kafkaoffset=0,
        eventtime=datetime(2026, 8, 3, tzinfo=timezone.utc),
        partition=0,
    )
    key = envelope.object_key("src", "type", "a/b/c")
    assert "/" not in key.split("partition=0/")[1]
