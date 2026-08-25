"""
Lectura del XML timbrado (CFDI 4.0) para armar la representacion impresa.

El XML es el documento con validez fiscal; el PDF es solo su "representacion
impresa". Para pintarla se necesita extraer del XML los datos del Timbre
Fiscal Digital (TFD): UUID, fecha de timbrado, sellos, certificados. Con eso
se arma la cadena original del complemento de certificacion y el contenido
del codigo QR que exige el SAT.

El parser es agnostico al namespace (compara por local-name), asi funciona
igual con el XML del mock que con el de un PAC real.
"""
from xml.etree import ElementTree as ET


def _local(tag):
    return tag.rsplit('}', 1)[-1] if '}' in tag else tag


def _find_by_local(root, name):
    for el in root.iter():
        if _local(el.tag) == name:
            return el
    return None


def parse_timbre(xml_data):
    """Extrae los datos fiscales del XML timbrado. Acepta str o bytes.
    Devuelve None si el XML no se puede parsear o no trae TFD."""
    if not xml_data:
        return None
    if isinstance(xml_data, str):
        xml_data = xml_data.encode('utf-8')
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return None

    comprobante = root if _local(root.tag) == 'Comprobante' else _find_by_local(root, 'Comprobante')
    tfd = _find_by_local(root, 'TimbreFiscalDigital')
    if tfd is None:
        return None

    a = tfd.attrib
    comp_attr = comprobante.attrib if comprobante is not None else {}
    return {
        'uuid': a.get('UUID', ''),
        'fecha_timbrado': a.get('FechaTimbrado', ''),
        'sello_cfd': a.get('SelloCFD', ''),
        'sello_sat': a.get('SelloSAT', ''),
        'no_certificado_sat': a.get('NoCertificadoSAT', ''),
        'rfc_prov_certif': a.get('RfcProvCertif', ''),
        'tfd_version': a.get('Version', '1.1'),
        'no_certificado': comp_attr.get('NoCertificado', ''),
    }


def cadena_original_tfd(data):
    """Cadena original del complemento de certificacion (TFD 1.1):
    ||version|UUID|FechaTimbrado|RfcProvCertif|SelloCFD|NoCertificadoSAT||"""
    if not data:
        return ''
    campos = [
        data.get('tfd_version', '1.1'),
        data.get('uuid', ''),
        data.get('fecha_timbrado', ''),
        data.get('rfc_prov_certif', ''),
        data.get('sello_cfd', ''),
        data.get('no_certificado_sat', ''),
    ]
    return '||' + '|'.join(campos) + '||'


def qr_content(data, rfc_emisor, rfc_receptor, total):
    """Contenido del QR de verificacion del SAT (CFDI 4.0)."""
    uuid = (data or {}).get('uuid', '')
    sello = (data or {}).get('sello_cfd', '') or ''
    fe = sello[-8:] if len(sello) >= 8 else sello
    try:
        tt = f'{float(total):.6f}'
    except (TypeError, ValueError):
        tt = '0.000000'
    return (
        'https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx'
        f'?id={uuid}&re={rfc_emisor or ""}&rr={rfc_receptor or ""}&tt={tt}&fe={fe}'
    )
