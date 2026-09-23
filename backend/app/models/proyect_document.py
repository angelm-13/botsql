from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def to_json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class ProyectDocument(Base):
    __tablename__ = 'proyect_document'

    id_proyect_document: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey('proyect.id_proyect'), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    file_path: Mapped[str] = mapped_column(String(400), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(10), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize_summary(self) -> dict:
        # Sin file_path: la ruta en disco no debe salir en la respuesta.
        return {
            'id_proyect_document': self.id_proyect_document,
            'id_proyect': self.id_proyect,
            'title': self.title,
            'original_filename': self.original_filename,
            'extension': self.extension,
            'mime_type': self.mime_type,
            'file_size': self.file_size,
            'created_by': self.created_by,
            'creation_date': to_json_value(self.creation_date),
        }
