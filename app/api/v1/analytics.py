from fastapi import APIRouter, Query
from typing import List, Optional
from app.models.analytics import (
    ExecutiveSummary,
    UnitEconomicsItem,
    CostBreakdownItem,
    FailureEconomicsSummary
)
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics & Economics"])

@router.get("/executive", response_model=ExecutiveSummary)
def get_executive_summary():
    """
    Get top-level executive economic summary: total spend, net economic benefit, AI ROI, failure waste.
    """
    return analytics_service.get_executive_summary()

@router.get("/unit-economics", response_model=List[UnitEconomicsItem])
def get_unit_economics(workflow_id: Optional[str] = Query(None)):
    """
    Get true unit economics per workflow / business unit (Cost per Successful Business Outcome).
    """
    return analytics_service.get_unit_economics(workflow_id=workflow_id)

@router.get("/breakdowns", response_model=List[CostBreakdownItem])
def get_cost_breakdowns(
    dimension: str = Query("model", description="Dimension: model, agent, workflow, tool, customer, day")
):
    """
    Get cost rollups across dimensions (model, agent, workflow, tool, customer, day).
    """
    return analytics_service.get_cost_breakdowns(dimension=dimension)

@router.get("/failure-economics", response_model=FailureEconomicsSummary)
def get_failure_economics():
    """
    Get failure economics summary: retry waste, human escalation costs, top failing workflows.
    """
    return analytics_service.get_failure_economics()
