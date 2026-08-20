from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from app.services.analytics_service import analytics_service
from app.services.optimization_service import optimization_service
from app.services.anomaly_service import anomaly_service

console = Console()

def run_savings_report():
    exec_summary = analytics_service.get_executive_summary()
    unit_econ = analytics_service.get_unit_economics()
    report = optimization_service.generate_savings_report()
    anomalies = anomaly_service.get_active_anomalies(limit=5)

    console.print()
    console.print(Panel(
        f"[bold white]AGENT ECONOMICS — EXECUTIVE FINANCIAL CONTROL PLANE[/bold white]\n"
        f"[dim]Verified Optimization & Cost Attribution Report (PRD §23 Build)[/dim]",
        style="bold blue",
        expand=False
    ))
    console.print()

    # Executive KPI Summary Table
    kpi_table = Table(title="Executive Economic Overview (Last 30 Days)", style="cyan", show_header=True)
    kpi_table.add_column("Metric", style="bold")
    kpi_table.add_column("Value", justify="right")
    kpi_table.add_column("Business Context / Impact", style="dim")

    kpi_table.add_row("Total Executions", f"{exec_summary.total_executions:,}", "Autonomous task runs across all agents")
    kpi_table.add_row("Success Rate", f"{exec_summary.success_rate_percentage:.1f}%", f"{exec_summary.successful_executions:,} successful outcomes")
    kpi_table.add_row("Total AI Spend", f"${exec_summary.total_ai_spend_usd:,.2f}", "Raw LLM tokens + external tool compute")
    kpi_table.add_row("Human Escalation Cost", f"${exec_summary.total_human_cost_usd:,.2f}", "Fallback human review overhead ($35/hr)")
    kpi_table.add_row("Failure Waste", f"${exec_summary.failed_execution_waste_usd:,.2f}", "Unrecovered failures, retries & aborted loops")
    kpi_table.add_row("Total Business Value", f"${exec_summary.total_business_value_usd:,.2f}", "Standard economic value delivered")
    kpi_table.add_row("Net Economic Benefit", f"[bold green]${exec_summary.net_economic_benefit_usd:,.2f}[/bold green]", "Value generated minus all AI & human costs")
    kpi_table.add_row("AI ROI", f"[bold green]{exec_summary.ai_roi_percentage:.0f}%[/bold green]", "Net Economic Benefit / AI Spend")
    console.print(kpi_table)
    console.print()

    # Unit Economics Table
    unit_table = Table(title="Workflow Unit Economics (True Cost per Outcome)", style="magenta", show_header=True)
    unit_table.add_column("Workflow", style="bold")
    unit_table.add_column("Outcome Unit")
    unit_table.add_column("Executions", justify="right")
    unit_table.add_column("Success %", justify="right")
    unit_table.add_column("True Cost / Unit", justify="right", style="bold yellow")
    unit_table.add_column("Unit Value", justify="right")
    unit_table.add_column("Unit Margin", justify="right", style="bold green")

    for u in unit_econ:
        unit_table.add_row(
            u.workflow_name,
            u.outcome_type,
            f"{u.total_executions:,}",
            f"{u.success_rate_pct:.1f}%",
            f"${u.cost_per_successful_outcome_usd:.2f}",
            f"${u.business_value_per_unit_usd:.2f}",
            f"${u.net_margin_per_unit_usd:.2f}"
        )
    console.print(unit_table)
    console.print()

    # Top 5 Verified Recommendations Table (PRD §23)
    rec_table = Table(title="Top 5 Verified Savings Recommendations (Zero Quality Loss)", style="green", show_header=True)
    rec_table.add_column("#", justify="center")
    rec_table.add_column("Optimization Opportunity", style="bold")
    rec_table.add_column("Category")
    rec_table.add_column("Projected Mo. Savings", justify="right", style="bold yellow")
    rec_table.add_column("Confidence", justify="right")
    rec_table.add_column("Quality Impact & Guardrail Guarantee", style="dim")

    for idx, r in enumerate(report.top_recommendations[:5], 1):
        rec_table.add_row(
            str(idx),
            r.title,
            r.category.value,
            f"${r.projected_monthly_savings_usd:,.2f}",
            f"{r.confidence_score * 100:.0f}%",
            r.quality_impact
        )
    console.print(rec_table)
    console.print()

    # Summary Panel
    console.print(Panel(
        f"[bold green]PROVEN MONTHLY SAVINGS IDENTIFIED: ${report.total_projected_savings_usd:,.2f} ({report.projected_savings_percentage:.1f}% Spend Reduction)[/bold green]\n\n"
        f"{report.executive_summary_text}",
        title="Economic Autopilot Verification Summary",
        style="bold green"
    ))
    console.print()

if __name__ == "__main__":
    run_savings_report()
