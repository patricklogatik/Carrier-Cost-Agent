# Carrier Cost Agent API Documentation

## Overview

The Carrier Cost Agent provides a RESTful API for carrier invoice validation and cost recovery automation.

**Base URL:** `http://localhost:8000/api/v1`

## Authentication

The API supports two authentication methods:

### API Key Authentication

Include the API key in the `X-API-Key` header:

```
X-API-Key: your-api-key
```

### Bearer Token Authentication (JWT)

Include the JWT token in the Authorization header:

```
Authorization: Bearer <token>
```

## Endpoints

### Health Check

#### GET /health

Check the health status of the API and its dependencies.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-15T10:30:00Z",
  "version": "0.1.0",
  "environment": "development",
  "checks": {
    "database": {"status": "healthy"}
  }
}
```

---

### Invoices

#### POST /api/v1/invoices

Upload a carrier invoice PDF for processing.

**Content-Type:** `multipart/form-data`

**Parameters:**
- `file` (required): PDF file (max 50MB)
- `carrier_id` (required): Carrier UUID

**Response:**
```json
{
  "invoice_id": "uuid",
  "status": "pending",
  "filename": "invoice.pdf",
  "uploaded_at": "2026-01-15T10:30:00Z",
  "message": "Invoice uploaded successfully and queued for processing"
}
```

#### GET /api/v1/invoices

List invoices with pagination and filtering.

**Query Parameters:**
- `limit` (default: 50, max: 100)
- `offset` (default: 0)
- `carrier_id` (optional)
- `status` (optional): pending, processing, completed, failed
- `date_from` (optional): YYYY-MM-DD
- `date_to` (optional): YYYY-MM-DD
- `sort_by` (optional): invoice_date, total_amount, created_at
- `sort_order` (optional): asc, desc

**Response:**
```json
{
  "items": [
    {
      "invoice_id": "uuid",
      "carrier_id": "uuid",
      "invoice_number": "INV-001",
      "invoice_date": "2026-01-15",
      "total_amount": 1234.56,
      "currency": "USD",
      "processing_status": "completed",
      "line_count": 25,
      "anomaly_count": 3,
      "created_at": "2026-01-15T10:30:00Z"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

#### GET /api/v1/invoices/{invoice_id}

Get detailed invoice information including line items.

**Response:**
```json
{
  "invoice_id": "uuid",
  "invoice_number": "INV-001",
  "invoice_date": "2026-01-15",
  "total_amount": 1234.56,
  "lines": [
    {
      "line_id": "uuid",
      "line_number": 1,
      "pro_number": "PRO123456",
      "tracking_number": "794644790292",
      "charge_type": "freight",
      "amount": 75.00,
      "weight": 5.5,
      "zone": "2"
    }
  ]
}
```

---

### Shipments

#### POST /api/v1/shipments/import

Bulk import shipments from TMS/WMS data.

**Request Body:**
```json
{
  "shipments": [
    {
      "carrier_id": "uuid",
      "pro_number": "PRO123456",
      "tracking_number": "794644790292",
      "origin_zip": "10001",
      "destination_zip": "90210",
      "service_level": "FedEx Ground",
      "ship_date": "2026-01-10",
      "expected_delivery": "2026-01-15",
      "weight": 5.5
    }
  ],
  "update_existing": true
}
```

**Response:**
```json
{
  "total": 100,
  "created": 80,
  "updated": 15,
  "errors": 5,
  "error_details": [
    {"index": 42, "error": "Invalid carrier_id"}
  ]
}
```

#### GET /api/v1/shipments

List shipments with filtering.

#### GET /api/v1/shipments/{shipment_id}

Get detailed shipment information.

---

### Contracts

#### POST /api/v1/contracts

Upload a carrier contract PDF for parsing.

**Content-Type:** `multipart/form-data`

**Parameters:**
- `file` (required): Contract PDF
- `carrier_id` (required): Carrier UUID
- `contract_number` (required): Contract identifier
- `effective_date` (required): YYYY-MM-DD
- `expiration_date` (required): YYYY-MM-DD

**Required Role:** Contract Manager or Administrator

**Response:**
```json
{
  "contract_id": "uuid",
  "status": "pending",
  "filename": "contract.pdf",
  "uploaded_at": "2026-01-15T10:30:00Z",
  "message": "Contract uploaded successfully and queued for parsing"
}
```

#### GET /api/v1/contracts/lookup

Look up applicable contract terms for a shipment.

**Query Parameters:**
- `carrier_id` (required)
- `service_level` (required)
- `zone` (optional)
- `weight` (optional)
- `ship_date` (optional)

**Response:**
```json
{
  "base_rate": {
    "amount": 12.50,
    "rate_type": "flat",
    "term_id": "uuid",
    "source_text": "Ground Zone 2: $12.50"
  },
  "surcharges": [
    {
      "surcharge_type": "Fuel Surcharge",
      "rate": 15,
      "rate_type": "percentage",
      "term_id": "uuid"
    }
  ],
  "sla": {
    "delivery_days": 5,
    "term_id": "uuid"
  },
  "contract_id": "uuid",
  "contract_number": "FEDX-2026-001"
}
```

#### GET /api/v1/contracts/{contract_id}

Get detailed contract with extracted terms.

#### PUT /api/v1/contracts/{contract_id}/terms/{term_id}/validate

Validate or update an extracted contract term.

**Required Role:** Contract Manager or Administrator

---

### Anomalies

#### GET /api/v1/anomalies

List detected anomalies with filtering.

**Query Parameters:**
- `status`: detected, validated, dismissed, disputed, resolved
- `anomaly_type`: duplicate, rate_error, late_delivery, unauthorized_surcharge
- `confidence_min`: 0-1
- `invoice_id` (optional)
- `sort_by`: variance, confidence_score, created_at
- `sort_order`: asc, desc

**Response:**
```json
{
  "items": [
    {
      "anomaly_id": "uuid",
      "anomaly_type": "rate_error",
      "expected_amount": 50.00,
      "actual_amount": 75.00,
      "variance": 25.00,
      "confidence_score": 0.95,
      "status": "detected",
      "invoice_number": "INV-001",
      "pro_number": "PRO123456",
      "has_claim": false
    }
  ],
  "total": 50,
  "limit": 50,
  "offset": 0
}
```

#### GET /api/v1/anomalies/{anomaly_id}

Get detailed anomaly with context (invoice line, shipment, contract term).

#### PUT /api/v1/anomalies/{anomaly_id}/status

Update anomaly status.

**Request Body:**
```json
{
  "status": "validated",
  "resolution_notes": "Confirmed rate discrepancy"
}
```

---

### Claims

#### POST /api/v1/claims

Create a new claim from an anomaly.

**Request Body:**
```json
{
  "anomaly_id": "uuid",
  "claim_text": "Optional custom claim text",
  "claim_subject": "Optional subject line",
  "regenerate": false
}
```

**Response:**
```json
{
  "claim_id": "uuid",
  "claim_number": "CLM-20260115-ABC123",
  "status": "draft",
  "requested_credit": 25.00
}
```

#### GET /api/v1/claims

List claims with filtering.

#### GET /api/v1/claims/{claim_id}

Get detailed claim with messages.

#### PUT /api/v1/claims/{claim_id}

Update claim details.

#### POST /api/v1/claims/{claim_id}/approve

Approve or reject a claim.

**Required Role:** Approver or Administrator

**Request Body:**
```json
{
  "approved": true,
  "comments": "Approved for submission"
}
```

#### POST /api/v1/claims/{claim_id}/messages

Add a message to the claim conversation.

**Request Body:**
```json
{
  "direction": "outbound",
  "message_type": "response",
  "content": "Response text...",
  "generate_response": false
}
```

---

### Analytics

#### GET /api/v1/analytics/recovery

Get recovery metrics for the dashboard.

**Query Parameters:**
- `date_from` (optional)
- `date_to` (optional)
- `carrier_id` (optional)

**Response:**
```json
{
  "total_identified": 125000.00,
  "total_submitted": 85000.00,
  "total_recovered": 65000.00,
  "recovery_rate": 76.47,
  "total_anomalies": 450,
  "total_claims": 320,
  "claims_won": 280,
  "claims_lost": 25,
  "claims_pending": 15,
  "by_status": {
    "identified": 125000.00,
    "submitted": 85000.00,
    "recovered": 65000.00,
    "pending": 20000.00
  },
  "by_type": [
    {
      "anomaly_type": "rate_error",
      "count": 200,
      "total_variance": 75000.00,
      "recovered_amount": 55000.00
    }
  ]
}
```

#### GET /api/v1/analytics/anomalies

Get anomaly detection metrics.

---

## Error Responses

All errors follow a standard format:

```json
{
  "detail": "Error message",
  "type": "error_type"
}
```

### HTTP Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict
- `413` - Request Entity Too Large
- `500` - Internal Server Error

---

## Rate Limiting

API requests are rate limited to 100 requests per 60 seconds per API key.

When rate limited, you'll receive a `429 Too Many Requests` response with a `Retry-After` header.

---

## Webhook Events

The following webhook events are available (when enabled):

- `invoice.processed` - Invoice processing completed
- `anomaly.detected` - New anomaly detected
- `claim.created` - New claim created
- `claim.submitted` - Claim submitted to carrier
- `claim.resolved` - Claim resolved (won/lost)
- `contract.parsed` - Contract parsing completed

Configure webhooks via the admin settings.
