import subprocess
import sys
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import PipelineRun
from app.schemas.schemas import PipelineStatusOut

router = APIRouter()


@router.get("/pipeline/status", response_model=PipelineStatusOut)
def get_pipeline_status(db: Session = Depends(get_db)):
    run = db.query(PipelineRun).order_by(desc(PipelineRun.id)).first()
    if not run:
        return PipelineStatusOut(status="no_runs")
    return PipelineStatusOut.model_validate(run)


@router.post("/pipeline/run")
def run_pipeline(db: Session = Depends(get_db)):
    # Check for an active run
    active = db.query(PipelineRun).filter(PipelineRun.status == "running").first()
    if active:
        raise HTTPException(status_code=409, detail="Pipeline is already running")

    # Create run record
    run = PipelineRun(started_at=datetime.now(timezone.utc), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    run_id = run.id

    def execute(run_id: int):
        try:
            result = subprocess.run(
                [sys.executable, "/app/scripts/pipeline.py", "--verbose"],
                capture_output=True,
                text=True,
                timeout=1800,
                cwd="/app",
            )
            status = "completed" if result.returncode == 0 else "failed"
            log_text = result.stdout
            if result.stderr:
                log_text += "\n--- STDERR ---\n" + result.stderr
        except subprocess.TimeoutExpired:
            status = "failed"
            log_text = "Pipeline timed out after 30 minutes"
        except Exception as e:
            status = "failed"
            log_text = f"Error running pipeline: {e}"

        # Update the run record using a fresh session
        session = SessionLocal()
        try:
            run_record = session.query(PipelineRun).get(run_id)
            if run_record:
                run_record.status = status
                run_record.completed_at = datetime.now(timezone.utc)
                run_record.log_text = log_text[:50000] if log_text else None
                session.commit()
        finally:
            session.close()

    thread = threading.Thread(target=execute, args=(run_id,), daemon=True)
    thread.start()

    return {"status": "started", "id": run_id}
