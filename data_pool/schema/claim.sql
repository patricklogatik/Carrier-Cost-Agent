-- Claim table for Celonis Data Pool (Vertica)
-- Stores carrier dispute claims

CREATE TABLE IF NOT EXISTS claim (
    claim_id VARCHAR(36) PRIMARY KEY,
    anomaly_id VARCHAR(36) NOT NULL REFERENCES anomaly(anomaly_id),
    claim_number VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',  -- draft, pending_approval, submitted, in_progress, won, lost, withdrawn
    claim_subject VARCHAR(500),
    claim_text VARCHAR(65000) NOT NULL,
    contract_citation VARCHAR(65000),
    evidence_references VARCHAR(65000),  -- JSON references to supporting documents
    requested_credit DECIMAL(15,2) NOT NULL,
    credit_amount DECIMAL(15,2),  -- Actual credit received
    carrier_reference VARCHAR(100),  -- Carrier's claim ID
    outcome VARCHAR(20),  -- approved, denied, partial
    submitted_date TIMESTAMP,
    resolution_date TIMESTAMP,
    submitted_by VARCHAR(255),
    approved_by VARCHAR(255),
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_claim_status CHECK (status IN (
        'draft', 'pending_approval', 'submitted', 'in_progress', 'won', 'lost', 'withdrawn'
    )),
    CONSTRAINT chk_claim_outcome CHECK (outcome IS NULL OR outcome IN ('approved', 'denied', 'partial')),
    CONSTRAINT uk_claim_number UNIQUE (claim_number)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_claim_anomaly ON claim(anomaly_id);
CREATE INDEX IF NOT EXISTS idx_claim_status ON claim(status);
CREATE INDEX IF NOT EXISTS idx_claim_number ON claim(claim_number);
CREATE INDEX IF NOT EXISTS idx_claim_submitted ON claim(submitted_date);

COMMENT ON TABLE claim IS 'Carrier dispute claims for cost recovery';
