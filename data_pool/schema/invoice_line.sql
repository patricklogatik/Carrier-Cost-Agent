-- Invoice Line table for Celonis Data Pool (Vertica)
-- Stores individual line items from carrier invoices

CREATE TABLE IF NOT EXISTS invoice_line (
    line_id VARCHAR(36) PRIMARY KEY,
    invoice_id VARCHAR(36) NOT NULL REFERENCES invoice(invoice_id),
    shipment_id VARCHAR(36) REFERENCES shipment(shipment_id),
    line_number INTEGER,
    pro_number VARCHAR(100),
    tracking_number VARCHAR(100),
    charge_type VARCHAR(50) NOT NULL,  -- freight, fuel_surcharge, residential, etc.
    charge_description VARCHAR(500),
    amount DECIMAL(15,2) NOT NULL,
    weight DECIMAL(10,2),
    zone VARCHAR(20),
    service_level VARCHAR(100),
    dimensions VARCHAR(500),  -- JSON: {length, width, height}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_line_invoice ON invoice_line(invoice_id);
CREATE INDEX IF NOT EXISTS idx_line_shipment ON invoice_line(shipment_id);
CREATE INDEX IF NOT EXISTS idx_line_pro ON invoice_line(pro_number);
CREATE INDEX IF NOT EXISTS idx_line_tracking ON invoice_line(tracking_number);
CREATE INDEX IF NOT EXISTS idx_line_charge_type ON invoice_line(charge_type);

COMMENT ON TABLE invoice_line IS 'Individual charge line items from carrier invoices';
