{{ config(materialized='view') }}

select
    transaction_id as address_id,
    transaction_id as party_id,
    null::string as address_lines,
    null::string as city,
    null::string as region,
    null::string as country,
    null::string as postal_code,
    null::string as address_type
from {{ source('raw', 'payment_transactions') }}
