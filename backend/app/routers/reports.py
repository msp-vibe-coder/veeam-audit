import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.models import GeneratedReport
from app.schemas.schemas import ReportGenerateRequest, GeneratedReportOut
from app.services.report_generator import generate_report

router = APIRouter()


@router.post("/reports/generate", response_model=GeneratedReportOut)
def generate_new_report(
    body: ReportGenerateRequest,
    db: Session = Depends(get_db),
):
    reports_dir = os.path.abspath(app_settings.reports_dir)
    os.makedirs(reports_dir, exist_ok=True)

    filename, file_path = generate_report(
        db=db,
        date_from=body.date_from,
        date_to=body.date_to,
        reports_dir=reports_dir,
    )

    report = GeneratedReport(
        filename=filename,
        report_type="audit",
        date_from=body.date_from,
        date_to=body.date_to,
        file_path=file_path,
        download_count=0,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return GeneratedReportOut.model_validate(report)


@router.get("/reports", response_model=list[GeneratedReportOut])
def list_reports(db: Session = Depends(get_db)):
    rows = db.query(GeneratedReport).order_by(desc(GeneratedReport.created_at)).all()
    return [GeneratedReportOut.model_validate(r) for r in rows]


@router.get("/reports/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    file_path = report.file_path
    if not file_path or not Path(file_path).is_file():
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    # Increment download count
    report.download_count = (report.download_count or 0) + 1
    db.commit()

    return FileResponse(
        path=file_path,
        filename=report.filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
