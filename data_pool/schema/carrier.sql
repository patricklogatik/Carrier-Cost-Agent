-- Carrier table for Celonis Data Pool (Vertica)
-- Stores carrier information (FedEx, UPS, etc.)

CREATE TABLE IF NOT EXISTS carrier (
    carrier_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(10) NOT NULL,
    portal_url VARCHAR(500),
    contact_email VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_carrier_code UNIQUE (code)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_carrier_code ON carrier(code);
CREATE INDEX IF NOT EXISTS idx_carrier_active ON carrier(is_active);

-- Comments
COMMENT ON TABLE carrier IS 'Carrier master data for freight companies';
COMMENT ON COLUMN carrier.carrier_id IS 'Unique identifier (UUID)';
COMMENT ON COLUMN carrier.code IS 'Short code (e.g., FEDX, UPS)';
