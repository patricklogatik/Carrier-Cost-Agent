"""ML Workbench Runner for Claim Generation.

This script is the entry point for generating claims
in the Celonis ML Workbench environment.
"""

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import structlog

from config.celonis_config import get_celonis_connection, get_data_pool, get_table
from ml_workbench.claim_generator.generator import ClaimGenerator

logger = structlog.get_logger(__name__)


def generate_claim(
    anomaly_id: str,
    company_name: str = "Our Company",
    created_by: str = "system",
    save_result: bool = True,
) -> Dict:
    """Generate a claim for a single anomaly.

    Args:
        anomaly_id: UUID of the anomaly.
        company_name: Company name for claim signature.
        created_by: Username for audit.
        save_result: Whether to save claim to Data Pool.

    Returns:
        Dict with generation results.
    """
    logger.info("Starting claim generation", anomaly_id=anomaly_id)

    # Initialize Celonis connection
    celonis = get_celonis_connection()
    data_pool = get_data_pool(celonis)

    # Create generator
    generator = ClaimGenerator(data_pool=data_pool)

    # Generate claim
    claim = generator.generate_claim(
        anomaly_id=anomaly_id,
        company_name=company_name,
    )

    if not claim:
        return {
            "anomaly_id": anomaly_id,
            "status": "failed",
            "error": "Failed to generate claim",
        }

    # Save if requested
    claim_id = None
    if save_result:
        claim_id = generator.save_claim(claim, anomaly_id, created_by)

    return {
        "anomaly_id": anomaly_id,
        "claim_id": claim_id,
        "status": "success",
        "claim_subject": claim.claim_subject,
        "requested_credit": float(claim.requested_credit),
        "timestamp": datetime.now().isoformat(),
    }


def generate_claims_for_validated_anomalies(
    limit: int = 50,
    company_name: str = "Our Company",
    created_by: str = "system",
) -> List[Dict]:
    """Generate claims for all validated anomalies without claims.

    Args:
        limit: Maximum number of claims to generate.
        company_name: Company name for claim signature.
        created_by: Username for audit.

    Returns:
        List of generation results.
    """
    logger.info("Starting batch claim generation", limit=limit)

    # Initialize Celonis connection
    celonis = get_celonis_connection()
    data_pool = get_data_pool(celonis)

    # Find validated anomalies without claims
    anomaly_table = get_table("anomaly", data_pool)
    anomalies = anomaly_table.get_data_frame(
        filter="status = 'validated'"
    )

    if anomalies.empty:
        logger.info("No validated anomalies found")
        return []

    # Check which already have claims
    claim_table = get_table("claim", data_pool)
    existing_claims = claim_table.get_data_frame()

    if not existing_claims.empty:
        claimed_anomaly_ids = set(existing_claims["anomaly_id"].tolist())
        anomalies = anomalies[~anomalies["anomaly_id"].isin(claimed_anomaly_ids)]

    if anomalies.empty:
        logger.info("All validated anomalies already have claims")
        return []

    # Generate claims
    generator = ClaimGenerator(data_pool=data_pool)
    results = []

    for _, anomaly in anomalies.head(limit).iterrows():
        anomaly_id = anomaly["anomaly_id"]

        try:
            claim = generator.generate_claim(
                anomaly_id=anomaly_id,
                company_name=company_name,
            )

            if claim:
                claim_id = generator.save_claim(claim, anomaly_id, created_by)
                results.append({
                    "anomaly_id": anomaly_id,
                    "claim_id": claim_id,
                    "status": "success",
                    "requested_credit": float(claim.requested_credit),
                })
            else:
                results.append({
                    "anomaly_id": anomaly_id,
                    "status": "failed",
                    "error": "Generation returned None",
                })

        except Exception as e:
            logger.error("Claim generation failed", anomaly_id=anomaly_id, error=str(e))
            results.append({
                "anomaly_id": anomaly_id,
                "status": "error",
                "error": str(e),
            })

    # Summary
    successful = sum(1 for r in results if r["status"] == "success")
    total_credit = sum(r.get("requested_credit", 0) for r in results if r["status"] == "success")

    logger.info(
        "Batch generation complete",
        total=len(results),
        successful=successful,
        total_credit=total_credit,
    )

    return results


def regenerate_claim(
    claim_id: str,
    created_by: str = "system",
) -> Dict:
    """Regenerate an existing claim with new text.

    Args:
        claim_id: UUID of the existing claim.
        created_by: Username for audit.

    Returns:
        Dict with regeneration results.
    """
    # Initialize Celonis connection
    celonis = get_celonis_connection()
    data_pool = get_data_pool(celonis)

    # Get existing claim
    claim_table = get_table("claim", data_pool)
    claims = claim_table.get_data_frame(filter=f"claim_id = '{claim_id}'")

    if claims.empty:
        return {"error": "Claim not found", "claim_id": claim_id}

    existing = claims.iloc[0]
    anomaly_id = existing["anomaly_id"]

    # Generate new text
    generator = ClaimGenerator(data_pool=data_pool)
    new_claim = generator.generate_claim(
        anomaly_id=anomaly_id,
        regenerate=True,
    )

    if not new_claim:
        return {"error": "Regeneration failed", "claim_id": claim_id}

    # Update existing claim
    update_df = pd.DataFrame([{
        "claim_id": claim_id,
        "claim_subject": new_claim.claim_subject,
        "claim_text": new_claim.claim_text,
        "updated_at": datetime.now(),
    }])
    claim_table.upsert(update_df, keys=["claim_id"])

    return {
        "claim_id": claim_id,
        "status": "regenerated",
        "new_subject": new_claim.claim_subject,
    }


# Main entry point
if __name__ == "__main__":
    # Example: Generate claims for validated anomalies
    results = generate_claims_for_validated_anomalies(limit=10)
    print(f"Generated {len(results)} claims")

    for result in results:
        status = result.get("status")
        credit = result.get("requested_credit", 0)
        print(f"  - {result.get('claim_id')}: {status} (${credit:.2f})")
