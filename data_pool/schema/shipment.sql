-- Shipment table for Celonis Data Pool (Vertica)
-- Stores shipment data from TMS/WMS systems

CREATE TABLE IF NOT EXISTS shipment (
    shipment_id VARCHAR(36) PRIMARY KEY,
    carrier_id VARCHAR(36) NOT NULL REFERENCES carrier(carrier_id),
    pro_number VARCHAR(100),
    tracking_number VARCHAR(100),
    origin_zip VARCHAR(20),
    origin_city VARCHAR(255),
    origin_state VARCHAR(100),
    origin_country VARCHAR(3) DEFAULT 'US',
    destination_zip VARCHAR(20),
    destination_city VARCHAR(255),
    destination_state VARCHAR(100),
    destination_country VARCHAR(3) DEFAULT 'US',
    service_level VARCHAR(100),
    ship_date DATE NOT NULL,
    expected_delivery DATE,
    actual_delivery DATE,
    weight DECIMAL(10,2),
    dimensions VARCHAR(500),  -- JSON: {length, width, height, dim_weight}
    reference_numbers VARCHAR(65000),  -- JSON array of reference numbers
    source_system VARCHAR(100),  -- TMS name
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_shipment_carrier ON shipment(carrier_id);
CREATE INDEX IF NOT EXISTS idx_shipment_pro ON shipment(pro_number);
CREATE INDEX IF NOT EXISTS idx_shipment_tracking ON shipment(tracking_number);
CREATE INDEX IF NOT EXISTS idx_shipment_ship_date ON shipment(ship_date);
CREATE INDEX IF NOT EXISTS idx_shipment_service ON shipment(service_level);

COMMENT ON TABLE shipment IS 'Shipment data from TMS/WMS for matching with invoices';
