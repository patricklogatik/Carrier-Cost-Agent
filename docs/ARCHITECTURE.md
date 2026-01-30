# Architecture Document
## Celonis Carrier Cost Agent powered by Logatik

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Last Updated** | January 28, 2026 |
| **Status** | Draft - Co-Innovation Phase |
| **Platform** | Celonis |

---

## 1. Executive Summary

This document describes the technical architecture for the Celonis Carrier Cost Agent, an AI-powered system for automated carrier invoice validation and cost recovery. The architecture is designed to integrate natively with the Celonis platform while leveraging GenAI capabilities for contract intelligence and claim automation.

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CELONIS PLATFORM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   Data       │    │   Process    │    │   Action     │                  │
│  │   Layer      │───▶│   Layer      │───▶│   Layer      │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│         │                   │                   │                           │
│         ▼                   ▼                   ▼                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CARRIER COST AGENT                                │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │   Ingest    │ │   Detect    │ │   Validate  │ │   Execute   │   │   │
│  │  │   Module    │ │   Module    │ │   Module    │ │   Module    │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────┐   │   │
│  │  │   Monitor   │ │   Contract  │ │      GenAI Services         │   │   │
│  │  │   Module    │ │   Engine    │ │  (Contract Intelligence)    │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    TMS       │    │    WMS       │    │   Carrier    │
│   Systems    │    │   Systems    │    │   Portals    │
└──────────────┘    └──────────────┘    └──────────────┘
```

### 2.2 Core Design Principles

| Principle | Description |
|-----------|-------------|
| **Platform-Native** | Built as a Celonis native application leveraging platform capabilities |
| **AI-First** | GenAI at the core for contract parsing, claim generation, and Q&A |
| **Event-Driven** | Reactive architecture responding to invoice and shipment events |
| **Modular** | Loosely coupled components for independent scaling and evolution |
| **Auditable** | Complete traceability of all decisions and actions |

---

## 3. System Components

### 3.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CARRIER COST AGENT                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      PRESENTATION LAYER                           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │ │
│  │  │  Dashboard  │  │   Claim     │  │     Contract            │   │ │
│  │  │    UI       │  │   Manager   │  │     Manager             │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                 │                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      APPLICATION LAYER                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │ │
│  │  │  Anomaly    │  │   Claim     │  │       Q&A               │   │ │
│  │  │  Detector   │  │   Generator │  │     Response Engine     │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │ │
│  │  │  Contract   │  │  Recovery   │  │      Workflow           │   │ │
│  │  │  Parser     │  │  Tracker    │  │      Orchestrator       │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                 │                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                        DATA LAYER                                 │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │ │
│  │  │  Invoice    │  │  Shipment   │  │     Contract            │   │ │
│  │  │  Store      │  │  Store      │  │     Store               │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │ │
│  │  │   Claim     │  │  Anomaly    │  │      Audit              │   │ │
│  │  │   Store     │  │  Store      │  │      Log                │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                 │                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                     INTEGRATION LAYER                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │ │
│  │  │  Invoice    │  │    TMS      │  │     Carrier             │   │ │
│  │  │  Connector  │  │  Connector  │  │     Portal Connector    │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Details

#### 3.2.1 Presentation Layer

| Component | Description | Technology |
|-----------|-------------|------------|
| **Dashboard UI** | Recovery metrics, claim pipeline, anomaly overview | Celonis Studio |
| **Claim Manager** | Review, edit, approve, and track claims | Celonis Apps |
| **Contract Manager** | Upload, view, and validate parsed contracts | Celonis Apps |

#### 3.2.2 Application Layer

| Component | Description | Key Functions |
|-----------|-------------|---------------|
| **Anomaly Detector** | Identifies billing discrepancies | Pattern matching, rule engine, ML scoring |
| **Claim Generator** | Creates dispute documentation | Template rendering, evidence assembly, citation |
| **Q&A Response Engine** | Handles carrier communications | Context management, response generation |
| **Contract Parser** | Extracts structured data from PDFs | GenAI extraction, validation, versioning |
| **Recovery Tracker** | Monitors claim lifecycle | Status tracking, outcome recording |
| **Workflow Orchestrator** | Coordinates multi-step processes | State management, event routing |

#### 3.2.3 Data Layer

| Component | Description | Storage |
|-----------|-------------|---------|
| **Invoice Store** | Carrier billing data | Celonis Data Pool |
| **Shipment Store** | TMS/WMS shipment records | Celonis Data Pool |
| **Contract Store** | Structured contract data | Celonis Object Store |
| **Claim Store** | Claim records and history | Celonis Data Pool |
| **Anomaly Store** | Detected anomalies | Celonis Data Pool |
| **Audit Log** | System activity records | Celonis Data Pool |

#### 3.2.4 Integration Layer

| Component | Description | Protocols |
|-----------|-------------|-----------|
| **Invoice Connector** | Ingests carrier invoices | PDF parsing, EDI (210/214) |
| **TMS Connector** | Retrieves shipment data | REST API, SFTP |
| **Carrier Portal Connector** | Submits claims (future) | REST API, RPA |

---

## 4. Data Architecture

### 4.1 Data Model Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA MODEL                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐       ┌───────────────┐       ┌───────────────┐     │
│  │   CARRIER     │       │   CONTRACT    │       │   CONTRACT    │     │
│  │               │──────▶│               │──────▶│   TERM        │     │
│  │ carrier_id    │       │ contract_id   │       │ term_id       │     │
│  │ name          │       │ carrier_id    │       │ contract_id   │     │
│  │ portal_url    │       │ effective_dt  │       │ term_type     │     │
│  └───────────────┘       │ expiration_dt │       │ conditions    │     │
│                          └───────────────┘       │ value         │     │
│                                                  └───────────────┘     │
│                                                                         │
│  ┌───────────────┐       ┌───────────────┐       ┌───────────────┐     │
│  │   INVOICE     │       │ INVOICE_LINE  │       │   SHIPMENT    │     │
│  │               │──────▶│               │◀──────│               │     │
│  │ invoice_id    │       │ line_id       │       │ shipment_id   │     │
│  │ carrier_id    │       │ invoice_id    │       │ pro_number    │     │
│  │ invoice_num   │       │ shipment_id   │       │ origin        │     │
│  │ invoice_dt    │       │ charge_type   │       │ destination   │     │
│  │ total_amount  │       │ amount        │       │ service_level │     │
│  └───────────────┘       └───────────────┘       │ ship_date     │     │
│                                 │                │ delivery_date │     │
│                                 ▼                └───────────────┘     │
│                          ┌───────────────┐                             │
│                          │   ANOMALY     │       ┌───────────────┐     │
│                          │               │──────▶│    CLAIM      │     │
│                          │ anomaly_id    │       │               │     │
│                          │ line_id       │       │ claim_id      │     │
│                          │ anomaly_type  │       │ anomaly_id    │     │
│                          │ expected_amt  │       │ status        │     │
│                          │ actual_amt    │       │ claim_text    │     │
│                          │ confidence    │       │ submitted_dt  │     │
│                          │ contract_ref  │       │ resolution_dt │     │
│                          └───────────────┘       │ outcome       │     │
│                                                  │ credit_amount │     │
│                                                  └───────────────┘     │
│                                                         │              │
│                                                         ▼              │
│                                                  ┌───────────────┐     │
│                                                  │ CLAIM_MESSAGE │     │
│                                                  │               │     │
│                                                  │ message_id    │     │
│                                                  │ claim_id      │     │
│                                                  │ direction     │     │
│                                                  │ content       │     │
│                                                  │ timestamp     │     │
│                                                  └───────────────┘     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Entity Definitions

#### 4.2.1 Carrier
```
CARRIER {
    carrier_id: UUID (PK)
    name: String
    code: String (e.g., "FEDX", "UPS")
    portal_url: String
    contact_email: String
    created_at: Timestamp
    updated_at: Timestamp
}
```

#### 4.2.2 Contract
```
CONTRACT {
    contract_id: UUID (PK)
    carrier_id: UUID (FK)
    contract_number: String
    effective_date: Date
    expiration_date: Date
    source_document: Binary (PDF)
    parsing_status: Enum (pending, processing, completed, failed)
    version: Integer
    created_at: Timestamp
    updated_at: Timestamp
}
```

#### 4.2.3 Contract Term
```
CONTRACT_TERM {
    term_id: UUID (PK)
    contract_id: UUID (FK)
    term_type: Enum (rate, surcharge, discount, sla, exception)
    service_level: String
    zone: String
    weight_min: Decimal
    weight_max: Decimal
    rate: Decimal
    conditions: JSON
    source_page: Integer
    source_text: String
    confidence_score: Decimal
    validated: Boolean
    created_at: Timestamp
}
```

#### 4.2.4 Invoice
```
INVOICE {
    invoice_id: UUID (PK)
    carrier_id: UUID (FK)
    invoice_number: String
    invoice_date: Date
    due_date: Date
    total_amount: Decimal
    currency: String
    source_type: Enum (pdf, edi, api)
    source_document: Binary
    processing_status: Enum (pending, processing, completed, failed)
    created_at: Timestamp
}
```

#### 4.2.5 Invoice Line
```
INVOICE_LINE {
    line_id: UUID (PK)
    invoice_id: UUID (FK)
    shipment_id: UUID (FK)
    line_number: Integer
    charge_type: String
    charge_description: String
    amount: Decimal
    weight: Decimal
    dimensions: JSON
    zone: String
    created_at: Timestamp
}
```

#### 4.2.6 Shipment
```
SHIPMENT {
    shipment_id: UUID (PK)
    pro_number: String
    tracking_number: String
    carrier_id: UUID (FK)
    origin_address: JSON
    destination_address: JSON
    service_level: String
    ship_date: Date
    expected_delivery: Date
    actual_delivery: Date
    weight: Decimal
    dimensions: JSON
    source_system: String (TMS/WMS/ERP)
    created_at: Timestamp
}
```

#### 4.2.7 Anomaly
```
ANOMALY {
    anomaly_id: UUID (PK)
    line_id: UUID (FK)
    anomaly_type: Enum (duplicate, rate_error, late_delivery, unauthorized_surcharge,
                        weight_discrepancy, address_correction, service_failure)
    expected_amount: Decimal
    actual_amount: Decimal
    variance: Decimal
    confidence_score: Decimal
    contract_reference: String
    contract_term_id: UUID (FK)
    detection_rule: String
    status: Enum (detected, validated, disputed, resolved)
    created_at: Timestamp
}
```

#### 4.2.8 Claim
```
CLAIM {
    claim_id: UUID (PK)
    anomaly_id: UUID (FK)
    claim_number: String
    status: Enum (draft, pending_approval, submitted, in_progress,
                  won, lost, withdrawn)
    claim_text: Text
    contract_citation: Text
    evidence_references: JSON
    submitted_date: Timestamp
    resolution_date: Timestamp
    outcome: Enum (approved, denied, partial)
    credit_amount: Decimal
    carrier_reference: String
    created_at: Timestamp
    updated_at: Timestamp
}
```

#### 4.2.9 Claim Message
```
CLAIM_MESSAGE {
    message_id: UUID (PK)
    claim_id: UUID (FK)
    direction: Enum (outbound, inbound)
    message_type: Enum (initial_claim, response, inquiry, resolution)
    content: Text
    attachments: JSON
    sender: String
    timestamp: Timestamp
}
```

### 4.3 Data Flow

```
                    ┌─────────────────┐
                    │  Carrier        │
                    │  Invoice (PDF)  │
                    └────────┬────────┘
                             │
                             ▼
┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│  TMS Shipment   │  │   Data Ingestion │  │  Contract PDF   │
│  Data           │─▶│   Pipeline       │◀─│  Upload         │
└─────────────────┘  └────────┬─────────┘  └─────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌────────────┐  ┌────────────┐  ┌────────────┐
       │  Invoice   │  │  Shipment  │  │  Contract  │
       │  Store     │  │  Store     │  │  Store     │
       └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
             │               │               │
             └───────────────┼───────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Anomaly         │
                    │  Detection       │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Contract        │
                    │  Validation      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Claim           │
                    │  Generation      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  User Review &   │
                    │  Approval        │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Claim           │
                    │  Submission      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Resolution      │
                    │  Tracking        │
                    └──────────────────┘
```

---

## 5. GenAI Architecture

### 5.1 GenAI Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GenAI SERVICES                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    CONTRACT INTELLIGENCE                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │  Document   │  │   Entity    │  │     Structure           │  │   │
│  │  │  Parser     │─▶│  Extractor  │─▶│     Builder             │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    CLAIM GENERATION                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │  Context    │  │   Claim     │  │     Citation            │  │   │
│  │  │  Assembler  │─▶│  Composer   │─▶│     Generator           │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Q&A RESPONSE ENGINE                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │  Query      │  │  Evidence   │  │     Response            │  │   │
│  │  │  Analyzer   │─▶│  Retriever  │─▶│     Generator           │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    SHARED SERVICES                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │  Prompt     │  │   Model     │  │     Embedding           │  │   │
│  │  │  Manager    │  │   Gateway   │  │     Service             │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Contract Intelligence Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PDF        │     │   OCR &      │     │   Section    │
│   Upload     │────▶│   Text       │────▶│   Detection  │
│              │     │   Extraction │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Contract   │     │   Validation │     │   Entity     │
│   Digital    │◀────│   &          │◀────│   Extraction │
│   Twin       │     │   Scoring    │     │   (GenAI)    │
└──────────────┘     └──────────────┘     └──────────────┘
```

**Entity Extraction Targets:**
- Rate tables (service level, zone, weight, rate)
- Discount structures (volume, commitment)
- Surcharge definitions (fuel, residential, peak, etc.)
- SLA terms (delivery timeframes, guarantees)
- Penalty clauses (late delivery refunds)
- Exception rules (holidays, weather, etc.)

### 5.3 Claim Generation Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Anomaly    │     │   Context    │     │   Contract   │
│   Record     │────▶│   Assembly   │────▶│   Lookup     │
│              │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Claim      │     │   Citation   │     │   Claim      │
│   Draft      │◀────│   Generation │◀────│   Composition│
│              │     │   (GenAI)    │     │   (GenAI)    │
└──────────────┘     └──────────────┘     └──────────────┘
```

**Claim Components:**
- Anomaly summary
- Invoice reference (number, date, line item)
- Shipment reference (PRO, tracking)
- Expected vs. actual charge
- Contract citation (section, page, text)
- Requested credit amount

### 5.4 Q&A Response Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Carrier    │     │   Query      │     │   Intent     │
│   Message    │────▶│   Parsing    │────▶│   Detection  │
│              │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Response   │     │   Response   │     │   Evidence   │
│   Draft      │◀────│   Generation │◀────│   Retrieval  │
│              │     │   (GenAI)    │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
```

**Common Carrier Queries Handled:**
- Request for proof of delivery
- Service level verification
- Rate validation requests
- Documentation requests
- Clarification requests

### 5.5 Model Configuration

| Use Case | Model Type | Characteristics |
|----------|------------|-----------------|
| Contract Parsing | LLM (Large) | High accuracy, complex reasoning |
| Entity Extraction | LLM (Medium) | Structured output, high throughput |
| Claim Composition | LLM (Large) | Natural language generation |
| Q&A Response | LLM (Large) | Context awareness, reasoning |
| Embeddings | Embedding Model | Semantic search, similarity |

---

## 6. Integration Architecture

### 6.1 Integration Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CARRIER COST AGENT                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    INTEGRATION HUB                               │   │
│  │                                                                  │   │
│  │   ┌──────────────────────────────────────────────────────────┐  │   │
│  │   │                 INBOUND CONNECTORS                        │  │   │
│  │   │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────────────┐  │  │   │
│  │   │  │  PDF   │  │  EDI   │  │  TMS   │  │  WMS/ERP       │  │  │   │
│  │   │  │ Parser │  │ Parser │  │  API   │  │  Connector     │  │  │   │
│  │   │  └────────┘  └────────┘  └────────┘  └────────────────┘  │  │   │
│  │   └──────────────────────────────────────────────────────────┘  │   │
│  │                                                                  │   │
│  │   ┌──────────────────────────────────────────────────────────┐  │   │
│  │   │                 OUTBOUND CONNECTORS                       │  │   │
│  │   │  ┌────────────────┐  ┌────────────────┐  ┌────────────┐  │  │   │
│  │   │  │  Carrier       │  │  Notification  │  │  Export    │  │  │   │
│  │   │  │  Portal API    │  │  Service       │  │  Service   │  │  │   │
│  │   │  └────────────────┘  └────────────────┘  └────────────┘  │  │   │
│  │   └──────────────────────────────────────────────────────────┘  │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────┐
    │  FedEx  │   │   UPS   │   │   TMS   │   │  ERP/WMS    │
    │ Portal  │   │ Portal  │   │ System  │   │  System     │
    └─────────┘   └─────────┘   └─────────┘   └─────────────┘
```

### 6.2 Invoice Ingestion

#### 6.2.1 PDF Processing
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   PDF       │     │   OCR       │     │   Structure │
│   Upload    │────▶│   Engine    │────▶│   Detection │
│             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   Field     │
                                        │   Extraction│
                                        │             │
                                        └─────────────┘
```

**Extracted Fields:**
- Invoice number, date, due date
- Carrier information
- Line item details
- Charge amounts and types
- Shipment references

#### 6.2.2 EDI Processing

**Supported EDI Transactions:**
| Transaction | Description |
|-------------|-------------|
| EDI 210 | Motor Carrier Freight Details and Invoice |
| EDI 214 | Transportation Carrier Shipment Status |

### 6.3 TMS/WMS Integration

**Integration Patterns:**
| Pattern | Use Case | Protocol |
|---------|----------|----------|
| Batch Pull | Historical data load | SFTP, API |
| Real-time Push | New shipment events | Webhook, API |
| Query | On-demand lookups | REST API |

**Common TMS Systems:**
- Oracle Transportation Management
- SAP TM
- Blue Yonder TMS
- Manhattan TMS
- Descartes

### 6.4 API Specification

#### 6.4.1 REST API Endpoints

```
# Invoice Management
POST   /api/v1/invoices              # Upload invoice
GET    /api/v1/invoices/{id}         # Get invoice details
GET    /api/v1/invoices              # List invoices

# Anomaly Management
GET    /api/v1/anomalies             # List anomalies
GET    /api/v1/anomalies/{id}        # Get anomaly details
PUT    /api/v1/anomalies/{id}/status # Update anomaly status

# Claim Management
POST   /api/v1/claims                # Create claim
GET    /api/v1/claims/{id}           # Get claim details
PUT    /api/v1/claims/{id}           # Update claim
POST   /api/v1/claims/{id}/submit    # Submit claim
POST   /api/v1/claims/{id}/messages  # Add message

# Contract Management
POST   /api/v1/contracts             # Upload contract
GET    /api/v1/contracts/{id}        # Get contract details
GET    /api/v1/contracts/{id}/terms  # Get contract terms

# Analytics
GET    /api/v1/analytics/recovery    # Recovery metrics
GET    /api/v1/analytics/anomalies   # Anomaly metrics
```

#### 6.4.2 Webhook Events

```
# Events published
invoice.processed
anomaly.detected
claim.created
claim.submitted
claim.resolved
contract.parsed
```

---

## 7. Anomaly Detection Engine

### 7.1 Detection Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ANOMALY DETECTION ENGINE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐                                                      │
│  │   Invoice     │                                                      │
│  │   Line Item   │                                                      │
│  └───────┬───────┘                                                      │
│          │                                                              │
│          ▼                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    DETECTION PIPELINE                              │ │
│  │                                                                    │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │ │
│  │  │  Rule-Based │  │   ML-Based  │  │  Contract   │               │ │
│  │  │  Detection  │  │  Detection  │  │  Validation │               │ │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │ │
│  │         │                │                │                       │ │
│  │         └────────────────┼────────────────┘                       │ │
│  │                          ▼                                        │ │
│  │                   ┌─────────────┐                                 │ │
│  │                   │  Anomaly    │                                 │ │
│  │                   │  Aggregator │                                 │ │
│  │                   └──────┬──────┘                                 │ │
│  │                          │                                        │ │
│  └──────────────────────────┼────────────────────────────────────────┘ │
│                             ▼                                          │
│                      ┌─────────────┐                                   │
│                      │  Confidence │                                   │
│                      │  Scoring    │                                   │
│                      └──────┬──────┘                                   │
│                             │                                          │
│                             ▼                                          │
│                      ┌─────────────┐                                   │
│                      │  Anomaly    │                                   │
│                      │  Store      │                                   │
│                      └─────────────┘                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Anomaly Types and Detection Rules

#### 7.2.1 Duplicate Charges
```
RULE: Duplicate Detection
CONDITIONS:
  - Same PRO number appears on multiple invoice lines
  - Same shipment_id with same charge_type
  - Same tracking number with identical amount
CONFIDENCE: HIGH when all identifiers match
```

#### 7.2.2 Rate Errors
```
RULE: Rate Validation
CONDITIONS:
  - Invoice rate != Contract rate for (service_level, zone, weight)
  - Variance exceeds threshold (default: $0.01)
REQUIRES: Contract Digital Twin
CONFIDENCE: Based on contract term confidence score
```

#### 7.2.3 Late Delivery Charges
```
RULE: Late Delivery False Charge
CONDITIONS:
  - Invoice contains late delivery surcharge
  - Shipment actual_delivery <= expected_delivery
REQUIRES: Shipment data from TMS
CONFIDENCE: HIGH when delivery timestamps are verified
```

#### 7.2.4 Unauthorized Surcharges
```
RULE: Surcharge Validation
CONDITIONS:
  - Invoice surcharge type not in contract surcharge list
  - Surcharge amount exceeds contracted cap
REQUIRES: Contract Digital Twin
CONFIDENCE: Based on surcharge term extraction confidence
```

#### 7.2.5 Weight/Dimension Discrepancies
```
RULE: Weight Validation
CONDITIONS:
  - Invoice weight > Shipment actual weight + tolerance
  - Invoice dim weight calculated incorrectly
REQUIRES: Shipment data with actual weights
CONFIDENCE: MEDIUM (depends on weight data accuracy)
```

#### 7.2.6 Address Correction Fees
```
RULE: Address Correction Validation
CONDITIONS:
  - Invoice contains address correction charge
  - Original address matches delivery address
REQUIRES: Shipment data with address history
CONFIDENCE: HIGH when address data is complete
```

#### 7.2.7 Service Failures
```
RULE: Service Failure Detection
CONDITIONS:
  - Shipment not delivered
  - Shipment delivered significantly late (>SLA threshold)
  - Damage claims filed
REQUIRES: Shipment status data, claims data
CONFIDENCE: Based on delivery status confidence
```

### 7.3 Confidence Scoring

| Score Range | Classification | Action |
|-------------|----------------|--------|
| 0.9 - 1.0 | High | Auto-generate claim |
| 0.7 - 0.9 | Medium | Generate claim for review |
| 0.5 - 0.7 | Low | Flag for manual investigation |
| < 0.5 | Very Low | Log only, no action |

---

## 8. Security Architecture

### 8.1 Security Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SECURITY ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    PERIMETER SECURITY                            │   │
│  │  • WAF (Web Application Firewall)                               │   │
│  │  • DDoS Protection                                              │   │
│  │  • IP Whitelisting (optional)                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    IDENTITY & ACCESS                             │   │
│  │  • SSO Integration (SAML 2.0, OIDC)                             │   │
│  │  • Role-Based Access Control (RBAC)                             │   │
│  │  • API Key Management                                           │   │
│  │  • MFA Enforcement                                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DATA SECURITY                                 │   │
│  │  • Encryption at Rest (AES-256)                                 │   │
│  │  • Encryption in Transit (TLS 1.3)                              │   │
│  │  • Data Masking for PII                                         │   │
│  │  • Key Management (Customer-managed option)                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AUDIT & COMPLIANCE                            │   │
│  │  • Comprehensive Audit Logging                                  │   │
│  │  • Data Retention Policies                                      │   │
│  │  • SOC 2 Type II Compliance                                     │   │
│  │  • GDPR Compliance                                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Role-Based Access Control

| Role | Permissions |
|------|-------------|
| **Viewer** | View dashboards, view claims (read-only) |
| **Analyst** | View + create claims, add messages |
| **Approver** | Analyst + approve/submit claims |
| **Contract Manager** | Upload/manage contracts, validate terms |
| **Administrator** | Full access, user management, configuration |

### 8.3 Data Classification

| Classification | Examples | Handling |
|----------------|----------|----------|
| **Confidential** | Contract terms, rates | Encrypted, access-controlled |
| **Internal** | Invoice data, claims | Encrypted, logged access |
| **Restricted** | PII (names, addresses) | Masked, limited retention |

---

## 9. Deployment Architecture

### 9.1 Celonis Platform Deployment

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CELONIS CLOUD PLATFORM                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    EXECUTION MANAGEMENT SYSTEM (EMS)              │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐  │  │
│  │  │   Celonis      │  │   Celonis      │  │    Celonis         │  │  │
│  │  │   Studio       │  │   Apps         │  │    Action Engine   │  │  │
│  │  └────────────────┘  └────────────────┘  └────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    PROCESS INTELLIGENCE                           │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐  │  │
│  │  │   Data Pool    │  │   Process      │  │    ML/AI           │  │  │
│  │  │   (Storage)    │  │   Mining       │  │    Workbench       │  │  │
│  │  └────────────────┘  └────────────────┘  └────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    CARRIER COST AGENT SERVICES                    │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐  │  │
│  │  │   Agent        │  │   GenAI        │  │    Integration     │  │  │
│  │  │   Runtime      │  │   Services     │  │    Services        │  │  │
│  │  └────────────────┘  └────────────────┘  └────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Component Hosting

| Component | Hosting | Technology |
|-----------|---------|------------|
| UI/Dashboard | Celonis Studio | Celonis native |
| Application Services | Celonis Apps | Celonis runtime |
| Data Storage | Celonis Data Pool | Vertica |
| GenAI Services | Celonis AI | LLM integration |
| Integration | Celonis Extractor | ETL framework |

### 9.3 Environment Strategy

| Environment | Purpose | Data |
|-------------|---------|------|
| **Development** | Feature development | Synthetic data |
| **Staging** | Integration testing | Anonymized production data |
| **Production** | Live customer use | Customer data |

---

## 10. Performance and Scalability

### 10.1 Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Invoice ingestion | 1,000+ invoices/hour | Throughput |
| Anomaly detection | <5 seconds/invoice | Latency |
| Contract parsing | <10 minutes/100 pages | Duration |
| Claim generation | <30 seconds | Latency |
| Dashboard load | <3 seconds | Latency |
| API response | <500ms (p95) | Latency |

### 10.2 Scalability Targets

| Dimension | Target |
|-----------|--------|
| Invoices per customer per year | 10M+ |
| Concurrent users per customer | 50+ |
| Contracts per customer | 100+ |
| Historical data retention | 7 years |

### 10.3 Scaling Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SCALING ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │                    HORIZONTAL SCALING                              ││
│  │  • Stateless application services                                  ││
│  │  • Auto-scaling based on queue depth                               ││
│  │  • Load balancing across service instances                         ││
│  └────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │                    ASYNC PROCESSING                                ││
│  │  • Message queues for invoice processing                           ││
│  │  • Background jobs for contract parsing                            ││
│  │  • Event-driven anomaly detection                                  ││
│  └────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │                    CACHING                                         ││
│  │  • Contract terms cached in memory                                 ││
│  │  • Rate tables cached for fast lookup                              ││
│  │  • Dashboard queries cached                                        ││
│  └────────────────────────────────────────────────────────────────────┘│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Monitoring and Observability

### 11.1 Monitoring Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      OBSERVABILITY STACK                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │
│  │    METRICS      │  │    LOGGING      │  │    TRACING              │ │
│  │                 │  │                 │  │                         │ │
│  │  • Throughput   │  │  • App logs     │  │  • Request tracing      │ │
│  │  • Latency      │  │  • Audit logs   │  │  • GenAI call tracing   │ │
│  │  • Error rates  │  │  • Error logs   │  │  • Integration tracing  │ │
│  │  • Queue depth  │  │  • Access logs  │  │                         │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘ │
│           │                   │                       │                 │
│           └───────────────────┼───────────────────────┘                 │
│                               ▼                                         │
│                    ┌─────────────────────┐                             │
│                    │    DASHBOARDS &     │                             │
│                    │    ALERTING         │                             │
│                    └─────────────────────┘                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Key Metrics

| Category | Metric | Alert Threshold |
|----------|--------|-----------------|
| **Availability** | Service uptime | <99.9% |
| **Latency** | API p95 response time | >500ms |
| **Throughput** | Invoices processed/hour | <500 |
| **Errors** | Error rate | >1% |
| **GenAI** | Contract parsing failures | >5% |
| **Business** | Anomalies detected/day | Anomaly |

### 11.3 Alerting Rules

| Severity | Condition | Response |
|----------|-----------|----------|
| **Critical** | Service down | Immediate page |
| **High** | Error rate >5% | Page within 15 min |
| **Medium** | Latency >2x baseline | Ticket creation |
| **Low** | Queue backlog | Daily review |

---

## 12. Disaster Recovery

### 12.1 Recovery Objectives

| Metric | Target |
|--------|--------|
| Recovery Point Objective (RPO) | 1 hour |
| Recovery Time Objective (RTO) | 4 hours |

### 12.2 Backup Strategy

| Data Type | Backup Frequency | Retention |
|-----------|-----------------|-----------|
| Transactional data | Continuous | 30 days |
| Configuration | Daily | 90 days |
| Contracts (PDF) | On upload | 7 years |
| Audit logs | Continuous | 7 years |

### 12.3 Failover Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DISASTER RECOVERY                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────┐       ┌─────────────────────────┐         │
│  │    PRIMARY REGION       │       │    SECONDARY REGION     │         │
│  │                         │       │                         │         │
│  │  ┌─────────────────┐   │       │   ┌─────────────────┐   │         │
│  │  │  Application    │   │       │   │  Application    │   │         │
│  │  │  Services       │   │  ───▶ │   │  Services       │   │         │
│  │  └─────────────────┘   │ Sync  │   └─────────────────┘   │         │
│  │                         │       │                         │         │
│  │  ┌─────────────────┐   │       │   ┌─────────────────┐   │         │
│  │  │  Data Store     │   │  ───▶ │   │  Data Store     │   │         │
│  │  │  (Primary)      │   │ Repl  │   │  (Replica)      │   │         │
│  │  └─────────────────┘   │       │   └─────────────────┘   │         │
│  │                         │       │                         │         │
│  └─────────────────────────┘       └─────────────────────────┘         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 13. Implementation Roadmap

### 13.1 Phase 1: MVP (Pilot)

**Duration:** 8-12 weeks
**Scope:** FedEx US invoices for Ingka/IKEA

```
Week 1-2:  Infrastructure setup, data model implementation
Week 3-4:  Invoice ingestion (PDF), basic parsing
Week 5-6:  Core anomaly detection (duplicates, rate errors)
Week 7-8:  Contract parsing MVP, basic Digital Twin
Week 9-10: Claim generation, user review workflow
Week 11-12: Dashboard, testing, pilot deployment
```

**Deliverables:**
- [ ] Invoice ingestion pipeline
- [ ] 4 anomaly detection rules
- [ ] Basic contract parsing
- [ ] Claim generation
- [ ] Recovery dashboard

### 13.2 Phase 2: GA Release

**Duration:** 12-16 weeks
**Scope:** Multi-carrier, full feature set

```
Week 1-4:   EDI support, additional carriers
Week 5-8:   Full anomaly detection suite
Week 9-12:  Q&A Response Engine
Week 13-16: Advanced analytics, API integrations
```

**Deliverables:**
- [ ] EDI 210/214 support
- [ ] Full anomaly detection (7+ types)
- [ ] Q&A Response Engine
- [ ] API for integrations
- [ ] Advanced analytics

### 13.3 Phase 3: Platform Extension

**Duration:** Ongoing
**Scope:** Enterprise features

- Custom anomaly rules
- Multi-region deployment
- Carrier portal integrations
- Advanced ML optimization
- White-label options

---

## 14. Technical Decisions and Trade-offs

### 14.1 Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Platform | Celonis native | Customer ecosystem, data access |
| GenAI approach | LLM for contract parsing | Handles unstructured complexity |
| Detection method | Hybrid (rules + ML) | Explainability + flexibility |
| Integration | API-first | Flexibility for TMS diversity |
| Data storage | Celonis Data Pool | Platform alignment |

### 14.2 Trade-offs

| Trade-off | Decision | Impact |
|-----------|----------|--------|
| Accuracy vs. Speed | Favor accuracy for claims | Longer processing, higher quality |
| Automation vs. Control | Human-in-the-loop | Slower but safer claim submission |
| Generalization vs. Customization | Start specific (FedEx) | Faster time-to-value, iterate |

---

## 15. Appendix

### 15.1 Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Celonis Studio, Celonis Apps |
| Backend | Celonis Action Engine |
| Database | Celonis Data Pool (Vertica) |
| GenAI | Celonis AI / LLM Integration |
| Integration | Celonis Extractor Framework |
| Authentication | Celonis IAM + SSO |

### 15.2 Glossary

| Term | Definition |
|------|------------|
| **Digital Twin** | Structured representation of carrier contract |
| **EDI** | Electronic Data Interchange |
| **EMS** | Execution Management System (Celonis) |
| **LLM** | Large Language Model |
| **PRO Number** | Progressive number (freight shipment ID) |
| **TMS** | Transportation Management System |
| **WMS** | Warehouse Management System |

### 15.3 References

- Celonis Platform Documentation
- Celonis AI/ML Workbench Documentation
- EDI 210/214 Specifications
- FedEx API Documentation
