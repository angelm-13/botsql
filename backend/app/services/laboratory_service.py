from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError

from app.models import CustomerSupplier, LaboratoryEquipment, LaboratoryServiceOrder, LaboratoryServiceOrderStatusHistory, LogisticsContact, User
from app.models.session import transaction_context
from app.services.document_service import _actor_id, _actor_project, _actor_type, _is_unrestricted, _safe_int
from app.utils.errors import AppError


ORDER_STATUSES = {
    "received", "awaiting_diagnosis", "diagnosing", "pending_authorization", "authorized",
    "not_authorized", "repairing", "awaiting_parts", "repaired", "not_repairable",
    "ready_for_delivery", "delivered", "cancelled",
}
ORDER_TRANSITIONS = {
    "received": {"awaiting_diagnosis", "diagnosing", "cancelled"},
    "awaiting_diagnosis": {"diagnosing", "cancelled"},
    "diagnosing": {"pending_authorization", "not_repairable", "cancelled"},
    "pending_authorization": {"authorized", "not_authorized", "cancelled"},
    "authorized": {"repairing", "awaiting_parts", "cancelled"},
    "not_authorized": {"authorized", "cancelled"},
    "repairing": {"awaiting_parts", "repaired", "not_repairable", "cancelled"},
    "awaiting_parts": {"repairing", "cancelled"},
    "repaired": {"ready_for_delivery"},
    "not_repairable": {"ready_for_delivery", "cancelled"},
    "ready_for_delivery": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


def _datetime_value(value, field: str):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise AppError("errors.invalid_field", 400, {"field": field})


class LaboratoryService:
    @staticmethod
    def _scope_orders(stmt, user_data: dict):
        if _is_unrestricted(user_data):
            return stmt
        stmt = stmt.where(LaboratoryServiceOrder.id_proyect == _actor_project(user_data))
        actor_type = _actor_type(user_data)
        if actor_type in {"client", "supplier"}:
            stmt = stmt.join(CustomerSupplier, CustomerSupplier.id_customer_supplier == LaboratoryServiceOrder.id_customer_supplier).where(CustomerSupplier.id_user == _actor_id(user_data))
        return stmt

    @staticmethod
    def _scope_equipment(stmt, user_data: dict):
        if _is_unrestricted(user_data):
            return stmt
        stmt = stmt.where(LaboratoryEquipment.id_proyect == _actor_project(user_data))
        if _actor_type(user_data) in {"client", "supplier"}:
            stmt = stmt.join(CustomerSupplier, CustomerSupplier.id_customer_supplier == LaboratoryEquipment.id_customer_supplier).where(CustomerSupplier.id_user == _actor_id(user_data))
        return stmt

    @classmethod
    def _order(cls, db, order_id: int, user_data: dict):
        stmt = select(LaboratoryServiceOrder).where(LaboratoryServiceOrder.id_laboratory_service_order == order_id, LaboratoryServiceOrder.deletion_date.is_(None))
        record = db.scalars(cls._scope_orders(stmt, user_data)).first()
        if not record:
            raise AppError("errors.resource_not_found", 404)
        return record

    @staticmethod
    def _ensure_assigned_technician(record: LaboratoryServiceOrder, user_data: dict):
        if _actor_type(user_data) == "employee" and record.id_technician and record.id_technician != _actor_id(user_data):
            raise AppError("errors.resource_not_found", 404)

    @staticmethod
    def _customer(db, customer_id, project_id):
        customer = db.get(CustomerSupplier, _safe_int(customer_id, "id_customer_supplier"))
        owner = db.get(User, customer.id_user) if customer else None
        if not customer or customer.deletion_date is not None or customer.type != "client" or not owner or owner.id_proyect != project_id:
            raise AppError("errors.invalid_field", 400, {"field": "id_customer_supplier"})
        return customer

    @classmethod
    def list_orders(cls, user_data: dict, page=1, per_page=20, filters=None):
        page, per_page = max(1, int(page)), min(100, max(1, int(per_page)))
        filters = filters or {}
        with transaction_context() as db:
            stmt = cls._scope_orders(select(LaboratoryServiceOrder).where(LaboratoryServiceOrder.deletion_date.is_(None)), user_data)
            if filters.get("status"):
                stmt = stmt.where(LaboratoryServiceOrder.status == filters["status"])
            if filters.get("id_technician"):
                stmt = stmt.where(LaboratoryServiceOrder.id_technician == _safe_int(filters["id_technician"], "id_technician"))
            if filters.get("search"):
                pattern = f"%{str(filters['search']).strip()}%"
                stmt = stmt.where(or_(LaboratoryServiceOrder.folio.ilike(pattern), LaboratoryServiceOrder.reported_failure.ilike(pattern)))
            total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            records = db.scalars(stmt.order_by(LaboratoryServiceOrder.reception_date.desc()).offset((page - 1) * per_page).limit(per_page)).all()
            return {"items": [item.serialize() for item in records], "total": total, "page": page, "per_page": per_page}

    @classmethod
    def get_order(cls, order_id: int, user_data: dict):
        with transaction_context() as db:
            return cls._order(db, order_id, user_data).serialize()

    @classmethod
    def list_equipment(cls, user_data: dict, page=1, per_page=20, search=None):
        page, per_page = max(1, int(page)), min(100, max(1, int(per_page)))
        with transaction_context() as db:
            stmt = cls._scope_equipment(select(LaboratoryEquipment).where(LaboratoryEquipment.deletion_date.is_(None)), user_data)
            if search:
                pattern = f"%{str(search).strip()}%"
                stmt = stmt.where(or_(LaboratoryEquipment.equipment_type.ilike(pattern), LaboratoryEquipment.brand.ilike(pattern), LaboratoryEquipment.model.ilike(pattern), LaboratoryEquipment.serial_number.ilike(pattern)))
            total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            records = db.scalars(stmt.order_by(LaboratoryEquipment.creation_date.desc()).offset((page - 1) * per_page).limit(per_page)).all()
            return {"items": [item.serialize() for item in records], "total": total, "page": page, "per_page": per_page}

    @classmethod
    def create_equipment(cls, user_data: dict, payload: dict):
        actor_id, project_id = _actor_id(user_data), _actor_project(user_data)
        customer_id = _safe_int(payload.get("id_customer_supplier"), "id_customer_supplier")
        equipment_type = str(payload.get("equipment_type") or "").strip()
        serial_number = str(payload.get("serial_number") or "").strip().upper() or None
        if not equipment_type:
            raise AppError("errors.validation_failed", 400, {"fields": ["equipment_type"]})
        try:
            with transaction_context() as db:
                cls._customer(db, customer_id, project_id)
                if serial_number:
                    duplicate = db.scalars(select(LaboratoryEquipment).where(
                        LaboratoryEquipment.id_proyect == project_id,
                        LaboratoryEquipment.id_customer_supplier == customer_id,
                        LaboratoryEquipment.serial_number == serial_number,
                    )).first()
                    if duplicate:
                        raise AppError("errors.duplicate_resource", 409, {"field": "serial_number"})
                record = LaboratoryEquipment(
                    id_proyect=project_id, id_customer_supplier=customer_id,
                    equipment_type=equipment_type, brand=payload.get("brand"), model=payload.get("model"),
                    serial_number=serial_number, created_by=actor_id,
                )
                db.add(record); db.flush()
                return record.serialize()
        except IntegrityError as exc:
            if "uq_laboratory_equipment_owner_serial" in str(exc.orig):
                raise AppError("errors.duplicate_resource", 409, {"field": "serial_number"}) from exc
            raise

    @classmethod
    def create_order(cls, user_data: dict, payload: dict):
        actor_id, project_id = _actor_id(user_data), _actor_project(user_data)
        with transaction_context() as db:
            customer = cls._customer(db, payload.get("id_customer_supplier"), project_id)
            equipment = db.get(LaboratoryEquipment, _safe_int(payload.get("id_laboratory_equipment"), "id_laboratory_equipment"))
            if not equipment or equipment.deletion_date is not None or equipment.id_proyect != project_id or equipment.id_customer_supplier != customer.id_customer_supplier:
                raise AppError("errors.invalid_field", 400, {"field": "id_laboratory_equipment"})
            contact = None
            if payload.get("id_logistics_contact"):
                contact = db.get(LogisticsContact, _safe_int(payload["id_logistics_contact"], "id_logistics_contact"))
                if not contact or contact.deletion_date is not None or contact.id_customer_supplier != customer.id_customer_supplier:
                    raise AppError("errors.invalid_field", 400, {"field": "id_logistics_contact"})
            technician_id = payload.get("id_technician") or None
            if technician_id:
                technician_id = _safe_int(technician_id, "id_technician")
                technician = db.get(User, technician_id)
                if not technician or technician.deletion_date is not None or technician.id_proyect != project_id or not technician.is_employee:
                    raise AppError("errors.invalid_field", 400, {"field": "id_technician"})
            contact_name = str(payload.get("contact_name") or (contact.full_name if contact else customer.contact_name) or "").strip()
            reported_failure = str(payload.get("reported_failure") or "").strip()
            if not contact_name or not reported_failure:
                raise AppError("errors.validation_failed", 400, {"fields": [name for name, value in (("contact_name", contact_name), ("reported_failure", reported_failure)) if not value]})
            for field in ("estimated_budget", "final_cost"):
                if payload.get(field) not in (None, ""):
                    try:
                        if Decimal(str(payload[field])) < 0:
                            raise ValueError
                    except (InvalidOperation, ValueError):
                        raise AppError("errors.invalid_field", 400, {"field": field})
            record = LaboratoryServiceOrder(
                id_proyect=project_id, folio=str(payload.get("folio") or f"PENDING-{actor_id}-{datetime.now().timestamp()}")[:80],
                id_laboratory_equipment=equipment.id_laboratory_equipment, id_customer_supplier=customer.id_customer_supplier,
                id_logistics_contact=contact.id_logistics_contact if contact else None, contact_name=contact_name,
                contact_email=payload.get("contact_email") or (contact.email if contact else customer.email),
                contact_phone=payload.get("contact_phone") or (contact.phone if contact else customer.phone),
                delivered_accessories=payload.get("delivered_accessories"), reception_condition=payload.get("reception_condition"),
                reported_failure=reported_failure, id_technician=technician_id,
                priority=payload.get("priority") or "normal", estimated_budget=payload.get("estimated_budget") or None,
                estimated_delivery_date=_datetime_value(payload.get("estimated_delivery_date"), "estimated_delivery_date"),
                observations=payload.get("observations"), service_conditions=payload.get("service_conditions"), created_by=actor_id,
            )
            db.add(record); db.flush()
            if not payload.get("folio"):
                record.folio = f"LAB-{record.creation_date:%Y%m}-{record.id_laboratory_service_order:06d}"
            db.add(LaboratoryServiceOrderStatusHistory(id_laboratory_service_order=record.id_laboratory_service_order, previous_status=None, new_status="received", comments="Registro inicial", created_by=actor_id))
            db.flush()
            return record.serialize()

    @classmethod
    def update_diagnosis(cls, order_id: int, user_data: dict, payload: dict):
        fields = {"technical_diagnosis", "recommended_repair", "estimated_budget", "estimated_repair_time", "diagnosis_date", "observations"}
        with transaction_context() as db:
            record = cls._order(db, order_id, user_data)
            cls._ensure_assigned_technician(record, user_data)
            for key, value in payload.items():
                if key in fields:
                    setattr(record, key, _datetime_value(value, key) if key == "diagnosis_date" else value or None)
            if not record.diagnosis_date and record.technical_diagnosis:
                record.diagnosis_date = datetime.now(timezone.utc).replace(tzinfo=None)
            db.flush()
            return record.serialize()

    @classmethod
    def transition(cls, order_id: int, user_data: dict, new_status: str, comments=None):
        new_status = str(new_status or "").strip()
        if new_status not in ORDER_STATUSES:
            raise AppError("laboratory.invalid_status", 400, {"status": new_status})
        with transaction_context() as db:
            record = cls._order(db, order_id, user_data)
            cls._ensure_assigned_technician(record, user_data)
            previous = record.status
            if new_status not in ORDER_TRANSITIONS.get(previous, set()):
                raise AppError("laboratory.invalid_transition", 409, {"previous_status": previous, "new_status": new_status})
            if new_status == "pending_authorization" and not record.technical_diagnosis:
                raise AppError("laboratory.diagnosis_required", 409)
            if new_status in {"cancelled", "not_authorized", "not_repairable"} and not str(comments or "").strip():
                raise AppError("laboratory.transition_comments_required", 400)
            record.status = new_status
            if new_status == "delivered":
                record.actual_delivery_date = datetime.now(timezone.utc).replace(tzinfo=None)
            db.add(LaboratoryServiceOrderStatusHistory(id_laboratory_service_order=record.id_laboratory_service_order, previous_status=previous, new_status=new_status, comments=comments, created_by=_actor_id(user_data)))
            db.flush()
            return record.serialize()

    @classmethod
    def history(cls, order_id: int, user_data: dict):
        with transaction_context() as db:
            record = cls._order(db, order_id, user_data)
            items = db.scalars(select(LaboratoryServiceOrderStatusHistory).where(LaboratoryServiceOrderStatusHistory.id_laboratory_service_order == record.id_laboratory_service_order).order_by(LaboratoryServiceOrderStatusHistory.creation_date)).all()
            return [item.serialize() for item in items]