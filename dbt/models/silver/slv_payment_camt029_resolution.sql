{{ config(materialized='view') }}

select
    transaction_id as resolution_id,
    transaction_id as cancellation_id,
    null::string as resolution_status,
    null::timestamp as resolution_timestamp,
    null::string as resolution_notes,
    null::string as assigned_owner
from {{ source('raw', 'payment_transactions') }}
