# Architecture Roadmap

Purpose
- Provide the master enterprise architecture roadmap for the Enterprise Payments AI Platform.
- Align architecture, data, AI and platform teams on artefacts, phases and acceptance criteria.

Scope
- Canonical payment domain modelling
- Governance and ADRs for AI/agents
- Lakehouse physical model and data products
- Retrieval, graph and orchestration integration for AI

Platform Vision (unchanged)
- AI-enabled enterprise payment intelligence platform.
- Not a payment processing engine.
- Enterprise data remains the source of truth.

Summary (principles and layers)
- Medallion layers: Source → Raw → Staging → Bronze → Silver → Gold → Data Products → AI Agents
- Core technology direction: Python, dbt, Apache Iceberg, MinIO, Qdrant, Neo4j, LangGraph and open-source LLMs

-**Architecture Artefacts**
- **Architecture Decision Records (ADR)**: formalise architectural choices, trade-offs, and owners. ADRs follow a controlled numbering strategy to ensure governance and traceability:
  - **ADR-001**: Enterprise Payments AI Platform Architecture
  - **ADR-002**: Lakehouse Architecture (MinIO + Iceberg)
  - **ADR-003**: Canonical Payment Domain Model
  - **ADR-004**: Gold Dimensional Modelling Strategy
  - **ADR-005**: Data Governance and Data Quality Framework
  - **ADR-006**: DLP, PII Protection and Security Architecture
  - **ADR-007**: LLM and Agent Strategy
  - **ADR-008**: Knowledge Graph and Vector Retrieval Architecture
- **Conceptual Payment Domain Model**: high-level business concepts, entities and relationships (ER diagrams).
- **Logical Silver Canonical Payment Model**: canonical domain schemas, event modelling and lineage requirements.
- **Physical Lakehouse Model**: Iceberg table designs, partitioning, retention, storage layout on MinIO.
- **Gold Dimensional Model**: star schemas, facts and conformed dimensions for analytics and BI.
- **Data Product Marketplace**: catalogue, ownership, SLAs and access patterns for governed data products.
- **Data Governance Model**: ownership, metadata, lineage, quality frameworks and DQ automation.
- **Security and DLP Architecture**: RBAC/ABAC design, encryption, masking, tokenisation and audit logging.
- **Knowledge Graph Architecture**: Neo4j model for parties, accounts, payments and investigation networks.
- **Vector Retrieval Architecture**: embedding strategy, Qdrant indexing, chunking, freshness and similarity controls.
- **AI Agent Architecture**: LangGraph orchestration, agent interfaces, prompt/chains-of-trust, observability.
- **Deployment Architecture**: CI/CD, environment isolation (dev/stage/prod), infra-as-code and monitoring.

Roadmap Phases (ordered: Architecture → Data Model → Physical Platform → Data Products → AI)

Phase 1: Architecture Foundation
- Deliverable: Core ADR set, architecture principles, and roadmap governance.
- Purpose: Establish decision-making guardrails, owners, and a single source of architectural truth.
- Dependencies: Stakeholder alignment (data, security, AI), access to existing requirements.
- Acceptance criteria:
  - ADRs covering data platform, LLM policy, and security are approved with owners.
  - Roadmap published and linked from central docs.

Phase 2: Payment Domain Modelling
- Deliverable: Conceptual Payment Domain Model and Logical Silver Canonical Payment Model.
- Purpose: Define canonical business entities (Payment, Payment Event, Party, Account, Mandate, Investigation) and event semantics.
- Dependencies: Message samples (pain.*, pacs.*, camt.*), business glossary, stakeholder review.
- Acceptance criteria:
  - ER diagrams and canonical schemas reviewed and approved by domain SMEs.
  - Mapping matrix from message types to canonical fields completed for key messages. The mapping must explicitly cover ISO 20022 messages and define relationships between source messages and the canonical Silver payment model, including:
    - `pain.001` Customer Credit Transfer Initiation
    - `pain.002` Customer Payment Status Report
    - `pacs.008` FI to FI Customer Credit Transfer
    - `camt.029` Resolution of Investigation
    - `camt.055` Payment Cancellation Request
    The mapping matrix must define relationships between source messages and the canonical Silver payment model.

Phase 3: Lakehouse Data Platform
- Deliverable: Physical Lakehouse Model, dbt model skeletons, Iceberg table designs and storage layout.
- Purpose: Implement the physical foundation for Raw→Silver→Gold with performance, governance and time-travel capabilities.
- Dependencies: MinIO access, Iceberg deployment plan, dbt environment, sample datasets.
- Acceptance criteria:
  - Iceberg tables defined for Raw/Bronze/Silver/Gold with partition strategy.
  - dbt models implementing canonical Silver models for sample messages; CI pipeline validates schema tests.

Phase 4: Data Products
- Deliverable: Gold Dimensional Models, Data Product Marketplace prototype and QA rules.
- Purpose: Expose governed analytics-ready datasets with SLAs, owners and quality gates.
- Dependencies: Silver canonical models, DQ framework, BI/user requirements.
- Acceptance criteria:
  - At least two Gold data products implemented with owner, documentation, and quality tests.
  - Data product entries present in marketplace with SLA and lineage links.
  - Gold data products must implement measurable data quality rules covering the seven dimensions defined in the platform data quality framework and `.clinerules`:
    - Accuracy
    - Completeness
    - Consistency
    - Timeliness
    - Validity
    - Uniqueness
    - Integrity
    These rules must be automated where possible and tied to data product acceptance tests.

Phase 5: AI Knowledge Architecture
- Deliverable: Knowledge Graph design, Vector Retrieval architecture and ingestion pipelines.
- Purpose: Provide retrieval and relationship intelligence layers for AI (Neo4j + Qdrant integrations).
- Dependencies: Silver/Gold datasets, embedding strategy, Neo4j capacity plan.
- Acceptance criteria:
  - Neo4j model for Parties/Accounts/Payments with initial ingestion of sample data.
  - Qdrant index created for sample documents and embeddings; retrieval tests demonstrate precision/recall targets.

Phase 6: AI Agents
- Deliverable: LangGraph flows, agent interface contracts, ADR for LLM & Agent Strategy.
- Purpose: Orchestrate agents for Payment Investigation, Data Quality, and Documentation with traceability.
- Dependencies: Retrieval pipelines (Qdrant), knowledge graph sync, LLM selection and prompt governance.
- Acceptance criteria:
  - Prototype Payment Investigation agent that returns traceable evidence from Silver/Gold datasets.
  - Monitoring and observability for agent actions; runbook for escalation.

Phase 7: Implementation and Operationalisation
- Deliverable: CI/CD, infra-as-code, monitoring, DLP enforcement, production runbooks and SLOs.
- Purpose: Move artefacts into production with operational resilience and compliance controls.
- Dependencies: Completed artefacts from Phases 1–6, security approval, infra provisioning.
- Acceptance criteria:
  - Production deployment pipelines with automated tests and schema checks.
  - SLOs and monitoring dashboards in place; security scans and DLP controls validated.

Owners & Roles
- Data Modeling: Data Platform / Data Engineering (dbt owners).
- AI & Agents: AI Engineering / MLOps.
- Security & Governance: Security / Compliance teams.

Next Steps
- Assign owners for each artefact and open ADR issues for key technical decisions (LLM policy, retrieval design, DLP).
- Kick off a focused 2-week sprint to complete Phase 1 artefacts and begin Phase 2 modelling work.

Acceptance checklist (cross-phase)
- Each artefact must have: owner, scope, deliverables, tests and acceptance criteria.
- Traceability from AI outputs to Silver/Gold datasets must be demonstrable for every agent workflow.
- Security and DLP controls must be documented and tested prior to production access.
