{{ config(materialized='view') }}

select
    payment_information_id,
    message_id,
    instruction_id,
    payment_information_type,
    instruction_timestamp,
    payment_method,
    payment_scheme
from {{ source('raw', 'payment_information') }}
