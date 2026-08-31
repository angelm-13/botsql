"""
PAC SIMULADO (mock).

No se conecta a ningun servicio: genera un UUID y un XML ficticios para
poder desarrollar y probar todo el flujo de facturacion sin credenciales.
Las facturas que produce NO tienen validez fiscal alguna.
"""
import uuid as _uuid
from datetime import datetime

from .base import PACProvider, StampResult
from .builder import draft_totals


class MockPAC(PACProvider):
    name = 'mock'

    def test_connection(self):
        return True, 'Modo simulado activo (sin validez fiscal).'

    def cancelar(self, uuid, motivo='02', folio_sustitucion=None):
        if not uuid:
            return False, None, 'Falta el UUID del comprobante a cancelar.'
        if motivo == '01' and not folio_sustitucion:
            return False, None, 'El motivo 01 requiere el UUID del comprobante que sustituye.'
        return True, 'cancelado', 'Cancelacion simulada (sin validez fiscal).'

    def timbrar(self, draft):
        totals = draft_totals(draft)
        subtotal, total = totals['subtotal'], totals['total']

        # UUID unico por timbrado, como haria un PAC real.
        fake_uuid = str(_uuid.uuid4()).upper()
        fecha_timbrado = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        no_cert_emisor = '30001000000400000001'
        no_cert_sat = '30001000000400000002'
        rfc_prov_certif = 'MOCK010101AAA'
        sello_cfd = ('MOCKSELLOCFD' + fake_uuid.replace('-', ''))[:172].ljust(172, 'A')
        sello_sat = ('MOCKSELLOSAT' + fake_uuid.replace('-', ''))[:172].ljust(172, 'B')

        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!-- CFDI SIMULADO: SIN VALIDEZ FISCAL -->\n'
            '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" '
            'xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" '
            f'Version="4.0" SubTotal="{subtotal:.2f}" Total="{total:.2f}" '
            f'Moneda="{draft.moneda}" NoCertificado="{no_cert_emisor}">'
            f'<cfdi:Emisor Rfc="{draft.emisor.rfc}" RegimenFiscal="{draft.emisor.regimen_fiscal}"/>'
            f'<cfdi:Receptor Rfc="{draft.receptor.rfc}" UsoCFDI="{draft.receptor.uso_cfdi}"/>'
            '<cfdi:Complemento>'
            '<tfd:TimbreFiscalDigital Version="1.1" '
            f'UUID="{fake_uuid}" FechaTimbrado="{fecha_timbrado}" '
            f'RfcProvCertif="{rfc_prov_certif}" '
            f'SelloCFD="{sello_cfd}" NoCertificadoSAT="{no_cert_sat}" '
            f'SelloSAT="{sello_sat}"/>'
            '</cfdi:Complemento>'
            '</cfdi:Comprobante>'
        )

        return StampResult(
            success=True,
            uuid=fake_uuid,
            serie=(draft.serie or '').strip() or None,
            folio=(str(draft.folio).strip() if draft.folio else '0'),
            xml=xml,
            raw_response='{"mock": true, "note": "sin validez fiscal"}',
            provider=self.name,
        )
