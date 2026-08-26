"""Validacion de un CFDI 4.0 ya construido, antes o despues de timbrar.

Complementa a `invoice_builder.inspect_draft`: aquel revisa los datos de
origen, este revisa el documento XML final. Sirve para tres cosas:

* comprobar que lo que enviamos al PAC es apto para el SAT;
* auditar el XML que el PAC nos devuelve timbrado;
* revisar los CFDI de proveedores que se cargan por `POST /invoice/upload-xml`.

Se validan las reglas que provocan rechazo (estructura del Anexo 20,
catalogos y aritmetica de importes). No sustituye la validacion del XSD ni la
verificacion criptografica del sello, que solo el SAT y el PAC pueden hacer.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

from app.services.invoice_catalogs import (
    CLAVE_PROD_SERV_PATTERN,
    CLAVE_UNIDAD_PATTERN,
    EXPORTACION,
    FORMA_PAGO,
    IMPUESTO,
    METODO_PAGO,
    NOMBRE_PUBLICO_GENERAL,
    OBJETO_IMP,
    OBJETO_IMP_CON_DESGLOSE,
    OBJETO_IMP_SIN_DESGLOSE,
    REGIMEN_FISCAL,
    RFC_PUBLICO_GENERAL,
    RFC_RESIDENTE_EXTRANJERO,
    TASAS_IVA_TRASLADO,
    TIPO_COMPROBANTE,
    USO_CFDI_DETALLE,
)


CFDI_NS = "http://www.sat.gob.mx/cfd/4"
CENT = Decimal("0.01")
RFC_PATTERN = re.compile(r"^[A-ZÑ&]{3,4}[0-9]{6}[A-Z0-9]{3}$")
CP_PATTERN = re.compile(r"^[0-9]{5}$")
FECHA_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$")
UUID_PATTERN = re.compile(r"^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$")

# El SAT tolera una desviacion de un centavo por concepto al comparar
# Importe contra Cantidad * ValorUnitario y los importes de impuestos.
TOLERANCE = CENT


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _child(element, name):
    if element is None:
        return None
    return next((item for item in element if _local(item.tag) == name), None)


def _children(element, name):
    if element is None:
        return []
    return [item for item in element if _local(item.tag) == name]


def _text(element, name, default=""):
    if element is None:
        return default
    value = element.attrib.get(name)
    return default if value is None else str(value).strip()


def _number(element, name):
    """Lee un atributo monetario; devuelve None si falta o no es numerico."""
    if element is None:
        return None
    raw = element.attrib.get(name)
    if raw in (None, ""):
        return None
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        return None


def _off_by_more_than(left, right, tolerance=TOLERANCE) -> bool:
    return abs((left or Decimal("0")) - (right or Decimal("0"))) > tolerance


def _validate_parties(root, errors, warnings):
    issuer = _child(root, "Emisor")
    receiver = _child(root, "Receptor")
    if issuer is None:
        errors.append("cfdi.emisor_missing")
    if receiver is None:
        errors.append("cfdi.receptor_missing")
        return

    issuer_rfc = _text(issuer, "Rfc").upper()
    if not RFC_PATTERN.match(issuer_rfc):
        errors.append("cfdi.emisor_rfc_invalid")
    if not _text(issuer, "Nombre"):
        errors.append("cfdi.emisor_nombre_required")
    if _text(issuer, "RegimenFiscal") not in REGIMEN_FISCAL:
        errors.append("cfdi.emisor_regimen_fiscal_invalid")

    receiver_rfc = _text(receiver, "Rfc").upper()
    receiver_name = _text(receiver, "Nombre")
    receiver_regime = _text(receiver, "RegimenFiscalReceptor")
    cfdi_use = _text(receiver, "UsoCFDI")

    if not RFC_PATTERN.match(receiver_rfc):
        errors.append("cfdi.receptor_rfc_invalid")
    if not receiver_name:
        errors.append("cfdi.receptor_nombre_required")
    if not CP_PATTERN.match(_text(receiver, "DomicilioFiscalReceptor")):
        errors.append("cfdi.receptor_domicilio_fiscal_invalid")
    if receiver_regime not in REGIMEN_FISCAL:
        errors.append("cfdi.receptor_regimen_fiscal_invalid")
    if cfdi_use not in USO_CFDI_DETALLE:
        errors.append("cfdi.uso_cfdi_invalid")

    if receiver_rfc == RFC_PUBLICO_GENERAL:
        if receiver_name.upper() != NOMBRE_PUBLICO_GENERAL:
            errors.append("cfdi.receptor_generico_nombre_invalid")
        if receiver_regime != "616":
            errors.append("cfdi.receptor_generico_regimen_invalid")
        if cfdi_use != "S01":
            errors.append("cfdi.receptor_generico_uso_cfdi_invalid")
    elif receiver_rfc == RFC_RESIDENTE_EXTRANJERO:
        if receiver_regime != "616":
            errors.append("cfdi.receptor_extranjero_regimen_invalid")
        if cfdi_use != "S01":
            errors.append("cfdi.receptor_extranjero_uso_cfdi_invalid")
    elif cfdi_use in USO_CFDI_DETALLE and receiver_regime in REGIMEN_FISCAL:
        allowed = USO_CFDI_DETALLE[cfdi_use][1]
        if receiver_regime not in allowed:
            errors.append("cfdi.uso_cfdi_incompatible_con_regimen_receptor")


def _validate_header(root, errors, warnings):
    if _text(root, "Version") != "4.0":
        errors.append("cfdi.version_must_be_4_0")
    if not FECHA_PATTERN.match(_text(root, "Fecha")):
        errors.append("cfdi.fecha_invalid_format")
    if not _text(root, "Sello"):
        errors.append("cfdi.sello_required")
    if not _text(root, "Certificado"):
        errors.append("cfdi.certificado_required")
    if not _text(root, "NoCertificado"):
        errors.append("cfdi.no_certificado_required")
    if not CP_PATTERN.match(_text(root, "LugarExpedicion")):
        errors.append("cfdi.lugar_expedicion_invalid")

    cfdi_type = _text(root, "TipoDeComprobante")
    if cfdi_type not in TIPO_COMPROBANTE:
        errors.append("cfdi.tipo_de_comprobante_invalid")
    if _text(root, "Exportacion") not in EXPORTACION:
        errors.append("cfdi.exportacion_invalid")

    payment_form = _text(root, "FormaPago")
    payment_method = _text(root, "MetodoPago")
    # FormaPago y MetodoPago son obligatorios en Ingreso y Egreso.
    if cfdi_type in {"I", "E"}:
        if payment_form not in FORMA_PAGO:
            errors.append("cfdi.forma_pago_invalid")
        if payment_method not in METODO_PAGO:
            errors.append("cfdi.metodo_pago_invalid")
        if payment_method == "PPD" and payment_form != "99":
            errors.append("cfdi.ppd_requiere_forma_pago_99")
        if payment_method == "PUE" and payment_form == "99":
            errors.append("cfdi.pue_no_admite_forma_pago_99")

    currency = _text(root, "Moneda")
    exchange_rate = _number(root, "TipoCambio")
    if not currency:
        errors.append("cfdi.moneda_required")
    elif currency not in {"MXN", "XXX"}:
        if exchange_rate is None:
            errors.append("cfdi.tipo_cambio_required_para_moneda_extranjera")
        elif exchange_rate <= 0:
            errors.append("cfdi.tipo_cambio_invalid")
    elif currency == "MXN" and exchange_rate is not None and exchange_rate != Decimal("1"):
        errors.append("cfdi.tipo_cambio_debe_ser_1_en_mxn")


def _concept_tax_entries(concept, group_name, item_name):
    taxes = _child(concept, "Impuestos")
    group = _child(taxes, group_name) if taxes is not None else None
    return _children(group, item_name)


def _validate_concepts(root, errors, warnings):
    container = _child(root, "Conceptos")
    concepts = _children(container, "Concepto")
    if not concepts:
        errors.append("cfdi.conceptos_required")
        return concepts

    for index, concept in enumerate(concepts):
        prefix = f"cfdi.conceptos.{index}"
        if not _text(concept, "Descripcion"):
            errors.append(f"{prefix}.descripcion_required")
        product_key = _text(concept, "ClaveProdServ")
        if not CLAVE_PROD_SERV_PATTERN.match(product_key):
            errors.append(f"{prefix}.clave_prod_serv_invalid")
        if not CLAVE_UNIDAD_PATTERN.match(_text(concept, "ClaveUnidad").upper()):
            errors.append(f"{prefix}.clave_unidad_invalid")

        quantity = _number(concept, "Cantidad")
        unit_price = _number(concept, "ValorUnitario")
        amount = _number(concept, "Importe")
        discount = _number(concept, "Descuento") or Decimal("0")
        if quantity is None or quantity <= 0:
            errors.append(f"{prefix}.cantidad_invalid")
        if unit_price is None or unit_price < 0:
            errors.append(f"{prefix}.valor_unitario_invalid")
        if amount is None or amount < 0:
            errors.append(f"{prefix}.importe_invalid")
        if quantity is not None and unit_price is not None and amount is not None:
            if _off_by_more_than(amount, quantity * unit_price):
                errors.append(f"{prefix}.importe_no_cuadra_con_cantidad_por_valor_unitario")
        if discount < 0 or (amount is not None and discount > amount):
            errors.append(f"{prefix}.descuento_invalid")

        tax_object = _text(concept, "ObjetoImp")
        has_tax_node = _child(concept, "Impuestos") is not None
        if tax_object not in OBJETO_IMP:
            errors.append(f"{prefix}.objeto_imp_invalid")
        elif tax_object in OBJETO_IMP_CON_DESGLOSE and not has_tax_node:
            errors.append(f"{prefix}.objeto_imp_requiere_nodo_impuestos")
        elif tax_object in OBJETO_IMP_SIN_DESGLOSE and has_tax_node:
            errors.append(f"{prefix}.objeto_imp_no_admite_nodo_impuestos")

        base = (amount or Decimal("0")) - discount
        for kind, group_name, item_name in (
            ("traslado", "Traslados", "Traslado"),
            ("retencion", "Retenciones", "Retencion"),
        ):
            for entry in _concept_tax_entries(concept, group_name, item_name):
                tax = _text(entry, "Impuesto")
                factor = _text(entry, "TipoFactor")
                if tax not in IMPUESTO:
                    errors.append(f"{prefix}.{kind}.impuesto_invalid")
                if factor not in {"Tasa", "Cuota", "Exento"}:
                    errors.append(f"{prefix}.{kind}.tipo_factor_invalid")
                entry_base = _number(entry, "Base")
                if entry_base is None or entry_base <= 0:
                    errors.append(f"{prefix}.{kind}.base_invalid")
                elif _off_by_more_than(entry_base, base):
                    errors.append(f"{prefix}.{kind}.base_no_cuadra_con_importe_menos_descuento")

                if factor == "Exento":
                    if kind == "retencion":
                        errors.append(f"{prefix}.retencion_no_admite_tipo_factor_exento")
                    if entry.attrib.get("TasaOCuota") is not None:
                        errors.append(f"{prefix}.exento_no_admite_tasa_o_cuota")
                    if entry.attrib.get("Importe") is not None:
                        errors.append(f"{prefix}.exento_no_admite_importe")
                    continue

                rate = _number(entry, "TasaOCuota")
                entry_amount = _number(entry, "Importe")
                if rate is None:
                    errors.append(f"{prefix}.{kind}.tasa_o_cuota_required")
                elif kind == "traslado" and tax == "002" and factor == "Tasa" and rate not in TASAS_IVA_TRASLADO:
                    errors.append(f"{prefix}.traslado_iva_tasa_fuera_de_catalogo")
                if entry_amount is None:
                    errors.append(f"{prefix}.{kind}.importe_required")
                elif rate is not None and entry_base is not None and factor == "Tasa":
                    if _off_by_more_than(entry_amount, entry_base * rate):
                        errors.append(f"{prefix}.{kind}.importe_no_cuadra_con_base_por_tasa")
    return concepts


def _sum_concept_taxes(concepts, group_name, item_name):
    total = Decimal("0")
    for concept in concepts:
        for entry in _concept_tax_entries(concept, group_name, item_name):
            if _text(entry, "TipoFactor") == "Exento":
                continue
            total += _number(entry, "Importe") or Decimal("0")
    return total


def _validate_totals(root, concepts, errors, warnings):
    subtotal = _number(root, "SubTotal")
    total = _number(root, "Total")
    discount = _number(root, "Descuento") or Decimal("0")
    if subtotal is None:
        errors.append("cfdi.subtotal_required")
    if total is None:
        errors.append("cfdi.total_required")

    concept_amounts = sum((_number(item, "Importe") or Decimal("0") for item in concepts), Decimal("0"))
    concept_discounts = sum((_number(item, "Descuento") or Decimal("0") for item in concepts), Decimal("0"))
    if subtotal is not None and _off_by_more_than(subtotal, concept_amounts):
        errors.append("cfdi.subtotal_no_cuadra_con_suma_de_conceptos")
    if _off_by_more_than(discount, concept_discounts):
        errors.append("cfdi.descuento_no_cuadra_con_suma_de_conceptos")
    if subtotal is not None and discount > subtotal:
        errors.append("cfdi.descuento_mayor_que_subtotal")

    transferred = _sum_concept_taxes(concepts, "Traslados", "Traslado")
    retained = _sum_concept_taxes(concepts, "Retenciones", "Retencion")

    summary = _child(root, "Impuestos")
    if summary is None:
        if transferred or retained:
            errors.append("cfdi.impuestos_resumen_required")
    else:
        declared_transferred = _number(summary, "TotalImpuestosTrasladados")
        declared_retained = _number(summary, "TotalImpuestosRetenidos")
        if transferred and declared_transferred is None:
            errors.append("cfdi.total_impuestos_trasladados_required")
        elif declared_transferred is not None and _off_by_more_than(declared_transferred, transferred):
            errors.append("cfdi.total_impuestos_trasladados_no_cuadra")
        if retained and declared_retained is None:
            errors.append("cfdi.total_impuestos_retenidos_required")
        elif declared_retained is not None and _off_by_more_than(declared_retained, retained):
            errors.append("cfdi.total_impuestos_retenidos_no_cuadra")

    if subtotal is not None and total is not None:
        expected = subtotal - discount + transferred - retained
        if _off_by_more_than(total, expected):
            errors.append("cfdi.total_no_cuadra_con_subtotal_menos_descuento_mas_impuestos")
        if total < 0:
            errors.append("cfdi.total_negativo")


def _validate_stamp(root, errors, warnings):
    """El timbre solo se exige si el comprobante ya paso por el PAC."""
    stamp = next(
        (element for element in root.iter() if _local(element.tag) == "TimbreFiscalDigital"),
        None,
    )
    if stamp is None:
        warnings.append("cfdi.sin_timbre_fiscal_digital")
        return
    if _text(stamp, "Version") != "1.1":
        errors.append("cfdi.timbre_version_invalid")
    if not UUID_PATTERN.match(_text(stamp, "UUID").upper()):
        errors.append("cfdi.timbre_uuid_invalid")
    if not FECHA_PATTERN.match(_text(stamp, "FechaTimbrado")):
        errors.append("cfdi.timbre_fecha_invalid")
    if not RFC_PATTERN.match(_text(stamp, "RfcProvCertif").upper()):
        errors.append("cfdi.timbre_rfc_proveedor_invalid")
    for attribute, key in (
        ("SelloCFD", "cfdi.timbre_sello_cfd_required"),
        ("SelloSAT", "cfdi.timbre_sello_sat_required"),
        ("NoCertificadoSAT", "cfdi.timbre_no_certificado_sat_required"),
    ):
        if not _text(stamp, attribute):
            errors.append(key)


def inspect_cfdi_xml(xml_content) -> dict[str, list[str]]:
    """Revisa un CFDI 4.0 completo.

    Devuelve `{"errors": [...], "warnings": [...]}`. Sin errores, el
    comprobante cumple las reglas de estructura, catalogos y aritmetica que
    el SAT valida al timbrar.
    """
    payload = xml_content.encode("utf-8") if isinstance(xml_content, str) else bytes(xml_content or b"")
    if not payload:
        return {"errors": ["cfdi.xml_vacio"], "warnings": []}

    lowered = payload[:8192].lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        return {"errors": ["cfdi.xml_con_dtd_o_entidades"], "warnings": []}

    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return {"errors": ["cfdi.xml_mal_formado"], "warnings": []}

    if _local(root.tag) != "Comprobante":
        return {"errors": ["cfdi.raiz_no_es_comprobante"], "warnings": []}

    errors: list[str] = []
    warnings: list[str] = []
    if root.tag != f"{{{CFDI_NS}}}Comprobante":
        warnings.append("cfdi.namespace_no_es_cfd_4")

    _validate_header(root, errors, warnings)
    _validate_parties(root, errors, warnings)
    concepts = _validate_concepts(root, errors, warnings)
    _validate_totals(root, concepts, errors, warnings)
    _validate_stamp(root, errors, warnings)
    return {"errors": errors, "warnings": warnings}


def validate_cfdi_xml(xml_content) -> list[str]:
    """Errores que harian que el SAT rechace el comprobante."""
    return inspect_cfdi_xml(xml_content)["errors"]
