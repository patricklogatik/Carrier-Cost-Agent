-- Contract Term table for Celonis Data Pool (Vertica)
-- Stores extracted contract terms (rates, surcharges, SLAs)

CREATE TABLE IF NOT EXISTS contract_term (
    term_id VARCHAR(36) PRIMARY KEY,
    contract_id VARCHAR(36) NOT NULL REFERENCES contract(contract_id),
    term_type VARCHAR(20) NOT NULL,  -- rate, surcharge, discount, sla, exception
    service_level VARCHAR(100),
    zone VARCHAR(20),
    weight_min DECIMAL(10,2),
    weight_max DECIMAL(10,2),
    rate DECIMAL(15,4),
    rate_type VARCHAR(20),  -- flat, per_pound, percentage
    conditions VARCHAR(65000),  -- JSON conditions
    source_page INTEGER,
    source_text VARCHAR(65000),
    confidence_score DECIMAL(5,4),
    validated BOOLEAN DEFAULT FALSE,
    validated_by VARCHAR(255),
    validated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_term_type CHECK (term_type IN ('rate', 'surcharge', 'discount', 'sla', 'exception')),
    CONSTRAINT chk_rate_type CHECK (rate_type IN ('flat', 'per_pound', 'percentage'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_term_contract ON contract_term(contract_id);
CREATE INDEX IF NOT EXISTS idx_term_type ON contract_term(term_type);
CREATE INDEX IF NOT EXISTS idx_term_service_level ON contract_term(service_level);
CREATE INDEX IF NOT EXISTS idx_term_zone ON contract_term(zone);
CREATE INDEX IF NOT EXISTS idx_term_validated ON contract_term(validated);

COMMENT ON TABLE contract_term IS 'Extracted contract terms for anomaly validation';
