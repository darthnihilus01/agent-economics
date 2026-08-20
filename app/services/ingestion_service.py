import uuid
import json
from datetime import datetime, timezone
from typing import List, Tuple
from app.models.trace import (
    ExecutionInput,
    ExecutionRecord,
    SpanInput,
    SpanRecord,
    SpanType,
    ExecutionStatus,
    IngestResponse
)
from app.services.pricing_service import pricing_service
from app.db.session import get_db

class IngestionService:
    def ingest_execution(self, exec_input: ExecutionInput) -> ExecutionRecord:
        """
        Processes and enriches a single execution trace, calculating all granular span and roll-up costs.
        """
        execution_id = exec_input.execution_id or str(uuid.uuid4())
        agent_id = exec_input.agent_id
        agent_name = exec_input.agent_name or agent_id
        workflow_id = exec_input.workflow_id
        workflow_name = exec_input.workflow_name or workflow_id
        customer_id = exec_input.customer_id
        outcome_type = exec_input.outcome_type or "standard_task"
        status = exec_input.status.value if isinstance(exec_input.status, ExecutionStatus) else str(exec_input.status)
        business_value = exec_input.business_value
        metadata = exec_input.metadata or {}

        # Parse timestamps & calculate duration
        started_at = exec_input.started_at or datetime.now(timezone.utc)
        ended_at = exec_input.ended_at or datetime.now(timezone.utc)
        duration_ms = max(0.0, (ended_at - started_at).total_seconds() * 1000.0)

        # Process spans
        span_records: List[SpanRecord] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_cached_tokens = 0
        total_llm_cost = 0.0
        total_tool_cost = 0.0
        retry_cost_waste = 0.0
        error_count = 0
        retry_count = 0
        human_handoff_count = 0

        for span in exec_input.spans:
            s_input_cost, s_output_cost, s_llm_cost = (0.0, 0.0, 0.0)
            s_tool_call_cost, s_compute_cost, s_tool_cost = (0.0, 0.0, 0.0)

            if span.span_type == SpanType.LLM_CALL or span.model is not None:
                s_input_cost, s_output_cost, s_llm_cost = pricing_service.calculate_llm_cost(
                    model_name=span.model,
                    input_tokens=span.input_tokens,
                    output_tokens=span.output_tokens,
                    cached_tokens=span.cached_tokens
                )
                total_input_tokens += span.input_tokens
                total_output_tokens += span.output_tokens
                total_cached_tokens += span.cached_tokens
                total_llm_cost += s_llm_cost

            if span.span_type in [SpanType.TOOL_CALL, SpanType.RETRIEVAL, SpanType.CODE_EXECUTION, SpanType.BROWSER_ACTION] or span.tool_name:
                t_name = span.tool_name or span.name
                s_tool_call_cost, s_compute_cost, s_tool_cost = pricing_service.calculate_tool_cost(
                    tool_name=t_name,
                    duration_seconds=span.tool_duration_seconds,
                    call_count=1
                )
                total_tool_cost += s_tool_cost

            if span.span_type == SpanType.HUMAN_HANDOFF:
                human_handoff_count += 1

            if span.is_retry or span.retry_attempt > 0:
                retry_count += 1
                retry_cost_waste += (s_llm_cost + s_tool_cost)

            if span.status.upper() == "ERROR" or span.error_message:
                error_count += 1

            span_total_cost = span.override_cost_usd if span.override_cost_usd is not None else round(s_llm_cost + s_tool_cost, 7)

            s_started = span.started_at or started_at
            s_ended = span.ended_at or ended_at
            s_lat = span.latency_ms if span.latency_ms > 0 else max(0.0, (s_ended - s_started).total_seconds() * 1000.0)

            s_record = SpanRecord(
                span_id=span.span_id,
                execution_id=execution_id,
                parent_span_id=span.parent_span_id,
                span_type=span.span_type,
                name=span.name,
                model=span.model,
                provider=span.provider or (pricing_service.get_model_pricing(span.model).provider if span.model else None),
                input_tokens=span.input_tokens,
                output_tokens=span.output_tokens,
                cached_tokens=span.cached_tokens,
                input_cost_usd=s_input_cost,
                output_cost_usd=s_output_cost,
                tool_cost_usd=s_tool_call_cost,
                compute_cost_usd=s_compute_cost,
                total_cost_usd=span_total_cost,
                latency_ms=s_lat,
                is_retry=span.is_retry or (span.retry_attempt > 0),
                retry_attempt=span.retry_attempt,
                status=span.status.upper(),
                error_message=span.error_message,
                started_at=s_started,
                ended_at=s_ended,
                payload_preview=span.payload_preview
            )
            span_records.append(s_record)

        # Calculate human escalation cost
        human_time_sec = exec_input.human_time_seconds
        human_cost = exec_input.human_cost_usd if exec_input.human_cost_usd is not None else pricing_service.calculate_human_cost(human_time_sec)
        
        # Calculate failure waste (cost of failed executions + retries + human intervention overhead on failure)
        total_execution_cost = round(total_llm_cost + total_tool_cost + human_cost, 6)
        
        failure_waste = 0.0
        if status in [ExecutionStatus.FAILURE.value, ExecutionStatus.ABORTED.value, ExecutionStatus.TIMEOUT.value]:
            failure_waste = total_execution_cost
        elif status == ExecutionStatus.ESCALATED_TO_HUMAN.value:
            # When escalated, part of the AI execution is sunk waste plus the human cost
            failure_waste = round((total_llm_cost * 0.5) + human_cost, 6)
        else:
            failure_waste = round(retry_cost_waste, 6)

        exec_record = ExecutionRecord(
            execution_id=execution_id,
            agent_id=agent_id,
            agent_name=agent_name,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            customer_id=customer_id,
            outcome_type=outcome_type,
            status=status,
            business_value=business_value,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            total_cost_usd=total_execution_cost,
            llm_cost_usd=round(total_llm_cost, 6),
            tool_cost_usd=round(total_tool_cost, 6),
            human_cost_usd=round(human_cost, 6),
            failure_waste_usd=round(failure_waste, 6),
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            cached_tokens=total_cached_tokens,
            step_count=len(span_records),
            error_count=error_count,
            retry_count=retry_count,
            human_handoff_count=human_handoff_count,
            human_time_seconds=human_time_sec,
            metadata=metadata,
            spans=span_records
        )

        self._save_to_duckdb(exec_record)
        return exec_record

    def ingest_batch(self, executions: List[ExecutionInput]) -> IngestResponse:
        records: List[ExecutionRecord] = []
        total_spans = 0
        total_cost = 0.0
        ids = []

        for e in executions:
            r = self.ingest_execution(e)
            records.append(r)
            total_spans += len(r.spans)
            total_cost += r.total_cost_usd
            ids.append(r.execution_id)

        return IngestResponse(
            success=True,
            ingested_executions=len(records),
            ingested_spans=total_spans,
            total_calculated_cost_usd=round(total_cost, 6),
            execution_ids=ids
        )

    def _save_to_duckdb(self, rec: ExecutionRecord):
        conn = get_db()
        meta_str = json.dumps(rec.metadata) if rec.metadata else "{}"

        # Insert execution
        conn.execute("""
            INSERT OR REPLACE INTO executions (
                execution_id, agent_id, agent_name, workflow_id, workflow_name, customer_id,
                outcome_type, status, business_value, started_at, ended_at, duration_ms,
                total_cost_usd, llm_cost_usd, tool_cost_usd, human_cost_usd, failure_waste_usd,
                input_tokens, output_tokens, cached_tokens, step_count, error_count, retry_count,
                human_handoff_count, human_time_seconds, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            rec.execution_id, rec.agent_id, rec.agent_name, rec.workflow_id, rec.workflow_name,
            rec.customer_id, rec.outcome_type, rec.status, rec.business_value,
            rec.started_at, rec.ended_at, rec.duration_ms,
            rec.total_cost_usd, rec.llm_cost_usd, rec.tool_cost_usd, rec.human_cost_usd,
            rec.failure_waste_usd, rec.input_tokens, rec.output_tokens, rec.cached_tokens,
            rec.step_count, rec.error_count, rec.retry_count, rec.human_handoff_count,
            rec.human_time_seconds, meta_str
        ])

        # Insert spans in batch
        if rec.spans:
            span_tuples = [
                (
                    s.span_id, s.execution_id, s.parent_span_id, s.span_type.value if hasattr(s.span_type, 'value') else str(s.span_type),
                    s.name, s.model, s.provider, s.input_tokens, s.output_tokens, s.cached_tokens,
                    s.input_cost_usd, s.output_cost_usd, s.tool_cost_usd, s.compute_cost_usd,
                    s.total_cost_usd, s.latency_ms, s.is_retry, s.retry_attempt, s.status,
                    s.error_message, s.started_at, s.ended_at, s.payload_preview
                )
                for s in rec.spans
            ]
            conn.executemany("""
                INSERT OR REPLACE INTO spans (
                    span_id, execution_id, parent_span_id, span_type, name, model, provider,
                    input_tokens, output_tokens, cached_tokens, input_cost_usd, output_cost_usd,
                    tool_cost_usd, compute_cost_usd, total_cost_usd, latency_ms, is_retry,
                    retry_attempt, status, error_message, started_at, ended_at, payload_preview
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, span_tuples)

ingestion_service = IngestionService()
