from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _value(value):
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    return value


class CalendarProfile(Base):
    __tablename__ = "calendar_profile"
    __table_args__ = (UniqueConstraint("calendar_code", name="uq_calendar_profile_code"),)

    id_calendar_profile: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False)
    calendar_code: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: _value(getattr(self, column.name)) for column in self.__table__.columns}


class AppointmentType(Base):
    __tablename__ = "appointment_type"

    id_appointment_type: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_calendar_profile: Mapped[int] = mapped_column(Integer, ForeignKey("calendar_profile.id_calendar_profile"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    buffer_before_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    buffer_after_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minimum_notice_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    booking_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    meeting_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: _value(getattr(self, column.name)) for column in self.__table__.columns}


class AvailabilityRule(Base):
    __tablename__ = "availability_rule"

    id_availability_rule: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_calendar_profile: Mapped[int] = mapped_column(Integer, ForeignKey("calendar_profile.id_calendar_profile"), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: _value(getattr(self, column.name)) for column in self.__table__.columns}


class AvailabilityOverride(Base):
    __tablename__ = "availability_override"

    id_availability_override: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_calendar_profile: Mapped[int] = mapped_column(Integer, ForeignKey("calendar_profile.id_calendar_profile"), nullable=False)
    override_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: _value(getattr(self, column.name)) for column in self.__table__.columns}


class Appointment(Base):
    __tablename__ = "appointment"
    __table_args__ = (UniqueConstraint("management_token_hash", name="uq_appointment_management_token"),)

    id_appointment: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_calendar_profile: Mapped[int] = mapped_column(Integer, ForeignKey("calendar_profile.id_calendar_profile"), nullable=False)
    id_appointment_type: Mapped[int] = mapped_column(Integer, ForeignKey("appointment_type.id_appointment_type"), nullable=False)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False)
    guest_name: Mapped[str] = mapped_column(String(150), nullable=False)
    guest_email: Mapped[str] = mapped_column(String(254), nullable=False)
    guest_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    blocked_starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    blocked_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    guest_timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="confirmed")
    meeting_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    meeting_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    external_status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_required")
    management_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    cancellation_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmation_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self, *, include_private: bool = False) -> dict:
        hidden = {"management_token_hash"}
        if not include_private:
            hidden.update({"guest_email", "guest_notes"})
        return {
            column.name: _value(getattr(self, column.name))
            for column in self.__table__.columns
            if column.name not in hidden
        }