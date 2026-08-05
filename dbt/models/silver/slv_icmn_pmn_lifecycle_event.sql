{{ config(materialized='view') }}

select
    transaction_id as lifecycle_event_id,
    transaction_id,
    'VPM_PMN' as event_type,
    null::timestamp as event_timestamp,
    'VPM/PMN' as source_system,
    null::string as technical_status,
    null::string as source_event_id,
    null::string as processing_step
from {{ source('raw', 'payment_transactions') }}
