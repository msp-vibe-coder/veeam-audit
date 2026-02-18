import re
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Anomaly
from app.schemas.schemas import IssueOut

router = APIRouter()

# Pattern to extract site codes from anomaly descriptions (e.g., "Site ABC-123: ...")
_SITE_CODE_RE = re.compile(r"\b(?:site\s+)?([A-Z]{2,5}[-_][A-Z0-9]+)", re.IGNORECASE)


def _extract_site_code(description: Optional[str]) -> Optional[str]:
    """Try to extract a site code from the anomaly description text."""
    if not description:
        return None
    match = _SITE_CODE_RE.search(description)
    return match.group(1) if match else None


@router.get("/issues", response_model=list[IssueOut])
def list_issues(
    severity: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Anomaly)
    if severity:
        q = q.filter(Anomaly.severity == severity)
    if type:
        q = q.filter(Anomaly.type == type)

    anomalies = q.order_by(Anomaly.report_date.desc(), Anomaly.id.desc()).all()

    issues: list[IssueOut] = []
    for a in anomalies:
        issues.append(
            IssueOut(
                id=a.id,
                report_date=a.report_date,
                site_code=_extract_site_code(a.description),
                severity=a.severity,
                type=a.type,
                description=a.description,
                detected_date=a.report_date,
            )
        )
    return issues
