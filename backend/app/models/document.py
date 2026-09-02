from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


class DocumentCategory(Base):
    __tablename__ = "document_category"

    id_document_category: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: _json_value(getattr(self, column.name)) for column in self.__table__.columns}

    def serialize_summary(self) -> dict:
        return {"id_document_category": self.id_document_category, "code": self.code, "name": self.name}


class Document(Base):
    __tablename__ = "document"

    id_document: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_document_category: Mapped[int] = mapped_column(Integer, ForeignKey("document_category.id_document_category"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_reference_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    business_reference_value: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft")
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: _json_value(getattr(self, column.name)) for column in self.__table__.columns}

    def serialize_summary(self) -> dict:
        return {"id_document": self.id_document, "title": self.title, "status": self.status}


class DocumentVersion(Base):
    __tablename__ = "document_version"
    __table_args__ = (UniqueConstraint("id_document", "version", name="uq_document_version_number"),)

    id_document_version: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_document: Mapped[int] = mapped_column(Integer, ForeignKey("document.id_document"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(10), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded", server_default="uploaded")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft")
    # JSONB en Postgres, que es lo que declara la migracion, pero JSON liso en
    # SQLite: la suite corre con TESTING=1 sobre SQLite y crea el esquema desde
    # los modelos, y su compilador no conoce JSONB. Con `JSONB` a secas fallaba
    # el `create_all` completo, asi que reventaban 638 pruebas de todo el
    # proyecto -no solo las de este modulo- con
    # "'SQLiteTypeCompiler' object has no attribute 'visit_JSONB'".
    source_snapshot: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    id_parent_document_version: Mapped[int | None] = mapped_column(Integer, ForeignKey("document_version.id_document_version"), nullable=True)
    generated_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    generation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: _json_value(getattr(self, column.name)) for column in self.__table__.columns}

    def serialize_summary(self) -> dict:
        return {"id_document_version": self.id_document_version, "id_document": self.id_document, "version": self.version}


class DocumentRelation(Base):
    __tablename__ = "document_relation"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN id_customer_supplier IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN id_employee IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN id_laboratory_equipment IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN id_laboratory_service_order IS NULL THEN 0 ELSE 1 END) = 1",
            name="ck_document_relation_single_target",
        ),
    )

    id_document_relation: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_document: Mapped[int] = mapped_column(Integer, ForeignKey("document.id_document"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    id_customer_supplier: Mapped[int | None] = mapped_column(Integer, ForeignKey("customer_supplier.id_customer_supplier"), nullable=True, index=True)
    id_employee: Mapped[int | None] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=True, index=True)
    id_laboratory_equipment: Mapped[int | None] = mapped_column(Integer, ForeignKey("laboratory_equipment.id_laboratory_equipment"), nullable=True, index=True)
    id_laboratory_service_order: Mapped[int | None] = mapped_column(Integer, ForeignKey("laboratory_service_order.id_laboratory_service_order"), nullable=True, index=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: _json_value(getattr(self, column.name)) for column in self.__table__.columns}

    def serialize_summary(self) -> dict:
        return {"id_document_relation": self.id_document_relation, "id_document": self.id_document}