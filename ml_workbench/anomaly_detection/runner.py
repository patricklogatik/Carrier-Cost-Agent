"""ML Workbench Runner for Anomaly Detection.

This script is the entry point for running anomaly detection
in the Celonis ML Workbench environment.

Usage:
    In ML Workbench, run this script with the invoice_id parameter:

    ```python
    from ml_workbench.anomaly_detection.runner import run_detection

    # Run detection on a single invoice
    results = run_detection(invoice_id="your-invoice-uuid")

    # Run detection on all pending invoices
    results = run_batch_detection()
    ```
"""

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import structlog

from config.celonis_config import get_celonis_connection, get_data_pool, get_table
from ml_workbench.anomaly_detection.detector import AnomalyDetector

logger = structlog.get_logger(__name__)


def run_detection(
    invoice_id: str,
    save_results: bool = True,
    confidence_threshold: float = 0.5,
) -> Dict:
    """Run anomaly detection on a single invoice.

    Args:
        invoice_id: UUID of the invoice to analyze.
        save_results: Whether to save anomalies to Data Pool.
        confidence_threshold: Minimum confidence to record anomaly.

    Returns:
        Dict with detection results including anomaly count and details.
    """
    logger.info("Starting detection run", invoice_id=invoice_id)

    # Initialize Celonis connection
    celonis = get_celonis_connection()
    data_pool = get_data_pool(celonis)

    # Create detector
    detector = AnomalyDetector(
        data_pool=data_pool,
        confidence_threshold=confidence_threshold,
    )

    # Run detection
    anomalies = detector.detect_anomalies(invoice_id)

    # Save results if requested
    anomaly_ids = []
    if save_results and anomalies:
        anomaly_ids = detector.save_anomalies(anomalies, invoice_id)

    # Build results
    results = {
        "invoice_id": invoice_id,
        "timestamp": datetime.now().isoformat(),
        "anomalies_detected": len(anomalies),
        "anomaly_ids": anomaly_ids,
        "anomalies": [
            {
                "type": a.anomaly_type,
                "variance": float(a.variance),
                "confidence": float(a.confidence_score),
                "rule": a.detection_rule,
                "description": a.description,
            }
            for a in anomalies
        ],
    }

    logger.info("Detection run completed", results=results)
    return results


def run_batch_detection(
    status: str = "completed",
    limit: int = 100,
    save_results: bool = True,
    confidence_threshold: float = 0.5,
) -> List[Dict]:
    """Run anomaly detection on multiple invoices.

    Fetches invoices with the specified processing status and
    runs detection on each one.

    Args:
        status: Processing status to filter invoices (default: completed).
        limit: Maximum number of invoices to process.
        save_results: Whether to save anomalies to Data Pool.
        confidence_threshold: Minimum confidence to record anomaly.

    Returns:
        List of detection results for each invoice.
    """
    logger.info("Starting batch detection", status=status, limit=limit)

    # Initialize Celonis connection
    celonis = get_celonis_connection()
    data_pool = get_data_pool(celonis)

    # Fetch invoices to process
    invoice_table = get_table("invoice")
    invoices = invoice_table.get_data_frame(
        filter=f"processing_status = '{status}'"
    )

    if invoices.empty:
        logger.info("No invoices to process")
        return []

    # Limit number of invoices
    invoices = invoices.head(limit)

    # Create detector
    detector = AnomalyDetector(
        data_pool=data_pool,
        confidence_threshold=confidence_threshold,
    )

    # Process each invoice
    results = []
    for _, invoice in invoices.iterrows():
        invoice_id = invoice["invoice_id"]

        try:
            anomalies = detector.detect_anomalies(invoice_id)

            anomaly_ids = []
            if save_results and anomalies:
                anomaly_ids = detector.save_anomalies(anomalies, invoice_id)

            results.append({
                "invoice_id": invoice_id,
                "invoice_number": invoice.get("invoice_number"),
                "anomalies_detected": len(anomalies),
                "anomaly_ids": anomaly_ids,
                "status": "success",
            })

        except Exception as e:
            logger.error(
                "Detection failed",
                invoice_id=invoice_id,
                error=str(e),
            )
            results.append({
                "invoice_id": invoice_id,
                "invoice_number": invoice.get("invoice_number"),
                "anomalies_detected": 0,
                "status": "error",
                "error": str(e),
            })

    # Summary
    total_anomalies = sum(r["anomalies_detected"] for r in results)
    logger.info(
        "Batch detection completed",
        invoices_processed=len(results),
        total_anomalies=total_anomalies,
    )

    return results


def get_detection_summary(days: int = 7) -> pd.DataFrame:
    """Get summary of anomaly detection over recent period.

    Args:
        days: Number of days to look back.

    Returns:
        DataFrame with detection summary by type.
    """
    # Initialize connection
    celonis = get_celonis_connection()
    data_pool = get_data_pool(celonis)

    # Fetch anomalies
    anomaly_table = get_table("anomaly", data_pool)
    anomalies = anomaly_table.get_data_frame()

    if anomalies.empty:
        return pd.DataFrame()

    # Filter by date if created_at column exists
    if "created_at" in anomalies.columns:
        cutoff = datetime.now() - pd.Timedelta(days=days)
        anomalies = anomalies[pd.to_datetime(anomalies["created_at"]) >= cutoff]

    # Group by type
    summary = anomalies.groupby("anomaly_type").agg({
        "anomaly_id": "count",
        "variance": "sum",
        "confidence_score": "mean",
    }).rename(columns={
        "anomaly_id": "count",
        "variance": "total_variance",
        "confidence_score": "avg_confidence",
    })

    return summary


# Main entry point for ML Workbench
if __name__ == "__main__":
    # Example: Run batch detection on completed invoices
    results = run_batch_detection(limit=10)
    print(f"Processed {len(results)} invoices")

    # Print summary
    summary = get_detection_summary(days=30)
    print("\nDetection Summary (Last 30 Days):")
    print(summary)
