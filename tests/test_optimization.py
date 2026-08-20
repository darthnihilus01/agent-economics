import pytest
import uuid
from app.models.optimization import BacktestRequest, GuardrailConstraints
from app.services.optimization_service import optimization_service
from app.services.verification_service import verification_service
from app.services.anomaly_service import anomaly_service

def test_recommendation_generation():
    recs = optimization_service.generate_recommendations()
    assert isinstance(recs, list)

def test_backtest_execution():
    recs = optimization_service.get_recommendations()
    if recs:
        target_rec = recs[0]
        req = BacktestRequest(
            recommendation_id=target_rec.id,
            sample_size=50,
            guardrails=GuardrailConstraints(min_success_rate_pct=90.0, max_latency_p95_ms=10000.0)
        )
        res = verification_service.run_backtest(req)
        assert res.recommendation_id == target_rec.id
        assert res.passed_guardrails in [True, False]
        assert res.simulated_savings_usd >= 0.0
