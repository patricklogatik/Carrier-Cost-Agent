"""TMS data ingestion to Celonis Data Pool.

This module provides connectors for pushing shipment data
from Transportation Management Systems to the Celonis Data Pool.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pandas as pd
import structlog

from config.celonis_config import get_celonis_connection, get_data_pool, get_table

logger = structlog.get_logger(__name__)


class TMSConnector:
    """Push shipment data from TMS to Celonis Data Pool.

    Supports ingestion from:
    - CSV/Excel files (batch import)
    - Direct API calls (structured data)
    - JSON files
    """

    def __init__(self, data_pool=None):
        """Initialize the TMS connector.

        Args:
            data_pool: Optional Celonis Data Pool connection.
        """
        if data_pool is None:
            celonis = get_celonis_connection()
            data_pool = get_data_pool(celonis)

        self.data_pool = data_pool
        self.shipment_table = get_table("shipment", data_pool)

    def import_shipments(
        self,
        shipments: List[Dict[str, Any]],
        carrier_id: str,
        update_existing: bool = True,
    ) -> Dict[str, Any]:
        """Import shipments from structured data.

        Args:
            shipments: List of shipment dictionaries.
            carrier_id: UUID of the carrier.
            update_existing: Whether to update existing shipments.

        Returns:
            Dict with import results.
        """
        logger.info("Importing shipments", count=len(shipments))

        results = {
            "total": len(shipments),
            "created": 0,
            "updated": 0,
            "errors": 0,
            "error_details": [],
        }

        for i, shipment_data in enumerate(shipments):
            try:
                result = self._import_single(shipment_data, carrier_id, update_existing)

                if result.get("status") == "created":
                    results["created"] += 1
                elif result.get("status") == "updated":
                    results["updated"] += 1

            except Exception as e:
                results["errors"] += 1
                results["error_details"].append({
                    "index": i,
                    "error": str(e),
                    "pro_number": shipment_data.get("pro_number"),
                })
                logger.warning(
                    "Failed to import shipment",
                    index=i,
                    pro_number=shipment_data.get("pro_number"),
                    error=str(e),
                )

        logger.info("Shipment import complete", results=results)
        return results

    def _import_single(
        self,
        data: Dict[str, Any],
        carrier_id: str,
        update_existing: bool,
    ) -> Dict[str, Any]:
        """Import a single shipment."""
        # Use PRO number or tracking number as identifier
        pro_number = data.get("pro_number")
        tracking_number = data.get("tracking_number")

        if not pro_number and not tracking_number:
            raise ValueError("Shipment must have pro_number or tracking_number")

        # Check for existing
        existing = pd.DataFrame()
        if pro_number:
            existing = self.shipment_table.get_data_frame(
                filter=f"pro_number = '{pro_number}' AND carrier_id = '{carrier_id}'"
            )
        if existing.empty and tracking_number:
            existing = self.shipment_table.get_data_frame(
                filter=f"tracking_number = '{tracking_number}' AND carrier_id = '{carrier_id}'"
            )

        if not existing.empty:
            if not update_existing:
                return {"status": "skipped", "reason": "exists"}

            shipment_id = existing.iloc[0]["shipment_id"]
            status = "updated"
        else:
            shipment_id = str(uuid4())
            status = "created"

        # Build shipment record
        shipment_record = {
            "shipment_id": shipment_id,
            "carrier_id": carrier_id,
            "pro_number": pro_number,
            "tracking_number": tracking_number,
            "origin_zip": data.get("origin_zip"),
            "origin_city": data.get("origin_city"),
            "origin_state": data.get("origin_state"),
            "origin_country": data.get("origin_country", "US"),
            "destination_zip": data.get("destination_zip"),
            "destination_city": data.get("destination_city"),
            "destination_state": data.get("destination_state"),
            "destination_country": data.get("destination_country", "US"),
            "service_level": data.get("service_level"),
            "ship_date": data.get("ship_date"),
            "expected_delivery": data.get("expected_delivery"),
            "actual_delivery": data.get("actual_delivery"),
            "weight": data.get("weight"),
            "dimensions": str(data.get("dimensions")) if data.get("dimensions") else None,
            "reference_numbers": str(data.get("reference_numbers")) if data.get("reference_numbers") else None,
            "source_system": data.get("source_system", "TMS"),
            "created_at": datetime.now() if status == "created" else existing.iloc[0].get("created_at"),
            "updated_at": datetime.now(),
        }

        # Save to Data Pool
        df = pd.DataFrame([shipment_record])
        self.shipment_table.upsert(df, keys=["shipment_id"])

        return {"status": status, "shipment_id": shipment_id}

    def import_csv(
        self,
        csv_path: str,
        carrier_id: str,
        mapping: Optional[Dict[str, str]] = None,
        update_existing: bool = True,
    ) -> Dict[str, Any]:
        """Import shipments from a CSV file.

        Args:
            csv_path: Path to the CSV file.
            carrier_id: UUID of the carrier.
            mapping: Column name mapping (csv_col -> our_field).
            update_existing: Whether to update existing shipments.

        Returns:
            Dict with import results.
        """
        logger.info("Importing from CSV", csv_path=csv_path)

        df = pd.read_csv(csv_path)

        # Apply column mapping
        if mapping:
            df = df.rename(columns=mapping)

        # Convert dates
        date_columns = ["ship_date", "expected_delivery", "actual_delivery"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Convert to list of dicts
        data = df.to_dict("records")

        return self.import_shipments(data, carrier_id, update_existing)

    def import_json(
        self,
        json_path: str,
        carrier_id: str,
        update_existing: bool = True,
    ) -> Dict[str, Any]:
        """Import shipments from a JSON file.

        Args:
            json_path: Path to the JSON file.
            carrier_id: UUID of the carrier.
            update_existing: Whether to update existing shipments.

        Returns:
            Dict with import results.
        """
        import json

        logger.info("Importing from JSON", json_path=json_path)

        with open(json_path, "r") as f:
            data = json.load(f)

        # Handle both list and dict with "shipments" key
        if isinstance(data, dict):
            data = data.get("shipments", [])

        return self.import_shipments(data, carrier_id, update_existing)

    def update_delivery_status(
        self,
        tracking_number: str,
        carrier_id: str,
        actual_delivery: datetime,
        delivery_status: str = "delivered",
    ) -> Dict[str, Any]:
        """Update delivery status for a shipment.

        Args:
            tracking_number: Tracking number of the shipment.
            carrier_id: UUID of the carrier.
            actual_delivery: Actual delivery date/time.
            delivery_status: Status (delivered, attempted, etc.).

        Returns:
            Dict with update result.
        """
        # Find shipment
        shipments = self.shipment_table.get_data_frame(
            filter=f"tracking_number = '{tracking_number}' AND carrier_id = '{carrier_id}'"
        )

        if shipments.empty:
            return {"status": "not_found", "tracking_number": tracking_number}

        shipment_id = shipments.iloc[0]["shipment_id"]

        # Update record
        update_df = pd.DataFrame([{
            "shipment_id": shipment_id,
            "actual_delivery": actual_delivery,
            "updated_at": datetime.now(),
        }])

        self.shipment_table.upsert(update_df, keys=["shipment_id"])

        logger.info(
            "Delivery status updated",
            shipment_id=shipment_id,
            tracking_number=tracking_number,
            actual_delivery=actual_delivery,
        )

        return {
            "status": "updated",
            "shipment_id": shipment_id,
            "actual_delivery": actual_delivery.isoformat(),
        }


# Export
__all__ = ["TMSConnector"]
