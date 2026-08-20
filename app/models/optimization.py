from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

def utc_now():
    return datetime.now(timezone.utc)

class OptimizationCategory(str, Enum):
    MODEL_ROUTING = "MODEL_ROUTING"
    CONTEXT_PRUNING = "CONTEXT_PRUNING"
    RETRY_OPTIMIZATION = "RETRY_OPTIMIZATION"
    PROMPT_CACHING = "PROMPT_CACHING"
    TOOL_CONSOLIDATION = "TOOL_CONSOLIDATION"
    HUMAN_ROUTING = "HUMAN_ROUTING"

class OptimizationStatus(str, Enum):
    PROPOSED = "PROPOSED"
    BACKTESTED = "BACKTESTED"
    APPROVED = "APPROVED"
    DEPLOYED = "DEPLOYED"
    REJECTED = "REJECTED"

class GuardrailConstraints(BaseModel):
    min_success_rate_pct: float = Field(default=95.0, description="Minimum allowable success rate %")
    max_latency_p95_ms: float = Field(default=5000.0, description="Maximum allowable P95 latency in ms")
    max_error_rate_pct: float = Field(default=5.0, description="Maximum error rate %")
    max_allowed_cost_per_task_usd: Optional[float] = None

class OptimizationRecommendation(BaseModel):
    id: str
    agent_id: str
    workflow_id: str
    category: OptimizationCategory
    title: str
    description: str
    target_component: str
    current_cost_usd: float
    projected_cost_usd: float
    projected_monthly_savings_usd: float
    quality_impact: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    status: OptimizationStatus = OptimizationStatus.PROPOSED
    guardrail_compliance: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    backtest_summary: Optional[Dict[str, Any]] = None

class BacktestRequest(BaseModel):
    recommendation_id: str
    sample_size: int = Field(default=200, description="Number of recent historical traces to backtest")
    guardrails: GuardrailConstraints = Field(default_factory=GuardrailConstraints)

class BacktestResult(BaseModel):
    recommendation_id: str
    passed_guardrails: bool
    sample_size: int
    baseline_total_cost_usd: float
    simulated_total_cost_usd: float
    simulated_savings_usd: float
    simulated_savings_pct: float
    baseline_success_rate_pct: float
    simulated_success_rate_pct: float
    baseline_p95_latency_ms: float
    simulated_p95_latency_ms: float
    violations: List[str] = Field(default_factory=list)
    tested_at: datetime = Field(default_factory=utc_now)

class VerifiedSavingsReport(BaseModel):
    report_title: str = "Agent Economics — Verified Optimization & Savings Report"
    generated_at: datetime = Field(default_factory=utc_now)
    period_days: int = 30
    total_baseline_spend_usd: float
    total_projected_savings_usd: float
    projected_savings_percentage: float
    total_active_agents: int
    total_workflows: int
    top_recommendations: List[OptimizationRecommendation]
    executive_summary_text: str
    guardrails_verified: bool
