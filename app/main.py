from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.router import api_v1_router
from app.db.session import get_master_connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DuckDB tables and connection pool
    conn = get_master_connection()
    yield
    # Shutdown / flush if needed

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Financial control plane and optimization engine for autonomous AI agents.",
    lifespan=lifespan
)

# Enable CORS for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "duckdb_embedded"
    }

# Register API v1 routes
app.include_router(api_v1_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
