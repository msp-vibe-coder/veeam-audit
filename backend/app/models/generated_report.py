from sqlalchemy import Column, Integer, String, Date, DateTime, func

from app.database import Base


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(500), nullable=False)
    report_type = Column(String(50))
    date_from = Column(Date)
    date_to = Column(Date)
    file_path = Column(String(1000))
    download_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
