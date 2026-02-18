from sqlalchemy import Column, Date, Numeric, Integer, DateTime, func

from app.database import Base


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    report_date = Column(Date, primary_key=True)
    veeam_tb = Column(Numeric(12, 4))
    wasabi_active_tb = Column(Numeric(12, 4))
    wasabi_deleted_tb = Column(Numeric(12, 4))
    discrepancy_pct = Column(Numeric(8, 2))
    total_cost = Column(Numeric(12, 2))
    low_disk_count = Column(Integer, default=0)
    high_discrepancy_count = Column(Integer, default=0)
    high_deleted_count = Column(Integer, default=0)
    failed_job_count = Column(Integer, default=0)
    warning_job_count = Column(Integer, default=0)
    total_jobs = Column(Integer, default=0)
    successful_jobs = Column(Integer, default=0)
    failed_jobs = Column(Integer, default=0)
    warning_jobs = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
