{{ config(materialized='view') }}

select
    transaction_id as mandate_id,
    null::string as mandate_reference,
    null::string as creditor_id,
    null::string as debtor_id,
    null::string as mandate_status,
    null::date as effective_date,
    null::date as expiry_date
from {{ source('raw', 'payment_transactions') }}
