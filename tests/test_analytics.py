import pytest
from app.services.analytics_service import analytics_service

def test_executive_summary():
    summary = analytics_service.get_executive_summary()
    assert summary.total_executions >= 0
    assert summary.total_ai_spend_usd >= 0.0
    assert summary.success_rate_percentage >= 0.0

def test_unit_economics():
    units = analytics_service.get_unit_economics()
    assert isinstance(units, list)
    for u in units:
        assert u.workflow_id is not None
        assert u.cost_per_successful_outcome_usd >= 0.0

def test_cost_breakdowns():
    model_breakdowns = analytics_service.get_cost_breakdowns(dimension="model")
    assert isinstance(model_breakdowns, list)
