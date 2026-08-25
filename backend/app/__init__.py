from __future__ import annotations
import os
import sys
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_babel import Babel
from werkzeug.exceptions import HTTPException
from app.utils.errors import AppError
from app.routes.health import bp_health
from app.routes.auth import bp_auth
from app.routes.security import bp_security
from app.routes.sales_catalog import bp_sales_catalog
from app.routes.sales_catalog_api_keys import bp_sales_catalog_api_keys
from app.routes.public_catalog import bp_public_catalog
from app.routes.public_auth import bp_public_auth
from app.routes.web_shoppers import bp_web_shoppers
from app.routes.user import bp_user
from app.routes.user_mfa import bp_user_mfa
from app.routes.payroll_period import bp_payroll_period
from app.routes.payroll_detail import bp_payroll_detail
from app.routes.payroll_concept import bp_payroll_concept
from app.routes.payroll_movement import bp_payroll_movement
from app.routes.customer_supplier import bp_customer_supplier
from app.routes.proyect import bp_proyect
from app.routes.bank import bp_bank
from app.routes.bank_account import bp_bank_account
from app.routes.invoice import bp_invoice
from app.routes.invoice_material_service import bp_invoice_material_service
from app.routes.product_family import bp_product_family
from app.routes.incident_type import bp_incident_type
from app.routes.incident import bp_incident
from app.routes.incident_detail import bp_incident_detail
from app.routes.brand import bp_brand
from app.routes.unit import bp_unit
from app.routes.material import bp_material
from app.routes.material_component import bp_material_component
from app.routes.movement import bp_movement
from app.routes.location_type import bp_location_type
from app.routes.location import bp_location
from app.routes.product import bp_product
from app.routes.nm_incident_product import bp_nm_incident_product
from app.routes.task import bp_task
from app.routes.task_note import bp_task_note
from app.routes.ticket import bp_ticket
from app.routes.fiscal_account import bp_fiscal_account
from app.routes.fiscal_stamp import bp_fiscal_stamp
from app.routes.fiscal_record import bp_fiscal_record
from app.routes.service import bp_service
from app.routes.status import bp_status
from app.routes.theme import bp_theme
from app.routes.department import bp_department
from app.routes.subdepartment import bp_subdepartment
from app.routes.level import bp_level
from app.routes.field import bp_field
from app.routes.permission import bp_permission
from app.routes.nm_field_permission import bp_nm_field_permission
from app.routes.event_log import bp_event_log
from app.routes.task_type import bp_task_type
from app.routes.template import bp_template
from app.routes.nm_template_task import bp_nm_template_task
from app.routes.survey_question import bp_survey_question
from app.routes.survey_multiple_answer import bp_survey_multiple_answer
from app.routes.nm_survey_user import bp_nm_survey_user
from app.routes.entity_permission import bp_entity_permission
from app.routes.inventory_status import bp_inventory_status
from app.routes.product_sale_config import bp_product_sale_config
from app.routes.public_api_key import bp_public_api_key
from app.routes.stamping import bp_stamping
from app.routes.client_portal import bp_client_portal
from app.routes.bank_statements import bp_bank_statements
from app.restaurante import blueprints_restaurante

def _documents_reports_app_path() -> str:
    return os.getenv('DOCUMENTS_REPORTS_APP_PATH', '/documents-reports/app')


def _documents_templates_dir() -> str:
    return os.getenv('DOCUMENTS_TEMPLATES_DIR', '/documents-reports/templates')


def _pascal_from_snake(value: str) -> str:
    return ''.join(part.capitalize() for part in str(value or '').split('_') if part)


def _doc_to_dict(record) -> dict:
    if not record:
        return {}
    if hasattr(record, 'to_dict'):
        return record.to_dict()
    from sqlalchemy import inspect as sqlalchemy_inspect
    return {column.key: getattr(record, column.key) for column in sqlalchemy_inspect(record.__class__).columns}


def _doc_money(value, currency='MXN') -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0
    return f"${amount:,.2f}"


def _doc_date(value) -> str:
    if not value:
        return '—'
    raw = str(value)
    raw = raw[:10] if 'T' in raw else raw[:10]
    parts = raw.split('-')
    if len(parts) == 3:
        return parts[2] + '/' + parts[1] + '/' + parts[0]
    return str(value)


def _doc_join(parts) -> str:
    values = [str(part or '').strip() for part in parts if str(part or '').strip()]
    return ', '.join(values) if values else '—'


def _doc_logo_uri(path_value) -> str:
    raw = str(path_value or '').strip()
    if not raw:
        return ''
    if raw.startswith(('http://', 'https://', 'data:')):
        return raw
    normalized = raw.replace('\\', '/').lstrip('/')
    candidates = []
    if os.path.isabs(raw):
        candidates.append(raw)
    if normalized.startswith('uploads/'):
        candidates.append('/' + normalized)
    upload_root = os.getenv('UPLOAD_ROOT', '/uploads').rstrip('/') or '/uploads'
    if normalized.startswith('uploads/'):
        candidates.append(os.path.join(os.path.dirname(upload_root), normalized))
    else:
        candidates.append(os.path.join(upload_root, normalized))
    candidates.append(os.path.join(os.getcwd(), normalized))
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return 'file://' + os.path.abspath(candidate)
    return ''


def _doc_customer_context(customer) -> dict:
    data = _doc_to_dict(customer)
    if not data:
        return {
            'display_name': '—',
            'address_line': '—',
            'contact_line': '—',
            'email': '—',
            'phone': '—',
            'web_site': '—',
            'tax_id': '—',
            'fiscal_type': '—',
            'logo_uri': '',
        }

    street = _doc_join([
        data.get('street'),
        ('No. ' + str(data.get('number_ext'))) if data.get('number_ext') else '',
        ('Int. ' + str(data.get('number_int'))) if data.get('number_int') else '',
    ])
    city = _doc_join([data.get('neighborhood'), data.get('city'), data.get('geographic_state')])
    postal_code = str(data.get('postal_code') or '').strip()
    address = _doc_join([street if street != '—' else '', city if city != '—' else '', ('CP ' + postal_code) if postal_code else ''])
    contact = _doc_join([data.get('contact_name'), data.get('phone'), data.get('email')])

    data.update({
        'display_name': data.get('name') or data.get('title') or data.get('tax_id') or '—',
        'address_line': address,
        'contact_line': contact,
        'email': data.get('email') or '—',
        'phone': data.get('phone') or '—',
        'web_site': data.get('web_site') or '—',
        'tax_id': data.get('tax_id') or '—',
        'fiscal_type': data.get('fiscal_type') or '—',
        'logo_uri': _doc_logo_uri(data.get('path_logo') or data.get('logo_path') or data.get('logo')),
    })
    return data


def _doc_first_by_id(db_session, model_cls, pk_name: str, value):
    if value in (None, ''):
        return None
    try:
        lookup = int(value)
    except (TypeError, ValueError):
        lookup = value
    return db_session.query(model_cls).filter(getattr(model_cls, pk_name) == lookup).first()


# issue_12_phase7_cfdi_original_xml_path
def _cfdi_xml_original_path(invoice_id) -> str | None:
    if not invoice_id:
        return None
    try:
        upload_root = os.getenv('UPLOAD_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'uploads'))
        candidate = os.path.join(upload_root, 'cfdi_xml', 'invoice_' + str(invoice_id) + '.xml')
        return candidate if os.path.exists(candidate) else None
    except Exception:
        return None


def _load_quotation_document_record(record_id: str) -> dict:
    from app.models.invoice import Invoice
    from app.models.invoice_material_service import InvoiceMaterialService
    from app.models.customer_supplier import CustomerSupplier
    from app.models.proyect import Proyect
    from app.models.product import Product
    from app.models.service import Service
    from app.models.unit import Unit
    from app.models.session import transaction_context

    try:
        invoice_id = int(record_id)
    except (TypeError, ValueError):
        invoice_id = record_id

    with transaction_context() as db_session:
        invoice = db_session.query(Invoice).filter(Invoice.id_invoice == invoice_id).first()
        if invoice is None:
            return {}

        data = _doc_to_dict(invoice)
        currency = data.get('currency') or 'MXN'
        invoice_id_value = data.get('id_invoice') or record_id
        data['folio'] = data.get('folio') or ('COT-' + str(invoice_id_value).zfill(6))
        data['status_label'] = data.get('invoice_status') or 'Cotizacion'
        data['date_emision_label'] = _doc_date(data.get('date_emision'))
        data['date_expiration_label'] = _doc_date(data.get('date_expiration'))
        data['subtotal_label'] = _doc_money(data.get('subtotal'), currency)
        data['tax_label'] = _doc_money(data.get('tax'), currency)
        data['total_label'] = _doc_money(data.get('total'), currency)
        # issue_12_phase7_cfdi_original_xml_path
        data['_xml_original_path'] = _cfdi_xml_original_path(invoice_id_value)

        issuer = _doc_first_by_id(db_session, CustomerSupplier, 'id_customer_supplier', data.get('id_issuer_customer_supplier'))
        receiver = _doc_first_by_id(db_session, CustomerSupplier, 'id_customer_supplier', data.get('id_customer_supplier'))
        fiscal_supplier = _doc_first_by_id(db_session, CustomerSupplier, 'id_customer_supplier', data.get('tax_certification_supplier'))
        project = _doc_first_by_id(db_session, Proyect, 'id_proyect', data.get('id_proyect'))

        data['issuer'] = _doc_customer_context(issuer)
        data['receiver'] = _doc_customer_context(receiver)
        data['fiscal_supplier'] = _doc_customer_context(fiscal_supplier)
        project_data = _doc_to_dict(project)
        data['project'] = project_data
        data['project_label'] = project_data.get('title') or project_data.get('proyect_description') or 'Sin proyecto'

        rows = (
            db_session.query(InvoiceMaterialService)
            .filter(InvoiceMaterialService.id_invoice == invoice_id_value)
            .order_by(InvoiceMaterialService.id_invoice_material_service)
            .all()
        )

        items = []
        authorized_items = []
        authorized_subtotal_value = 0
        authorized_tax_value = 0
        # issue_12_phase5_grouped_authorized_requirements
        for row in rows:
            item = _doc_to_dict(row)
            line_type = item.get('line_type') or 'custom'
            product = _doc_first_by_id(db_session, Product, 'id_product', item.get('id_product')) if item.get('id_product') else None
            service = _doc_first_by_id(db_session, Service, 'id_service', item.get('id_service')) if item.get('id_service') else None
            unit = _doc_first_by_id(db_session, Unit, 'id_unit', item.get('id_unit')) if item.get('id_unit') else None
            product_data = _doc_to_dict(product)
            service_data = _doc_to_dict(service)
            unit_data = _doc_to_dict(unit)

            reference = 'Concepto personalizado'
            if line_type == 'product':
                reference = product_data.get('product_code') or product_data.get('descripcion') or str(item.get('id_product') or '—')
            elif line_type == 'service':
                reference = service_data.get('service_description') or str(item.get('id_service') or '—')

            try:
                quantity = float(item.get('quantity') or 0)
            except (TypeError, ValueError):
                quantity = 0
            try:
                price = float(item.get('gross_price') or 0)
            except (TypeError, ValueError):
                price = 0
            subtotal = item.get('line_total')
            if subtotal in (None, ''):
                subtotal = quantity * price
            try:
                subtotal_value = float(subtotal or 0)
            except (TypeError, ValueError):
                subtotal_value = 0
            try:
                tax_value = float(item.get('line_tax') or 0)
            except (TypeError, ValueError):
                tax_value = 0

            item.update({
                'line_number': len(items) + 1,
                'type_label': {
                    'product': 'Producto existente',
                    'service': 'Servicio existente',
                    'custom': 'Concepto personalizado',
                }.get(line_type, line_type),
                'reference_label': reference,
                'description_label': item.get('invoice_material_service_description') or product_data.get('descripcion') or service_data.get('service_description') or '—',
                'quantity_label': ('%g' % quantity) if quantity else '0',
                'unit_label': unit_data.get('symbol') or unit_data.get('unit_code') or unit_data.get('unit_name') or '—',
                'gross_price_label': _doc_money(price, currency),
                'line_tax_label': _doc_money(tax_value, currency),
                'line_subtotal_label': _doc_money(subtotal_value, currency),
                'line_total_label': _doc_money(subtotal_value + tax_value, currency),
            })
            if str(item.get('authorization_status') or '').strip().lower() == 'authorized':
                authorized_items.append(item)
                authorized_subtotal_value += subtotal_value
                authorized_tax_value += tax_value
            items.append(item)

        data['line_items'] = items
        data['authorized_line_items'] = authorized_items
        data['has_authorized_items'] = bool(authorized_items)
        data['authorized_count_label'] = str(len(authorized_items)) + ' partida(s) autorizada(s)'
        data['authorized_subtotal_label'] = _doc_money(authorized_subtotal_value, currency)
        data['authorized_tax_label'] = _doc_money(authorized_tax_value, currency)
        data['authorized_total_label'] = _doc_money(authorized_subtotal_value + authorized_tax_value, currency)
        data['grouped_requirement_folio'] = 'OC-' + str(invoice_id_value).zfill(6)
        data['has_items'] = bool(items)
        return data


# issue_12_phase4_purchase_requirement_loader
def _doc_auth_status_label(value) -> str:
    status = str(value or '').strip().lower()
    return {
        'pending': 'Pendiente',
        'authorized': 'Autorizada',
        'rejected': 'No autorizada',
    }.get(status, status or 'Pendiente')


def _load_purchase_requirement_document_record(record_id: str) -> dict:
    from app.models.invoice import Invoice
    from app.models.invoice_material_service import InvoiceMaterialService
    from app.models.customer_supplier import CustomerSupplier
    from app.models.proyect import Proyect
    from app.models.product import Product
    from app.models.service import Service
    from app.models.unit import Unit
    from app.models.user import User
    from app.models.session import transaction_context

    try:
        line_id = int(record_id)
    except (TypeError, ValueError):
        line_id = record_id

    with transaction_context() as db_session:
        line = db_session.query(InvoiceMaterialService).filter(
            InvoiceMaterialService.id_invoice_material_service == line_id
        ).first()
        if line is None:
            return {}

        line_data = _doc_to_dict(line)
        invoice = _doc_first_by_id(db_session, Invoice, 'id_invoice', line_data.get('id_invoice'))
        invoice_data = _doc_to_dict(invoice)
        currency = invoice_data.get('currency') or 'MXN'

        issuer = _doc_first_by_id(db_session, CustomerSupplier, 'id_customer_supplier', invoice_data.get('id_issuer_customer_supplier'))
        receiver = _doc_first_by_id(db_session, CustomerSupplier, 'id_customer_supplier', invoice_data.get('id_customer_supplier') or line_data.get('id_customer_supplier'))
        project = _doc_first_by_id(db_session, Proyect, 'id_proyect', invoice_data.get('id_proyect'))

        product = _doc_first_by_id(db_session, Product, 'id_product', line_data.get('id_product')) if line_data.get('id_product') else None
        service = _doc_first_by_id(db_session, Service, 'id_service', line_data.get('id_service')) if line_data.get('id_service') else None
        unit = _doc_first_by_id(db_session, Unit, 'id_unit', line_data.get('id_unit')) if line_data.get('id_unit') else None
        authorized_user = _doc_first_by_id(db_session, User, 'id_user', line_data.get('id_authorized')) if line_data.get('id_authorized') else None

        product_data = _doc_to_dict(product)
        service_data = _doc_to_dict(service)
        unit_data = _doc_to_dict(unit)
        project_data = _doc_to_dict(project)
        authorized_user_data = _doc_to_dict(authorized_user)

        line_type = line_data.get('line_type') or 'custom'
        reference = 'Concepto personalizado'
        if line_type == 'product':
            reference = product_data.get('product_code') or product_data.get('descripcion') or str(line_data.get('id_product') or '—')
        elif line_type == 'service':
            reference = service_data.get('service_description') or str(line_data.get('id_service') or '—')

        try:
            quantity = float(line_data.get('quantity') or 0)
        except (TypeError, ValueError):
            quantity = 0
        try:
            price = float(line_data.get('gross_price') or 0)
        except (TypeError, ValueError):
            price = 0
        subtotal = line_data.get('line_total')
        if subtotal in (None, ''):
            subtotal = quantity * price
        try:
            subtotal_value = float(subtotal or 0)
        except (TypeError, ValueError):
            subtotal_value = 0
        try:
            tax_value = float(line_data.get('line_tax') or 0)
        except (TypeError, ValueError):
            tax_value = 0

        authorization_status = line_data.get('authorization_status') or 'pending'
        invoice_id_value = invoice_data.get('id_invoice') or line_data.get('id_invoice')
        invoice_folio = invoice_data.get('folio') or ('COT-' + str(invoice_id_value).zfill(6) if invoice_id_value else '—')

        requester = (
            authorized_user_data.get('username')
            or authorized_user_data.get('full_name')
            or authorized_user_data.get('email')
            or str(line_data.get('id_authorized') or '—')
        )

        result = dict(line_data)
        result.update({
            'requirement_folio': 'REQ-' + str(line_data.get('id_invoice_material_service') or record_id).zfill(6),
            'document_title': 'Requerimiento / Orden de compra',
            'authorization_status_label': _doc_auth_status_label(authorization_status),
            'authorization_date_label': _doc_date(line_data.get('authorization_date')),
            'authorization_note_label': line_data.get('authorization_note') or '—',
            'authorized_by_label': requester,
            'invoice': invoice_data,
            'invoice_folio': invoice_folio,
            'invoice_status_label': invoice_data.get('invoice_status') or '—',
            'invoice_date_label': _doc_date(invoice_data.get('date_emision')),
            'invoice_expiration_label': _doc_date(invoice_data.get('date_expiration')),
            'invoice_currency': currency,
            'invoice_terms': invoice_data.get('commercial_terms') or invoice_data.get('condiciones_pago') or '—',
            'issuer': _doc_customer_context(issuer),
            'receiver': _doc_customer_context(receiver),
            'project': project_data,
            'project_label': project_data.get('title') or project_data.get('proyect_description') or 'Sin proyecto',
            'project_description_label': project_data.get('proyect_description') or '—',
            'line_type_label': {
                'product': 'Producto existente',
                'service': 'Servicio existente',
                'custom': 'Concepto personalizado',
            }.get(line_type, line_type),
            'line_reference_label': reference,
            'line_description_label': line_data.get('invoice_material_service_description') or product_data.get('descripcion') or service_data.get('service_description') or '—',
            'quantity_label': ('%g' % quantity) if quantity else '0',
            'unit_label': unit_data.get('symbol') or unit_data.get('unit_code') or unit_data.get('unit_name') or '—',
            'gross_price_label': _doc_money(price, currency),
            'line_subtotal_label': _doc_money(subtotal_value, currency),
            'line_tax_label': _doc_money(tax_value, currency),
            'line_total_label': _doc_money(subtotal_value + tax_value, currency),
            'generated_requirement_note': 'Documento generado desde una partida autorizada de cotizacion/factura.',
        })
        return result


def _load_document_record(entity: str, record_id: str) -> dict:
    from importlib import import_module
    from sqlalchemy import inspect as sqlalchemy_inspect
    from app.models.session import transaction_context

    entity_key = str(entity or '').strip()
    if not entity_key:
        raise ValueError('Missing document entity')

    if entity_key == 'invoice':
        return _load_quotation_document_record(record_id)
    if entity_key == 'invoice_material_service':
        return _load_purchase_requirement_document_record(record_id)

    module = import_module(f'app.models.{entity_key}')
    model_cls = getattr(module, _pascal_from_snake(entity_key))
    mapper = sqlalchemy_inspect(model_cls)
    pk_columns = list(mapper.primary_key)
    if not pk_columns:
        raise ValueError(f'Missing primary key for document entity {entity_key}')

    pk_attr = pk_columns[0].key
    try:
        lookup_value = int(record_id)
    except (TypeError, ValueError):
        lookup_value = record_id

    with transaction_context() as db_session:
        record = (
            db_session.query(model_cls)
            .filter(getattr(model_cls, pk_attr) == lookup_value)
            .first()
        )
        if record is None:
            return {}
        if hasattr(record, 'to_dict'):
            return record.to_dict()
        return {column.key: getattr(record, column.key) for column in mapper.columns}


def _register_documents_blueprint(app: Flask) -> None:
    documents_app_path = _documents_reports_app_path()
    documents_routes = os.path.join(documents_app_path, 'documents', 'routes.py')
    documents_templates = _documents_templates_dir()

    if not os.path.exists(documents_routes):
        app.logger.info('Documents blueprint not registered: %s not found', documents_routes)
        return

    if documents_app_path not in sys.path:
        sys.path.insert(0, documents_app_path)

    try:
        from documents.routes import create_documents_blueprint
        app.register_blueprint(
            create_documents_blueprint(
                templates_dir=documents_templates,
                record_loader=_load_document_record,
            )
        )
    except Exception as exc:
        app.logger.exception('Documents blueprint registration failed: %s', exc)



def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config['TESTING'] = testing
    app.config['BABEL_DEFAULT_LOCALE'] = os.getenv('DEFAULT_LOCALE', 'es')
    app.config['JSON_SORT_KEYS'] = False
    default_upload_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'uploads'))
    app.config['UPLOAD_ROOT'] = os.getenv('UPLOAD_ROOT', default_upload_root)
    CORS(app)
    Babel(app)
    app.register_blueprint(bp_health)
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_security)
    app.register_blueprint(bp_sales_catalog)
    app.register_blueprint(bp_sales_catalog_api_keys)
    app.register_blueprint(bp_public_catalog)
    app.register_blueprint(bp_public_auth)
    app.register_blueprint(bp_web_shoppers)
    app.register_blueprint(bp_user)
    app.register_blueprint(bp_user_mfa)
    app.register_blueprint(bp_payroll_period)
    app.register_blueprint(bp_payroll_detail)
    app.register_blueprint(bp_payroll_concept)
    app.register_blueprint(bp_payroll_movement)
    app.register_blueprint(bp_customer_supplier)
    app.register_blueprint(bp_proyect)
    app.register_blueprint(bp_bank)
    app.register_blueprint(bp_bank_account)
    app.register_blueprint(bp_invoice)
    app.register_blueprint(bp_invoice_material_service)
    app.register_blueprint(bp_product_family)
    app.register_blueprint(bp_incident_type)
    app.register_blueprint(bp_incident)
    app.register_blueprint(bp_incident_detail)
    app.register_blueprint(bp_brand)
    app.register_blueprint(bp_unit)
    app.register_blueprint(bp_material)
    app.register_blueprint(bp_material_component)
    app.register_blueprint(bp_movement)
    app.register_blueprint(bp_location_type)
    app.register_blueprint(bp_location)
    app.register_blueprint(bp_product)
    app.register_blueprint(bp_nm_incident_product)
    app.register_blueprint(bp_task)
    app.register_blueprint(bp_task_note)
    app.register_blueprint(bp_ticket)
    app.register_blueprint(bp_fiscal_account)
    app.register_blueprint(bp_fiscal_stamp)
    app.register_blueprint(bp_fiscal_record)
    app.register_blueprint(bp_service)
    app.register_blueprint(bp_status)
    app.register_blueprint(bp_theme)
    app.register_blueprint(bp_department)
    app.register_blueprint(bp_subdepartment)
    app.register_blueprint(bp_level)
    app.register_blueprint(bp_field)
    app.register_blueprint(bp_permission)
    app.register_blueprint(bp_nm_field_permission)
    app.register_blueprint(bp_event_log)
    app.register_blueprint(bp_task_type)
    app.register_blueprint(bp_template)
    app.register_blueprint(bp_nm_template_task)
    app.register_blueprint(bp_survey_question)
    app.register_blueprint(bp_survey_multiple_answer)
    app.register_blueprint(bp_nm_survey_user)
    app.register_blueprint(bp_entity_permission)
    app.register_blueprint(bp_inventory_status)
    app.register_blueprint(bp_product_sale_config)
    app.register_blueprint(bp_public_api_key)
    app.register_blueprint(bp_stamping)
    app.register_blueprint(bp_client_portal)
    app.register_blueprint(bp_bank_statements)

    for blueprint, url_prefix in blueprints_restaurante:
        app.register_blueprint(blueprint, url_prefix=url_prefix)

    _register_documents_blueprint(app)

    @app.route('/uploads/products/<path:filename>')
    def uploaded_product_image(filename):
        return send_from_directory(os.path.join(app.config['UPLOAD_ROOT'], 'products'), filename)

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return jsonify({'error_key': error.message_key, 'meta': error.meta}), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        return jsonify({
            'error_key': f'errors.http_{error.code}',
            'meta': {'description': error.description},
        }), error.code

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        app.logger.exception(error)
        return jsonify({'error_key': 'errors.internal_server_error'}), 500

    return app
