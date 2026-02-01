# Celonis Carrier Cost Agent

AI-powered carrier invoice validation and cost recovery solution built natively on the Celonis platform.

## Overview

The Carrier Cost Agent automates freight audit by:
1. **Detecting billing anomalies** across all carrier invoices
2. **Validating charges** against structured "Digital Twin" of PDF contracts
3. **Generating portal-ready claims** with contract citations
4. **Handling carrier Q&A** to recover overcharges

**Target Impact:** 3-7% of shipment spend recovered/prevented

## Architecture

This is a **Celonis-native** application leveraging:
- **PyCelonis** - Official Python SDK for Celonis EMS
- **Celonis Data Pool (Vertica)** - Data storage
- **Celonis ML Workbench** - Python execution environment
- **pycelonis_llm** - Native Celonis LLM integration for GenAI features
- **Celonis Studio** - Dashboard and UI
- **Data Ingestion API** - Real-time data push from TMS/invoices

## Project Structure

```
carrier-cost-agent/
├── config/                     # Celonis connection configuration
│   ├── celonis_config.py       # PyCelonis connection setup
│   └── settings.py             # Application settings
├── data_pool/                  # Celonis Data Pool
│   └── schema/                 # Vertica DDL schemas
│       ├── carrier.sql
│       ├── contract.sql
│       ├── invoice.sql
│       ├── shipment.sql
│       ├── anomaly.sql
│       └── claim.sql
├── ml_workbench/               # Celonis ML Workbench components
│   ├── anomaly_detection/      # Anomaly detection engine
│   │   ├── rules/              # Detection rules
│   │   │   ├── duplicate.py
│   │   │   ├── rate_error.py
│   │   │   ├── late_delivery.py
│   │   │   └── unauthorized_surcharge.py
│   │   ├── detector.py         # Main detector class
│   │   └── runner.py           # ML Workbench entry point
│   ├── contract_parser/        # Contract parsing with pycelonis_llm
│   │   ├── parser.py
│   │   └── runner.py
│   ├── claim_generator/        # Claim generation with pycelonis_llm
│   │   ├── generator.py
│   │   └── runner.py
│   └── invoice_parser/         # Invoice PDF parsing
│       ├── extractor.py
│       └── parser.py
├── ingestion/                  # Data Ingestion API connectors
│   ├── invoice_connector.py    # Invoice data ingestion
│   └── tms_connector.py        # TMS shipment data ingestion
├── studio/                     # Celonis Studio configuration
│   └── knowledge_model.yaml    # KPIs, process views, dashboards
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   └── conftest.py             # Test fixtures
├── scripts/                    # Utility scripts
│   └── seed_data.py            # Data Pool seeding
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md
│   └── PRD.md
├── .github/workflows/          # CI/CD
├── requirements.txt            # Celonis dependencies
├── pyproject.toml              # Python project config
├── .env.celonis.example        # Celonis environment template
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.11+
- Celonis EMS access with API token
- Celonis Data Pool (provisioned)
- Celonis ML Workbench (optional, for production execution)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/carrier-cost-agent.git
cd carrier-cost-agent
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

4. Configure Celonis connection:
```bash
cp .env.celonis.example .env
# Edit .env with your Celonis credentials:
# - CELONIS_BASE_URL
# - CELONIS_API_TOKEN
# - CELONIS_DATA_POOL_ID
```

5. Initialize Data Pool tables:
```bash
# Execute DDL scripts in data_pool/schema/ against your Celonis Data Pool
```

6. Seed initial data (optional):
```bash
python scripts/seed_data.py
```

### Running Locally

Run anomaly detection:
```python
from ml_workbench.anomaly_detection.runner import run_detection

results = run_detection(invoice_id="your-invoice-id")
print(f"Found {len(results)} anomalies")
```

Parse a contract:
```python
from ml_workbench.contract_parser.runner import parse_contract

terms = parse_contract(contract_id="your-contract-id", pdf_path="/path/to/contract.pdf")
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ml_workbench --cov=config --cov=ingestion

# Run specific test file
pytest tests/unit/test_anomaly_detection.py
```

## Celonis Integration

### Data Pool Tables

| Table | Description |
|-------|-------------|
| carrier | Carrier master data (FedEx, UPS, etc.) |
| contract | Carrier contract metadata |
| contract_term | Extracted contract terms (rates, surcharges, SLAs) |
| invoice | Carrier invoice headers |
| invoice_line | Invoice line items |
| shipment | Shipment data from TMS |
| anomaly | Detected billing anomalies |
| claim | Carrier dispute claims |
| claim_message | Claim conversation history |

### Knowledge Model KPIs

- **Total Identified** - Variance amount of detected anomalies
- **Total Submitted** - Requested credit for submitted claims
- **Total Recovered** - Credit from won claims
- **Recovery Rate** - Percentage recovered vs submitted
- **Win Rate** - Percentage of claims won

### ML Workbench Components

1. **Anomaly Detection** - Runs on invoice ingestion
2. **Contract Parser** - Extracts terms using pycelonis_llm
3. **Claim Generator** - Creates claims with LLM-enhanced text

## Development

### Code Style

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **Flake8** for linting
- **mypy** for type checking

```bash
# Format code
black ml_workbench config ingestion tests
isort ml_workbench config ingestion tests

# Lint
flake8 ml_workbench config ingestion tests
mypy ml_workbench config ingestion
```

### Pre-commit Hooks

```bash
pre-commit install
```

## MVP Scope (Phase 1)

**Target:** Celosphere 2026 | **Pilot:** Ingka/IKEA with FedEx US

### Features
- [x] Invoice ingestion (PDF upload to Celonis)
- [x] PDF text extraction and parsing
- [x] FedEx invoice field extraction
- [x] Shipment data import via Data Ingestion API
- [x] Invoice-shipment matching
- [x] Contract upload and pycelonis_llm parsing
- [x] Anomaly detection (duplicates, rate errors, late delivery, unauthorized surcharges)
- [x] Claim generation with contract citations
- [ ] Celonis Studio dashboards (Recovery Overview, Anomaly Queue, Claims Pipeline)
- [ ] Claim review and approval workflow in Studio

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Technical architecture details
- [PRD](docs/PRD.md) - Product requirements document

## License

Proprietary - Logatik GmbH

## Support

For questions or issues, contact the development team or open an issue in this repository.
