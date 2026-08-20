from fastapi import APIRouter
from app.models.optimization import VerifiedSavingsReport
from app.services.optimization_service import optimization_service
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/reports", tags=["Reports & PMF Validation"])

@router.get("/pmf-savings-report", response_model=VerifiedSavingsReport)
def get_pmf_savings_report():
    """
    PRD §23 First Validation Build:
    Generates the verified report: 'Here are the 5 changes that would have saved you $X last month with no measurable quality degradation.'
    """
    return optimization_service.generate_savings_report()
