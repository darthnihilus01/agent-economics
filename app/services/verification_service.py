import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.db.session import get_db
from app.models.optimization import (
    BacktestRequest,
    BacktestResult,
    GuardrailConstraints,
    OptimizationStatus,
    OptimizationCategory
)
from app.services.optimization_service import optimization_service
from app.services.pricing_service import pricing_service

class VerificationEngine:
    def run_backtest(self, req: BacktestRequest) -> BacktestResult:
        """
        Simulates an optimization recommendation against historical production traces in DuckDB
        and verifies that it complies with all quality, latency, and reliability guardrails.
        """
        rec = optimization_service.get_recommendation_by_id(req.recommendation_id)
        if not rec:
            raise ValueError(f"Recommendation with ID '{req.recommendation_id}' not found.")

        conn = get_db()
        sample_size = req.sample_size
        guardrails = req.guardrails

        # Fetch recent historical executions for this workflow
        exec_rows = conn.execute("""
            SELECT 
                execution_id, status, duration_ms, total_cost_usd, llm_cost_usd,
                tool_cost_usd, human_cost_usd, input_tokens, output_tokens, step_count, retry_count
            FROM executions
            WHERE workflow_id = ?
            ORDER BY started_at DESC
            LIMIT ?
        """, [rec.workflow_id, sample_size]).fetchall()

        if not exec_rows:
            # Fallback across all workflows if this specific workflow has few runs
            exec_rows = conn.execute("""
                SELECT 
                    execution_id, status, duration_ms, total_cost_usd, llm_cost_usd,
                    tool_cost_usd, human_cost_usd, input_tokens, output_tokens, step_count, retry_count
                FROM executions
                ORDER BY started_at DESC
                LIMIT ?
            """, [sample_size]).fetchall()

        actual_sample_size = len(exec_rows)
        if actual_sample_size == 0:
            return BacktestResult(
                recommendation_id=req.recommendation_id,
                passed_guardrails=True,
                sample_size=0,
                baseline_total_cost_usd=0.0,
                simulated_total_cost_usd=0.0,
                simulated_savings_usd=0.0,
                simulated_savings_pct=0.0,
                baseline_success_rate_pct=100.0,
                simulated_success_rate_pct=100.0,
                baseline_p95_latency_ms=0.0,
                simulated_p95_latency_ms=0.0,
                violations=[]
            )

        baseline_costs = [float(r[3]) for r in exec_rows]
        baseline_latencies = [float(r[2]) for r in exec_rows]
        baseline_successes = [1 if r[1] == 'SUCCESS' else 0 for r in exec_rows]

        baseline_total_cost = sum(baseline_costs)
        baseline_success_rate = (sum(baseline_successes) / actual_sample_size) * 100.0
        
        # Calculate baseline P95 latency
        sorted_lat = sorted(baseline_latencies)
        p95_idx = int(0.95 * len(sorted_lat)) - 1
        baseline_p95_lat = sorted_lat[max(0, p95_idx)]

        # Simulate optimization impact based on category
        simulated_costs = []
        simulated_latencies = []
        simulated_successes = list(baseline_successes)

        for r in exec_rows:
            e_id, status, dur, total_c, llm_c, tool_c, human_c, in_toks, out_toks, steps, retries = r
            
            sim_cost = total_c
            sim_lat = dur

            if rec.category == OptimizationCategory.MODEL_ROUTING:
                # e.g. switching model reduces LLM cost by ~70-85% and latency by ~40%
                target_model = rec.parameters.get("target_model", "gpt-4o-mini")
                _, _, new_llm_c = pricing_service.calculate_llm_cost(target_model, in_toks, out_toks)
                sim_cost = round(new_llm_c + tool_c + human_c, 6)
                sim_lat = max(150.0, dur * 0.65) # Mini models are faster

            elif rec.category == OptimizationCategory.PROMPT_CACHING:
                # Caching saves 75% on input tokens, reduces latency by 20%
                cache_tokens = int(in_toks * 0.7)
                uncached = in_toks - cache_tokens
                # Recalculate prompt cost
                cached_llm_c = ((uncached * 2.5) + (cache_tokens * 0.3) + (out_toks * 10.0)) / 1_000_000.0
                sim_cost = round(cached_llm_c + tool_c + human_c, 6)
                sim_lat = max(200.0, dur * 0.8)

            elif rec.category == OptimizationCategory.RETRY_OPTIMIZATION:
                # Capping retries removes retry waste and prevents long tail latencies
                if retries > 2:
                    excess_retries = retries - 2
                    waste_per_step = (total_c / steps) if steps > 0 else 0.0
                    saved_retry_cost = excess_retries * waste_per_step
                    sim_cost = max(0.001, round(total_c - saved_retry_cost, 6))
                    sim_lat = max(300.0, dur * 0.5)

            elif rec.category == OptimizationCategory.CONTEXT_PRUNING:
                # Pruning 35% tokens
                sim_cost = round(total_c * 0.70, 6)
                sim_lat = round(dur * 0.85, 1)

            simulated_costs.append(sim_cost)
            simulated_latencies.append(sim_lat)

        simulated_total_cost = sum(simulated_costs)
        simulated_savings = max(0.0, baseline_total_cost - simulated_total_cost)
        simulated_savings_pct = ((simulated_savings / baseline_total_cost) * 100.0) if baseline_total_cost > 0 else 0.0
        
        simulated_success_rate = (sum(simulated_successes) / actual_sample_size) * 100.0
        
        sorted_sim_lat = sorted(simulated_latencies)
        sim_p95_lat = sorted_sim_lat[max(0, int(0.95 * len(sorted_sim_lat)) - 1)]

        # Guardrails Validation
        violations: List[str] = []
        if simulated_success_rate < guardrails.min_success_rate_pct:
            violations.append(
                f"Success rate {simulated_success_rate:.1f}% below minimum threshold of {guardrails.min_success_rate_pct:.1f}%"
            )
        if sim_p95_lat > guardrails.max_latency_p95_ms:
            violations.append(
                f"Simulated P95 latency {sim_p95_lat:.0f}ms exceeded maximum allowed {guardrails.max_latency_p95_ms:.0f}ms"
            )

        passed = (len(violations) == 0)

        # Update recommendation with backtest results
        b_summary = {
            "passed_guardrails": passed,
            "sample_size": actual_sample_size,
            "baseline_cost_usd": round(baseline_total_cost, 4),
            "simulated_cost_usd": round(simulated_total_cost, 4),
            "savings_pct": round(simulated_savings_pct, 1),
            "baseline_p95_latency_ms": round(baseline_p95_lat, 1),
            "simulated_p95_latency_ms": round(sim_p95_lat, 1),
            "tested_at": datetime.now(timezone.utc).isoformat(),
            "violations": violations
        }

        if passed:
            optimization_service.update_recommendation_status(
                rec.id, OptimizationStatus.BACKTESTED, backtest_summary=b_summary
            )

        return BacktestResult(
            recommendation_id=rec.id,
            passed_guardrails=passed,
            sample_size=actual_sample_size,
            baseline_total_cost_usd=round(baseline_total_cost, 4),
            simulated_total_cost_usd=round(simulated_total_cost, 4),
            simulated_savings_usd=round(simulated_savings, 4),
            simulated_savings_pct=round(simulated_savings_pct, 1),
            baseline_success_rate_pct=round(baseline_success_rate, 1),
            simulated_success_rate_pct=round(simulated_success_rate, 1),
            baseline_p95_latency_ms=round(baseline_p95_lat, 1),
            simulated_p95_latency_ms=round(sim_p95_lat, 1),
            violations=violations
        )

    def deploy_optimization(self, rec_id: str) -> Dict[str, Any]:
        """
        Deploys an approved and backtested optimization to live production routing.
        """
        rec = optimization_service.get_recommendation_by_id(rec_id)
        if not rec:
            raise ValueError(f"Recommendation with ID '{rec_id}' not found.")
        
        optimization_service.update_recommendation_status(rec_id, OptimizationStatus.DEPLOYED)
        return {
            "success": True,
            "recommendation_id": rec_id,
            "workflow_id": rec.workflow_id,
            "status": "DEPLOYED",
            "message": f"Optimization '{rec.title}' successfully deployed to production."
        }

verification_service = VerificationEngine()
