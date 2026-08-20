from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Agent Economics"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # DuckDB file path (default to local agent_economics.duckdb)
    DB_PATH: str = str(Path("/home/tinchu/agent-economics/agent_economics.duckdb"))
    
    # Default economic metrics
    DEFAULT_HUMAN_HOURLY_RATE_USD: float = 35.0  # $35/hour fallback agent human intervention cost
    
    # Anomaly detection thresholds
    ANOMALY_RUNAWAY_STEP_THRESHOLD: int = 15
    ANOMALY_RETRY_COUNT_THRESHOLD: int = 3
    ANOMALY_TOOL_EXPLOSION_THRESHOLD: int = 10
    ANOMALY_COST_SPIKE_MULTIPLIER: float = 2.5
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
