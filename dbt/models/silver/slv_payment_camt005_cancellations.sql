{{ config(materialized='view') }}

select
    transaction_id as cancellation_id,
    transaction_id,
    null::timestamp as cancellation_timestamp,
    null::string as cancellation_reason,
    null::string as cancellation_status,
    null::string as source_reference
from {{ source('raw', 'payment_transactions') }}
