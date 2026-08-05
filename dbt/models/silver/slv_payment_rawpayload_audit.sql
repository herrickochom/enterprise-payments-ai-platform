{{ config(materialized='view') }}

select
    raw_audit_id,
    ingestion_timestamp,
    source_system,
    checksum,
    storage_pointer,
    payload_type,
    file_reference
from {{ source('raw', 'payment_payload_audit') }}
