from typing import Optional, Dict
from pydantic import BaseModel, Field

class ModelPricing(BaseModel):
    model_name: str
    provider: str
    input_cost_per_m: float = Field(..., description="Cost in USD per 1M input tokens")
    output_cost_per_m: float = Field(..., description="Cost in USD per 1M output tokens")
    cached_input_cost_per_m: Optional[float] = Field(None, description="Cost in USD per 1M cached prompt tokens")
    default_latency_ms: Optional[float] = Field(None, description="Benchmark median latency in ms")

class ToolPricing(BaseModel):
    tool_name: str
    cost_per_call_usd: float = 0.0
    cost_per_second_usd: float = 0.0
    description: Optional[str] = None

class PricingOverrideRequest(BaseModel):
    model_pricing_overrides: Dict[str, ModelPricing] = Field(default_factory=dict)
    tool_pricing_overrides: Dict[str, ToolPricing] = Field(default_factory=dict)
    human_hourly_rate_usd: Optional[float] = None
