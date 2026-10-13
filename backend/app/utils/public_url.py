"""Direccion publica del sistema y URLs absolutas de archivos.

Una sola fuente para `public_catalog` y `sales_catalog`: antes cada uno tenia su
copia de `_public_base_url`, y solo una leia `PUBLIC_BASE_URL`; la otra armaba
las URLs con `request.host_url`.

`PUBLIC_BASE_URL` (ej. `https://comala.torredigital.mx`) manda cuando existe. Sin
ella se cae a `request.host_url`, que sale del encabezado `Host` de la peticion
(lo controla quien llama) y, detras del Ingress, trae el esquema `http` aunque
el cliente haya entrado por `https`: una imagen `http://` dentro de una pagina
`https` el navegador la bloquea como contenido mixto. Por eso en un despliegue
real conviene fijarla.
"""
from __future__ import annotations

import os

from flask import request


def public_base_url() -> str:
    return (os.getenv('PUBLIC_BASE_URL') or request.host_url or '').strip().rstrip('/')


def image_url(path_value) -> str:
    """URL absoluta de un archivo guardado como ruta relativa (ej. `uploads/products/1.png`)."""
    raw = str(path_value or '').strip()
    if not raw:
        return ''
    if raw.startswith(('http://', 'https://')):
        return raw
    return public_base_url() + '/' + raw.lstrip('/')
