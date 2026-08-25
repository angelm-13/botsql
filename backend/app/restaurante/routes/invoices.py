"""
Rutas de facturacion CFDI 4.0.

Un restaurante = un solo emisor (Company, singleton) y un solo proveedor de
timbrado configurado a la vez (PacConfig, singleton). Se factura lo que YA
se cobro en caja (Order.status == 'pagado'), nunca una venta pendiente: el
receptor (RFC/razon social/regimen/CP fiscal/uso CFDI) se captura en el
momento de facturar, ya que un comensal de restaurante casi nunca tiene un
perfil de cliente guardado de antes.
"""
import json
import re
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, send_file
from io import BytesIO
from sqlalchemy import text

from app.extensions import db
from app.restaurante.models import Order, Company, PacConfig, Invoice, InvoiceItem, User
from app.restaurante.utils.security import roles_required
from app.restaurante.utils.errors import ApiError
from app.restaurante.utils.audit import log_action
from app.restaurante.utils.rate_limit import rate_limited
from app.restaurante import demo as demo_limits
from app.restaurante.services.invoicing import (
    get_pac_provider, build_draft_from_sale, draft_totals, catalogs_payload,
    PacNotImplementedError,
)
from app.restaurante.services.invoicing.builder import build_draft_nota_credito
from app.restaurante.services.invoicing.catalogs import REGIMEN_FISCAL, USO_CFDI, MOTIVO_CANCELACION
from app.restaurante.services.invoicing.cfdi_xml import parse_timbre
from app.restaurante.services.invoice_pdf import generate_invoice_pdf

invoices_bp = Blueprint('invoices', __name__)

RFC_MIN_LEN, RFC_MAX_LEN = 12, 13  # persona moral (12) o fisica (13)
RFC_PATTERN = re.compile(r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$')

# Namespace fijo para pg_advisory_xact_lock(classid, hashtext(serie)), usado
# al asignar folio (ver _next_folio y sus llamadas): sin esto, dos facturas
# timbradas casi al mismo tiempo pueden leer el mismo "count() + 1" antes de
# que cualquiera de las dos haga commit, y terminar con el mismo serie+folio
# -- dos CFDIs legalmente distintos compartiendo el mismo folio, lo cual
# rompe cualquier conciliacion posterior y es una violacion de cumplimiento
# ante el SAT. El lock se libera solo al terminar la transaccion.
FOLIO_LOCK_NAMESPACE = 447711


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _order_already_invoiced(order_id):
    """True si esta orden ya forma parte de una factura vigente (no
    cancelada). Se revisa en Python (no en SQL) porque order_ids_json es
    texto: el volumen de facturas de un restaurante es bajo, asi que esto
    no es un problema de rendimiento real."""
    for inv in Invoice.query.filter(Invoice.status == 'stamped', Invoice.cancel_status != 'cancelado').all():
        try:
            ids = json.loads(inv.order_ids_json or '[]')
        except (TypeError, ValueError):
            ids = []
        if order_id in ids:
            return True
    return False


def _lock_folio_sequence(serie):
    """Bloquea (para el resto de esta transaccion) la asignacion de folios de
    `serie`, para que _next_folio() + el insert del Invoice queden
    serializados entre dos facturas concurrentes de la misma serie."""
    db.session.execute(text('SELECT pg_advisory_xact_lock(:ns, hashtext(:serie))'), {'ns': FOLIO_LOCK_NAMESPACE, 'serie': serie})


def _next_folio(serie):
    count = Invoice.query.filter(Invoice.status == 'stamped', Invoice.serie == serie).count()
    return count + 1


def _validate_receptor(data):
    errors = []
    rfc = (data.get('rfc') or '').strip().upper()
    if not (RFC_MIN_LEN <= len(rfc) <= RFC_MAX_LEN) or not RFC_PATTERN.match(rfc):
        errors.append('El RFC del receptor no tiene un formato valido.')
    if not (data.get('nombre') or '').strip():
        errors.append('Falta la razon social del receptor.')
    regimen = (data.get('regimen_fiscal') or '').strip()
    if not regimen:
        errors.append('Falta el regimen fiscal del receptor.')
    elif regimen not in REGIMEN_FISCAL:
        errors.append('El regimen fiscal del receptor no es valido.')
    cp = (data.get('cp_fiscal') or '').strip()
    if not cp:
        errors.append('Falta el codigo postal fiscal del receptor.')
    elif not re.match(r'^\d{5}$', cp):
        errors.append('El codigo postal fiscal del receptor debe tener 5 digitos.')
    uso_cfdi = (data.get('uso_cfdi') or 'G03').strip()
    if uso_cfdi not in USO_CFDI:
        errors.append('El uso de CFDI no es valido.')
    return errors


def _load_orders(order_ids):
    if not order_ids or not isinstance(order_ids, list):
        raise ApiError('order_ids es requerido (lista de ids de ordenes pagadas)', 422, 'validation_error')
    orders = Order.query.filter(Order.id.in_(order_ids)).all()
    if len(orders) != len(set(order_ids)):
        raise ApiError('Una o mas ordenes no existen', 404, 'order_not_found')
    for o in orders:
        if o.status != 'pagado':
            raise ApiError(f'La orden #{o.id} todavia no esta pagada', 409, 'order_not_paid')
        if _order_already_invoiced(o.id):
            raise ApiError(f'La orden #{o.id} ya esta facturada', 409, 'already_invoiced')
    return orders


def _validate_before_stamp(company, orders, receptor_data):
    errors = []
    if not company.is_complete():
        errors.append('Faltan datos fiscales del restaurante (RFC, regimen, CP, razon social) -- configuralos en "Mi Negocio".')
    errors += _validate_receptor(receptor_data)
    if not orders:
        errors.append('No hay ordenes para facturar.')
    else:
        # Mismos chequeos que _load_orders(): antes preview_invoice no los
        # corria (solo create_invoice, via _load_orders), asi que una
        # previsualizacion podia salir "ok" para una orden sin pagar o ya
        # facturada, y solo fallar hasta el intento real de timbrar.
        for o in orders:
            if o.status != 'pagado':
                errors.append(f'La orden #{o.id} todavia no esta pagada.')
            elif _order_already_invoiced(o.id):
                errors.append(f'La orden #{o.id} ya esta facturada.')
        if not any(it.status != 'cancelado' for o in orders for it in o.items):
            errors.append('Esta cuenta no tiene platillos por facturar (todos estan cancelados).')
    return errors


# ---------------------------------------------------------------------------
# Catalogos
# ---------------------------------------------------------------------------

@invoices_bp.get('/catalogs')
@roles_required('cajero', 'admin', 'superadmin')
def get_catalogs():
    return jsonify(catalogs_payload())


# ---------------------------------------------------------------------------
# Configuracion: emisor (Company) y proveedor de timbrado (PacConfig)
# ---------------------------------------------------------------------------

@invoices_bp.get('/company')
@roles_required('admin', 'superadmin')
def get_company():
    return jsonify(Company.get_singleton().to_dict())


@invoices_bp.put('/company')
@roles_required('admin', 'superadmin')
def update_company():
    company = Company.get_singleton()
    data = request.get_json() or {}
    if 'rfc' in data:
        rfc = (data.get('rfc') or '').strip().upper()
        if rfc and (not (RFC_MIN_LEN <= len(rfc) <= RFC_MAX_LEN) or not RFC_PATTERN.match(rfc)):
            raise ApiError('El RFC del emisor no tiene un formato valido.', 422, 'validation_error')
    if 'regimen_fiscal' in data:
        regimen = (data.get('regimen_fiscal') or '').strip().upper()
        if regimen and regimen not in REGIMEN_FISCAL:
            raise ApiError('El regimen fiscal del emisor no es valido.', 422, 'validation_error')
    if 'cp' in data:
        cp = (data.get('cp') or '').strip()
        if cp and not re.match(r'^\d{5}$', cp):
            raise ApiError('El codigo postal del emisor debe tener 5 digitos.', 422, 'validation_error')
    for field in ('razon_social', 'rfc', 'regimen_fiscal', 'cp', 'direccion', 'serie'):
        if field in data:
            value = (data.get(field) or '').strip() or None
            setattr(company, field, value.upper() if field in ('rfc', 'regimen_fiscal') and value else value)
    db.session.commit()
    log_action('company.update', 'company', company.id, 'Actualizo los datos fiscales del restaurante (emisor).')
    db.session.commit()
    return jsonify(company.to_dict())


@invoices_bp.get('/pac-config')
@roles_required('admin', 'superadmin')
def get_pac_config():
    return jsonify(PacConfig.get_singleton().to_dict())


@invoices_bp.put('/pac-config')
@roles_required('admin', 'superadmin')
def update_pac_config():
    cfg = PacConfig.get_singleton()
    data = request.get_json() or {}
    if 'provider' in data:
        requested = (data.get('provider') or 'mock').strip()
        # Version freemium: solo se puede timbrar con el proveedor simulado
        # (ver app/demo.py) -- sin efecto si FREEMIUM_LIMITS_ENABLED esta
        # apagado.
        if demo_limits.pac_provider_locked(requested):
            raise ApiError(
                'La version de prueba solo permite el proveedor de timbrado simulado.',
                403, 'demo_pac_locked',
            )
        cfg.provider = requested
    if 'facturama_user' in data:
        cfg.facturama_user = (data.get('facturama_user') or '').strip() or None
    # La contrasena solo se actualiza si mandan una nueva (no vacia); asi
    # guardar el formulario sin tocarla no borra la que ya estaba guardada.
    if data.get('facturama_password'):
        cfg.facturama_password = data['facturama_password']
    db.session.commit()
    log_action('pac_config.update', 'pac_config', cfg.id, f'Cambio el proveedor de timbrado a "{cfg.provider}".')
    db.session.commit()
    return jsonify(cfg.to_dict())


@invoices_bp.post('/pac-config/test')
@roles_required('admin', 'superadmin')
def test_pac_config():
    cfg = PacConfig.get_singleton()
    try:
        provider = get_pac_provider(cfg)
    except PacNotImplementedError as e:
        return jsonify({'ok': False, 'message': str(e)}), 200
    ok, message = provider.test_connection()
    return jsonify({'ok': ok, 'message': message})


# ---------------------------------------------------------------------------
# Timbrar / consultar / cancelar
# ---------------------------------------------------------------------------

@invoices_bp.post('/preview')
@roles_required('cajero', 'admin', 'superadmin')
def preview_invoice():
    """Valida ANTES de timbrar: que falta (datos del emisor, del receptor,
    ordenes ya facturadas, etc.), sin gastar un folio ni llamar al PAC."""
    data = request.get_json() or {}
    company = Company.get_singleton()
    orders = Order.query.filter(Order.id.in_(data.get('order_ids') or [])).all()
    errors = _validate_before_stamp(company, orders, data.get('receptor') or {})
    if errors:
        return jsonify({'ok': False, 'errors': errors}), 200

    draft = build_draft_from_sale(orders, company, data.get('receptor'), company.serie, _next_folio(company.serie))
    totals = draft_totals(draft)
    return jsonify({'ok': True, 'errors': [], **totals})


@invoices_bp.post('')
@roles_required('cajero', 'admin', 'superadmin')
@rate_limited('invoice_create', max_requests=20, window_seconds=60)
def create_invoice():
    """Timbra una factura para una o varias ordenes ya pagadas (juntas, si
    fue un cobro combinado de mesa)."""
    data = request.get_json() or {}
    receptor_data = data.get('receptor') or {}
    company = Company.get_singleton()
    # El lock de folio se toma ANTES de _load_orders() (que es donde vive el
    # chequeo de "esta orden ya esta facturada", via _order_already_invoiced).
    # Antes ese chequeo corria SIN ningun lock: dos requests casi
    # simultaneos (doble clic, o dos cajeros facturando la misma cuenta a la
    # vez) podian leer ambos "no facturada todavia" antes de que cualquiera
    # comiteara, y las dos terminaban timbrando -dos CFDIs legalmente
    # validos y DISTINTOS para la misma venta. Con el lock tomado primero,
    # el segundo request espera a que el primero comitee (o revierta) antes
    # de correr su propia verificacion, y para entonces ya ve la factura
    # recien insertada por el primero.
    serie = company.serie
    _lock_folio_sequence(serie)
    orders = _load_orders(data.get('order_ids'))

    errors = _validate_before_stamp(company, orders, receptor_data)
    if errors:
        raise ApiError('; '.join(errors), 422, 'validation_error')
    # Tope mensual de facturas de la version freemium (ver app/demo.py) --
    # se checa ANTES de llamar al PAC para no gastar esa llamada de balde.
    if demo_limits.invoice_limit_reached():
        raise ApiError(
            f'La version de prueba permite hasta {demo_limits.MAX_INVOICES_PER_MONTH} facturas por mes.',
            403, 'demo_invoice_limit',
        )

    pac_config = PacConfig.get_singleton()
    try:
        provider = get_pac_provider(pac_config)
    except PacNotImplementedError as e:
        raise ApiError(str(e), 501, 'pac_not_implemented') from e

    folio = _next_folio(serie)
    draft = build_draft_from_sale(orders, company, receptor_data, serie, folio)
    result = provider.timbrar(draft)

    if not result.success:
        raise ApiError(result.error or 'No se pudo timbrar la factura', 502, 'stamp_failed')

    totals = draft_totals(draft)
    visit_id = orders[0].visit_id if orders else None
    invoice = Invoice(
        visit_id=visit_id,
        order_ids_json=json.dumps([o.id for o in orders]),
        uuid=result.uuid, serie=result.serie or serie, folio=result.folio or str(folio),
        cfdi_type='I', status='stamped',
        receptor_rfc=receptor_data.get('rfc', '').strip().upper(),
        receptor_nombre=(receptor_data.get('nombre') or '').strip(),
        receptor_regimen_fiscal=(receptor_data.get('regimen_fiscal') or '').strip(),
        receptor_cp_fiscal=(receptor_data.get('cp_fiscal') or '').strip(),
        receptor_email=(receptor_data.get('email') or '').strip() or None,
        uso_cfdi=(receptor_data.get('uso_cfdi') or 'G03').strip(),
        forma_pago=draft.forma_pago, metodo_pago=draft.metodo_pago, moneda=draft.moneda,
        subtotal=totals['subtotal'], iva_amount=totals['iva'], total=totals['total'],
        xml_content=result.xml, pac_provider=result.provider, pac_response=result.raw_response,
        stamped_at=datetime.utcnow(), created_by=_current_username(),
    )
    for c in draft.conceptos:
        invoice.items.append(InvoiceItem(
            description=c.descripcion, quantity=c.cantidad, unit_price=c.valor_unitario,
            subtotal=c.importe, clave_prod_serv=c.clave_prod_serv, clave_unidad=c.clave_unidad,
            iva_rate=c.iva_rate, iva_amount=round(c.importe * c.iva_rate, 2),
        ))
    db.session.add(invoice)
    db.session.commit()
    log_action('invoice.stamp', 'invoice', invoice.id,
               f'Timbro la factura {invoice.serie}{invoice.folio} (UUID {invoice.uuid}) por {invoice.total} a "{invoice.receptor_nombre}" (RFC {invoice.receptor_rfc}).')
    db.session.commit()
    return jsonify(invoice.to_dict()), 201


def _current_username():
    # El JWT solo trae 'role'/'waiter_id' como claims (ver auth.py); el
    # username no viaja en el token, asi que se busca el User igual que ya
    # hace log_action() en utils/audit.py.
    from flask_jwt_extended import get_jwt_identity
    user = User.query.get(int(get_jwt_identity()))
    return user.username if user else None


@invoices_bp.get('')
@roles_required('cajero', 'admin', 'superadmin')
def list_invoices():
    q = Invoice.query
    start = request.args.get('start')
    end = request.args.get('end')
    if start:
        q = q.filter(Invoice.stamped_at >= datetime.strptime(start, '%Y-%m-%d'))
    if end:
        q = q.filter(Invoice.stamped_at < datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1))
    invoices = q.order_by(Invoice.id.desc()).limit(300).all()
    return jsonify({'items': [inv.to_dict() for inv in invoices]})


@invoices_bp.get('/<int:invoice_id>')
@roles_required('cajero', 'admin', 'superadmin')
def get_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return jsonify(invoice.to_dict())


@invoices_bp.get('/<int:invoice_id>/xml')
@roles_required('cajero', 'admin', 'superadmin')
def download_xml(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if not invoice.xml_content:
        raise ApiError('Esta factura no tiene XML guardado', 404, 'xml_not_found')
    buf = BytesIO(invoice.xml_content.encode('utf-8'))
    return send_file(buf, mimetype='application/xml', as_attachment=True,
                      download_name=f'CFDI_{invoice.uuid or invoice.id}.xml')


@invoices_bp.get('/<int:invoice_id>/pdf')
@roles_required('cajero', 'admin', 'superadmin')
def download_pdf(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    company = Company.get_singleton()
    xml_data = parse_timbre(invoice.xml_content) if invoice.xml_content else None
    # El nombre del restaurante para el encabezado del PDF es la razon social
    # fiscal ya configurada (no hay i18n en el backend; las traducciones
    # viven solo en el frontend, y este nombre debe ser el fiscal de todos
    # modos para que el PDF sea consistente con el resto del CFDI).
    restaurant_name = company.razon_social or 'Mi Restaurante'
    pdf_buffer = generate_invoice_pdf(invoice, company, restaurant_name=restaurant_name, tagline='', xml_data=xml_data)
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=False,
                      download_name=f'CFDI_{invoice.uuid or invoice.id}.pdf')


@invoices_bp.post('/<int:invoice_id>/cancel')
@roles_required('cajero', 'admin', 'superadmin')
@rate_limited('invoice_cancel', max_requests=20, window_seconds=60)
def cancel_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    # cancel_status != 'cancelado' NO bastaba: 'en_proceso' (el PAC todavia
    # no confirma la cancelacion) tambien debe bloquear un segundo intento,
    # o el cajero podia disparar dos solicitudes de cancelacion SAT
    # distintas sobre la misma factura mientras la primera seguia pendiente.
    if invoice.status != 'stamped' or invoice.cancel_status in ('cancelado', 'en_proceso'):
        raise ApiError('Esta factura no esta vigente para cancelarse', 409, 'not_cancellable')
    if Invoice.query.filter(Invoice.relacion_uuid == invoice.uuid, Invoice.cancel_status != 'cancelado').first():
        raise ApiError('Esta factura ya tiene una nota de credito vigente; cancelarla dejaria el resumen de ventas descuadrado', 409, 'has_nota_credito')
    data = request.get_json() or {}
    motivo = (data.get('motivo') or '02').strip()
    if motivo not in MOTIVO_CANCELACION:
        raise ApiError('Motivo de cancelacion invalido', 422, 'validation_error')
    folio_sustitucion = (data.get('folio_sustitucion') or '').strip() or None
    if motivo == '01' and not folio_sustitucion:
        raise ApiError('El motivo 01 requiere el UUID del comprobante que sustituye', 422, 'validation_error')
    reason = (data.get('reason') or '').strip()
    if not reason:
        raise ApiError('Escribe un motivo antes de continuar', 400, 'reason_required')

    pac_config = PacConfig.get_singleton()
    try:
        provider = get_pac_provider(pac_config)
    except PacNotImplementedError as e:
        raise ApiError(str(e), 501, 'pac_not_implemented') from e

    ok, estatus, message = provider.cancelar(invoice.uuid, motivo=motivo, folio_sustitucion=folio_sustitucion)
    if not ok:
        raise ApiError(message, 502, 'cancel_failed')

    invoice.cancel_status = estatus or 'en_proceso'
    invoice.cancelled_reason = reason
    if invoice.cancel_status == 'cancelado':
        invoice.cancelled_at = datetime.utcnow()
    db.session.commit()
    log_action('invoice.cancel', 'invoice', invoice.id,
               f'Cancelo la factura {invoice.serie}{invoice.folio} (UUID {invoice.uuid}). Motivo: {reason}')
    db.session.commit()
    return jsonify({'message': message, 'data': invoice.to_dict()})


@invoices_bp.post('/<int:invoice_id>/nota-credito')
@roles_required('cajero', 'admin', 'superadmin')
@rate_limited('invoice_nota_credito', max_requests=20, window_seconds=60)
def create_nota_credito(invoice_id):
    original = Invoice.query.get_or_404(invoice_id)
    if original.status != 'stamped' or original.cancel_status == 'cancelado':
        raise ApiError('Solo se puede emitir nota de credito de una factura timbrada vigente', 400, 'validation_error')
    if original.cfdi_type != 'I':
        raise ApiError('Solo las facturas de Ingreso admiten nota de credito', 400, 'validation_error')
    # Sin este chequeo se podia pedir una nota de credito varias veces para
    # la misma factura: cada llamada timbraba otra nota de egreso completa,
    # y _compute_sales_summary restaba el total de la original una vez por
    # cada nota emitida, dejando las ventas reportadas mal por partida doble.
    if Invoice.query.filter(Invoice.relacion_uuid == original.uuid, Invoice.cancel_status != 'cancelado').first():
        raise ApiError('Esta factura ya tiene una nota de credito vigente', 409, 'nota_credito_exists')
    # Una nota de credito tambien timbra (status='stamped'), asi que cuenta
    # contra el mismo tope mensual que create_invoice() -- ver app/demo.py.
    if demo_limits.invoice_limit_reached():
        raise ApiError(
            f'La version de prueba permite hasta {demo_limits.MAX_INVOICES_PER_MONTH} facturas por mes.',
            403, 'demo_invoice_limit',
        )

    company = Company.get_singleton()
    orders = Order.query.filter(Order.id.in_(json.loads(original.order_ids_json or '[]'))).all()
    receptor_data = {
        'rfc': original.receptor_rfc, 'nombre': original.receptor_nombre,
        'regimen_fiscal': original.receptor_regimen_fiscal, 'cp_fiscal': original.receptor_cp_fiscal,
        'uso_cfdi': original.uso_cfdi,
    }
    base_draft = build_draft_from_sale(orders, company, receptor_data, original.serie, original.folio)
    draft = build_draft_nota_credito(base_draft, original.uuid)

    pac_config = PacConfig.get_singleton()
    try:
        provider = get_pac_provider(pac_config)
    except PacNotImplementedError as e:
        raise ApiError(str(e), 501, 'pac_not_implemented') from e

    # El folio se cuenta dentro de la serie del documento ORIGINAL
    # (original.serie), no la serie actual de la empresa: si el emisor
    # cambio de serie despues de timbrar la factura original, contar contra
    # company.serie mezclaba dos secuencias de folio distintas y podia
    # producir un folio duplicado o sin relacion con la serie real del CFDI.
    _lock_folio_sequence(original.serie)
    folio = _next_folio(original.serie)
    draft.folio = str(folio)
    result = provider.timbrar(draft)
    if not result.success:
        raise ApiError(result.error or 'No se pudo timbrar la nota de credito', 502, 'stamp_failed')

    totals = draft_totals(draft)
    nota = Invoice(
        visit_id=original.visit_id, order_ids_json=original.order_ids_json,
        uuid=result.uuid, serie=result.serie or original.serie, folio=result.folio or str(folio),
        cfdi_type='E', status='stamped', relacion_uuid=original.uuid,
        receptor_rfc=original.receptor_rfc, receptor_nombre=original.receptor_nombre,
        receptor_regimen_fiscal=original.receptor_regimen_fiscal, receptor_cp_fiscal=original.receptor_cp_fiscal,
        receptor_email=original.receptor_email, uso_cfdi=original.uso_cfdi,
        forma_pago=draft.forma_pago, metodo_pago=draft.metodo_pago, moneda=draft.moneda,
        subtotal=totals['subtotal'], iva_amount=totals['iva'], total=totals['total'],
        xml_content=result.xml, pac_provider=result.provider, pac_response=result.raw_response,
        stamped_at=datetime.utcnow(), created_by=_current_username(),
    )
    for c in draft.conceptos:
        nota.items.append(InvoiceItem(
            description=c.descripcion, quantity=c.cantidad, unit_price=c.valor_unitario,
            subtotal=c.importe, clave_prod_serv=c.clave_prod_serv, clave_unidad=c.clave_unidad,
            iva_rate=c.iva_rate, iva_amount=round(c.importe * c.iva_rate, 2),
        ))
    db.session.add(nota)
    db.session.commit()
    log_action('invoice.nota_credito', 'invoice', nota.id,
               f'Emitio nota de credito {nota.serie}{nota.folio} relacionada a {original.serie}{original.folio}.')
    db.session.commit()
    return jsonify(nota.to_dict()), 201


# ---------------------------------------------------------------------------
# Resumen de ventas facturadas (mismo patron que /cashier, pero sobre
# facturas reales en vez de todos los pedidos pagados).
# ---------------------------------------------------------------------------

def _compute_sales_summary(start, end):
    query = Invoice.query.filter(Invoice.status == 'stamped', Invoice.cancel_status != 'cancelado')
    if start:
        query = query.filter(Invoice.stamped_at >= datetime.strptime(start, '%Y-%m-%d'))
    if end:
        query = query.filter(Invoice.stamped_at < datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1))

    invoices = query.order_by(Invoice.stamped_at.asc()).all()
    days = {}
    total_sales = 0.0
    for inv in invoices:
        if not inv.stamped_at:
            continue
        day_key = inv.stamped_at.date().isoformat()
        signed_total = -abs(float(inv.total or 0)) if inv.cfdi_type == 'E' else float(inv.total or 0)
        bucket = days.setdefault(day_key, {'date': day_key, 'sales': 0.0, 'count': 0})
        bucket['sales'] += signed_total
        bucket['count'] += 1
        total_sales += signed_total

    days_list = [{'date': k, 'sales': round(v['sales'], 2), 'count': v['count']} for k, v in sorted(days.items())]
    return {'total_sales': round(total_sales, 2), 'invoice_count': len(invoices), 'days': days_list}


@invoices_bp.get('/sales-summary')
@roles_required('cajero', 'admin', 'superadmin')
def sales_summary():
    try:
        return jsonify(_compute_sales_summary(request.args.get('start'), request.args.get('end')))
    except ValueError:
        raise ApiError('Fecha invalida, usa el formato YYYY-MM-DD', 400, 'validation_error') from None
