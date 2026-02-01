-- Claim Message table for Celonis Data Pool (Vertica)
-- Stores Q&A conversation history for claims

CREATE TABLE IF NOT EXISTS claim_message (
    message_id VARCHAR(36) PRIMARY KEY,
    claim_id VARCHAR(36) NOT NULL REFERENCES claim(claim_id),
    direction VARCHAR(10) NOT NULL,  -- inbound (from carrier), outbound (to carrier)
    message_type VARCHAR(20) NOT NULL,  -- initial_claim, question, response, clarification, resolution
    content VARCHAR(65000) NOT NULL,
    attachments VARCHAR(65000),  -- JSON array of attachment references
    sender VARCHAR(255),
    is_auto_generated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_direction CHECK (direction IN ('inbound', 'outbound')),
    CONSTRAINT chk_message_type CHECK (message_type IN (
        'initial_claim', 'question', 'response', 'clarification', 'resolution'
    ))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_message_claim ON claim_message(claim_id);
CREATE INDEX IF NOT EXISTS idx_message_direction ON claim_message(direction);
CREATE INDEX IF NOT EXISTS idx_message_created ON claim_message(created_at);

COMMENT ON TABLE claim_message IS 'Q&A conversation history for claim disputes';
