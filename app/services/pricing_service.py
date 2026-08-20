from typing import Dict, Optional, Tuple
from app.models.pricing import ModelPricing, ToolPricing
from app.config import settings

# Built-in Default Model Catalog (Prices in USD per 1M tokens)
DEFAULT_MODEL_PRICING: Dict[str, ModelPricing] = {
    # OpenAI
    "gpt-4o": ModelPricing(model_name="gpt-4o", provider="openai", input_cost_per_m=2.50, output_cost_per_m=10.00, cached_input_cost_per_m=1.25, default_latency_ms=800.0),
    "gpt-4o-2024-08-06": ModelPricing(model_name="gpt-4o-2024-08-06", provider="openai", input_cost_per_m=2.50, output_cost_per_m=10.00, cached_input_cost_per_m=1.25, default_latency_ms=800.0),
    "gpt-4o-mini": ModelPricing(model_name="gpt-4o-mini", provider="openai", input_cost_per_m=0.15, output_cost_per_m=0.60, cached_input_cost_per_m=0.075, default_latency_ms=450.0),
    "o1": ModelPricing(model_name="o1", provider="openai", input_cost_per_m=15.00, output_cost_per_m=60.00, cached_input_cost_per_m=7.50, default_latency_ms=3500.0),
    "o3-mini": ModelPricing(model_name="o3-mini", provider="openai", input_cost_per_m=1.10, output_cost_per_m=4.40, cached_input_cost_per_m=0.55, default_latency_ms=1200.0),
    "gpt-4-turbo": ModelPricing(model_name="gpt-4-turbo", provider="openai", input_cost_per_m=10.00, output_cost_per_m=30.00, cached_input_cost_per_m=5.00, default_latency_ms=1400.0),
    "text-embedding-3-small": ModelPricing(model_name="text-embedding-3-small", provider="openai", input_cost_per_m=0.02, output_cost_per_m=0.0, default_latency_ms=100.0),
    "text-embedding-3-large": ModelPricing(model_name="text-embedding-3-large", provider="openai", input_cost_per_m=0.13, output_cost_per_m=0.0, default_latency_ms=150.0),

    # Anthropic
    "claude-3-5-sonnet": ModelPricing(model_name="claude-3-5-sonnet", provider="anthropic", input_cost_per_m=3.00, output_cost_per_m=15.00, cached_input_cost_per_m=0.30, default_latency_ms=900.0),
    "claude-3-5-sonnet-20241022": ModelPricing(model_name="claude-3-5-sonnet-20241022", provider="anthropic", input_cost_per_m=3.00, output_cost_per_m=15.00, cached_input_cost_per_m=0.30, default_latency_ms=900.0),
    "claude-3-5-haiku": ModelPricing(model_name="claude-3-5-haiku", provider="anthropic", input_cost_per_m=0.80, output_cost_per_m=4.00, cached_input_cost_per_m=0.08, default_latency_ms=400.0),
    "claude-3-5-haiku-20241022": ModelPricing(model_name="claude-3-5-haiku-20241022", provider="anthropic", input_cost_per_m=0.80, output_cost_per_m=4.00, cached_input_cost_per_m=0.08, default_latency_ms=400.0),
    "claude-3-opus-20240229": ModelPricing(model_name="claude-3-opus-20240229", provider="anthropic", input_cost_per_m=15.00, output_cost_per_m=75.00, cached_input_cost_per_m=1.50, default_latency_ms=2500.0),

    # Google Gemini
    "gemini-1.5-pro": ModelPricing(model_name="gemini-1.5-pro", provider="google", input_cost_per_m=1.25, output_cost_per_m=5.00, cached_input_cost_per_m=0.3125, default_latency_ms=1000.0),
    "gemini-1.5-flash": ModelPricing(model_name="gemini-1.5-flash", provider="google", input_cost_per_m=0.075, output_cost_per_m=0.30, cached_input_cost_per_m=0.01875, default_latency_ms=350.0),
    "gemini-2.0-flash": ModelPricing(model_name="gemini-2.0-flash", provider="google", input_cost_per_m=0.10, output_cost_per_m=0.40, cached_input_cost_per_m=0.025, default_latency_ms=320.0),

    # DeepSeek
    "deepseek-chat": ModelPricing(model_name="deepseek-chat", provider="deepseek", input_cost_per_m=0.14, output_cost_per_m=0.28, cached_input_cost_per_m=0.014, default_latency_ms=500.0),
    "deepseek-reasoner": ModelPricing(model_name="deepseek-reasoner", provider="deepseek", input_cost_per_m=0.55, output_cost_per_m=2.19, cached_input_cost_per_m=0.14, default_latency_ms=2800.0),

    # Open / Self-hosted
    "llama-3.3-70b": ModelPricing(model_name="llama-3.3-70b", provider="meta", input_cost_per_m=0.40, output_cost_per_m=0.40, default_latency_ms=450.0),
    "llama-3.1-8b": ModelPricing(model_name="llama-3.1-8b", provider="meta", input_cost_per_m=0.05, output_cost_per_m=0.05, default_latency_ms=200.0),
}

DEFAULT_TOOL_PRICING: Dict[str, ToolPricing] = {
    "web_search": ToolPricing(tool_name="web_search", cost_per_call_usd=0.010, description="Serp / Bing search query"),
    "browser_action": ToolPricing(tool_name="browser_action", cost_per_call_usd=0.005, cost_per_second_usd=0.001, description="Headless browser instance"),
    "code_execution": ToolPricing(tool_name="code_execution", cost_per_call_usd=0.002, cost_per_second_usd=0.0005, description="Isolated sandbox compute"),
    "vector_retrieval": ToolPricing(tool_name="vector_retrieval", cost_per_call_usd=0.001, description="Vector search retrieval"),
    "sql_query": ToolPricing(tool_name="sql_query", cost_per_call_usd=0.0002, description="Read/write DB query"),
}

class PricingService:
    def __init__(self):
        self._custom_model_pricing: Dict[str, ModelPricing] = {}
        self._custom_tool_pricing: Dict[str, ToolPricing] = {}
        self._human_hourly_rate: float = settings.DEFAULT_HUMAN_HOURLY_RATE_USD

    def set_custom_model_pricing(self, model: ModelPricing):
        self._custom_model_pricing[model.model_name.lower()] = model

    def set_custom_tool_pricing(self, tool: ToolPricing):
        self._custom_tool_pricing[tool.tool_name.lower()] = tool

    def set_human_hourly_rate(self, rate: float):
        self._human_hourly_rate = rate

    def get_model_pricing(self, model_name: Optional[str]) -> ModelPricing:
        if not model_name:
            return ModelPricing(model_name="unknown", provider="generic", input_cost_per_m=1.0, output_cost_per_m=2.0)
        
        cleaned = model_name.strip().lower()
        if cleaned in self._custom_model_pricing:
            return self._custom_model_pricing[cleaned]
        
        # Exact match in default
        if cleaned in DEFAULT_MODEL_PRICING:
            return DEFAULT_MODEL_PRICING[cleaned]
        
        # Fuzzy prefix match (e.g. gpt-4o-2024-05-13 -> gpt-4o)
        for key, pricing in DEFAULT_MODEL_PRICING.items():
            if key in cleaned or cleaned in key:
                return pricing
                
        # Default fallback reasonable tier
        return ModelPricing(model_name=model_name, provider="generic", input_cost_per_m=2.0, output_cost_per_m=8.0)

    def get_tool_pricing(self, tool_name: Optional[str]) -> ToolPricing:
        if not tool_name:
            return ToolPricing(tool_name="default", cost_per_call_usd=0.0)
        cleaned = tool_name.strip().lower()
        if cleaned in self._custom_tool_pricing:
            return self._custom_tool_pricing[cleaned]
        if cleaned in DEFAULT_TOOL_PRICING:
            return DEFAULT_TOOL_PRICING[cleaned]
        for key, pricing in DEFAULT_TOOL_PRICING.items():
            if key in cleaned:
                return pricing
        return ToolPricing(tool_name=tool_name, cost_per_call_usd=0.0)

    def calculate_llm_cost(
        self,
        model_name: Optional[str],
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0
    ) -> Tuple[float, float, float]:
        """
        Returns (input_cost_usd, output_cost_usd, total_llm_cost_usd)
        """
        pricing = self.get_model_pricing(model_name)
        
        uncached_input = max(0, input_tokens - cached_tokens)
        cached_rate = pricing.cached_input_cost_per_m if pricing.cached_input_cost_per_m is not None else (pricing.input_cost_per_m * 0.5)
        
        input_cost = ((uncached_input * pricing.input_cost_per_m) + (cached_tokens * cached_rate)) / 1_000_000.0
        output_cost = (output_tokens * pricing.output_cost_per_m) / 1_000_000.0
        total = round(input_cost + output_cost, 7)
        return round(input_cost, 7), round(output_cost, 7), total

    def calculate_tool_cost(
        self,
        tool_name: Optional[str],
        duration_seconds: float = 0.0,
        call_count: int = 1
    ) -> Tuple[float, float, float]:
        """
        Returns (call_cost_usd, compute_duration_cost_usd, total_tool_cost_usd)
        """
        pricing = self.get_tool_pricing(tool_name)
        call_cost = pricing.cost_per_call_usd * call_count
        compute_cost = pricing.cost_per_second_usd * duration_seconds
        total = round(call_cost + compute_cost, 7)
        return round(call_cost, 7), round(compute_cost, 7), total

    def calculate_human_cost(self, duration_seconds: float) -> float:
        """
        Calculates human escalation fallback cost: (seconds / 3600) * hourly_rate
        """
        if duration_seconds <= 0:
            return 0.0
        hours = duration_seconds / 3600.0
        return round(hours * self._human_hourly_rate, 4)

pricing_service = PricingService()
