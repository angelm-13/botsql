"""
Capa de timbrado AGNOSTICA al PAC (ver __init__.py para la idea general).
Version simplificada de la de cotizador_demo: sin complemento de pagos ni
alta de CSD multiemisor, porque un restaurante siempre cobra de contado y
es un solo emisor.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Emisor:
    """Quien emite la factura (el restaurante)."""
    rfc: str
    nombre: str
    regimen_fiscal: str   # clave SAT, ej. '601'
    cp: str                # codigo postal = lugar de expedicion


@dataclass
class Receptor:
    """A quien se le factura (el comensal)."""
    rfc: str
    nombre: str            # razon social EXACTA como en su constancia
    regimen_fiscal: str    # clave SAT del regimen del receptor
    cp_fiscal: str         # codigo postal del domicilio fiscal
    uso_cfdi: str          # clave SAT, ej. 'G03'


@dataclass
class Concepto:
    """Una partida/renglon de la factura (un platillo, o el consumo total)."""
    descripcion: str
    cantidad: float
    valor_unitario: float
    importe: float             # cantidad * valor_unitario (sin IVA)
    clave_prod_serv: str
    clave_unidad: str
    iva_rate: float = 0.16


@dataclass
class InvoiceDraft:
    """Borrador neutro de un CFDI, listo para timbrar."""
    emisor: Emisor
    receptor: Receptor
    conceptos: List[Concepto] = field(default_factory=list)
    forma_pago: str = '01'    # '01' efectivo por default
    metodo_pago: str = 'PUE'  # siempre de contado en un restaurante
    uso_cfdi: str = 'G03'
    moneda: str = 'MXN'
    cfdi_type: str = 'I'      # 'I' = Ingreso, 'E' = Egreso (nota de credito)
    serie: str = ''
    folio: str = ''
    relacion_uuid: Optional[str] = None  # nota de credito -> UUID de la factura original


@dataclass
class StampResult:
    """Resultado de intentar timbrar. `success` indica si se logro."""
    success: bool
    uuid: Optional[str] = None
    serie: Optional[str] = None
    folio: Optional[str] = None
    xml: Optional[str] = None
    raw_response: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[str] = None


class PACProvider(ABC):
    """Contrato que todo proveedor de timbrado debe cumplir."""
    name = 'base'

    @abstractmethod
    def timbrar(self, draft: 'InvoiceDraft') -> 'StampResult':
        raise NotImplementedError

    def test_connection(self):
        """Verifica que el PAC este disponible/configurado. Devuelve (ok, mensaje)."""
        return True, 'Disponible.'

    def cancelar(self, uuid, motivo='02', folio_sustitucion=None):
        """Solicita la cancelacion de un CFDI ante el SAT.
        Devuelve (ok: bool, estatus: str|None, mensaje: str)."""
        return False, None, 'Este PAC no soporta cancelacion.'
