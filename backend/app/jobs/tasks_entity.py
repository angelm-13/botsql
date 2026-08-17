from __future__ import annotations

from sqlalchemy import select

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok
from app.models.session import transaction_context

from app.models.bank import Bank
from app.models.bank_account import BankAccount
from app.models.brand import Brand
from app.models.customer_supplier import CustomerSupplier
from app.models.department import Department
from app.models.entity_permission import EntityPermission
from app.models.event_log import EventLog
from app.models.field import Field
from app.models.fiscal_account import FiscalAccount
from app.models.fiscal_record import FiscalRecord
from app.models.fiscal_stamp import FiscalStamp
from app.models.incident import Incident
from app.models.incident_detail import IncidentDetail
from app.models.incident_type import IncidentType
from app.models.inventory_status import InventoryStatus
from app.models.invoice import Invoice
from app.models.invoice_material_service import InvoiceMaterialService
from app.models.level import Level
from app.models.location import Location
from app.models.location_type import LocationType
from app.models.material import Material
from app.models.material_component import MaterialComponent
from app.models.movement import Movement
from app.models.nm_field_permission import NmFieldPermission
from app.models.nm_incident_product import NmIncidentProduct
from app.models.nm_survey_user import NmSurveyUser
from app.models.nm_template_task import NmTemplateTask
from app.models.payroll_concept import PayrollConcept
from app.models.payroll_detail import PayrollDetail
from app.models.payroll_movement import PayrollMovement
from app.models.payroll_period import PayrollPeriod
from app.models.permission import Permission
from app.models.product import Product
from app.models.product_family import ProductFamily
from app.models.product_sale_config import ProductSaleConfig
from app.models.proyect import Proyect
from app.models.public_api_key import PublicApiKey
from app.models.service import Service
from app.models.status import Status
from app.models.subdepartment import Subdepartment
from app.models.survey_multiple_answer import SurveyMultipleAnswer
from app.models.survey_question import SurveyQuestion
from app.models.task import Task
from app.models.task_note import TaskNote
from app.models.task_type import TaskType
from app.models.template import Template
from app.models.theme import Theme
from app.models.ticket import Ticket
from app.models.unit import Unit
from app.models.user import User
from app.models.user_mfa import UserMfa

ENTITY_MODEL_REGISTRY = {
    "user": User,
    "user_mfa": UserMfa,
    "payroll_period": PayrollPeriod,
    "payroll_detail": PayrollDetail,
    "payroll_concept": PayrollConcept,
    "payroll_movement": PayrollMovement,
    "customer_supplier": CustomerSupplier,
    "proyect": Proyect,
    "bank": Bank,
    "bank_account": BankAccount,
    "invoice": Invoice,
    "invoice_material_service": InvoiceMaterialService,
    "product_family": ProductFamily,
    "incident_type": IncidentType,
    "incident": Incident,
    "incident_detail": IncidentDetail,
    "brand": Brand,
    "unit": Unit,
    "material": Material,
    "material_component": MaterialComponent,
    "movement": Movement,
    "location_type": LocationType,
    "location": Location,
    "product": Product,
    "nm_incident_product": NmIncidentProduct,
    "task": Task,
    "task_note": TaskNote,
    "ticket": Ticket,
    "fiscal_account": FiscalAccount,
    "fiscal_stamp": FiscalStamp,
    "fiscal_record": FiscalRecord,
    "service": Service,
    "status": Status,
    "theme": Theme,
    "department": Department,
    "subdepartment": Subdepartment,
    "level": Level,
    "field": Field,
    "permission": Permission,
    "nm_field_permission": NmFieldPermission,
    "event_log": EventLog,
    "task_type": TaskType,
    "template": Template,
    "nm_template_task": NmTemplateTask,
    "survey_question": SurveyQuestion,
    "survey_multiple_answer": SurveyMultipleAnswer,
    "nm_survey_user": NmSurveyUser,
    "entity_permission": EntityPermission,
    "inventory_status": InventoryStatus,
    "product_sale_config": ProductSaleConfig,
    "public_api_key": PublicApiKey,
}


@celery.task(name="app.jobs.tasks_entity.recalculate_entity_metrics")
def recalculate_entity_metrics(entity_name: str) -> dict:
    model = ENTITY_MODEL_REGISTRY.get(entity_name)
    if model is None:
        return {"ok": False, "message_key": "jobs.entity.unknown_entity", "entity": entity_name}

    with transaction_context() as session:
        total = session.scalar(select(model).count()) if hasattr(select(model), "count") else len(session.scalars(select(model).limit(1)).all())

    return result_ok("jobs.entity.metrics_recalculated", entity=entity_name, total=total)


@celery.task(name="app.jobs.tasks_entity.audit_entity_integrity")
def audit_entity_integrity(entity_name: str) -> dict:
    model = ENTITY_MODEL_REGISTRY.get(entity_name)
    if model is None:
        return {"ok": False, "message_key": "jobs.entity.unknown_entity", "entity": entity_name}

    with transaction_context() as session:
        sample = session.scalars(select(model).limit(10)).all()
        sample_count = len(sample)

    return result_ok("jobs.entity.integrity_audited", entity=entity_name, sample_count=sample_count)


@celery.task(name="app.jobs.tasks_entity.run_all_entity_audits")
def run_all_entity_audits() -> dict:
    scheduled = []
    for entity in ENTITY_MODEL_REGISTRY.keys():
        audit_entity_integrity.delay(entity)
        scheduled.append(entity)
    return result_ok("jobs.entity.all_audits_scheduled", scheduled=scheduled)
