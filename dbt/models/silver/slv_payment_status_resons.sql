{{ config(materialized='view') }}

select
    transaction_id as status_id,
    transaction_id,
    null::string as status_code,
    null::string as status_reason,
    null::timestamp as effective_timestamp,
    null::string as status_source,
    null::string as status_scope
from {{ source('raw', 'payment_transactions') }}
