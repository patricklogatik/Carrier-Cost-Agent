"""ML Workbench Runner for Contract Parsing.

This script is the entry point for running contract parsing
in the Celonis ML Workbench environment.
"""

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import structlog

from config.celonis_config import get_celonis_connection, get_data_pool, get_table
from ml_workbench.contract_parser.parser import ContractParser

logger = structlog.get_logger(__name__)


def parse_contract(
    contract_id: str,
    pdf_path: str,
    save_results: bool = True,
) -> Dict:
    """Parse a single contract PDF.

    Args:
        contract_id: UUID of the contract record.
        pdf_path: Path to the contract PDF file.
        save_results: Whether to save terms to Data Pool.

    Returns:
        Dict with parsing results.
    """
    logger.info("Starting contract parsing", contract_id=contract_id)

    # Initialize Celonis connection
    celonis = get_celonis_connection()
    data_pool = get_data_pool(celonis)

    # Get contract record for carrier_id
    contract_table = get_table("contract", data_pool)
    contracts = contract_table.get_data_frame(
        filter=f"contract_id = '{contract_id}'"
    )

    if contracts.empty:
        return {"error": "Contract not found", "contract_id": contract_id}

    contract = contracts.iloc[0]
    carrier_id = contract["carrier_id"]

    # Update status to processing
    _update_contract_status(contract_id, "processing", data_pool)

    # Create parser and parse
    parser = ContractParser(data_pool=data_pool)

    try:
        terms = parser.parse_contract(pdf_path, contract_id, carrier_id)

        # Save terms if requested
        term_ids = []
        if save_results and terms:
            term_ids = parser.save_terms(terms, contract_id)

        # Update status to completed
        _update_contract_status(contract_id, "completed", data_pool)

        results = {
            "contract_id": contract_id,
            "carrier_id": carrier_id,
            "timestamp": datetime.now().isoformat(),
            "terms_extracted": len(terms),
            "term_ids": term_ids,
            "status": "completed",
            "terms_summary": _summarize_terms(terms),
        }

    except Exception as e:
        logger.error("Contract parsing failed", error=str(e))
        _update_contract_status(contract_id, "failed", data_pool)

        results = {
            "contract_id": contract_id,
            "status": "failed",
            "error": str(e),
        }

    return results


def parse_pending_contracts(limit: int = 10) -> List[Dict]:
    """Parse all pending contracts.

    Args:
        limit: Maximum number of contracts to process.

    Returns:
        List of parsing results.
    """
    logger.info("Starting batch contract parsing", limit=limit)

    # Initialize Celonis connection
    celonis = get_celonis_connection()
    data_pool = get_data_pool(celonis)

    # Fetch pending contracts
    contract_table = get_table("contract", data_pool)
    contracts = contract_table.get_data_frame(
        filter="parsing_status = 'pending'"
    )

    if contracts.empty:
        logger.info("No pending contracts found")
        return []

    # Process each contract
    results = []
    for _, contract in contracts.head(limit).iterrows():
        contract_id = contract["contract_id"]
        pdf_path = contract.get("source_document_path")

        if not pdf_path:
            logger.warning("No PDF path for contract", contract_id=contract_id)
            continue

        result = parse_contract(contract_id, pdf_path)
        results.append(result)

    logger.info("Batch parsing complete", contracts_processed=len(results))
    return results


def _update_contract_status(
    contract_id: str,
    status: str,
    data_pool,
):
    """Update the parsing status of a contract."""
    try:
        contract_table = get_table("contract", data_pool)
        df = pd.DataFrame([{
            "contract_id": contract_id,
            "parsing_status": status,
            "updated_at": datetime.now(),
        }])
        contract_table.upsert(df, keys=["contract_id"])
    except Exception as e:
        logger.warning("Failed to update contract status", error=str(e))


def _summarize_terms(terms) -> Dict:
    """Create a summary of extracted terms by type."""
    summary = {
        "rate": 0,
        "surcharge": 0,
        "sla": 0,
        "discount": 0,
        "exception": 0,
    }

    for term in terms:
        term_type = term.term_type
        if term_type in summary:
            summary[term_type] += 1

    return summary


# Main entry point
if __name__ == "__main__":
    # Example: Parse pending contracts
    results = parse_pending_contracts(limit=5)
    print(f"Processed {len(results)} contracts")

    for result in results:
        print(f"  - {result.get('contract_id')}: {result.get('status')}")
