{{ config(materialized='view') }}

select
    transaction_id as lifecycle_event_id,
    transaction_id,
    'CPO_PLM' as event_type,
    null::timestamp as event_timestamp,
    'CPO/PLM' as source_system,
    null::string as technical_status,
    null::string as source_event_id,
    null::string as processing_step
from {{ source('raw', 'payment_transactions') }}
