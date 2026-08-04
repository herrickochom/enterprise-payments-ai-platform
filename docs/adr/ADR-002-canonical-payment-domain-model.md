# ADR-002: Canonical Payment Domain Model

## Metadata
- **Number:** ADR-002
- **Title:** Canonical Payment Domain Model
- **Status:** Accepted
- **Date:** 2026-08-04

## Status

Accepted

## Context

The Enterprise Payments AI Platform requires a governed canonical payment domain model to support analytics, investigations, reconciliation, AI consumption, and enterprise data products.

Payment data originates from multiple sources including ISO 20022 messages, operational payment platforms, and internal processing systems.

The architecture requires separation between:

- Conceptual business domain modelling
- Silver logical canonical modelling
- Gold analytical consumption modelling

The Silver layer must provide a trusted enterprise payment representation without becoming a physical implementation model or analytical consumption layer.

## Decision

We will implement a transaction-centric Silver canonical payment model.

The primary enterprise anchor entity is:

```
slv_payment_transactions
```

There is intentionally no:

```
slv_payment
```

entity.

The canonical transaction represents the enterprise payment record used for downstream analytics, reconciliation, investigation, and AI consumption.

## Silver Canonical Entities

The Silver layer contains:

- slv_payment_rawpayload_audit
- slv_payment_messages
- slv_payment_information
- slv_payment_transactions
- slv_payment_party
- slv_payment_party_address
- slv_payment_account
- slv_payment_mandate
- slv_payment_batch
- slv_payment_status
- slv_payment_report
- slv_payment_cancellations
- slv_payment_resolution
- slv_payment_lifecycle_event

## Source Lineage Decision

Source lineage follows:

```
slv_payment_rawpayload_audit

|

v

slv_payment_messages

|

v

slv_payment_information

|

v

slv_payment_transactions
```

Raw payload evidence remains immutable and traceable.

ISO 20022 messages are preserved as source evidence and transformed into canonical Silver entities.

## Lifecycle Event Decision

Internal technical processing events are not treated as business payment status.

Lifecycle events are consolidated from operational platforms:

```
slv_cpo_plm_lifecycle_event

|

UNION ALL

|

v

slv_payment_lifecycle_event

^

UNION ALL

|

slv_vpm_pmn_lifecycle_event
```

`slv_payment_lifecycle_event` records technical processing history associated with:

```
slv_payment_transactions
```

Lifecycle events do not replace business status.

## Status and Reporting Decision

Payment status and reporting are separate canonical concepts.

Relationship:

```
slv_payment_transactions

|

+----------------+

|                |

v                v

slv_payment_status   slv_payment_report
```

Status represents business payment state history.

Reports represent reporting and reconciliation artefacts.

## Party and Account Modelling Decision

The Silver model does not introduce transaction bridge entities.

The following are intentionally not created:

```
slv_payment_transaction_party

slv_payment_transaction_account
```

Party roles and account roles are resolved in Gold consumption models.

Silver maintains canonical entities:

```
slv_payment_party

slv_payment_account
```

Gold models may introduce analytical structures such as:

- debtor role
- creditor role
- debtor agent
- creditor agent
- settlement account
- reporting dimensions

## Cancellation and Resolution Decision

Cancellation and resolution workflows are linked to the canonical transaction.

Relationship:

```
slv_payment_transactions

|

+----------------+

|                |

v                v

slv_payment_cancellations  slv_payment_resolution
```

A cancellation may initiate a resolution workflow, but resolution is not restricted only to cancellation scenarios.

## Architectural Principles

The following principles apply:

1. Silver is the enterprise canonical payment domain layer.
2. Silver is not Data Vault modelling.
3. Silver is not a reporting model.
4. Gold provides analytical and AI consumption structures.
5. Raw payload evidence is immutable.
6. Lineage is mandatory.
7. Lifecycle events are technical history.
8. Status represents business state.
9. LLMs consume governed data but are not systems of record.

## Consequences

Benefits:

- Consistent enterprise payment representation
- Clear separation of business and technical events
- Strong lineage and auditability
- ISO 20022 alignment
- Simplified Gold modelling

Trade-offs:

- Gold models require role resolution for analytical use cases.
- Some ISO 20022 complexity remains outside Silver and is handled through controlled mappings.
