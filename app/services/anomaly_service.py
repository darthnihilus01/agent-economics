import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional
from app.db.session import get_db
from app.config import settings
from app.models.analytics import CostAnomalyItem, AnomalyType, AnomalySeverity
from app.models.trace import ExecutionRecord

class AnomalyDetectionService:
    def scan_execution(self, rec: ExecutionRecord) -> List[CostAnomalyItem]:
        """
        Scans a single execution record for cost and behavioral anomalies.
        """
        anomalies: List[CostAnomalyItem] = []
        now = datetime.now(timezone.utc)

        # 1. Runaway Loop Detection
        if rec.step_count >= settings.ANOMALY_RUNAWAY_STEP_THRESHOLD:
            excess_steps = rec.step_count - settings.ANOMALY_RUNAWAY_STEP_THRESHOLD
            avg_step_cost = (rec.total_cost_usd / rec.step_count) if rec.step_count > 0 else 0.0
            excess_spend = round(excess_steps * avg_step_cost, 4)
            
            anomalies.append(CostAnomalyItem(
                id=str(uuid.uuid4()),
                execution_id=rec.execution_id,
                agent_id=rec.agent_id,
                workflow_id=rec.workflow_id,
                anomaly_type=AnomalyType.RUNAWAY_LOOP,
                severity=AnomalySeverity.HIGH,
                title=f"Runaway execution loop detected ({rec.step_count} steps)",
                description=f"Agent exceeded step threshold ({settings.ANOMALY_RUNAWAY_STEP_THRESHOLD}). Executed {rec.step_count} steps costing ${rec.total_cost_usd:.4f}.",
                actual_cost_usd=rec.total_cost_usd,
                expected_cost_usd=round(rec.total_cost_usd - excess_spend, 4),
                excess_spend_usd=excess_spend,
                detected_at=now,
                metadata={"step_count": rec.step_count}
            ))

        # 2. Retry Explosion Detection
        if rec.retry_count >= settings.ANOMALY_RETRY_COUNT_THRESHOLD:
            retry_cost = round(rec.failure_waste_usd, 4)
            anomalies.append(CostAnomalyItem(
                id=str(uuid.uuid4()),
                execution_id=rec.execution_id,
                agent_id=rec.agent_id,
                workflow_id=rec.workflow_id,
                anomaly_type=AnomalyType.RETRY_EXPLOSION,
                severity=AnomalySeverity.HIGH if rec.retry_count >= 5 else AnomalySeverity.MEDIUM,
                title=f"Excessive retries detected ({rec.retry_count} retries)",
                description=f"Agent repeatedly failed and retried {rec.retry_count} times, incurring ${retry_cost:.4f} in retry waste.",
                actual_cost_usd=rec.total_cost_usd,
                expected_cost_usd=max(0.0, round(rec.total_cost_usd - retry_cost, 4)),
                excess_spend_usd=retry_cost,
                detected_at=now,
                metadata={"retry_count": rec.retry_count}
            ))

        # 3. Context Bloat Detection (check if prompt tokens scale linearly without truncation)
        if len(rec.spans) >= 4:
            first_span_tokens = rec.spans[0].input_tokens if rec.spans else 0
            last_span_tokens = rec.spans[-1].input_tokens if rec.spans else 0
            if first_span_tokens > 0 and last_span_tokens > (first_span_tokens * 4) and last_span_tokens > 12000:
                excess_tokens = last_span_tokens - (first_span_tokens * 2)
                excess_cost = round((excess_tokens * 2.50) / 1_000_000, 4)
                anomalies.append(CostAnomalyItem(
                    id=str(uuid.uuid4()),
                    execution_id=rec.execution_id,
                    agent_id=rec.agent_id,
                    workflow_id=rec.workflow_id,
                    anomaly_type=AnomalyType.CONTEXT_BLOAT,
                    severity=AnomalySeverity.MEDIUM,
                    title="Rapid context bloat across agent steps",
                    description=f"Input prompt tokens ballooned from {first_span_tokens} to {last_span_tokens} without context window pruning or summarization.",
                    actual_cost_usd=rec.total_cost_usd,
                    expected_cost_usd=max(0.0, round(rec.total_cost_usd - excess_cost, 4)),
                    excess_spend_usd=excess_cost,
                    detected_at=now,
                    metadata={"initial_tokens": first_span_tokens, "final_tokens": last_span_tokens}
                ))

        # 4. Tool Explosion Detection
        tool_spans = [s for s in rec.spans if s.span_type in ['tool_call', 'retrieval', 'browser_action', 'code_execution']]
        if len(tool_spans) >= settings.ANOMALY_TOOL_EXPLOSION_THRESHOLD:
            tool_cost = sum(s.total_cost_usd for s in tool_spans)
            anomalies.append(CostAnomalyItem(
                id=str(uuid.uuid4()),
                execution_id=rec.execution_id,
                agent_id=rec.agent_id,
                workflow_id=rec.workflow_id,
                anomaly_type=AnomalyType.TOOL_EXPLOSION,
                severity=AnomalySeverity.HIGH,
                title=f"Tool execution explosion ({len(tool_spans)} tool calls)",
                description=f"Agent invoked {len(tool_spans)} external tool calls in a single task costing ${tool_cost:.4f}.",
                actual_cost_usd=rec.total_cost_usd,
                expected_cost_usd=max(0.0, round(rec.total_cost_usd - (tool_cost * 0.7), 4)),
                excess_spend_usd=round(tool_cost * 0.7, 4),
                detected_at=now,
                metadata={"tool_count": len(tool_spans)}
            ))

        # Save anomalies to DuckDB
        if anomalies:
            self._save_anomalies(anomalies)

        return anomalies

    def scan_historical_anomalies(self) -> List[CostAnomalyItem]:
        """
        Runs analytical queries across all historical executions in DuckDB to flag anomalies and cost spikes.
        """
        conn = get_db()
        now = datetime.now(timezone.utc)
        anomalies: List[CostAnomalyItem] = []

        # Find executions with cost > 2.5x the workflow average
        spike_rows = conn.execute("""
            WITH wf_stats AS (
                SELECT workflow_id, AVG(total_cost_usd) as avg_cost, STDDEV(total_cost_usd) as std_cost
                FROM executions
                GROUP BY workflow_id
            )
            SELECT 
                e.execution_id, e.agent_id, e.workflow_id, e.total_cost_usd, w.avg_cost, e.step_count, e.retry_count
            FROM executions e
            JOIN wf_stats w ON e.workflow_id = w.workflow_id
            WHERE e.total_cost_usd > (w.avg_cost * 2.5) AND e.total_cost_usd > 0.10
            ORDER BY e.total_cost_usd DESC
            LIMIT 20
        """).fetchall()

        for r in spike_rows:
            exec_id, ag_id, wf_id, actual_c, avg_c, steps, retries = r
            excess = max(0.0, actual_c - avg_c)
            anomalies.append(CostAnomalyItem(
                id=str(uuid.uuid4()),
                execution_id=exec_id,
                agent_id=ag_id,
                workflow_id=wf_id,
                anomaly_type=AnomalyType.COST_SPIKE,
                severity=AnomalySeverity.HIGH if actual_c > (avg_c * 4) else AnomalySeverity.MEDIUM,
                title=f"Statistical cost spike in workflow '{wf_id}'",
                description=f"Execution cost ${actual_c:.4f} is 2.5x+ higher than the workflow average (${avg_c:.4f}) with {steps} steps and {retries} retries.",
                actual_cost_usd=round(actual_c, 4),
                expected_cost_usd=round(avg_c, 4),
                excess_spend_usd=round(excess, 4),
                detected_at=now,
                metadata={"workflow_avg_cost": round(avg_c, 4), "steps": steps}
            ))

        if anomalies:
            self._save_anomalies(anomalies)

        return anomalies

    def get_active_anomalies(self, limit: int = 50) -> List[CostAnomalyItem]:
        conn = get_db()
        rows = conn.execute("""
            SELECT id, execution_id, agent_id, workflow_id, anomaly_type, severity,
                   title, description, actual_cost_usd, expected_cost_usd, excess_spend_usd,
                   detected_at, metadata
            FROM anomalies
            ORDER BY detected_at DESC
            LIMIT ?
        """, [limit]).fetchall()

        items = []
        for r in rows:
            items.append(CostAnomalyItem(
                id=r[0],
                execution_id=r[1],
                agent_id=r[2],
                workflow_id=r[3],
                anomaly_type=AnomalyType(r[4]),
                severity=AnomalySeverity(r[5]),
                title=r[6],
                description=r[7],
                actual_cost_usd=r[8],
                expected_cost_usd=r[9],
                excess_spend_usd=r[10],
                detected_at=r[11],
                metadata=json.loads(r[12]) if r[12] else {}
            ))
        return items

    def _save_anomalies(self, items: List[CostAnomalyItem]):
        conn = get_db()
        tuples = [
            (
                a.id, a.execution_id, a.agent_id, a.workflow_id, a.anomaly_type.value,
                a.severity.value, a.title, a.description, a.actual_cost_usd,
                a.expected_cost_usd, a.excess_spend_usd, a.detected_at,
                json.dumps(a.metadata)
            )
            for a in items
        ]
        conn.executemany("""
            INSERT OR REPLACE INTO anomalies (
                id, execution_id, agent_id, workflow_id, anomaly_type, severity,
                title, description, actual_cost_usd, expected_cost_usd, excess_spend_usd,
                detected_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tuples)

anomaly_service = AnomalyDetectionService()
