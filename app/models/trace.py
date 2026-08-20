from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
import uuid

class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    ESCALATED_TO_HUMAN = "ESCALATED_TO_HUMAN"
    TIMEOUT = "TIMEOUT"
    ABORTED = "ABORTED"

class SpanType(str, Enum):
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    RETRIEVAL = "retrieval"
    CODE_EXECUTION = "code_execution"
    BROWSER_ACTION = "browser_action"
    HUMAN_HANDOFF = "human_handoff"
    RETRY = "retry"
    OTHER = "other"

class SpanInput(BaseModel):
    span_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None
    span_type: SpanType = SpanType.LLM_CALL
    name: str
    model: Optional[str] = None
    provider: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    tool_name: Optional[str] = None
    tool_duration_seconds: float = 0.0
    latency_ms: float = 0.0
    is_retry: bool = False
    retry_attempt: int = 0
    status: str = "SUCCESS"
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    payload_preview: Optional[str] = None
    
    # Optional direct cost override if calculated upstream
    override_cost_usd: Optional[float] = None

class SpanRecord(SpanInput):
    execution_id: str
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    tool_cost_usd: float = 0.0
    compute_cost_usd: float = 0.0
    total_cost_usd: float = 0.0

class ExecutionInput(BaseModel):
    execution_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    agent_name: Optional[str] = None
    workflow_id: str
    workflow_name: Optional[str] = None
    customer_id: Optional[str] = None
    outcome_type: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    business_value: float = 0.0
    human_time_seconds: float = 0.0
    human_cost_usd: Optional[float] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    spans: List[SpanInput] = Field(default_factory=list)

class ExecutionRecord(BaseModel):
    execution_id: str
    agent_id: str
    agent_name: str
    workflow_id: str
    workflow_name: str
    customer_id: Optional[str]
    outcome_type: Optional[str]
    status: str
    business_value: float
    started_at: datetime
    ended_at: datetime
    duration_ms: float
    total_cost_usd: float
    llm_cost_usd: float
    tool_cost_usd: float
    human_cost_usd: float
    failure_waste_usd: float
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    step_count: int
    error_count: int
    retry_count: int
    human_handoff_count: int
    human_time_seconds: float
    metadata: Dict[str, Any]
    spans: List[SpanRecord] = Field(default_factory=list)

class TraceBatchIngest(BaseModel):
    executions: List[ExecutionInput]

class IngestResponse(BaseModel):
    success: bool
    ingested_executions: int
    ingested_spans: int
    total_calculated_cost_usd: float
    execution_ids: List[str]
