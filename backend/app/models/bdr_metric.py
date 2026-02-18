from sqlalchemy import Column, Integer, String, Date, Numeric, DateTime, UniqueConstraint, func

from app.database import Base


class BdrMetric(Base):
    __tablename__ = "bdr_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Date, nullable=False)
    bdr_server = Column(String(200), nullable=False)
    site_code = Column(String(50))
    backup_size_tb = Column(Numeric(12, 4))
    disk_free_tb = Column(Numeric(12, 4))
    disk_free_pct = Column(Numeric(5, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("report_date", "bdr_server", name="uq_bdr_metrics_date_server"),
    )
