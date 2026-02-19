from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailySummary, SiteMetric, Anomaly, PipelineRun
from app.schemas.schemas import DashboardResponse, DailySummaryOut

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    # ---- KPIs from the latest report date ----
    latest_date_row = (
        db.query(func.max(SiteMetric.report_date)).scalar()
    )

    total_veeam_tb = 0.0
    total_wasabi_tb = 0.0
    total_wasabi_deleted_tb = 0.0
    discrepancy_pct = 0.0
    total_cost = 0.0
    active_issues = 0

    if latest_date_row is not None:
        agg = (
            db.query(
                func.coalesce(func.sum(SiteMetric.veeam_tb), 0),
                func.coalesce(func.sum(SiteMetric.wasabi_active_tb), 0),
                func.coalesce(func.sum(SiteMetric.wasabi_deleted_tb), 0),
            )
            .filter(SiteMetric.report_date == latest_date_row)
            .one()
        )
        total_veeam_tb = float(agg[0])
        total_wasabi_tb = float(agg[1])
        total_wasabi_deleted_tb = float(agg[2])

        if total_veeam_tb > 0:
            discrepancy_pct = round(
                abs(total_veeam_tb - total_wasabi_tb) / total_veeam_tb * 100, 2
            )

        # Total cost from latest daily summary
        latest_summary = (
            db.query(DailySummary)
            .filter(DailySummary.report_date == latest_date_row)
            .first()
        )
        if latest_summary:
            total_cost = float(latest_summary.total_cost or 0)

        # Active issues = anomalies for the latest date
        active_issues = (
            db.query(func.count(Anomaly.id))
            .filter(Anomaly.report_date == latest_date_row)
            .scalar()
        ) or 0

    kpis = {
        "total_veeam_tb": total_veeam_tb,
        "total_wasabi_tb": total_wasabi_tb,
        "total_wasabi_deleted_tb": total_wasabi_deleted_tb,
        "discrepancy_pct": discrepancy_pct,
        "total_cost": total_cost,
        "active_issues": active_issues,
    }

    # ---- Daily summaries for chart data ----
    q = db.query(DailySummary)
    if date_from:
        q = q.filter(DailySummary.report_date >= date_from)
    if date_to:
        q = q.filter(DailySummary.report_date <= date_to)
    daily_summaries = q.order_by(DailySummary.report_date).all()

    # ---- Latest pipeline run ----
    pipeline_run = (
        db.query(PipelineRun).order_by(desc(PipelineRun.id)).first()
    )
    latest_pipeline_run = None
    if pipeline_run:
        latest_pipeline_run = {
            "id": pipeline_run.id,
            "started_at": pipeline_run.started_at.isoformat() if pipeline_run.started_at else None,
            "completed_at": pipeline_run.completed_at.isoformat() if pipeline_run.completed_at else None,
            "status": pipeline_run.status,
        }

    return DashboardResponse(
        kpis=kpis,
        daily_summaries=[DailySummaryOut.model_validate(s) for s in daily_summaries],
        latest_pipeline_run=latest_pipeline_run,
    )
