from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSONB, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
