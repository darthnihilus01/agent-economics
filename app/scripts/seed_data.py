import random
import uuid
from datetime import datetime, timedelta, timezone
from app.models.trace import ExecutionInput, SpanInput, SpanType, ExecutionStatus
from app.services.ingestion_service import ingestion_service
from app.services.anomaly_service import anomaly_service
from app.services.optimization_service import optimization_service
from rich.console import Console

console = Console()

WORKFLOW_SPECS = [
    {
        "agent_id": "support-agent-v2",
        "agent_name": "Tier-2 Customer Support Agent",
        "workflow_id": "ticket_resolution",
        "workflow_name": "Autonomous Zendesk Ticket Resolution",
        "outcome_type": "resolved_support_ticket",
        "business_value_per_unit": 18.50, # Manual support ticket costs ~$18.50
        "models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"],
        "tools": ["vector_retrieval", "zendesk_api_update", "kb_search"],
        "human_escalation_rate": 0.12,
        "failure_rate": 0.06,
        "runaway_loop_rate": 0.04
    },
    {
        "agent_id": "finance-agent-v1",
        "agent_name": "Autonomous Accounts Payable Agent",
        "workflow_id": "invoice_processing",
        "workflow_name": "ERP Invoice Extraction & Reconciliation",
        "outcome_type": "processed_invoice",
        "business_value_per_unit": 32.00, # Manual invoice reconciliation costs ~$32
        "models": ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"],
        "tools": ["ocr_parser", "erp_sap_lookup", "code_execution"],
        "human_escalation_rate": 0.08,
        "failure_rate": 0.04,
        "runaway_loop_rate": 0.02
    },
    {
        "agent_id": "devops-agent-v1",
        "agent_name": "Autonomous Code Review & PR Assistant",
        "workflow_id": "code_review_pipeline",
        "workflow_name": "Automated Pull Request Security & Quality Review",
        "outcome_type": "reviewed_pull_request",
        "business_value_per_unit": 45.00,
        "models": ["claude-3-5-sonnet", "gpt-4o", "deepseek-reasoner"],
        "tools": ["git_diff_parser", "linter_sandbox", "ast_analyzer"],
        "human_escalation_rate": 0.15,
        "failure_rate": 0.08,
        "runaway_loop_rate": 0.05
    },
    {
        "agent_id": "sales-agent-v3",
        "agent_name": "Autonomous Inbound Lead Qualifier",
        "workflow_id": "lead_qualification",
        "workflow_name": "Salesforce Lead Research & Enrichment",
        "outcome_type": "qualified_sales_lead",
        "business_value_per_unit": 25.00,
        "models": ["gpt-4o", "gpt-4o-mini", "gemini-1.5-flash"],
        "tools": ["web_search", "linkedin_enrichment", "salesforce_sync"],
        "human_escalation_rate": 0.05,
        "failure_rate": 0.03,
        "runaway_loop_rate": 0.01
    }
]

CUSTOMERS = ["AcmeCorp", "Stripe-EU", "Shopify-Merchant-481", "FinTech-Global", "Healthcare-Plus", "TechCorp-Global"]

def generate_traces(num_executions: int = 500):
    console.print(f"[bold cyan]Generating {num_executions} realistic enterprise agent execution traces...[/bold cyan]")
    now = datetime.now(timezone.utc)
    batch = []

    for i in range(num_executions):
        wf = random.choice(WORKFLOW_SPECS)
        customer = random.choice(CUSTOMERS)
        
        # Timestamp spread across last 30 days
        days_ago = random.uniform(0.1, 30.0)
        started_at = now - timedelta(days=days_ago)
        
        # Determine status
        rand_val = random.random()
        if rand_val < wf["failure_rate"]:
            status = ExecutionStatus.FAILURE
            human_time_sec = 0.0
            bval = 0.0
        elif rand_val < (wf["failure_rate"] + wf["human_escalation_rate"]):
            status = ExecutionStatus.ESCALATED_TO_HUMAN
            human_time_sec = random.uniform(180.0, 900.0) # 3 to 15 mins
            bval = wf["business_value_per_unit"] * 0.5
        else:
            status = ExecutionStatus.SUCCESS
            human_time_sec = 0.0
            bval = wf["business_value_per_unit"]

        is_runaway = (random.random() < wf["runaway_loop_rate"])
        step_count = random.randint(16, 24) if is_runaway else random.randint(3, 8)

        spans = []
        exec_id = str(uuid.uuid4())
        curr_time = started_at
        total_in_tokens = 0
        total_out_tokens = 0

        for step_idx in range(step_count):
            span_id = str(uuid.uuid4())
            is_llm = (random.random() > 0.35)
            
            if is_llm:
                model = random.choice(wf["models"])
                # Simulate token growth / context bloat on longer traces
                base_in = random.randint(800, 3000)
                in_tok = base_in + (step_idx * 1200 if is_runaway else step_idx * 200)
                out_tok = random.randint(150, 800)
                cached_tok = int(in_tok * 0.4) if random.random() > 0.5 else 0
                
                total_in_tokens += in_tok
                total_out_tokens += out_tok
                
                lat_ms = random.uniform(300.0, 2200.0)
                span_ended = curr_time + timedelta(milliseconds=lat_ms)
                
                is_retry = (random.random() < 0.15)
                retry_att = 1 if is_retry else 0
                
                spans.append(SpanInput(
                    span_id=span_id,
                    span_type=SpanType.LLM_CALL,
                    name=f"llm_step_{step_idx+1}_{model}",
                    model=model,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cached_tokens=cached_tok,
                    latency_ms=lat_ms,
                    is_retry=is_retry,
                    retry_attempt=retry_att,
                    status="ERROR" if is_retry and random.random() > 0.5 else "SUCCESS",
                    started_at=curr_time,
                    ended_at=span_ended
                ))
                curr_time = span_ended
            else:
                tool_name = random.choice(wf["tools"])
                dur_sec = random.uniform(0.2, 4.0)
                lat_ms = dur_sec * 1000.0
                span_ended = curr_time + timedelta(seconds=dur_sec)
                
                spans.append(SpanInput(
                    span_id=span_id,
                    span_type=SpanType.TOOL_CALL,
                    name=tool_name,
                    tool_name=tool_name,
                    tool_duration_seconds=dur_sec,
                    latency_ms=lat_ms,
                    status="SUCCESS",
                    started_at=curr_time,
                    ended_at=span_ended
                ))
                curr_time = span_ended

        exec_input = ExecutionInput(
            execution_id=exec_id,
            agent_id=wf["agent_id"],
            agent_name=wf["agent_name"],
            workflow_id=wf["workflow_id"],
            workflow_name=wf["workflow_name"],
            customer_id=customer,
            outcome_type=wf["outcome_type"],
            status=status,
            business_value=bval,
            human_time_seconds=human_time_sec,
            started_at=started_at,
            ended_at=curr_time,
            metadata={"source": "seed_pipeline", "environment": "production"},
            spans=spans
        )
        batch.append(exec_input)

    # Ingest in batch
    res = ingestion_service.ingest_batch(batch)
    console.print(f"[bold green]✓ Ingested {res.ingested_executions} executions with {res.ingested_spans} spans.[/bold green]")
    console.print(f"[bold green]✓ Total calculated trace spend: ${res.total_calculated_cost_usd:,.2f}[/bold green]")

    # Run anomaly detection scan
    console.print("[yellow]Running initial anomaly detection scan...[/yellow]")
    anomalies = anomaly_service.scan_historical_anomalies()
    console.print(f"[bold green]✓ Flagged {len(anomalies)} cost anomalies across historical executions.[/bold green]")

    # Generate initial optimization recommendations
    console.print("[yellow]Generating Economic Autopilot optimization recommendations...[/yellow]")
    recs = optimization_service.generate_recommendations()
    console.print(f"[bold green]✓ Generated {len(recs)} optimization recommendations.[/bold green]")

if __name__ == "__main__":
    generate_traces(600)
