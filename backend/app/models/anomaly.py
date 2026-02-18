from sqlalchemy import Column, Integer, String, Date, Numeric, Text, DateTime, func

from app.database import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Date, nullable=False)
    severity = Column(String(20), nullable=False)
    type = Column(String(100), nullable=False)
    metric = Column(String(100))
    previous_value = Column(Numeric(12, 4))
    current_value = Column(Numeric(12, 4))
    change_pct = Column(Numeric(8, 2))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
