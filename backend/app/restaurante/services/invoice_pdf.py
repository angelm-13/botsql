"""
Representacion impresa (PDF) de un CFDI emitido por el restaurante.

Incluye los elementos que el SAT exige en la representacion impresa de un
CFDI 4.0: codigo QR de verificacion, sellos del emisor y del SAT, cadena
original del complemento de certificacion, numeros de certificado, fecha de
timbrado y la leyenda de representacion impresa. El PAC simulado (mock)
produce un TFD con la forma correcta pero SIN validez, para poder
desarrollar/probar este PDF sin credenciales reales.
"""
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

from .invoicing.cfdi_xml import cadena_original_tfd, qr_content
from .invoicing.catalogs import FORMA_PAGO, METODO_PAGO, USO_CFDI, REGIMEN_FISCAL

# Misma paleta que theme.css (rediseno estilo POS de este mismo proyecto):
# azul primario + verde secundario + azul marino oscuro, para que el PDF se
# sienta parte de la misma marca que el resto de la app, no un documento aparte.
PRIMARY_COLOR = colors.HexColor('#2f6fed')
SECONDARY_COLOR = colors.HexColor('#1fae5c')
DARK_COLOR = colors.HexColor('#242a3b')
LIGHT_GRAY = colors.HexColor('#f3f4f9')
MID_GRAY = colors.HexColor('#c7cbd6')
WHITE = colors.white


def _money(value):
    try:
        return f'${float(value or 0):,.2f}'
    except (TypeError, ValueError):
        return '$0.00'


def _safe(value, default=''):
    if value is None:
        return default
    return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _desc(catalogo, clave):
    clave = (clave or '').strip()
    if not clave:
        return ''
    nombre = catalogo.get(clave, '')
    return f'{clave} {nombre}'.strip()


def _styles():
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('t', parent=base['Heading1'], fontName='Helvetica-Bold',
                                 fontSize=16, textColor=WHITE, alignment=TA_RIGHT),
        'sub': ParagraphStyle('sub', parent=base['Normal'], fontSize=9, textColor=WHITE, alignment=TA_RIGHT),
        'label': ParagraphStyle('l', parent=base['Normal'], fontName='Helvetica-Bold',
                                 fontSize=7.5, textColor=PRIMARY_COLOR, spaceAfter=1),
        'normal': ParagraphStyle('n', parent=base['Normal'], fontSize=8.5, leading=11),
        'th': ParagraphStyle('th', parent=base['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=WHITE),
        'cell': ParagraphStyle('c', parent=base['Normal'], fontSize=8, leading=10),
        'cell_r': ParagraphStyle('cr', parent=base['Normal'], fontSize=8, leading=10, alignment=TA_RIGHT),
        'foot': ParagraphStyle('f', parent=base['Normal'], fontSize=6.5, textColor=colors.grey, alignment=TA_CENTER),
        'sello': ParagraphStyle('s', parent=base['Normal'], fontName='Courier', fontSize=5, leading=6, textColor=colors.grey),
        'sello_lbl': ParagraphStyle('sl', parent=base['Normal'], fontName='Helvetica-Bold', fontSize=6, textColor=PRIMARY_COLOR),
    }


def _qr_image(text, size_inch=1.1):
    try:
        import qrcode
        qr = qrcode.QRCode(version=None, box_size=10, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return Image(buf, width=size_inch * inch, height=size_inch * inch)
    except Exception:
        return None


def _kv_box(st, filas, label_w, val_w, titulo=None):
    rows = []
    style = [
        ('BOX', (0, 0), (-1, -1), 0.5, MID_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]
    if titulo:
        rows.append([Paragraph(titulo, ParagraphStyle('bt', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE)), ''])
        style += [('SPAN', (0, 0), (1, 0)), ('BACKGROUND', (0, 0), (1, 0), PRIMARY_COLOR)]
    for k, v in filas:
        rows.append([Paragraph(k, st['label']), Paragraph(_safe(v), st['normal'])])
    t = Table(rows, colWidths=[label_w, val_w])
    t.setStyle(TableStyle(style))
    return t


def generate_invoice_pdf(invoice, company, restaurant_name='Mi Restaurante', tagline='', xml_data=None):
    """invoice: modelo Invoice (SQLAlchemy) ya timbrado. company: modelo
    Company (emisor) vigente. xml_data: dict de parse_timbre(invoice_xml)
    con los datos del TFD (uuid/sellos/fecha)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=30, bottomMargin=30, leftMargin=36, rightMargin=36)
    st = _styles()
    elements = []

    tfd = xml_data or {}
    total = float(invoice.total or 0)

    # --- Encabezado: nombre del restaurante + folio fiscal, sobre fondo oscuro ---
    header = Table([[
        Paragraph(f'<b>{_safe(restaurant_name)}</b><br/><font size=7>{_safe(tagline)}</font>', ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=14, textColor=WHITE, leading=16)),
        Paragraph(f"{'NOTA DE CRÉDITO' if invoice.cfdi_type == 'E' else 'FACTURA'}<br/><font size=9>Folio: {_safe(invoice.serie or '')}{_safe(invoice.folio or '')}</font>", st['title']),
    ]], colWidths=[320, 190])
    header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (0, 0), 14), ('RIGHTPADDING', (1, 0), (1, 0), 14),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 12))

    # --- Emisor / Receptor ---
    info = Table([[
        _kv_box(st, [
            ('RAZÓN SOCIAL', company.razon_social or ''),
            ('RFC', company.rfc or ''),
            ('RÉGIMEN FISCAL', _desc(REGIMEN_FISCAL, company.regimen_fiscal)),
            ('LUGAR DE EXPEDICIÓN', company.cp or ''),
        ], 90, 150, titulo='EMISOR'),
        _kv_box(st, [
            ('RAZÓN SOCIAL', invoice.receptor_nombre or ''),
            ('RFC', invoice.receptor_rfc or ''),
            ('RÉGIMEN FISCAL', _desc(REGIMEN_FISCAL, invoice.receptor_regimen_fiscal)),
            ('USO CFDI', _desc(USO_CFDI, invoice.uso_cfdi)),
        ], 90, 150, titulo='RECEPTOR'),
    ]], colWidths=[245, 245])
    info.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(info)
    elements.append(Spacer(1, 10))

    # --- Datos del comprobante ---
    datos = _kv_box(st, [
        ('FECHA DE TIMBRADO', tfd.get('fecha_timbrado', '') or (invoice.stamped_at.isoformat() if invoice.stamped_at else '')),
        ('FOLIO FISCAL (UUID)', tfd.get('uuid', '') or invoice.uuid or ''),
        ('FORMA DE PAGO', _desc(FORMA_PAGO, invoice.forma_pago)),
        ('MÉTODO DE PAGO', _desc(METODO_PAGO, invoice.metodo_pago)),
        ('MONEDA', invoice.moneda or 'MXN'),
    ], 130, 360)
    elements.append(datos)
    elements.append(Spacer(1, 12))

    # --- Conceptos ---
    rows = [[
        Paragraph('CANT', st['th']), Paragraph('UNIDAD', st['th']), Paragraph('DESCRIPCIÓN', st['th']),
        Paragraph('P. UNIT', st['th']), Paragraph('IMPORTE', st['th']),
    ]]
    for it in invoice.items:
        rows.append([
            Paragraph(f'{float(it.quantity or 0):g}', st['cell']),
            Paragraph(_safe(it.clave_unidad), st['cell']),
            Paragraph(_safe(it.description), st['cell']),
            Paragraph(_money(it.unit_price), st['cell_r']),
            Paragraph(_money(it.subtotal), st['cell_r']),
        ])
    table = Table(rows, colWidths=[35, 55, 245, 65, 80], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ('GRID', (0, 0), (-1, -1), 0.4, MID_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10))

    # --- Totales ---
    totales = Table([
        ['', Paragraph('Subtotal', st['normal']), Paragraph(_money(invoice.subtotal), st['cell_r'])],
        ['', Paragraph('IVA', st['normal']), Paragraph(_money(invoice.iva_amount), st['cell_r'])],
        ['', Paragraph('<b>Total</b>', st['normal']), Paragraph(f'<b>{_money(invoice.total)}</b>', st['cell_r'])],
    ], colWidths=[300, 100, 80])
    totales.setStyle(TableStyle([
        ('LINEABOVE', (1, -1), (-1, -1), 0.6, PRIMARY_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(totales)
    elements.append(Spacer(1, 16))

    # --- QR + sellos fiscales (obligatorios en la representacion impresa) ---
    qr_text = qr_content(tfd, company.rfc, invoice.receptor_rfc, total)
    qr_img = _qr_image(qr_text)
    sellos_txt = (
        f"<b>Sello digital del CFDI:</b><br/>{_safe(tfd.get('sello_cfd', '')[:200])}<br/><br/>"
        f"<b>Sello del SAT:</b><br/>{_safe(tfd.get('sello_sat', '')[:200])}<br/><br/>"
        f"<b>Cadena original del complemento de certificación digital del SAT:</b><br/>{_safe(cadena_original_tfd(tfd))}"
    )
    fiscal_row = Table([[
        qr_img or Paragraph('', st['normal']),
        Paragraph(sellos_txt, st['sello']),
    ]], colWidths=[100, 390])
    fiscal_row.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(fiscal_row)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(
        'Este documento es una representación impresa de un CFDI. '
        'Sin validez fiscal si el proveedor de timbrado es "Simulado".',
        st['foot'],
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
