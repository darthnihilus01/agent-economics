import duckdb
import threading
from typing import Optional
from pathlib import Path
from app.config import settings

_local = threading.local()
_master_conn: Optional[duckdb.DuckDBPyConnection] = None
_lock = threading.Lock()

def get_master_connection() -> duckdb.DuckDBPyConnection:
    global _master_conn
    with _lock:
        if _master_conn is None:
            # Ensure parent dir exists
            db_path = Path(settings.DB_PATH)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            _master_conn = duckdb.connect(settings.DB_PATH, read_only=False)
            init_db_schema(_master_conn)
        return _master_conn

def get_db() -> duckdb.DuckDBPyConnection:
    """
    Returns a cursor from the master connection for concurrent thread-safe operations.
    """
    master = get_master_connection()
    return master.cursor()

def init_db_schema(conn: duckdb.DuckDBPyConnection):
    """
    Initializes DuckDB tables and analytical indexes.
    """
    conn.execute("""
    CREATE TABLE IF NOT EXISTS executions (
        execution_id VARCHAR PRIMARY KEY,
        agent_id VARCHAR NOT NULL,
        agent_name VARCHAR NOT NULL,
        workflow_id VARCHAR NOT NULL,
        workflow_name VARCHAR NOT NULL,
        customer_id VARCHAR,
        outcome_type VARCHAR,
        status VARCHAR NOT NULL,
        business_value DOUBLE DEFAULT 0.0,
        started_at TIMESTAMP NOT NULL,
        ended_at TIMESTAMP NOT NULL,
        duration_ms DOUBLE DEFAULT 0.0,
        total_cost_usd DOUBLE DEFAULT 0.0,
        llm_cost_usd DOUBLE DEFAULT 0.0,
        tool_cost_usd DOUBLE DEFAULT 0.0,
        human_cost_usd DOUBLE DEFAULT 0.0,
        failure_waste_usd DOUBLE DEFAULT 0.0,
        input_tokens BIGINT DEFAULT 0,
        output_tokens BIGINT DEFAULT 0,
        cached_tokens BIGINT DEFAULT 0,
        step_count INT DEFAULT 0,
        error_count INT DEFAULT 0,
        retry_count INT DEFAULT 0,
        human_handoff_count INT DEFAULT 0,
        human_time_seconds DOUBLE DEFAULT 0.0,
        metadata VARCHAR DEFAULT '{}'
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS spans (
        span_id VARCHAR PRIMARY KEY,
        execution_id VARCHAR NOT NULL,
        parent_span_id VARCHAR,
        span_type VARCHAR NOT NULL,
        name VARCHAR NOT NULL,
        model VARCHAR,
        provider VARCHAR,
        input_tokens BIGINT DEFAULT 0,
        output_tokens BIGINT DEFAULT 0,
        cached_tokens BIGINT DEFAULT 0,
        input_cost_usd DOUBLE DEFAULT 0.0,
        output_cost_usd DOUBLE DEFAULT 0.0,
        tool_cost_usd DOUBLE DEFAULT 0.0,
        compute_cost_usd DOUBLE DEFAULT 0.0,
        total_cost_usd DOUBLE DEFAULT 0.0,
        latency_ms DOUBLE DEFAULT 0.0,
        is_retry BOOLEAN DEFAULT FALSE,
        retry_attempt INT DEFAULT 0,
        status VARCHAR DEFAULT 'SUCCESS',
        error_message VARCHAR,
        started_at TIMESTAMP,
        ended_at TIMESTAMP,
        payload_preview VARCHAR
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS model_pricing (
        model_name VARCHAR PRIMARY KEY,
        provider VARCHAR NOT NULL,
        input_cost_per_m DOUBLE NOT NULL,
        output_cost_per_m DOUBLE NOT NULL,
        cached_input_cost_per_m DOUBLE DEFAULT 0.0,
        default_latency_ms DOUBLE DEFAULT 0.0
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS tool_pricing (
        tool_name VARCHAR PRIMARY KEY,
        cost_per_call_usd DOUBLE DEFAULT 0.0,
        cost_per_second_usd DOUBLE DEFAULT 0.0,
        description VARCHAR
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS optimizations (
        id VARCHAR PRIMARY KEY,
        agent_id VARCHAR NOT NULL,
        workflow_id VARCHAR NOT NULL,
        category VARCHAR NOT NULL,
        title VARCHAR NOT NULL,
        description VARCHAR NOT NULL,
        target_component VARCHAR NOT NULL,
        current_cost_usd DOUBLE NOT NULL,
        projected_cost_usd DOUBLE NOT NULL,
        projected_monthly_savings_usd DOUBLE NOT NULL,
        quality_impact VARCHAR NOT NULL,
        confidence_score DOUBLE NOT NULL,
        status VARCHAR NOT NULL,
        guardrail_compliance BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP NOT NULL,
        parameters VARCHAR DEFAULT '{}',
        backtest_summary VARCHAR
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS anomalies (
        id VARCHAR PRIMARY KEY,
        execution_id VARCHAR NOT NULL,
        agent_id VARCHAR NOT NULL,
        workflow_id VARCHAR NOT NULL,
        anomaly_type VARCHAR NOT NULL,
        severity VARCHAR NOT NULL,
        title VARCHAR NOT NULL,
        description VARCHAR NOT NULL,
        actual_cost_usd DOUBLE NOT NULL,
        expected_cost_usd DOUBLE NOT NULL,
        excess_spend_usd DOUBLE NOT NULL,
        detected_at TIMESTAMP NOT NULL,
        metadata VARCHAR DEFAULT '{}'
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS business_units (
        outcome_type VARCHAR PRIMARY KEY,
        name VARCHAR NOT NULL,
        standard_human_cost_usd DOUBLE DEFAULT 15.0,
        default_business_value_usd DOUBLE DEFAULT 25.0,
        target_cost_usd DOUBLE DEFAULT 0.50,
        sla_seconds DOUBLE DEFAULT 300.0
    );
    """)
