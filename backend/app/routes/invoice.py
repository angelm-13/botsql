from __future__ import annotations
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file
from app.models import Invoice
from app.services.invoice_service import InvoiceService
from app.services.cfdi_xml import parse_cfdi
from app.services.invoice_artifacts import invoice_xml_path
from app.services.invoice_xml_classification import classify_invoice_direction, normalize_rfc
from app.services.invoice_xml_lines import persist_xml_lines
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
from datetime import datetime
from app.services.invoice_material_service_service import InvoiceMaterialServiceService
from app.services.quotation_service import calculate_totals, validate_transition
from app.services.manual_invoice_service import create_manual_invoice, preview_manual_invoice, validate_manual_invoice_context


bp_invoice = Blueprint('invoice', __name__, url_prefix='/invoice')
ALLOWED_FIELDS = ['id_invoice', 'date_emision', 'date_expiration', 'subtotal', 'tax', 'total', 'invoice_status', 'invoice_direction', 'payment_method', 'note', 'id_customer_supplier', 'fiscal_reference', 'serie_csd', 'internationalization', 'currency', 'type_exchange_rate', 'tax_certification_supplier', 'fiscal_certify_serie', 'certification_date', 'cfdi_code', 'sat_code', 'sat_certification_code', 'id_status', 'created_by', 'creation_date', 'last_update_date', 'deletion_date', 'nombre_emisor', 'lugar_expedicion', 'tipo_de_comprobante', 'rfc_receptor', 'nombre_receptor', 'regimen_fiscal_receptor', 'domicilio_fiscal_receptor', 'id_proveedor_de_sello', 'folio_fiscal', 'exportacion', 'folio', 'no_certificado_sat', 'sello_sat', 'sello_certificacion_sat', 'no_certificado', 'descuento', 'metodo_pago', 'condiciones_pago', 'id_issuer_customer_supplier', 'id_proyect', 'apply_tax', 'tax_rate', 'commercial_terms']

TECHNICAL_RESPONSE_FIELDS = {'id_invoice'}
FIELD_READ_BIT = 2


def _actor_has_unrestricted_field_access(user_data: dict) -> bool:
    return bool(
        user_data.get('is_superuser')
        or user_data.get('is_bootstrap_admin')
        or user_data.get('user_type') == 'admin'
    )


def _safe_int_value(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _visible_response_fields_for_actor(user_data: dict) -> set[str]:
    if _actor_has_unrestricted_field_access(user_data):
        return set(ALLOWED_FIELDS)

    permission_id = _safe_int_value(user_data.get('id_permission') or user_data.get('permission_id'))
    if not permission_id:
        return set(TECHNICAL_RESPONSE_FIELDS)

    from app.models.field import Field
    from app.models.nm_field_permission import NmFieldPermission
    from app.models.session import transaction_context

    visible = set()
    with transaction_context() as db_session:
        rows = (
            db_session.query(NmFieldPermission, Field)
            .join(Field, NmFieldPermission.id_field == Field.id_field)
            .filter(NmFieldPermission.id_permission == permission_id)
            .filter(NmFieldPermission.deletion_date.is_(None))
            .filter(Field.table_name == 'invoice')
            .filter(Field.deletion_date.is_(None))
            .all()
        )
        for permission_row, field_row in rows:
            try:
                control_type = int(permission_row.control_type)
            except (TypeError, ValueError):
                continue
            if (control_type & FIELD_READ_BIT) == FIELD_READ_BIT:
                visible.add(field_row.field_name)

    # La llave primaria puede viajar en la respuesta para navegacion interna,
    # acciones de fila y rutas REST, aunque el frontend no la pinte si no fue
    # marcada como visible en el gestor.
    return visible | set(TECHNICAL_RESPONSE_FIELDS)


def _filter_payload_for_actor(payload: dict, user_data: dict) -> dict:
    payload = dict(payload or {})
    if _actor_has_unrestricted_field_access(user_data):
        return payload
    writable_fields = _visible_response_fields_for_actor(user_data) - set(TECHNICAL_RESPONSE_FIELDS)
    return {key: value for key, value in payload.items() if key in writable_fields}


def _project_record_payload(record: dict | None, visible_fields: set[str]) -> dict | None:
    if record is None:
        return record
    return {key: value for key, value in dict(record).items() if key in visible_fields}


def _project_list_payload(payload: dict, visible_fields: set[str]) -> dict:
    result = dict(payload or {})
    result['items'] = [
        _project_record_payload(item, visible_fields)
        for item in result.get('items', [])
    ]
    return result


def _jsonify_projected_record(user_data: dict, record: dict | None, status: int | None = None):
    payload = _project_record_payload(record, _visible_response_fields_for_actor(user_data))
    response = jsonify(payload)
    return (response, status) if status is not None else response


def _jsonify_projected_list(user_data: dict, payload: dict):
    return jsonify(_project_list_payload(payload, _visible_response_fields_for_actor(user_data)))



@bp_invoice.route('/', methods=['GET'])
@token_required
@require_entity_permission('invoice', 'read')
def list_invoice(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort'} and k in ALLOWED_FIELDS}
    return _jsonify_projected_list(user_data, InvoiceService.list(page=page, per_page=per_page, filters=filters, sort=sort))


@bp_invoice.route('/<id_invoice>', methods=['GET'])
@token_required
@require_entity_permission('invoice', 'read')
def get_invoice(user_data, id_invoice):
    return _jsonify_projected_record(user_data, InvoiceService.get(id_invoice))


@bp_invoice.route('/<id_invoice>/lines', methods=['GET'])
@token_required
@require_entity_permission('invoice', 'read')
def get_invoice_lines(user_data, id_invoice):
    from app.models import InvoiceMaterialService
    from app.models.session import transaction_context

    invoice_id = _safe_int_value(id_invoice)
    with transaction_context() as db:
        if not db.get(Invoice, invoice_id):
            raise AppError('errors.resource_not_found', 404)
        lines = db.query(InvoiceMaterialService).filter(
            InvoiceMaterialService.id_invoice == invoice_id,
            InvoiceMaterialService.deletion_date.is_(None),
        ).order_by(InvoiceMaterialService.id_invoice_material_service).all()
        return jsonify({'items': [line.serialize() for line in lines], 'total': len(lines)})


def _invoice_document_access(id_invoice, user_data):
    from app.models.session import transaction_context

    with transaction_context() as db:
        invoice = db.get(Invoice, _safe_int_value(id_invoice))
        if not invoice:
            raise AppError('errors.resource_not_found', 404)
        unrestricted = bool(user_data.get('is_superuser') or user_data.get('is_bootstrap_admin'))
        actor_project = user_data.get('id_proyect') or user_data.get('project_id')
        if not unrestricted and str(actor_project) != str(invoice.id_proyect):
            raise AppError('errors.resource_not_found', 404)
        return invoice.invoice_status


@bp_invoice.route('/<id_invoice>/xml', methods=['GET'])
@token_required
@require_entity_permission('invoice', 'read')
def download_invoice_xml(user_data, id_invoice):
    _invoice_document_access(id_invoice, user_data)
    path = invoice_xml_path(id_invoice, _current_app.config.get('UPLOAD_ROOT'))
    if not path.is_file():
        raise AppError('invoice.xml_not_available', 404)
    return send_file(path, mimetype='application/xml', as_attachment=True, download_name=f'CFDI-{id_invoice}.xml')


@bp_invoice.route('/<id_invoice>/pdf', methods=['GET'])
@token_required
@require_entity_permission('invoice', 'read')
def download_invoice_pdf(user_data, id_invoice):
    invoice_status = _invoice_document_access(id_invoice, user_data)
    requested_document = str(request.args.get('document') or '').strip().lower()
    document_key = 'quotation_pdf' if requested_document == 'quotation' or (not requested_document and str(invoice_status).lower() == 'cotizacion') else 'invoice_pdf'
    try:
        from app import _documents_templates_dir, _load_quotation_document_record
        from documents.service import DocumentService

        payload = DocumentService(_documents_templates_dir()).render_pdf_bytes(
            document_key,
            _load_quotation_document_record(id_invoice),
            request.args.get('lang', 'es'),
        )
    except Exception as exc:
        raise AppError('invoice.pdf_generation_failed', 500, {'reason': str(exc)}) from exc
    prefix = 'Cotizacion' if document_key == 'quotation_pdf' else 'Factura'
    return send_file(BytesIO(payload), mimetype='application/pdf', as_attachment=True, download_name=f'{prefix}-{id_invoice}.pdf')


@bp_invoice.route('/', methods=['POST'])
@token_required
@require_entity_permission('invoice', 'create')
def create_invoice(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, InvoiceService.create(payload, user_id=user_data.get('id_user')), status=201)


@bp_invoice.route('/manual/preview', methods=['POST'])
@token_required
@require_entity_permission('invoice', 'create')
def preview_manual_invoice_route(user_data):
    payload = request.get_json(silent=True) or {}
    validate_manual_invoice_context(payload, user_data)
    return jsonify(preview_manual_invoice(payload))


@bp_invoice.route('/manual', methods=['POST'])
@token_required
@require_entity_permission('invoice', 'create')
def create_manual_invoice_route(user_data):
    return jsonify(create_manual_invoice(request.get_json(silent=True) or {}, user_data)), 201


@bp_invoice.route('/<id_invoice>', methods=['PUT'])
@token_required
@require_entity_permission('invoice', 'update')
def update_invoice(user_data, id_invoice):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, InvoiceService.update(id_invoice, payload, user_id=user_data.get('id_user')))


@bp_invoice.route('/<id_invoice>/quotation-transition', methods=['PATCH'])
@token_required
@require_entity_permission('invoice', 'update')
def transition_quotation(user_data, id_invoice):
    invoice = InvoiceService.get(id_invoice)
    if not invoice:
        raise AppError('errors.resource_not_found', 404)
    target_status = validate_transition(invoice.get('invoice_status'), (request.get_json(silent=True) or {}).get('status'))
    updated = InvoiceService.update(
        id_invoice,
        {'invoice_status': target_status},
        user_id=user_data.get('id_user'),
    )
    return jsonify({'id_invoice': updated.get('id_invoice'), 'invoice_status': updated.get('invoice_status')})


@bp_invoice.route('/<id_invoice>', methods=['DELETE'])
@token_required
@require_entity_permission('invoice', 'delete')
def delete_invoice(user_data, id_invoice):
    return jsonify(InvoiceService.delete(id_invoice, user_id=user_data.get('id_user')))


@bp_invoice.route('/line-authorization/<id_invoice_material_service>', methods=['PATCH'])
@token_required
@require_entity_permission('invoice', 'update')
def update_invoice_line_authorization(user_data, id_invoice_material_service):
    data = request.get_json(silent=True) or {}
    authorization_status = str(data.get('authorization_status') or '').strip().lower()
    allowed_statuses = {'pending', 'authorized', 'rejected'}

    if authorization_status not in allowed_statuses:
        raise AppError(
            'validations.invoice_material_service.authorization_status.invalid',
            400,
            {'allowed': sorted(allowed_statuses)}
        )

    payload = {
        'authorization_status': authorization_status,
        'authorization_note': data.get('authorization_note') or None,
        'id_authorized': user_data.get('id_user') or 1,
    }

    if authorization_status in {'authorized', 'rejected'}:
        payload['authorization_date'] = datetime.utcnow()
    else:
        payload['authorization_date'] = None

    updated = InvoiceMaterialServiceService.update(
        id_invoice_material_service,
        payload,
        user_id=user_data.get('id_user')
    )

    return jsonify({
        'id_invoice_material_service': updated.get('id_invoice_material_service'),
        'id_invoice': updated.get('id_invoice'),
        'authorization_status': updated.get('authorization_status'),
        'authorization_note': updated.get('authorization_note'),
        'authorization_date': updated.get('authorization_date'),
        'id_authorized': updated.get('id_authorized'),
    })

@bp_invoice.route('/convert-quotation/<id_invoice>', methods=['PATCH'])
@token_required
@require_entity_permission('invoice', 'update')
def convert_quotation_invoice(user_data, id_invoice):
    data = request.get_json(silent=True) or {}
    invoice = InvoiceService.get(id_invoice)
    if not invoice:
        raise AppError('errors.resource_not_found', 404)

    current_status = str(invoice.get('invoice_status') or '').strip()
    if current_status.lower() != 'cotizacion':
        raise AppError(
            'validations.invoice.quotation_conversion.invalid_status',
            400,
            {'current_status': current_status, 'required_status': 'Cotizacion'}
        )

    try:
        invoice_id_value = int(id_invoice)
    except (TypeError, ValueError):
        raise AppError('validations.invoice.quotation_conversion.invalid_invoice_id', 400, {'id_invoice': id_invoice})

    from app.models import InvoiceMaterialService
    from app.models.session import transaction_context

    with transaction_context() as db_session:
        line_rows = (
            db_session.query(InvoiceMaterialService)
            .filter(InvoiceMaterialService.id_invoice == invoice_id_value)
            .order_by(InvoiceMaterialService.id_invoice_material_service.asc())
            .all()
        )

    lines = [
        row.serialize() if hasattr(row, 'serialize') else {
            column.name: getattr(row, column.name)
            for column in row.__table__.columns
        }
        for row in line_rows
    ]
    authorized_lines = [
        line for line in lines
        if str(line.get('authorization_status') or '').strip().lower() == 'authorized'
    ]

    if not authorized_lines:
        raise AppError(
            'validations.invoice.quotation_conversion.no_authorized_lines',
            400,
            {'id_invoice': id_invoice}
        )

    totals = calculate_totals(authorized_lines, invoice.get('tax_rate') if invoice.get('apply_tax') else 0)
    conversion_note = str(
        data.get('conversion_note')
        or 'Convertida desde cotizacion usando solo partidas autorizadas.'
    ).strip()
    existing_note = str(invoice.get('note') or '').strip()
    note = (existing_note + '\n' + conversion_note).strip() if existing_note else conversion_note

    payload = {
        'invoice_status': 'pendiente',
        'subtotal': str(totals['subtotal']),
        'tax': str(totals['tax']),
        'total': str(totals['total']),
        'note': note,
    }

    updated = InvoiceService.update(id_invoice, payload, user_id=user_data.get('id_user'))

    return jsonify({
        'id_invoice': updated.get('id_invoice'),
        'previous_status': current_status,
        'invoice_status': updated.get('invoice_status'),
        'authorized_lines_count': len(authorized_lines),
        'excluded_lines_count': len(lines) - len(authorized_lines),
        'subtotal': updated.get('subtotal'),
        'tax': updated.get('tax'),
        'total': updated.get('total'),
        'purchase_requirement_grouped_url': f'/documents/purchase_requirement_grouped/{id_invoice}?format=pdf',
        'message_key': 'success.invoice.quotation_converted',
    })


import os as _os
from flask import current_app as _current_app
from werkzeug.utils import secure_filename as _secure_filename

from sqlalchemy import select as _select
from app.models.session import transaction_context as _transaction_context
try:
    from app.models import CustomerSupplier as _CustomerSupplier
except Exception:  # modelos opcionales segun CSV
    _CustomerSupplier = None


def _int_or_none(value):
    try:
        if value in (None, ''):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _principal_company():
    if _CustomerSupplier is None:
        return None
    with _transaction_context() as db:
        item = db.scalars(
            _select(_CustomerSupplier).where(
                _CustomerSupplier.is_principal.is_(True),
                _CustomerSupplier.deletion_date.is_(None),
            )
        ).first()
        return item.serialize() if item else None


def _resolve_cfdi_party(db, tax_id, name, partner_type, actor_id):
    normalized_tax_id = normalize_rfc(tax_id)
    candidates = db.scalars(
        _select(_CustomerSupplier).where(_CustomerSupplier.deletion_date.is_(None))
    ).all()
    existing = next(
        (item for item in candidates if normalize_rfc(item.tax_id) == normalized_tax_id),
        None,
    ) if normalized_tax_id else None
    if existing:
        return existing
    item = _CustomerSupplier(
        name=str(name or normalized_tax_id or 'Empresa CFDI')[:150],
        title=str(name or 'CFDI')[:50],
        contact_name=str(name or 'CFDI')[:150],
        tax_id=str(normalized_tax_id or 'XAXX010101000')[:50],
        type=partner_type,
        id_user=actor_id,
        created_by=actor_id,
    )
    db.add(item)
    db.flush()
    return item


def _resolve_cfdi_parties(cfdi_data, principal, direction, user_id=None):
    actor_id = _int_or_none(user_id) or 1
    principal_id = principal['id_customer_supplier']
    with _transaction_context() as db:
        issuer = None
        if direction == 'venta':
            issuer = db.get(_CustomerSupplier, principal_id)
            counterparty = _resolve_cfdi_party(
                db, cfdi_data.get('rfc_receptor'), cfdi_data.get('nombre_receptor'), 'client', actor_id
            )
        else:
            issuer = _resolve_cfdi_party(
                db, cfdi_data.get('rfc_emisor'), cfdi_data.get('nombre_emisor'), 'supplier', actor_id
            )
            counterparty = issuer
        return {
            'id_customer_supplier': counterparty.id_customer_supplier,
            'id_issuer_customer_supplier': issuer.id_customer_supplier,
        }



# issue_12_phase7_save_original_cfdi_xml
def _cfdi_xml_storage_path(invoice_id):
    upload_root = _current_app.config.get('UPLOAD_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..', 'uploads'))
    folder = _os.path.join(upload_root, 'cfdi_xml')
    _os.makedirs(folder, exist_ok=True)
    return _os.path.join(folder, 'invoice_' + str(invoice_id) + '.xml')


def _save_original_cfdi_xml(invoice_id, xml_bytes):
    if not invoice_id or not xml_bytes:
        return None
    path = _cfdi_xml_storage_path(invoice_id)
    with open(path, 'wb') as handle:
        handle.write(xml_bytes)
    return path

@bp_invoice.route('/upload-xml', methods=['POST'])
@token_required
@require_entity_permission('invoice', 'create')
def upload_xml_invoice(user_data):
    files = request.files.getlist('files')
    if not files and 'file' in request.files:
        files = [request.files['file']]
    if not files:
        return jsonify({'error_key': 'errors.no_files_provided', 'message': 'No se recibieron archivos XML'}), 400

    id_proyect = request.form.get('id_proyect') or request.form.get('proyect_id')
    user_id = user_data.get('id_user')
    principal = _principal_company()
    if not principal or not normalize_rfc(principal.get('tax_id')):
        return jsonify({
            'error_key': 'invoice.principal_company_required',
            'message': 'Define una empresa principal con RFC en Empresas antes de cargar facturas XML.',
        }), 409
    results = []

    for uploaded_file in files:
        filename = _secure_filename(uploaded_file.filename or 'unknown.xml')
        if not filename.lower().endswith('.xml'):
            results.append({'file': filename, 'status': 'error', 'message': 'El archivo debe ser XML'})
            continue
        try:
            xml_bytes = uploaded_file.read()
            cfdi_data = parse_cfdi(xml_bytes)
            direction = classify_invoice_direction(
                principal.get('tax_id'),
                cfdi_data.get('rfc_emisor'),
                cfdi_data.get('rfc_receptor'),
            )
            with _transaction_context() as db:
                duplicate = db.scalars(
                    _select(Invoice).where(Invoice.folio_fiscal == cfdi_data['uuid'])
                ).first()
            if duplicate:
                raise ValueError('El CFDI ya fue importado')
            parties = _resolve_cfdi_parties(cfdi_data, principal, direction, user_id=user_id)
            payload = {}
            payload['folio_fiscal'] = cfdi_data.get('uuid')
            payload['cfdi_code'] = cfdi_data.get('uuid')
            payload['nombre_emisor'] = cfdi_data.get('nombre_emisor')
            payload['rfc_receptor'] = cfdi_data.get('rfc_receptor')
            payload['nombre_receptor'] = cfdi_data.get('nombre_receptor')
            payload['subtotal'] = cfdi_data.get('subtotal')
            payload['tax'] = cfdi_data.get('tax')
            payload['total'] = cfdi_data.get('total')
            payload['currency'] = cfdi_data.get('currency', 'MXN')
            payload['tipo_de_comprobante'] = cfdi_data.get('tipo_de_comprobante')
            payload['payment_method'] = cfdi_data.get('payment_method')
            payload['metodo_pago'] = cfdi_data.get('metodo_pago')
            payload['lugar_expedicion'] = cfdi_data.get('lugar_expedicion')
            payload['exportacion'] = cfdi_data.get('exportacion')
            payload['folio'] = cfdi_data.get('folio')
            payload['no_certificado'] = cfdi_data.get('no_certificado')
            payload['condiciones_pago'] = cfdi_data.get('condiciones_pago')
            payload['date_emision'] = cfdi_data.get('fecha')
            payload['date_expiration'] = cfdi_data.get('fecha')
            payload['apply_tax'] = True
            payload['tax_rate'] = request.form.get('tax_rate') or 16
            payload['no_certificado_sat'] = cfdi_data.get('no_certificado_sat')
            payload['sello_sat'] = cfdi_data.get('sello_sat')
            payload['certification_date'] = cfdi_data.get('certification_date')
            payload['sat_certification_code'] = cfdi_data.get('uuid')
            payload['tax_certification_supplier'] = request.form.get('tax_certification_supplier') or 1
            payload['invoice_status'] = request.form.get('invoice_status') or 'pendiente'
            payload['invoice_direction'] = direction
            payload['note'] = f'Cargado desde XML: {filename}. Clasificación: {direction}.'
            if id_proyect:
                payload['id_proyect'] = int(id_proyect)
            payload.update(parties)
            payload.setdefault('id_status', request.form.get('id_status') or 1)
            payload = {k: v for k, v in payload.items() if v not in (None, '')}
            invoice = InvoiceService.create(payload, user_id=user_id)
            invoice_id = invoice.get('id_invoice')
            lines = persist_xml_lines(invoice, cfdi_data.get('conceptos', []), user_id=user_id)
            xml_path = _save_original_cfdi_xml(invoice_id, xml_bytes)
            results.append({'file': filename, 'status': 'created', 'id_invoice': invoice_id, 'invoice_direction': direction, 'items_count': len(lines), 'xml_saved': bool(xml_path), 'data': invoice})
        except ValueError as exc:
            results.append({'file': filename, 'status': 'error', 'message': str(exc)})
        except AppError as exc:
            results.append({'file': filename, 'status': 'error', 'message': exc.message_key, 'meta': exc.meta})
        except Exception as exc:
            results.append({'file': filename, 'status': 'error', 'message': str(exc)})
    created = [r for r in results if r['status'] == 'created']
    errors = [r for r in results if r['status'] == 'error']
    response = {'created': len(created), 'errors': len(errors), 'results': results}
    if errors:
        response['message'] = '; '.join([f"{r.get('file')}: {r.get('message')} {r.get('meta', '')}" for r in errors])
    return jsonify(response), (201 if created else 422)
