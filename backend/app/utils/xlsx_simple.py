"""Un .xlsx minimo de una hoja, sin dependencias (un .xlsx es un zip de XML).

Lo usan la hoja de nomina y el reporte de asistencia para RH. Numeros como
numero y lo demas como texto; sin estilos.
"""
from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

_NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
_REL = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
_CABECERA = '<?xml version="1.0" encoding="UTF-8"?>'
MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _ref(col: int, fila: int) -> str:
    letras = ""
    col += 1
    while col:
        col, resto = divmod(col - 1, 26)
        letras = chr(65 + resto) + letras
    return f"{letras}{fila}"


def _celda(ref: str, valor) -> str:
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return f'<c r="{ref}"><v>{valor}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(valor))}</t></is></c>'


def _anchos(filas: list[list]) -> str:
    """Ancho de cada columna segun su texto mas largo: sin esto Excel cortaba encabezados y nombres."""
    largos: dict[int, int] = {}
    for fila in filas:
        for j, v in enumerate(fila):
            largos[j] = max(largos.get(j, 0), len(str(v)))
    if not largos:
        return ""
    return "<cols>" + "".join(f'<col min="{j + 1}" max="{j + 1}" width="{min(max(n + 2, 8), 60)}" customWidth="1"/>'
                              for j, n in sorted(largos.items())) + "</cols>"


def libro(nombre_hoja: str, filas: list[list]) -> bytes:
    hoja = "".join(f'<row r="{i + 1}">' + "".join(_celda(_ref(j, i + 1), v) for j, v in enumerate(f)) + "</row>"
                   for i, f in enumerate(filas))
    archivos = {
        "[Content_Types].xml": f'{_CABECERA}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels": f'{_CABECERA}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        # Excel no acepta en el nombre de la hoja : \ / ? * [ ] ni mas de 31 caracteres.
        "xl/workbook.xml": f'{_CABECERA}<workbook {_NS} {_REL}><sheets>'
        f'<sheet name="{escape("".join(c for c in nombre_hoja if c not in ":\\/?*[]")[:31])}" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": f'{_CABECERA}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": f'{_CABECERA}<worksheet {_NS}>{_anchos(filas)}<sheetData>{hoja}</sheetData></worksheet>',
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in archivos.items():
            z.writestr(nombre, contenido)
    return buffer.getvalue()
