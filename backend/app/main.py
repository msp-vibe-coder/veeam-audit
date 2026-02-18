from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import dashboard, sites, trends, issues, reports, settings, pipeline

app = FastAPI(title="Veeam Audit API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
app.include_router(sites.router, prefix="/api/v1", tags=["sites"])
app.include_router(trends.router, prefix="/api/v1", tags=["trends"])
app.include_router(issues.router, prefix="/api/v1", tags=["issues"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(settings.router, prefix="/api/v1", tags=["settings"])
app.include_router(pipeline.router, prefix="/api/v1", tags=["pipeline"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
