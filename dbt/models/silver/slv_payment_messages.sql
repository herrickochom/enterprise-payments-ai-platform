{{ config(materialized='view') }}

select
    message_id,
    raw_audit_id,
    message_type,
    message_identifier,
    creation_timestamp,
    sender,
    receiver,
    message_reference,
    source_system
from {{ source('raw', 'payment_messages') }}
