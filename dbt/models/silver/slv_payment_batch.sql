{{ config(materialized='view') }}

select
    transaction_id as batch_id,
    null::string as batch_reference,
    null::string as file_name,
    null::string as origin_system,
    null::string as processing_window,
    null::string as batch_status
from {{ source('raw', 'payment_transactions') }}
