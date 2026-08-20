from fastapi import APIRouter, Query
from typing import List
from app.models.analytics import CostAnomalyItem
from app.services.anomaly_service import anomaly_service

router = APIRouter(prefix="/anomalies", tags=["Cost Anomalies"])

@router.get("", response_model=List[CostAnomalyItem])
def list_anomalies(limit: int = Query(50, ge=1, le=200)):
    """
    List detected cost anomalies (runaway loops, context bloat, retry explosions, tool explosions, cost spikes).
    """
    return anomaly_service.get_active_anomalies(limit=limit)

@router.post("/scan", response_model=List[CostAnomalyItem])
def run_anomaly_scan():
    """
    Triggers an analytical anomaly detection scan over historical executions.
    """
    return anomaly_service.scan_historical_anomalies()
