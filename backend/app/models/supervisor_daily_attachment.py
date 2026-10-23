from __future__ import annotations
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.models.base import Base


class SupervisorDailyAttachment(Base):
    __tablename__ = "supervisor_daily_attachment"

    id_supervisor_daily_attachment = Column(Integer, primary_key=True)
    id_supervisor_activity_log = Column(
        Integer,
        ForeignKey("supervisor_activity_log.id_supervisor_activity_log"),
        nullable=False,
    )
    attachment_date = Column(String, nullable=False)
    file_path = Column(String(400), nullable=False)
    original_filename = Column(String(255), nullable=False)
    extension = Column(String(10), nullable=False)
    mime_type = Column(String(120), nullable=False)
    file_size = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    description = Column(Text)
    created_by = Column(Integer, nullable=False, default=1)
    creation_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_update_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    deletion_date = Column(DateTime)
