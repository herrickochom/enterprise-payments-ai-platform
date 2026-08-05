{{ config(materialized='view') }}

select
    transaction_id as report_id,
    transaction_id as status_id,
    null::string as report_type,
    null::timestamp as report_timestamp,
    null::string as reconciliation_status,
    null::string as report_reference
from {{ source('raw', 'payment_transactions') }}
