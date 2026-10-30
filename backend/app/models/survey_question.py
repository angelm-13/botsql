from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func
from app.models.base import Base
from app.utils.tiempo import a_iso_utc


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class SurveyQuestion(Base):
    __tablename__ = 'survey_question'

    id_survey_question: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    question: Mapped[object] = mapped_column(String(300), nullable=False)
    question_type: Mapped[object] = mapped_column(Enum('multiple_option', 'single_option', 'boolean', 'score', 'short_text', 'long_text', name='survey_question_question_type_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=False)
    owner: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_survey_question': to_json_value(self.id_survey_question),
            'question': to_json_value(self.question),
            'question_type': to_json_value(self.question_type),
            'owner': to_json_value(self.owner),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_survey_question': self.id_survey_question}
