from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Index, Integer, DateTime, ForeignKey, func, text
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


class NmTeamUser(Base):
    __tablename__ = 'nm_team_user'
    # Una persona no esta dos veces en el mismo equipo a la vez, pero puede volver a uno del que
    # ya se le dio de baja: cada periodo es su propia fila. Igual que la migracion
    # `20261022100000_unicidad_nm_team_user_solo_vigentes.sql`.
    __table_args__ = (
        Index(
            'uq_nm_team_user_vigente', 'id_team', 'id_user', unique=True,
            postgresql_where=text('deletion_date IS NULL'),
            sqlite_where=text('deletion_date IS NULL'),
        ),
    )

    id_nm_team_user: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_team: Mapped[int] = mapped_column(Integer, ForeignKey('team.id_team'), nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_nm_team_user': to_json_value(self.id_nm_team_user),
            'id_team': to_json_value(self.id_team),
            'id_user': to_json_value(self.id_user),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_nm_team_user': self.id_nm_team_user}
