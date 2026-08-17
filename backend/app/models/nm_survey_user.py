from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class NmSurveyUser(Base):
    __tablename__ = 'nm_survey_user'

    id_nm_survey_user: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_survey_question: Mapped[int] = mapped_column(Integer, ForeignKey('survey_question.id_survey_question'), nullable=False)
    id_survey_multiple_answer: Mapped[int] = mapped_column(Integer, ForeignKey('survey_multiple_answer.id_survey_multiple_answer'), nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    nm_survey_user_description: Mapped[object] = mapped_column(String(300), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[int] = mapped_column(Integer, ForeignKey('status.id_status'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_nm_survey_user': to_json_value(self.id_nm_survey_user),
            'id_survey_question': to_json_value(self.id_survey_question),
            'id_survey_multiple_answer': to_json_value(self.id_survey_multiple_answer),
            'id_user': to_json_value(self.id_user),
            'nm_survey_user_description': to_json_value(self.nm_survey_user_description),
            'score': to_json_value(self.score),
            'status': to_json_value(self.status),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_nm_survey_user': self.id_nm_survey_user}
