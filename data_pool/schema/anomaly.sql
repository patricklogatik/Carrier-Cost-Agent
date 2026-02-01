-- Anomaly table for Celonis Data Pool (Vertica)
-- Stores detected billing anomalies

CREATE TABLE IF NOT EXISTS anomaly (
    anomaly_id VARCHAR(36) PRIMARY KEY,
    line_id VARCHAR(36) NOT NULL REFERENCES invoice_line(line_id),
    contract_term_id VARCHAR(36) REFERENCES contract_term(term_id),
    anomaly_type VARCHAR(30) NOT NULL,  -- duplicate, rate_error, late_delivery, unauthorized_surcharge, etc.
    expected_amount DECIMAL(15,2),
    actual_amount DECIMAL(15,2) NOT NULL,
    variance DECIMAL(15,2) NOT NULL,
    confidence_score DECIMAL(5,4) NOT NULL,
    detection_rule VARCHAR(100),
    duplicate_of_line_id VARCHAR(36) REFERENCES invoice_line(line_id),
    contract_reference VARCHAR(500),
    status VARCHAR(20) DEFAULT 'detected',  -- detected, validated, dismissed, disputed, resolved
    resolution_notes VARCHAR(65000),
    resolved_by VARCHAR(255),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_anomaly_type CHECK (anomaly_type IN (
        'duplicate', 'rate_error', 'late_delivery', 'unauthorized_surcharge',
        'weight_discrepancy', 'address_correction', 'service_failure'
    )),
    CONSTRAINT chk_anomaly_status CHECK (status IN ('detected', 'validated', 'dismissed', 'disputed', 'resolved'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_anomaly_line ON anomaly(line_id);
CREATE INDEX IF NOT EXISTS idx_anomaly_type ON anomaly(anomaly_type);
CREATE INDEX IF NOT EXISTS idx_anomaly_status ON anomaly(status);
CREATE INDEX IF NOT EXISTS idx_anomaly_confidence ON anomaly(confidence_score);
CREATE INDEX IF NOT EXISTS idx_anomaly_created ON anomaly(created_at);

COMMENT ON TABLE anomaly IS 'Detected billing anomalies for cost recovery';
