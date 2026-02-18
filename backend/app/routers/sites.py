from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SiteMetric, BdrMetric, BucketMetric
from app.schemas.schemas import (
    SiteListResponse,
    SiteMetricOut,
    SiteDetailResponse,
    BdrMetricOut,
    BucketMetricOut,
)

router = APIRouter()


@router.get("/sites", response_model=SiteListResponse)
def list_sites(
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("site_code"),
    sort_dir: Optional[str] = Query("asc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    # Determine the latest report date
    latest_date = db.query(func.max(SiteMetric.report_date)).scalar()
    if latest_date is None:
        return SiteListResponse(sites=[], total=0)

    q = db.query(SiteMetric).filter(SiteMetric.report_date == latest_date)

    if search:
        q = q.filter(SiteMetric.site_code.ilike(f"%{search}%"))

    # Total count before pagination
    total = q.count()

    # Sorting
    sort_column = getattr(SiteMetric, sort_by, SiteMetric.site_code)
    if sort_dir and sort_dir.lower() == "desc":
        q = q.order_by(desc(sort_column))
    else:
        q = q.order_by(asc(sort_column))

    sites = q.offset(skip).limit(limit).all()

    return SiteListResponse(
        sites=[SiteMetricOut.model_validate(s) for s in sites],
        total=total,
    )


@router.get("/sites/{code}", response_model=SiteDetailResponse)
def get_site_detail(code: str, db: Session = Depends(get_db)):
    # Latest date for this site
    latest_date = (
        db.query(func.max(SiteMetric.report_date))
        .filter(SiteMetric.site_code == code)
        .scalar()
    )
    if latest_date is None:
        raise HTTPException(status_code=404, detail=f"Site '{code}' not found")

    current = (
        db.query(SiteMetric)
        .filter(SiteMetric.site_code == code, SiteMetric.report_date == latest_date)
        .first()
    )

    history = (
        db.query(SiteMetric)
        .filter(SiteMetric.site_code == code)
        .order_by(SiteMetric.report_date)
        .all()
    )

    return SiteDetailResponse(
        site_code=code,
        site_name=current.site_name if current else None,
        current=SiteMetricOut.model_validate(current),
        history=[SiteMetricOut.model_validate(h) for h in history],
    )


@router.get("/sites/{code}/bdrs", response_model=list[BdrMetricOut])
def get_site_bdrs(code: str, db: Session = Depends(get_db)):
    latest_date = (
        db.query(func.max(BdrMetric.report_date))
        .filter(BdrMetric.site_code == code)
        .scalar()
    )
    if latest_date is None:
        return []

    rows = (
        db.query(BdrMetric)
        .filter(BdrMetric.site_code == code, BdrMetric.report_date == latest_date)
        .all()
    )
    return [BdrMetricOut.model_validate(r) for r in rows]


@router.get("/sites/{code}/buckets", response_model=list[BucketMetricOut])
def get_site_buckets(code: str, db: Session = Depends(get_db)):
    latest_date = (
        db.query(func.max(BucketMetric.report_date))
        .filter(BucketMetric.site_code == code)
        .scalar()
    )
    if latest_date is None:
        return []

    rows = (
        db.query(BucketMetric)
        .filter(BucketMetric.site_code == code, BucketMetric.report_date == latest_date)
        .all()
    )
    return [BucketMetricOut.model_validate(r) for r in rows]
