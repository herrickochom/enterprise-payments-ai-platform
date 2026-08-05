{{ config(materialized='view') }}

select
    transaction_id as party_id,
    null::string as party_name,
    null::string as party_type,
    null::string as legal_identifier,
    null::string as roles,
    null::string as country
from {{ source('raw', 'payment_transactions') }}
