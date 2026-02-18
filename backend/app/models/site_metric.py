from sqlalchemy import Column, Integer, String, Date, Numeric, DateTime, UniqueConstraint, func

from app.database import Base


class SiteMetric(Base):
    __tablename__ = "site_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Date, nullable=False)
    site_code = Column(String(50), nullable=False)
    site_name = Column(String(200))
    veeam_tb = Column(Numeric(12, 4))
    wasabi_active_tb = Column(Numeric(12, 4))
    wasabi_deleted_tb = Column(Numeric(12, 4))
    discrepancy_pct = Column(Numeric(8, 2))
    success_rate_pct = Column(Numeric(5, 2))
    total_jobs = Column(Integer, default=0)
    increment_jobs = Column(Integer, default=0)
    reverse_increment_jobs = Column(Integer, default=0)
    gold_jobs = Column(Integer, default=0)
    silver_jobs = Column(Integer, default=0)
    bronze_jobs = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("report_date", "site_code", name="uq_site_metrics_date_code"),
    )
