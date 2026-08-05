{{ config(materialized='view') }}

select
    transaction_id as account_id,
    null::string as iban,
    null::string as account_number,
    null::string as account_type,
    currency,
    null::string as bank_identifier,
    null::string as account_status
from {{ source('raw', 'payment_transactions') }}
