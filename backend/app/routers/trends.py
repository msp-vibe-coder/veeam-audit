from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailySummary, SiteMetric, Anomaly
from app.schemas.schemas import DailySummaryOut, SiteMetricOut, AnomalyOut

router = APIRouter()


@router.get("/trends/daily", response_model=list[DailySummaryOut])
def get_daily_trends(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(DailySummary)
    if date_from:
        q = q.filter(DailySummary.report_date >= date_from)
    if date_to:
        q = q.filter(DailySummary.report_date <= date_to)

    rows = q.order_by(DailySummary.report_date).all()
    return [DailySummaryOut.model_validate(r) for r in rows]


@router.get("/trends/sites", response_model=list[SiteMetricOut])
def get_site_trends(db: Session = Depends(get_db)):
    latest_date = db.query(func.max(SiteMetric.report_date)).scalar()
    if latest_date is None:
        return []

    rows = (
        db.query(SiteMetric)
        .filter(SiteMetric.report_date == latest_date)
        .order_by(SiteMetric.site_code)
        .all()
    )
    return [SiteMetricOut.model_validate(r) for r in rows]


@router.get("/trends/anomalies", response_model=list[AnomalyOut])
def get_anomaly_trends(
    severity: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Anomaly)
    if severity:
        q = q.filter(Anomaly.severity == severity)
    if type:
        q = q.filter(Anomaly.type == type)
    if date_from:
        q = q.filter(Anomaly.report_date >= date_from)
    if date_to:
        q = q.filter(Anomaly.report_date <= date_to)

    rows = q.order_by(Anomaly.report_date.desc()).all()
    return [AnomalyOut.model_validate(r) for r in rows]
