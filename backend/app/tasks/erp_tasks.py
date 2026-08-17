from __future__ import annotations
from app.celery_app import celery

ENTITIES = ['user', 'user_mfa', 'payroll_period', 'payroll_detail', 'payroll_concept', 'payroll_movement', 'customer_supplier', 'proyect', 'bank', 'bank_account', 'invoice', 'invoice_material_service', 'product_family', 'incident_type', 'incident', 'incident_detail', 'brand', 'unit', 'material', 'material_component', 'movement', 'location_type', 'location', 'product', 'nm_incident_product', 'task', 'task_note', 'ticket', 'fiscal_account', 'fiscal_stamp', 'fiscal_record', 'service', 'status', 'theme', 'department', 'subdepartment', 'level', 'field', 'permission', 'nm_field_permission', 'event_log', 'task_type', 'template', 'nm_template_task', 'survey_question', 'survey_multiple_answer', 'nm_survey_user', 'entity_permission', 'inventory_status', 'product_sale_config', 'public_api_key']


@celery.task(name='erp.recalculate_kpis')
def recalculate_kpis() -> dict:
    # Punto de extensión: leer calculated.csv y recalcular indicadores por entidad.
    return {'message_key': 'jobs.kpis_recalculated', 'entities': ENTITIES}


@celery.task(name='erp.generate_pending_documents')
def generate_pending_documents() -> dict:
    # Punto de extensión: usar documents.csv y document-bindings.csv.
    return {'message_key': 'jobs.documents_generated'}


@celery.task(name='erp.sync_scm_stock')
def sync_scm_stock() -> dict:
    # Punto de extensión: movimientos, materiales, productos, ubicaciones.
    return {'message_key': 'jobs.scm_stock_synced'}
