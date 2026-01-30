# Product Requirements Document (PRD)
## Celonis Carrier Cost Agent powered by Logatik

| Field | Value |
|-------|-------|
| **Product Name** | Celonis Carrier Cost Agent powered by Logatik |
| **PMM** | @pmm |
| **PM** | @person |
| **Key Stakeholders** | Logatik Team (Patrick Groth, Philipp Winklmann, Valentin Lorenz), Celonis Partner Management, Pilot Customer (Ingka/IKEA) |
| **Last Updated** | 28th of January, 2026 |
| **Release Scope** | Celosphere 2026 |
| **Status** | Co-Innovation Scoping (Ingka Pilot) |

---

## 1. Executive Summary

The Celonis Carrier Cost Agent is an AI-powered solution that automates carrier invoice validation and cost recovery. Built on the Celonis platform, it transforms freight audit from a reactive cost-center into a proactive value-recovery engine using GenAI-driven contract intelligence.

**Target Impact:** 3-7% of shipment spend recovered/prevented
- Conrad: €33 million potential
- INGKA US: €68 million potential

---

## 2. Problem Statement

### 2.1 Current State
Ingka (IKEA) processes massive shipment volumes via FedEx US. Manual audit is currently reactive, leaving millions in recoverable overcharges (duplicates, errors, surcharges) on the table because billing cannot be systematically matched against 100+ page PDF contracts.

### 2.2 Pain Points

| Pain Point | Description | Impact |
|------------|-------------|--------|
| **Discovery Lag** | Billing errors are found by accident, not by design | Revenue leakage goes undetected |
| **Evidence Gaps** | Finding the right shipment data vs. contract clause takes hours | Claims are incomplete or abandoned |
| **Carrier Pushback** | Disputes are abandoned or outsourced because responding to carrier Q&A is too labor-intensive | Low recovery rates |
| **Institutional Memory Loss** | Each claim starts from scratch without a history of won/lost patterns | Repeated mistakes, no learning |
| **Unstructured Contracts** | 100+ page PDFs with conditional logic that existing systems can't query | Cannot validate charges programmatically |

### 2.3 Why Standard Tools Fail
Standard BI tools only show the error; they don't:
- Draft the claim
- Cite the contract
- Handle carrier back-and-forth
- Track resolution to completion

---

## 3. User Personas

### 3.1 Primary User: Freight Analyst / AP Claims Specialist

**Role:** Manages manual evidence gathering for carrier disputes

**Current Challenges:**
- Relies on ad-hoc spot checks or accidental discovery
- Struggles to parse complex contract terms across thousands of lines
- Spends ~45 minutes per claim gathering evidence
- Cannot scale audit coverage beyond <5% of invoices

**Goals:**
- Automated anomaly detection across all invoices
- Quick access to relevant contract clauses
- Pre-drafted claims with proper citations
- Efficient handling of carrier responses

### 3.2 Buying Personas (Decision Makers)

| Persona | Focus Area | Key Concern |
|---------|------------|-------------|
| **VP Supply Chain / COO** | Operational efficiency | Audit coverage and team productivity |
| **CFO / Head of Finance** | Cost recovery | Bottom-line impact and ROI |
| **Head of Logistics Operations** | Process optimization | Reducing manual workload |

### 3.3 Influencers

| Persona | Role in Decision |
|---------|------------------|
| **Procurement** | Owns carrier contract negotiations; needs structured contract data |
| **IT Directors** | System integration for TMS/ERP data connectivity |

---

## 4. Business Objectives

### 4.1 Primary Objective
Enable customers to systematically recover shipping overcharges that are currently lost to manual complexity. Transform the "Freight Audit" function from a cost-center into a value-recovery engine.

### 4.2 Success Metrics

| Metric | Current State | Target State |
|--------|--------------|--------------|
| **Audit Coverage** | <5% spot checks | 100% of carrier invoices scanned |
| **Time per Claim** | ~45 minutes | <5 minutes |
| **Claim Success Rate** | Baseline | +20% improvement through better contract citation |
| **Recovery Rate** | Unknown | 15-25% of all identified anomalies successfully credited |
| **Spend Recovery** | Reactive/minimal | 3-7% of shipment spend recovered/prevented |

---

## 5. Product Description

### 5.1 Overview
An AI-powered agent that:
1. Detects billing anomalies
2. Validates them against structured versions of PDF contracts
3. Generates portal-ready claims
4. Handles the carrier Q&A loop to recover overcharges

### 5.2 Key Features

#### 5.2.1 Invoice Anomaly Detection
**Description:** Auto-detects billing anomalies across all line items

**Anomaly Patterns Detected:**
1. Duplicate charges
2. Late delivery charges (when delivery was on-time)
3. Service failures
4. Incorrect rate application
5. Unauthorized surcharges
6. Weight/dimension discrepancies
7. Address correction fees (when address was correct)

**Requirements:**
- REQ-001: System shall scan 100% of incoming carrier invoices
- REQ-002: System shall identify duplicates based on PRO number, shipment ID, and charge amount
- REQ-003: System shall flag charges that exceed contracted rates
- REQ-004: System shall cross-reference delivery dates against service level commitments
- REQ-005: System shall detect surcharges not defined in active contract

#### 5.2.2 GenAI Contract Intelligence
**Description:** Parses 100+ page carrier PDFs into structured rules

**Capabilities:**
- Extract rate tables and discount structures
- Map surcharge triggers and thresholds
- Identify conditional clauses and exceptions
- Maintain version history of contract changes

**Requirements:**
- REQ-006: System shall ingest PDF contracts up to 200 pages
- REQ-007: System shall extract rate cards with carrier, service level, zone, weight break, and rate
- REQ-008: System shall identify surcharge conditions (fuel, residential, peak, etc.)
- REQ-009: System shall maintain a structured "Digital Twin" of each contract
- REQ-010: System shall support contract versioning with effective date tracking

#### 5.2.3 Automated Claim Generation
**Description:** Drafts category-specific dispute text with evidence

**Capabilities:**
- Generate carrier-portal-ready claim text
- Include exact invoice references
- Cite specific contract sections
- Attach supporting documentation references

**Requirements:**
- REQ-011: System shall generate claim drafts within 30 seconds of user request
- REQ-012: Claims shall include invoice number, line item, charge amount, and expected amount
- REQ-013: Claims shall cite specific contract clause supporting the dispute
- REQ-014: System shall provide category-specific templates (duplicate, rate error, service failure, etc.)
- REQ-015: User shall be able to edit and approve claims before submission

#### 5.2.4 Q&A Response Engine
**Description:** Handles carrier pushback with evidence-based replies

**Capabilities:**
- Maintain context of ongoing disputes
- Suggest evidence-based replies
- Track carrier response patterns
- Learn from successful dispute resolutions

**Requirements:**
- REQ-016: System shall maintain full conversation history per claim
- REQ-017: System shall suggest responses based on carrier questions
- REQ-018: Responses shall reference specific shipment data and contract terms
- REQ-019: System shall flag claims requiring human escalation
- REQ-020: System shall learn from won/lost claim patterns

#### 5.2.5 Recovery Tracking Dashboard
**Description:** ROI dashboard tracking realized savings

**Capabilities:**
- Track claims from "identified" to "credited"
- Calculate realized vs. potential recovery
- Segment by carrier, anomaly type, and time period
- Export reports for stakeholder communication

**Requirements:**
- REQ-021: Dashboard shall show claim pipeline by status (identified, submitted, in-progress, won, lost)
- REQ-022: Dashboard shall calculate total recovery value by period
- REQ-023: Dashboard shall show recovery rate by anomaly category
- REQ-024: Dashboard shall support drill-down to individual claims
- REQ-025: Dashboard shall export to PDF/Excel for reporting

---

## 6. Functional Requirements

### 6.1 Data Ingestion

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | Ingest carrier invoices in PDF format | P0 |
| FR-002 | Ingest carrier invoices in EDI format (210, 214) | P0 |
| FR-003 | Connect to TMS systems for shipment data | P0 |
| FR-004 | Connect to WMS systems for fulfillment data | P1 |
| FR-005 | Connect to ERP systems for order data | P1 |
| FR-006 | Support batch and real-time data ingestion | P0 |
| FR-007 | Validate data quality and flag incomplete records | P1 |

### 6.2 Anomaly Detection

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-008 | Detect duplicate charges across invoices | P0 |
| FR-009 | Identify rate discrepancies vs. contract | P0 |
| FR-010 | Flag late delivery charges for on-time shipments | P0 |
| FR-011 | Detect unauthorized surcharges | P0 |
| FR-012 | Identify weight/dimension billing errors | P1 |
| FR-013 | Flag address correction fees for valid addresses | P1 |
| FR-014 | Support custom anomaly rules per customer | P2 |

### 6.3 Contract Management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-015 | Upload and parse carrier contracts (PDF) | P0 |
| FR-016 | Create structured contract "Digital Twin" | P0 |
| FR-017 | Extract and store rate tables | P0 |
| FR-018 | Map surcharge conditions and thresholds | P0 |
| FR-019 | Support multiple contract versions | P1 |
| FR-020 | Track contract effective dates and expiration | P1 |
| FR-021 | Highlight contract changes between versions | P2 |

### 6.4 Claim Management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-022 | Generate draft claims automatically | P0 |
| FR-023 | Allow user review and editing of claims | P0 |
| FR-024 | Support claim approval workflow | P1 |
| FR-025 | Track claim status through lifecycle | P0 |
| FR-026 | Generate carrier-specific claim formats | P1 |
| FR-027 | Batch claim submission capability | P2 |

### 6.5 Q&A and Dispute Resolution

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-028 | Log carrier responses to claims | P0 |
| FR-029 | Generate suggested responses to carrier queries | P0 |
| FR-030 | Maintain dispute conversation history | P0 |
| FR-031 | Support document attachment to responses | P1 |
| FR-032 | Escalation workflow for complex disputes | P1 |

### 6.6 Reporting and Analytics

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-033 | Dashboard showing claim pipeline | P0 |
| FR-034 | Recovery metrics by carrier | P0 |
| FR-035 | Recovery metrics by anomaly type | P0 |
| FR-036 | Time-series analysis of recoveries | P1 |
| FR-037 | Export capabilities (PDF, Excel) | P1 |
| FR-038 | Scheduled report generation | P2 |

---

## 7. Non-Functional Requirements

### 7.1 Performance

| ID | Requirement |
|----|-------------|
| NFR-001 | Invoice processing: >1000 invoices/hour |
| NFR-002 | Anomaly detection: <5 seconds per invoice |
| NFR-003 | Claim generation: <30 seconds |
| NFR-004 | Dashboard load time: <3 seconds |
| NFR-005 | Contract parsing: <10 minutes for 100-page PDF |

### 7.2 Scalability

| ID | Requirement |
|----|-------------|
| NFR-006 | Support 10M+ invoices per year per customer |
| NFR-007 | Support 50+ concurrent users per customer |
| NFR-008 | Support 100+ carrier contracts per customer |

### 7.3 Security

| ID | Requirement |
|----|-------------|
| NFR-009 | Data encryption at rest (AES-256) |
| NFR-010 | Data encryption in transit (TLS 1.3) |
| NFR-011 | Role-based access control (RBAC) |
| NFR-012 | Audit logging for all user actions |
| NFR-013 | SOC 2 Type II compliance |
| NFR-014 | GDPR compliance for EU operations |

### 7.4 Availability

| ID | Requirement |
|----|-------------|
| NFR-015 | 99.9% uptime SLA |
| NFR-016 | Automated failover for critical components |
| NFR-017 | Recovery Point Objective (RPO): 1 hour |
| NFR-018 | Recovery Time Objective (RTO): 4 hours |

### 7.5 Integration

| ID | Requirement |
|----|-------------|
| NFR-019 | RESTful API for all core functions |
| NFR-020 | Webhook support for event notifications |
| NFR-021 | SSO integration (SAML 2.0, OIDC) |
| NFR-022 | Native Celonis platform integration |

---

## 8. User Workflows

### 8.1 Daily Claim Review Workflow

```
1. Analyst logs into Carrier Cost Agent
2. Dashboard shows new anomalies detected overnight
3. Analyst reviews top-priority anomalies
4. For each anomaly:
   a. View anomaly details and contract reference
   b. Review auto-generated claim draft
   c. Edit if necessary
   d. Approve for submission
5. System submits approved claims to carrier portals
6. Analyst reviews any carrier responses requiring action
```

### 8.2 Contract Upload Workflow

```
1. User uploads new carrier contract PDF
2. System parses contract using GenAI
3. System presents extracted rates and terms for validation
4. User reviews and corrects any extraction errors
5. User confirms contract effective dates
6. System activates contract for anomaly validation
```

### 8.3 Dispute Resolution Workflow

```
1. Carrier responds to submitted claim
2. System logs response and analyzes content
3. System generates suggested reply with evidence
4. Analyst reviews and approves response
5. If escalation needed, system routes to supervisor
6. Process repeats until resolution
7. Outcome logged for learning
```

---

## 9. Competitive Positioning

### 9.1 Competitive Landscape

| Alternative | Description | Limitations |
|-------------|-------------|-------------|
| **Manual Audit** | Internal teams doing spot checks | Slow, <5% coverage, no scalability |
| **3rd Party Audit & Pay** | External firms handle audits | Charge 15-30% of recovery, high data friction |
| **Standard BI** | TMS dashboards | Detection only, no action or claim generation |
| **Specialized Software** | Point solutions | No agentic features, no WMS/TMS access, manual contract setup |

### 9.2 Differentiation

| Capability | Carrier Cost Agent | Competitors |
|------------|-------------------|-------------|
| AI-powered anomaly detection | Yes | Partial |
| GenAI contract parsing | Yes | No |
| Automated claim generation | Yes | No |
| Q&A response engine | Yes | No |
| Celonis platform integration | Native | None |
| End-to-end workflow | Yes | Fragmented |

---

## 10. Positioning Guidelines

### 10.1 What We Are
- AI-powered agent that drafts claims and interprets contract text
- Software-led automation of the audit cycle
- Works with existing TMS shipment data
- Validates what was paid to carriers

### 10.2 What We Are NOT
- **Not a TMS replacement:** Works with shipment data from existing TMS
- **Not a simple dashboard:** It is an Agent that drafts claims and interprets text
- **Not a financial payment service:** We do not pay the carriers, we validate what was paid
- **Not a consulting project:** Software-led automation of the audit cycle

---

## 11. Release Phases

### Phase 1: MVP (Pilot with Ingka/IKEA)
**Scope:** FedEx US invoices
- Invoice ingestion (PDF)
- Core anomaly detection (duplicates, rate errors, late delivery)
- Basic contract parsing
- Claim generation
- Manual claim submission
- Basic recovery dashboard

### Phase 2: GA Release
**Scope:** Multi-carrier support
- EDI invoice support
- Full anomaly detection suite
- Advanced contract intelligence
- Q&A response engine
- API integrations
- Full analytics suite

### Phase 3: Platform Extension
**Scope:** Enterprise features
- Custom anomaly rules
- Multi-region support
- Advanced learning/optimization
- Carrier portal integrations
- White-label capabilities

---

## 12. Success Criteria for Pilot

| Criterion | Target |
|-----------|--------|
| Invoices processed | 100% of FedEx US invoices |
| Anomalies identified | Document baseline |
| Claims generated | 50+ claims in pilot period |
| Time savings | Demonstrate <5 min per claim |
| Recovery value | Identify $X in recoverable charges |
| User satisfaction | Positive feedback from pilot users |

---

## 13. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Contract parsing accuracy | High | Medium | Human validation workflow; iterative AI improvement |
| Carrier response variability | Medium | High | Flexible Q&A engine; escalation paths |
| Data integration complexity | High | Medium | Start with FedEx; phased carrier onboarding |
| User adoption | High | Low | Clear ROI demonstration; training program |
| Regulatory compliance | High | Low | Legal review of automated claim submission |

---

## 14. Appendix

### 14.1 Glossary

| Term | Definition |
|------|------------|
| **Anomaly** | A billing discrepancy between carrier invoice and expected charge |
| **Digital Twin** | Structured representation of carrier contract terms |
| **EDI** | Electronic Data Interchange; standard format for business documents |
| **PRO Number** | Progressive number; unique identifier for freight shipments |
| **TMS** | Transportation Management System |
| **WMS** | Warehouse Management System |
| **ERP** | Enterprise Resource Planning system |

### 14.2 References
- Celonis Platform Documentation
- FedEx Billing Specifications
- EDI 210 (Freight Invoice) Standard
- EDI 214 (Shipment Status) Standard
