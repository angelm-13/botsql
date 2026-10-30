"""El validador debe rechazar los CFDI que el SAT rechazaria.

Las pruebas positivas viven en `test_cfdi_document.py`. Aqui se parte de un
comprobante correcto y se rompe un atributo a la vez, para comprobar que cada
regla detecta su propio defecto.
"""

import xml.etree.ElementTree as ET

import pytest

from app.services.cfdi_validation import inspect_cfdi_xml, validate_cfdi_xml


CFDI_NS = "http://www.sat.gob.mx/cfd/4"
TFD_NS = "http://www.sat.gob.mx/TimbreFiscalDigital"

VALID_CFDI = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
  Version="4.0" Serie="A" Folio="7" Fecha="2026-08-26T10:00:00"
  Sello="SELLO" NoCertificado="30001000000400000001" Certificado="CERT"
  SubTotal="1000.00" Descuento="100.00" Moneda="MXN" Total="1044.00"
  TipoDeComprobante="I" Exportacion="01" MetodoPago="PUE" FormaPago="03"
  LugarExpedicion="37500">
  <cfdi:Emisor Rfc="AAA010101AA1" Nombre="EMPRESA DEMO" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB010101BB1" Nombre="CLIENTE DEMO"
    DomicilioFiscalReceptor="37000" RegimenFiscalReceptor="601" UsoCFDI="G03"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="81111500" Cantidad="1" ClaveUnidad="E48"
      Descripcion="Servicio" ValorUnitario="1000" Importe="1000.00"
      Descuento="100.00" ObjetoImp="02">
      <cfdi:Impuestos>
        <cfdi:Traslados>
          <cfdi:Traslado Base="900.00" Impuesto="002" TipoFactor="Tasa"
            TasaOCuota="0.160000" Importe="144.00"/>
        </cfdi:Traslados>
      </cfdi:Impuestos>
    </cfdi:Concepto>
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="144.00">
    <cfdi:Traslados>
      <cfdi:Traslado Base="900.00" Impuesto="002" TipoFactor="Tasa"
        TasaOCuota="0.160000" Importe="144.00"/>
    </cfdi:Traslados>
  </cfdi:Impuestos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital Version="1.1"
      UUID="3F2C9A1B-4D5E-4F60-8A71-B2C3D4E5F607"
      FechaTimbrado="2026-08-26T10:00:05" RfcProvCertif="MOC010101AAA"
      SelloCFD="SELLOCFD" NoCertificadoSAT="30001000000400000002" SelloSAT="SELLOSAT"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""


def _mutate(**changes):
    """Devuelve el CFDI base con atributos cambiados o eliminados.

    Las claves usan la forma `Nodo.Atributo`; el valor `None` elimina el
    atributo. `Nodo` puede ser Comprobante, Emisor, Receptor, Concepto,
    Traslado (el del concepto), Resumen (el nodo Impuestos del comprobante),
    ResumenTraslado o Timbre.
    """
    root = ET.fromstring(VALID_CFDI)
    nodes = {
        "Comprobante": root,
        "Emisor": root.find(f"{{{CFDI_NS}}}Emisor"),
        "Receptor": root.find(f"{{{CFDI_NS}}}Receptor"),
        "Concepto": root.find(f"{{{CFDI_NS}}}Conceptos/{{{CFDI_NS}}}Concepto"),
        "Traslado": root.find(
            f"{{{CFDI_NS}}}Conceptos/{{{CFDI_NS}}}Concepto/{{{CFDI_NS}}}Impuestos"
            f"/{{{CFDI_NS}}}Traslados/{{{CFDI_NS}}}Traslado"
        ),
        "Resumen": root.find(f"{{{CFDI_NS}}}Impuestos"),
        "ResumenTraslado": root.find(
            f"{{{CFDI_NS}}}Impuestos/{{{CFDI_NS}}}Traslados/{{{CFDI_NS}}}Traslado"
        ),
        "Timbre": root.find(f"{{{CFDI_NS}}}Complemento/{{{TFD_NS}}}TimbreFiscalDigital"),
    }
    for key, value in changes.items():
        node_name, attribute = key.split(".", 1)
        node = nodes[node_name]
        if value is None:
            node.attrib.pop(attribute, None)
        else:
            node.set(attribute, value)
    return ET.tostring(root, encoding="unicode")


def test_the_reference_document_is_valid():
    """Si esta base fallara, el resto de las pruebas no probaria nada."""
    assert inspect_cfdi_xml(VALID_CFDI) == {"errors": [], "warnings": []}


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"Comprobante.Version": "3.3"}, "cfdi.version_must_be_4_0"),
        ({"Comprobante.Sello": None}, "cfdi.sello_required"),
        ({"Comprobante.Certificado": None}, "cfdi.certificado_required"),
        ({"Comprobante.NoCertificado": None}, "cfdi.no_certificado_required"),
        ({"Comprobante.Fecha": "2026-08-26"}, "cfdi.fecha_invalid_format"),
        ({"Comprobante.LugarExpedicion": "3750"}, "cfdi.lugar_expedicion_invalid"),
        ({"Comprobante.TipoDeComprobante": "factura"}, "cfdi.tipo_de_comprobante_invalid"),
        ({"Comprobante.Exportacion": "09"}, "cfdi.exportacion_invalid"),
        ({"Comprobante.FormaPago": "07"}, "cfdi.forma_pago_invalid"),
        ({"Comprobante.MetodoPago": "PUD"}, "cfdi.metodo_pago_invalid"),
        ({"Comprobante.MetodoPago": "PPD"}, "cfdi.ppd_requiere_forma_pago_99"),
        ({"Comprobante.FormaPago": "99"}, "cfdi.pue_no_admite_forma_pago_99"),
        ({"Comprobante.Moneda": "USD"}, "cfdi.tipo_cambio_required_para_moneda_extranjera"),
        ({"Comprobante.TipoCambio": "17.25"}, "cfdi.tipo_cambio_debe_ser_1_en_mxn"),
    ],
)
def test_header_rules(changes, expected):
    assert expected in validate_cfdi_xml(_mutate(**changes))


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"Emisor.Rfc": "AAA1"}, "cfdi.emisor_rfc_invalid"),
        ({"Emisor.Nombre": ""}, "cfdi.emisor_nombre_required"),
        ({"Emisor.RegimenFiscal": "999"}, "cfdi.emisor_regimen_fiscal_invalid"),
        ({"Receptor.Rfc": "BBB1"}, "cfdi.receptor_rfc_invalid"),
        ({"Receptor.Nombre": ""}, "cfdi.receptor_nombre_required"),
        ({"Receptor.DomicilioFiscalReceptor": "370"}, "cfdi.receptor_domicilio_fiscal_invalid"),
        ({"Receptor.RegimenFiscalReceptor": "999"}, "cfdi.receptor_regimen_fiscal_invalid"),
        ({"Receptor.UsoCFDI": "ZZ99"}, "cfdi.uso_cfdi_invalid"),
        ({"Receptor.UsoCFDI": "D01"}, "cfdi.uso_cfdi_incompatible_con_regimen_receptor"),
    ],
)
def test_party_rules(changes, expected):
    assert expected in validate_cfdi_xml(_mutate(**changes))


def test_generic_receiver_rules():
    errors = validate_cfdi_xml(_mutate(**{"Receptor.Rfc": "XAXX010101000"}))
    assert "cfdi.receptor_generico_nombre_invalid" in errors
    assert "cfdi.receptor_generico_regimen_invalid" in errors
    assert "cfdi.receptor_generico_uso_cfdi_invalid" in errors

    ok = _mutate(**{
        "Receptor.Rfc": "XAXX010101000",
        "Receptor.Nombre": "PUBLICO EN GENERAL",
        "Receptor.RegimenFiscalReceptor": "616",
        "Receptor.UsoCFDI": "S01",
    })
    assert validate_cfdi_xml(ok) == []


def test_foreign_receiver_rules():
    errors = validate_cfdi_xml(_mutate(**{"Receptor.Rfc": "XEXX010101000"}))
    assert "cfdi.receptor_extranjero_regimen_invalid" in errors
    assert "cfdi.receptor_extranjero_uso_cfdi_invalid" in errors


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"Concepto.Descripcion": ""}, "cfdi.conceptos.0.descripcion_required"),
        ({"Concepto.ClaveProdServ": "8111150"}, "cfdi.conceptos.0.clave_prod_serv_invalid"),
        ({"Concepto.ClaveUnidad": "PIEZA"}, "cfdi.conceptos.0.clave_unidad_invalid"),
        ({"Concepto.Cantidad": "0"}, "cfdi.conceptos.0.cantidad_invalid"),
        ({"Concepto.ObjetoImp": "09"}, "cfdi.conceptos.0.objeto_imp_invalid"),
    ],
)
def test_concept_rules(changes, expected):
    assert expected in validate_cfdi_xml(_mutate(**changes))


def test_concept_amount_must_match_quantity_times_unit_price():
    broken = _mutate(**{"Concepto.ValorUnitario": "900"})
    assert "cfdi.conceptos.0.importe_no_cuadra_con_cantidad_por_valor_unitario" in validate_cfdi_xml(broken)


def test_tax_object_01_cannot_carry_a_tax_node():
    broken = _mutate(**{"Concepto.ObjetoImp": "01"})
    assert "cfdi.conceptos.0.objeto_imp_no_admite_nodo_impuestos" in validate_cfdi_xml(broken)


def test_tax_object_02_requires_a_tax_node():
    root = ET.fromstring(VALID_CFDI)
    concept = root.find(f"{{{CFDI_NS}}}Conceptos/{{{CFDI_NS}}}Concepto")
    concept.remove(concept.find(f"{{{CFDI_NS}}}Impuestos"))
    errors = validate_cfdi_xml(ET.tostring(root, encoding="unicode"))
    assert "cfdi.conceptos.0.objeto_imp_requiere_nodo_impuestos" in errors


def test_tax_base_must_be_amount_minus_discount():
    broken = _mutate(**{"Traslado.Base": "1000.00"})
    assert "cfdi.conceptos.0.traslado.base_no_cuadra_con_importe_menos_descuento" in validate_cfdi_xml(broken)


def test_tax_amount_must_be_base_times_rate():
    broken = _mutate(**{"Traslado.Importe": "160.00"})
    assert "cfdi.conceptos.0.traslado.importe_no_cuadra_con_base_por_tasa" in validate_cfdi_xml(broken)


def test_iva_rate_outside_the_catalog_is_rejected():
    broken = _mutate(**{"Traslado.TasaOCuota": "0.150000", "Traslado.Importe": "135.00"})
    assert "cfdi.conceptos.0.traslado_iva_tasa_fuera_de_catalogo" in validate_cfdi_xml(broken)


def test_exempt_transfer_cannot_declare_rate_or_amount():
    broken = _mutate(**{"Traslado.TipoFactor": "Exento"})
    errors = validate_cfdi_xml(broken)
    assert "cfdi.conceptos.0.exento_no_admite_tasa_o_cuota" in errors
    assert "cfdi.conceptos.0.exento_no_admite_importe" in errors


def test_payment_complement_is_valid_without_concepts():
    """El comprobante de pago (tipo P) no lleva partidas -- el importe vive en
    el complemento de pagos, no en Conceptos -- asi que no debe exigirlas.
    """
    root = ET.fromstring(VALID_CFDI)
    root.remove(root.find(f"{{{CFDI_NS}}}Conceptos"))
    root.remove(root.find(f"{{{CFDI_NS}}}Impuestos"))
    root.attrib.pop("Descuento", None)
    root.set("TipoDeComprobante", "P")
    root.set("SubTotal", "0")
    root.set("Total", "0")
    root.find(f"{{{CFDI_NS}}}Receptor").set("UsoCFDI", "CP01")
    assert validate_cfdi_xml(ET.tostring(root, encoding="unicode")) == []


def test_other_comprobante_types_still_require_concepts():
    root = ET.fromstring(VALID_CFDI)
    root.remove(root.find(f"{{{CFDI_NS}}}Conceptos"))
    assert "cfdi.conceptos_required" in validate_cfdi_xml(ET.tostring(root, encoding="unicode"))


def test_subtotal_must_equal_the_sum_of_the_concepts():
    broken = _mutate(**{"Comprobante.SubTotal": "1000.50", "Comprobante.Total": "1044.50"})
    assert "cfdi.subtotal_no_cuadra_con_suma_de_conceptos" in validate_cfdi_xml(broken)


def test_discount_must_equal_the_sum_of_the_concept_discounts():
    broken = _mutate(**{"Comprobante.Descuento": "50.00"})
    assert "cfdi.descuento_no_cuadra_con_suma_de_conceptos" in validate_cfdi_xml(broken)


def test_total_must_reconcile_with_subtotal_discount_and_taxes():
    """El descuadre de un centavo que producia el redondeo global."""
    broken = _mutate(**{"Comprobante.Total": "1044.01"})
    assert validate_cfdi_xml(broken) == []  # un centavo entra en la tolerancia
    broken = _mutate(**{"Comprobante.Total": "1044.05"})
    assert "cfdi.total_no_cuadra_con_subtotal_menos_descuento_mas_impuestos" in validate_cfdi_xml(broken)


def test_summary_totals_must_match_the_concept_breakdown():
    broken = _mutate(**{"Resumen.TotalImpuestosTrasladados": "160.00"})
    assert "cfdi.total_impuestos_trasladados_no_cuadra" in validate_cfdi_xml(broken)


def test_summary_node_is_required_when_there_are_taxes():
    root = ET.fromstring(VALID_CFDI)
    root.remove(root.find(f"{{{CFDI_NS}}}Impuestos"))
    assert "cfdi.impuestos_resumen_required" in validate_cfdi_xml(ET.tostring(root, encoding="unicode"))


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"Timbre.Version": "1.0"}, "cfdi.timbre_version_invalid"),
        ({"Timbre.UUID": "no-es-uuid"}, "cfdi.timbre_uuid_invalid"),
        ({"Timbre.FechaTimbrado": "26/08/2026"}, "cfdi.timbre_fecha_invalid"),
        ({"Timbre.RfcProvCertif": "MOC1"}, "cfdi.timbre_rfc_proveedor_invalid"),
        ({"Timbre.SelloCFD": ""}, "cfdi.timbre_sello_cfd_required"),
        ({"Timbre.SelloSAT": ""}, "cfdi.timbre_sello_sat_required"),
        ({"Timbre.NoCertificadoSAT": ""}, "cfdi.timbre_no_certificado_sat_required"),
    ],
)
def test_stamp_rules(changes, expected):
    assert expected in validate_cfdi_xml(_mutate(**changes))


@pytest.mark.parametrize(
    "payload,expected",
    [
        (b"", "cfdi.xml_vacio"),
        (b"<not-xml", "cfdi.xml_mal_formado"),
        (b"<Otro/>", "cfdi.raiz_no_es_comprobante"),
        (
            b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><Comprobante/>',
            "cfdi.xml_con_dtd_o_entidades",
        ),
        # El DTD no se esconde tras un comentario largo ni cambiando la codificacion.
        (
            b"<!--" + b"x" * 9000 + b'--><!DOCTYPE x [<!ENTITY e "a">]><Comprobante/>',
            "cfdi.xml_con_dtd_o_entidades",
        ),
        (
            '<!DOCTYPE x [<!ENTITY e "a">]><Comprobante/>'.encode("utf-16"),
            "cfdi.xml_con_dtd_o_entidades",
        ),
    ],
)
def test_malformed_input_is_rejected_without_raising(payload, expected):
    assert validate_cfdi_xml(payload) == [expected]
