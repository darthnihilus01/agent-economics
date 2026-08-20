from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models.optimization import (
    OptimizationRecommendation,
    BacktestRequest,
    BacktestResult,
    OptimizationStatus
)
from app.services.optimization_service import optimization_service
from app.services.verification_service import verification_service

router = APIRouter(prefix="/optimizations", tags=["Economic Autopilot & Optimizations"])

@router.get("", response_model=List[OptimizationRecommendation])
def list_optimizations(status: Optional[str] = Query(None)):
    """
    List optimization opportunities surfaced by Economic Autopilot.
    """
    recs = optimization_service.get_recommendations(status=status)
    if not recs:
        # Generate initial recommendations if none exist
        recs = optimization_service.generate_recommendations()
    return recs

@router.post("/generate", response_model=List[OptimizationRecommendation])
def generate_optimizations():
    """
    Analyze current production traces and generate new optimization recommendations.
    """
    return optimization_service.generate_recommendations()

@router.post("/backtest", response_model=BacktestResult)
def backtest_optimization(payload: BacktestRequest):
    """
    Backtest an optimization recommendation against historical traces under strict guardrails.
    """
    try:
        return verification_service.run_backtest(payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{recommendation_id}/deploy")
def deploy_optimization(recommendation_id: str):
    """
    Deploy an approved and backtested optimization to live production routing.
    """
    try:
        return verification_service.deploy_optimization(recommendation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
