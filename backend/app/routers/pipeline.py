from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PipelineRun
from app.schemas.schemas import PipelineStatusOut

router = APIRouter()


@router.get("/pipeline/status", response_model=PipelineStatusOut)
def get_pipeline_status(db: Session = Depends(get_db)):
    run = db.query(PipelineRun).order_by(desc(PipelineRun.id)).first()
    if not run:
        return PipelineStatusOut(status="no_runs")
    return PipelineStatusOut.model_validate(run)
