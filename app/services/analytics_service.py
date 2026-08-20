import json
from typing import List, Optional, Dict, Any
from app.db.session import get_db
from app.models.analytics import (
    ExecutiveSummary,
    UnitEconomicsItem,
    CostBreakdownItem,
    FailureEconomicsSummary
)
from app.models.trace import ExecutionRecord, SpanRecord

class AnalyticsService:
    def get_executive_summary(self) -> ExecutiveSummary:
        conn = get_db()
        
        # Aggregations across all executions
        row = conn.execute("""
            SELECT 
                COUNT(*) as total_executions,
                COALESCE(SUM(total_cost_usd), 0.0) as total_economic_cost,
                COALESCE(SUM(llm_cost_usd), 0.0) as total_llm_cost,
                COALESCE(SUM(tool_cost_usd), 0.0) as total_tool_cost,
                COALESCE(SUM(human_cost_usd), 0.0) as total_human_cost,
                COALESCE(SUM(failure_waste_usd), 0.0) as failure_waste,
                COALESCE(SUM(business_value), 0.0) as total_business_val,
                COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens,
                COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END), 0) as successful_count,
                COALESCE(SUM(CASE WHEN status IN ('FAILURE', 'ABORTED', 'TIMEOUT') THEN 1 ELSE 0 END), 0) as failed_count,
                COALESCE(SUM(CASE WHEN status = 'ESCALATED_TO_HUMAN' THEN 1 ELSE 0 END), 0) as escalated_count
            FROM executions
        """).fetchone()

        total_execs = row[0] or 0
        total_economic_cost = float(row[1] or 0.0)
        total_llm_cost = float(row[2] or 0.0)
        total_tool_cost = float(row[3] or 0.0)
        total_human_cost = float(row[4] or 0.0)
        failure_waste = float(row[5] or 0.0)
        total_business_val = float(row[6] or 0.0)
        total_tokens = int(row[7] or 0)
        successful_count = int(row[8] or 0)
        failed_count = int(row[9] or 0)
        escalated_count = int(row[10] or 0)

        # Active anomalies count
        anomaly_row = conn.execute("SELECT COUNT(*) FROM anomalies").fetchone()
        active_anomalies = anomaly_row[0] if anomaly_row else 0

        # Identified monthly savings from optimizations
        savings_row = conn.execute("""
            SELECT COALESCE(SUM(projected_monthly_savings_usd), 0.0) 
            FROM optimizations 
            WHERE status IN ('PROPOSED', 'BACKTESTED', 'APPROVED')
        """).fetchone()
        identified_savings = float(savings_row[0] if savings_row else 0.0)

        # Derived calculations
        success_rate = (successful_count / total_execs * 100.0) if total_execs > 0 else 0.0
        total_ai_spend = round(total_llm_cost + total_tool_cost, 4)
        net_economic_benefit = round(total_business_val - total_economic_cost, 4)
        
        # Automation savings vs typical manual benchmark ($15/task manual human baseline)
        baseline_human_benchmark = total_execs * 15.0
        automation_savings = max(0.0, round(baseline_human_benchmark - total_economic_cost, 4))
        
        ai_roi_pct = ((net_economic_benefit / total_ai_spend) * 100.0) if total_ai_spend > 0 else 0.0

        return ExecutiveSummary(
            total_ai_spend_usd=total_ai_spend,
            total_tool_cost_usd=round(total_tool_cost, 4),
            total_human_cost_usd=round(total_human_cost, 4),
            total_economic_cost_usd=round(total_economic_cost, 4),
            total_business_value_usd=round(total_business_val, 4),
            automation_savings_usd=automation_savings,
            failed_execution_waste_usd=round(failure_waste, 4),
            net_economic_benefit_usd=net_economic_benefit,
            ai_roi_percentage=round(ai_roi_pct, 2),
            total_executions=total_execs,
            successful_executions=successful_count,
            failed_executions=failed_count,
            escalated_executions=escalated_count,
            success_rate_percentage=round(success_rate, 2),
            total_tokens=total_tokens,
            identified_monthly_savings_usd=round(identified_savings, 2),
            active_anomalies_count=active_anomalies
        )

    def get_unit_economics(self, workflow_id: Optional[str] = None) -> List[UnitEconomicsItem]:
        conn = get_db()
        where_clause = "WHERE workflow_id = ?" if workflow_id else ""
        params = [workflow_id] if workflow_id else []

        query = f"""
            SELECT 
                workflow_id,
                MAX(workflow_name) as workflow_name,
                COALESCE(MAX(outcome_type), 'standard_task') as outcome_type,
                COUNT(*) as total_executions,
                COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END), 0) as successful_outcomes,
                COALESCE(SUM(CASE WHEN status IN ('FAILURE', 'ABORTED', 'TIMEOUT') THEN 1 ELSE 0 END), 0) as failed_outcomes,
                COALESCE(SUM(CASE WHEN status = 'ESCALATED_TO_HUMAN' THEN 1 ELSE 0 END), 0) as escalated_outcomes,
                COALESCE(SUM(total_cost_usd), 0.0) as total_spend,
                COALESCE(SUM(llm_cost_usd), 0.0) as llm_spend,
                COALESCE(SUM(tool_cost_usd), 0.0) as tool_spend,
                COALESCE(SUM(human_cost_usd), 0.0) as human_spend,
                COALESCE(SUM(failure_waste_usd), 0.0) as failure_waste,
                COALESCE(AVG(duration_ms), 0.0) as avg_duration,
                COALESCE(AVG(input_tokens + output_tokens), 0.0) as avg_tokens,
                COALESCE(SUM(business_value), 0.0) as total_business_val
            FROM executions
            {where_clause}
            GROUP BY workflow_id
            ORDER BY total_spend DESC
        """
        rows = conn.execute(query, params).fetchall()
        results: List[UnitEconomicsItem] = []

        for r in rows:
            w_id = r[0]
            w_name = r[1] or w_id
            outcome_type = r[2]
            total_execs = int(r[3] or 0)
            successful = int(r[4] or 0)
            failed = int(r[5] or 0)
            escalated = int(r[6] or 0)
            total_spend = float(r[7] or 0.0)
            llm_spend = float(r[8] or 0.0)
            tool_spend = float(r[9] or 0.0)
            human_spend = float(r[10] or 0.0)
            failure_waste = float(r[11] or 0.0)
            avg_duration = float(r[12] or 0.0)
            avg_tokens = float(r[13] or 0.0)
            total_bval = float(r[14] or 0.0)

            success_rate = (successful / total_execs * 100.0) if total_execs > 0 else 0.0
            avg_cost_per_exec = (total_spend / total_execs) if total_execs > 0 else 0.0
            # TRUE Cost per successful business outcome = Total spend for that workflow / Successful outcomes
            cost_per_success = (total_spend / successful) if successful > 0 else total_spend
            
            bval_per_unit = (total_bval / successful) if successful > 0 else 0.0
            net_margin = bval_per_unit - cost_per_success

            results.append(UnitEconomicsItem(
                workflow_id=w_id,
                workflow_name=w_name,
                outcome_type=outcome_type,
                total_executions=total_execs,
                successful_outcomes=successful,
                failed_outcomes=failed,
                escalated_outcomes=escalated,
                success_rate_pct=round(success_rate, 2),
                total_spend_usd=round(total_spend, 4),
                llm_spend_usd=round(llm_spend, 4),
                tool_spend_usd=round(tool_spend, 4),
                human_fallback_cost_usd=round(human_spend, 4),
                failure_waste_usd=round(failure_waste, 4),
                avg_cost_per_execution_usd=round(avg_cost_per_exec, 4),
                cost_per_successful_outcome_usd=round(cost_per_success, 4),
                avg_latency_ms=round(avg_duration, 1),
                avg_tokens_per_task=round(avg_tokens, 1),
                business_value_per_unit_usd=round(bval_per_unit, 2),
                net_margin_per_unit_usd=round(net_margin, 2)
            ))

        return results

    def get_cost_breakdowns(self, dimension: str = "model") -> List[CostBreakdownItem]:
        conn = get_db()
        dimension = dimension.lower()

        if dimension == "model":
            query = """
                SELECT 
                    COALESCE(model, 'unknown') as k,
                    SUM(total_cost_usd) as cost,
                    COUNT(*) as cnt,
                    COALESCE(SUM(input_tokens + output_tokens), 0) as tokens
                FROM spans
                WHERE span_type = 'llm_call' OR model IS NOT NULL
                GROUP BY model
                ORDER BY cost DESC
            """
        elif dimension == "agent":
            query = """
                SELECT 
                    COALESCE(agent_name, agent_id) as k,
                    SUM(total_cost_usd) as cost,
                    COUNT(*) as cnt,
                    COALESCE(SUM(input_tokens + output_tokens), 0) as tokens
                FROM executions
                GROUP BY agent_name, agent_id
                ORDER BY cost DESC
            """
        elif dimension == "workflow":
            query = """
                SELECT 
                    COALESCE(workflow_name, workflow_id) as k,
                    SUM(total_cost_usd) as cost,
                    COUNT(*) as cnt,
                    COALESCE(SUM(input_tokens + output_tokens), 0) as tokens
                FROM executions
                GROUP BY workflow_name, workflow_id
                ORDER BY cost DESC
            """
        elif dimension == "tool":
            query = """
                SELECT 
                    name as k,
                    SUM(total_cost_usd) as cost,
                    COUNT(*) as cnt,
                    0 as tokens
                FROM spans
                WHERE span_type IN ('tool_call', 'retrieval', 'browser_action', 'code_execution')
                GROUP BY name
                ORDER BY cost DESC
            """
        elif dimension == "customer":
            query = """
                SELECT 
                    COALESCE(customer_id, 'anonymous') as k,
                    SUM(total_cost_usd) as cost,
                    COUNT(*) as cnt,
                    COALESCE(SUM(input_tokens + output_tokens), 0) as tokens
                FROM executions
                GROUP BY customer_id
                ORDER BY cost DESC
                LIMIT 25
            """
        elif dimension == "day":
            query = """
                SELECT 
                    strftime(started_at, '%Y-%m-%d') as k,
                    SUM(total_cost_usd) as cost,
                    COUNT(*) as cnt,
                    COALESCE(SUM(input_tokens + output_tokens), 0) as tokens
                FROM executions
                GROUP BY strftime(started_at, '%Y-%m-%d')
                ORDER BY k ASC
            """
        else:
            return []

        rows = conn.execute(query).fetchall()
        total_cost = sum(r[1] for r in rows) if rows else 0.0

        items: List[CostBreakdownItem] = []
        for r in rows:
            k = str(r[0])
            cost = float(r[1] or 0.0)
            cnt = int(r[2] or 0)
            tokens = int(r[3] or 0)
            pct = (cost / total_cost * 100.0) if total_cost > 0 else 0.0
            items.append(CostBreakdownItem(
                key=k,
                cost_usd=round(cost, 4),
                percentage_of_total=round(pct, 2),
                execution_count=cnt,
                tokens=tokens
            ))

        return items

    def get_failure_economics(self) -> FailureEconomicsSummary:
        conn = get_db()
        
        # Overall failure metrics
        row = conn.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN status IN ('FAILURE', 'ABORTED', 'TIMEOUT') THEN 1 ELSE 0 END), 0) as total_failures,
                COALESCE(SUM(CASE WHEN status IN ('FAILURE', 'ABORTED', 'TIMEOUT') THEN total_cost_usd ELSE 0.0 END), 0.0) as failure_waste,
                COALESCE(SUM(retry_count * (total_cost_usd / NULLIF(step_count, 0))), 0.0) as retry_waste,
                COALESCE(SUM(human_cost_usd), 0.0) as escalation_waste,
                COALESCE(SUM(failure_waste_usd), 0.0) as total_waste,
                COUNT(*) as total_execs
            FROM executions
        """).fetchone()

        total_failures = int(row[0] or 0)
        failure_waste = float(row[1] or 0.0)
        retry_waste = float(row[2] or 0.0)
        escalation_waste = float(row[3] or 0.0)
        total_waste = float(row[4] or 0.0)
        total_execs = int(row[5] or 0)

        failure_rate = (total_failures / total_execs * 100.0) if total_execs > 0 else 0.0
        expected_failure_cost_per_task = (total_waste / total_execs) if total_execs > 0 else 0.0

        # Top failing workflows
        wf_rows = conn.execute("""
            SELECT 
                workflow_id,
                MAX(workflow_name) as wf_name,
                COUNT(*) as failed_count,
                COALESCE(SUM(total_cost_usd), 0.0) as waste_usd
            FROM executions
            WHERE status IN ('FAILURE', 'ABORTED', 'TIMEOUT')
            GROUP BY workflow_id
            ORDER BY waste_usd DESC
            LIMIT 5
        """).fetchall()

        top_failing_wf = [
            {"workflow_id": r[0], "workflow_name": r[1] or r[0], "failed_executions": r[2], "wasted_cost_usd": round(r[3], 4)}
            for r in wf_rows
        ]

        # Top failure error reasons from spans
        err_rows = conn.execute("""
            SELECT 
                COALESCE(error_message, 'Unknown execution error') as reason,
                COUNT(*) as count,
                COALESCE(SUM(total_cost_usd), 0.0) as cost_usd
            FROM spans
            WHERE status = 'ERROR' OR error_message IS NOT NULL
            GROUP BY reason
            ORDER BY count DESC
            LIMIT 5
        """).fetchall()

        top_reasons = [
            {"reason": r[0], "occurrences": r[1], "cost_usd": round(r[2], 4)}
            for r in err_rows
        ]

        return FailureEconomicsSummary(
            total_failures=total_failures,
            total_failure_waste_usd=round(failure_waste, 4),
            total_retry_waste_usd=round(retry_waste, 4),
            total_escalation_waste_usd=round(escalation_waste, 4),
            total_waste_usd=round(total_waste, 4),
            expected_failure_cost_per_task_usd=round(expected_failure_cost_per_task, 4),
            failure_rate_pct=round(failure_rate, 2),
            top_failing_workflows=top_failing_wf,
            top_failure_reasons=top_reasons
        )

    def get_executions(
        self,
        agent_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        conn = get_db()
        conditions = []
        params = []

        if agent_id:
            conditions.append("agent_id = ?")
            params.append(agent_id)
        if workflow_id:
            conditions.append("workflow_id = ?")
            params.append(workflow_id)
        if status:
            conditions.append("status = ?")
            params.append(status.upper())

        where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.extend([limit, offset])

        query = f"""
            SELECT 
                execution_id, agent_id, agent_name, workflow_id, workflow_name, customer_id,
                outcome_type, status, business_value, started_at, ended_at, duration_ms,
                total_cost_usd, llm_cost_usd, tool_cost_usd, human_cost_usd, failure_waste_usd,
                input_tokens, output_tokens, step_count, retry_count, metadata
            FROM executions
            {where_sql}
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(query, params).fetchall()
        results = []
        for r in rows:
            results.append({
                "execution_id": r[0],
                "agent_id": r[1],
                "agent_name": r[2],
                "workflow_id": r[3],
                "workflow_name": r[4],
                "customer_id": r[5],
                "outcome_type": r[6],
                "status": r[7],
                "business_value": r[8],
                "started_at": r[9].isoformat() if r[9] else None,
                "ended_at": r[10].isoformat() if r[10] else None,
                "duration_ms": r[11],
                "total_cost_usd": r[12],
                "llm_cost_usd": r[13],
                "tool_cost_usd": r[14],
                "human_cost_usd": r[15],
                "failure_waste_usd": r[16],
                "input_tokens": r[17],
                "output_tokens": r[18],
                "step_count": r[19],
                "retry_count": r[20],
                "metadata": json.loads(r[21]) if r[21] else {}
            })
        return results

    def get_execution_detail(self, execution_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db()
        exec_row = conn.execute("""
            SELECT 
                execution_id, agent_id, agent_name, workflow_id, workflow_name, customer_id,
                outcome_type, status, business_value, started_at, ended_at, duration_ms,
                total_cost_usd, llm_cost_usd, tool_cost_usd, human_cost_usd, failure_waste_usd,
                input_tokens, output_tokens, cached_tokens, step_count, error_count, retry_count,
                human_handoff_count, human_time_seconds, metadata
            FROM executions
            WHERE execution_id = ?
        """, [execution_id]).fetchone()

        if not exec_row:
            return None

        # Fetch spans
        span_rows = conn.execute("""
            SELECT 
                span_id, execution_id, parent_span_id, span_type, name, model, provider,
                input_tokens, output_tokens, cached_tokens, input_cost_usd, output_cost_usd,
                tool_cost_usd, compute_cost_usd, total_cost_usd, latency_ms, is_retry,
                retry_attempt, status, error_message, started_at, ended_at, payload_preview
            FROM spans
            WHERE execution_id = ?
            ORDER BY started_at ASC
        """, [execution_id]).fetchall()

        spans = []
        for s in span_rows:
            spans.append({
                "span_id": s[0],
                "parent_span_id": s[2],
                "span_type": s[3],
                "name": s[4],
                "model": s[5],
                "provider": s[6],
                "input_tokens": s[7],
                "output_tokens": s[8],
                "cached_tokens": s[9],
                "input_cost_usd": s[10],
                "output_cost_usd": s[11],
                "tool_cost_usd": s[12],
                "compute_cost_usd": s[13],
                "total_cost_usd": s[14],
                "latency_ms": s[15],
                "is_retry": s[16],
                "retry_attempt": s[17],
                "status": s[18],
                "error_message": s[19],
                "started_at": s[20].isoformat() if s[20] else None,
                "ended_at": s[21].isoformat() if s[21] else None,
                "payload_preview": s[22]
            })

        return {
            "execution_id": exec_row[0],
            "agent_id": exec_row[1],
            "agent_name": exec_row[2],
            "workflow_id": exec_row[3],
            "workflow_name": exec_row[4],
            "customer_id": exec_row[5],
            "outcome_type": exec_row[6],
            "status": exec_row[7],
            "business_value": exec_row[8],
            "started_at": exec_row[9].isoformat() if exec_row[9] else None,
            "ended_at": exec_row[10].isoformat() if exec_row[10] else None,
            "duration_ms": exec_row[11],
            "total_cost_usd": exec_row[12],
            "llm_cost_usd": exec_row[13],
            "tool_cost_usd": exec_row[14],
            "human_cost_usd": exec_row[15],
            "failure_waste_usd": exec_row[16],
            "input_tokens": exec_row[17],
            "output_tokens": exec_row[18],
            "cached_tokens": exec_row[19],
            "step_count": exec_row[20],
            "error_count": exec_row[21],
            "retry_count": exec_row[22],
            "human_handoff_count": exec_row[23],
            "human_time_seconds": exec_row[24],
            "metadata": json.loads(exec_row[25]) if exec_row[25] else {},
            "spans": spans
        }

analytics_service = AnalyticsService()
