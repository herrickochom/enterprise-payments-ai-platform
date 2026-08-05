{{ config(materialized='view') }}

select
    transaction_id,
    message_id,
    payment_information_id,
    party_id,
    account_id,
    mandate_id,
    batch_id,
    raw_payload_audit_id,
    payment_reference,
    end_to_end_id,
    instruction_id,
    amount,
    currency,
    value_date,
    initiation_date,
    payment_purpose,
    payment_type,
    transaction_status_summary
from {{ source('raw', 'payment_transactions') }}
