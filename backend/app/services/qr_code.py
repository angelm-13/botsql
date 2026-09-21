"""Genera el codigo QR de un CFDI como imagen embebible en HTML.

WeasyPrint no necesita un archivo en disco: basta un data URI en base64 para
que el <img> lo renderice directo en el PDF.
"""

from __future__ import annotations

import base64
from io import BytesIO

import qrcode


def png_data_uri(data: str, box_size: int = 8, border: int = 1) -> str:
    image = qrcode.make(data, box_size=box_size, border=border)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
