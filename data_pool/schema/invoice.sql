-- Invoice table for Celonis Data Pool (Vertica)
-- Stores carrier invoice header data

CREATE TABLE IF NOT EXISTS invoice (
    invoice_id VARCHAR(36) PRIMARY KEY,
    carrier_id VARCHAR(36) NOT NULL REFERENCES carrier(carrier_id),
    invoice_number VARCHAR(100) NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE,
    total_amount DECIMAL(15,2),
    currency VARCHAR(3) DEFAULT 'USD',
    source_type VARCHAR(20),  -- pdf, edi, api
    source_document_path VARCHAR(500),
    processing_status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    processed_at TIMESTAMP,
    raw_text VARCHAR(65000),  -- Extracted text for debugging
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_source_type CHECK (source_type IN ('pdf', 'edi', 'api')),
    CONSTRAINT chk_invoice_status CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_invoice_carrier ON invoice(carrier_id);
CREATE INDEX IF NOT EXISTS idx_invoice_number ON invoice(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoice_date ON invoice(invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoice_status ON invoice(processing_status);

COMMENT ON TABLE invoice IS 'Carrier invoice headers';
