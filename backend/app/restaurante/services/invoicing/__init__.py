"""
Facturacion CFDI 4.0 para restaurante.

Arquitectura (misma idea que el proyecto hermano cotizador_demo, simplificada
para un solo emisor y ventas de contado): el resto de la app nunca habla
directamente con un PAC concreto. En su lugar arma un InvoiceDraft neutro
(ver base.py) y llama a provider.timbrar(draft). Cambiar o agregar un PAC
solo implica una clase nueva que herede de PACProvider.
"""
from .base import Emisor, Receptor, Concepto, InvoiceDraft, StampResult, PACProvider
from .catalogs import catalogs_payload, MOTIVO_CANCELACION
from .builder import build_draft_from_sale, draft_totals
from .mock import MockPAC

# Modulo barril: estos nombres se re-exportan a proposito para que el resto
# de la app (routes/invoices.py) los importe desde app.services.invoicing
# directamente, sin conocer la estructura interna de submodulos.
__all__ = [
    'Emisor', 'Receptor', 'Concepto', 'InvoiceDraft', 'StampResult', 'PACProvider',
    'catalogs_payload', 'MOTIVO_CANCELACION',
    'build_draft_from_sale', 'draft_totals',
    'MockPAC', 'PacNotImplementedError', 'get_pac_provider',
]


class PacNotImplementedError(Exception):
    """El proveedor elegido en la configuracion todavia no tiene integracion
    real conectada. A proposito NO cae de vuelta al mock en silencio: timbrar
    'de mentiras' sin que el restaurante se de cuenta seria un error grave en
    un contexto fiscal, asi que se avisa claro en vez de fingir que si se
    facturo de verdad."""
    pass


def get_pac_provider(pac_config):
    """Fabrica: dado un PacConfig, devuelve la instancia del PAC
    correspondiente. 'mock' no requiere credenciales y siempre funciona."""
    provider = (pac_config.provider or 'mock') if pac_config else 'mock'
    if provider == 'mock':
        return MockPAC()
    raise PacNotImplementedError(
        f"El proveedor '{provider}' todavia no esta conectado en este servidor. "
        "Usa 'Simulado' para probar el flujo, o pide que se conecte Facturama de verdad."
    )
