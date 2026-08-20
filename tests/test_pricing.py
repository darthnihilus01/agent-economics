import pytest
from app.services.pricing_service import pricing_service

def test_llm_pricing_gpt4o():
    # 1,000,000 input tokens at $2.50/M + 1,000,000 output tokens at $10.00/M = $12.50
    in_cost, out_cost, total = pricing_service.calculate_llm_cost("gpt-4o", 1_000_000, 1_000_000)
    assert in_cost == 2.50
    assert out_cost == 10.00
    assert total == 12.50

def test_llm_pricing_with_cache():
    # 500k uncached ($1.25) + 500k cached ($0.625) + 100k out ($1.00) = $2.875
    in_cost, out_cost, total = pricing_service.calculate_llm_cost(
        "gpt-4o", input_tokens=1_000_000, output_tokens=100_000, cached_tokens=500_000
    )
    assert in_cost == pytest.approx(1.875, rel=1e-3)
    assert out_cost == pytest.approx(1.00, rel=1e-3)
    assert total == pytest.approx(2.875, rel=1e-3)

def test_tool_pricing():
    call_c, comp_c, total = pricing_service.calculate_tool_cost("web_search", duration_seconds=0, call_count=5)
    assert total == 0.05

def test_human_cost():
    # 30 mins (1800s) at $35/hr = $17.50
    cost = pricing_service.calculate_human_cost(1800.0)
    assert cost == 17.50
