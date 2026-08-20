from fastapi import APIRouter
from app.api.v1.traces import router as traces_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.anomalies import router as anomalies_router
from app.api.v1.optimizations import router as optimizations_router
from app.api.v1.reports import router as reports_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(traces_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(anomalies_router)
api_v1_router.include_router(optimizations_router)
api_v1_router.include_router(reports_router)
