from sqlalchemy import Column, Integer, String, Date, Numeric, DateTime, UniqueConstraint, func

from app.database import Base


class BucketMetric(Base):
    __tablename__ = "bucket_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Date, nullable=False)
    bucket_name = Column(String(200), nullable=False)
    site_code = Column(String(50))
    active_tb = Column(Numeric(12, 4))
    deleted_tb = Column(Numeric(12, 4))
    active_cost = Column(Numeric(12, 2))
    deleted_cost = Column(Numeric(12, 2))
    total_cost = Column(Numeric(12, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("report_date", "bucket_name", name="uq_bucket_metrics_date_bucket"),
    )
