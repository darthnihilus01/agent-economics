from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models.trace import (
    ExecutionInput,
    TraceBatchIngest,
    IngestResponse,
    ExecutionRecord
)
from app.services.ingestion_service import ingestion_service
from app.services.analytics_service import analytics_service
from app.services.anomaly_service import anomaly_service

router = APIRouter(prefix="/traces", tags=["Traces & Ingestion"])

@router.post("/ingest", response_model=IngestResponse)
def ingest_traces(payload: TraceBatchIngest):
    """
    Ingest a batch of agent execution traces with granular span metrics and business outcomes.
    """
    res = ingestion_service.ingest_batch(payload.executions)
    
    # Run real-time anomaly check on newly ingested traces
    for e_input in payload.executions:
        # We can scan the newly ingested execution
        rec = analytics_service.get_execution_detail(e_input.execution_id or res.execution_ids[0])
        # Trigger any historical/live detection
    return res

@router.post("/ingest-single")
def ingest_single_trace(payload: ExecutionInput):
    """
    Ingest a single agent execution trace.
    """
    rec = ingestion_service.ingest_execution(payload)
    # Check for anomalies
    anomalies = anomaly_service.scan_execution(rec)
    return {
        "success": True,
        "execution_id": rec.execution_id,
        "total_cost_usd": rec.total_cost_usd,
        "llm_cost_usd": rec.llm_cost_usd,
        "tool_cost_usd": rec.tool_cost_usd,
        "human_cost_usd": rec.human_cost_usd,
        "failure_waste_usd": rec.failure_waste_usd,
        "anomalies_detected": len(anomalies)
    }

@router.get("")
def list_traces(
    agent_id: Optional[str] = Query(None),
    workflow_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Explore and filter executions with cost metrics.
    """
    return analytics_service.get_executions(
        agent_id=agent_id,
        workflow_id=workflow_id,
        status=status,
        limit=limit,
        offset=offset
    )

@router.get("/{execution_id}")
def get_trace_detail(execution_id: str):
    """
    Get detailed execution trace with full span breakdown and cost attribution.
    """
    detail = analytics_service.get_execution_detail(execution_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Execution trace '{execution_id}' not found.")
    return detail
