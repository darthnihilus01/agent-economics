from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

class AnomalyType(str, Enum):
    RUNAWAY_LOOP = "RUNAWAY_LOOP"
    CONTEXT_BLOAT = "CONTEXT_BLOAT"
    RETRY_EXPLOSION = "RETRY_EXPLOSION"
    EXPENSIVE_MODEL = "EXPENSIVE_MODEL"
    TOOL_EXPLOSION = "TOOL_EXPLOSION"
    COST_SPIKE = "COST_SPIKE"

class AnomalySeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class CostAnomalyItem(BaseModel):
    id: str
    execution_id: str
    agent_id: str
    workflow_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    title: str
    description: str
    actual_cost_usd: float
    expected_cost_usd: float
    excess_spend_usd: float
    detected_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExecutiveSummary(BaseModel):
    total_ai_spend_usd: float
    total_tool_cost_usd: float
    total_human_cost_usd: float
    total_economic_cost_usd: float
    total_business_value_usd: float
    automation_savings_usd: float
    failed_execution_waste_usd: float
    net_economic_benefit_usd: float
    ai_roi_percentage: float
    total_executions: int
    successful_executions: int
    failed_executions: int
    escalated_executions: int
    success_rate_percentage: float
    total_tokens: int
    identified_monthly_savings_usd: float
    active_anomalies_count: int

class UnitEconomicsItem(BaseModel):
    workflow_id: str
    workflow_name: str
    outcome_type: str
    total_executions: int
    successful_outcomes: int
    failed_outcomes: int
    escalated_outcomes: int
    success_rate_pct: float
    total_spend_usd: float
    llm_spend_usd: float
    tool_spend_usd: float
    human_fallback_cost_usd: float
    failure_waste_usd: float
    avg_cost_per_execution_usd: float
    cost_per_successful_outcome_usd: float
    avg_latency_ms: float
    avg_tokens_per_task: float
    business_value_per_unit_usd: float
    net_margin_per_unit_usd: float

class CostBreakdownItem(BaseModel):
    key: str
    cost_usd: float
    percentage_of_total: float
    execution_count: int
    tokens: int

class FailureEconomicsSummary(BaseModel):
    total_failures: int
    total_failure_waste_usd: float
    total_retry_waste_usd: float
    total_escalation_waste_usd: float
    total_waste_usd: float
    expected_failure_cost_per_task_usd: float
    failure_rate_pct: float
    top_failing_workflows: List[Dict[str, Any]]
    top_failure_reasons: List[Dict[str, Any]]
