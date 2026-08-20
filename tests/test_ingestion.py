import pytest
import uuid
from datetime import datetime, timezone
from app.models.trace import ExecutionInput, SpanInput, SpanType, ExecutionStatus
from app.services.ingestion_service import ingestion_service
from app.services.analytics_service import analytics_service

def test_ingest_single_trace():
    exec_id = f"test-exec-{uuid.uuid4()}"
    span_id = str(uuid.uuid4())
    
    payload = ExecutionInput(
        execution_id=exec_id,
        agent_id="test-agent",
        agent_name="Test Agent",
        workflow_id="test-workflow",
        workflow_name="Test Workflow",
        customer_id="cust-101",
        outcome_type="test_outcome",
        status=ExecutionStatus.SUCCESS,
        business_value=20.0,
        spans=[
            SpanInput(
                span_id=span_id,
                span_type=SpanType.LLM_CALL,
                name="step_1_llm",
                model="gpt-4o",
                input_tokens=1000,
                output_tokens=500,
                latency_ms=450.0
            ),
            SpanInput(
                span_type=SpanType.TOOL_CALL,
                name="web_search",
                tool_name="web_search",
                tool_duration_seconds=1.5,
                latency_ms=1500.0
            )
        ]
    )

    rec = ingestion_service.ingest_execution(payload)
    assert rec.execution_id == exec_id
    assert rec.step_count == 2
    assert rec.total_cost_usd > 0.0
    assert rec.llm_cost_usd > 0.0
    assert rec.tool_cost_usd > 0.0

    # Verify retrieval from DuckDB
    detail = analytics_service.get_execution_detail(exec_id)
    assert detail is not None
    assert detail["execution_id"] == exec_id
    assert len(detail["spans"]) == 2
