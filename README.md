# Celonis Carrier Cost Agent

AI-powered carrier invoice validation and cost recovery solution built on the Celonis platform.

## Overview

The Carrier Cost Agent automates freight audit by:
1. **Detecting billing anomalies** across all carrier invoices
2. **Validating charges** against structured "Digital Twin" of PDF contracts
3. **Generating portal-ready claims** with contract citations
4. **Handling carrier Q&A** to recover overcharges

**Target Impact:** 3-7% of shipment spend recovered/prevented

## Project Structure

```
carrier-cost-agent/
├── src/
│   ├── api/                    # REST API endpoints
│   │   ├── routes/             # Route handlers
│   │   ├── middleware/         # Auth, validation, logging
│   │   └── schemas/            # Pydantic request/response models
│   ├── services/               # Business logic services
│   │   ├── invoice/            # Invoice ingestion & processing
│   │   ├── contract/           # Contract parsing & management
│   │   ├── anomaly/            # Anomaly detection engine
│   │   ├── claim/              # Claim generation & management
│   │   └── analytics/          # Dashboard & reporting
│   ├── models/                 # Database models (SQLAlchemy)
│   ├── core/                   # Core utilities
│   │   ├── config.py           # Configuration management
│   │   ├── security.py         # Authentication & authorization
│   │   └── logging.py          # Logging configuration
│   └── integrations/           # External system connectors
│       ├── pdf/                # PDF parsing (OCR, text extraction)
│       ├── genai/              # LLM integration for contract parsing
│       └── storage/            # Object storage (Celonis/S3)
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── fixtures/               # Test data and fixtures
├── migrations/                 # Database migrations (Alembic)
├── config/                     # Configuration files
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md         # Technical architecture
│   ├── PRD.md                  # Product requirements
│   └── API.md                  # API documentation
├── scripts/                    # Utility scripts
├── .github/                    # GitHub Actions CI/CD
│   └── workflows/
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Development dependencies
├── pyproject.toml              # Python project configuration
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore patterns
└── README.md                   # This file
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or Celonis Data Pool access)
- Redis (for job queue)

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

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the development server:
```bash
uvicorn src.api.main:app --reload
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_anomaly_detection.py
```

## API Documentation

Once the server is running, access the API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Code Style

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **Flake8** for linting
- **mypy** for type checking

Run formatting and linting:
```bash
# Format code
black src tests
isort src tests

# Lint
flake8 src tests
mypy src
```

### Pre-commit Hooks

Install pre-commit hooks to ensure code quality:
```bash
pre-commit install
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed technical architecture.

## Product Requirements

See [docs/PRD.md](docs/PRD.md) for full product requirements document.

## MVP Scope (Phase 1)

**Target:** Celosphere 2026 | **Pilot:** Ingka/IKEA with FedEx US

### Features
- [x] Invoice ingestion (PDF upload)
- [x] PDF text extraction and parsing
- [x] FedEx invoice field extraction
- [x] Shipment data import (CSV/JSON)
- [x] Invoice-shipment matching
- [x] Contract upload and GenAI parsing
- [x] Anomaly detection (duplicates, rate errors, late delivery, unauthorized surcharges)
- [x] Claim generation with contract citations
- [x] Claim review and approval workflow
- [x] Recovery dashboard

## License

Proprietary - Logatik GmbH

## Support

For questions or issues, contact the development team or open an issue in this repository.
