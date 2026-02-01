-- Contract table for Celonis Data Pool (Vertica)
-- Stores carrier contract metadata

CREATE TABLE IF NOT EXISTS contract (
    contract_id VARCHAR(36) PRIMARY KEY,
    carrier_id VARCHAR(36) NOT NULL REFERENCES carrier(carrier_id),
    contract_number VARCHAR(100) NOT NULL,
    effective_date DATE NOT NULL,
    expiration_date DATE NOT NULL,
    source_document_path VARCHAR(500),
    parsing_status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_contract_dates CHECK (expiration_date > effective_date),
    CONSTRAINT chk_parsing_status CHECK (parsing_status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_contract_carrier ON contract(carrier_id);
CREATE INDEX IF NOT EXISTS idx_contract_number ON contract(contract_number);
CREATE INDEX IF NOT EXISTS idx_contract_active ON contract(is_active);
CREATE INDEX IF NOT EXISTS idx_contract_dates ON contract(effective_date, expiration_date);

COMMENT ON TABLE contract IS 'Carrier contracts with rate terms and conditions';
