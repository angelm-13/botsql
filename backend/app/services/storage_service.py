"""Cuanto espacio consume este despliegue y cuanto le queda.

Por que existe
--------------
El plan trae un tope de almacenamiento -`limites.almacenamiento_gb`- y hasta
ahora era un numero que nadie miraba. Este servicio lo hace valer, y de paso
contesta la pregunta comercial: cuanto lleva usado el cliente, para poder
ofrecerle mas.

Que se cuenta
-------------
Los archivos que la aplicacion guarda por peticion de alguien: comprobantes
XML, PDF, estados de cuenta y fotografias de producto. Es lo que crece con el
uso y lo que se puede vender.

No se cuenta la base de datos. Podria, pero mezclar las dos cosas en un solo
numero deja al cliente sin saber que borrar para liberar espacio: los archivos
se pueden mirar y decidir; las filas de la contabilidad no se borran.

Que pasa al pasarse del tope
----------------------------
**Se bloquean las subidas nuevas. Nunca las operaciones.** Que no se pueda
cobrar una venta o timbrar una factura porque el disco esta lleno seria peor que
regalar el almacenamiento: se para el negocio del cliente por un problema
nuestro de cobranza.

Lo que si se bloquea es adjuntar un archivo mas. Duele lo justo para que llame,
y no le impide operar.

**El XML del timbrado es la excepcion.** Timbrar consume un folio ante el SAT y
no se puede deshacer; negarse a guardar su XML despues de emitirlo dejaria un
comprobante existente sin respaldo. Si hace falta, se guarda y el tope se pasa:
un comprobante sin XML es un problema fiscal, y un gigabyte de mas no.

La medicion
-----------
Se recorre el arbol de archivos. Con muchos archivos eso cuesta, asi que el
resultado se guarda unos segundos: la cifra se usa para avisar y para cobrar, no
para contabilidad al byte, y una foto de hace medio minuto vale igual.
"""

from __future__ import annotations

import os
import time

from flask import current_app

from app.utils.errors import AppError


BYTES_POR_GB = 1024 ** 3

# Cuanto vale la medicion antes de volver a recorrer el arbol. Ver el encabezado.
SEGUNDOS_DE_CACHE = 30

_medicion: tuple[float, dict] | None = None


def _raiz() -> str | None:
    try:
        return current_app.config.get("UPLOAD_ROOT")
    except RuntimeError:
        # Fuera de un contexto de aplicacion no hay nada que medir.
        return None


def _recorrer(raiz: str) -> dict:
    """Bytes y numero de archivos, por carpeta y en total."""
    por_carpeta: dict[str, dict] = {}
    total_bytes = 0
    total_archivos = 0

    for actual, _, archivos in os.walk(raiz):
        relativa = os.path.relpath(actual, raiz)
        carpeta = "." if relativa == "." else relativa.split(os.sep)[0]
        entrada = por_carpeta.setdefault(carpeta, {"bytes": 0, "files": 0})
        for nombre in archivos:
            try:
                tamano = os.path.getsize(os.path.join(actual, nombre))
            except OSError:
                # Un archivo que desaparece mientras se recorre no es un error
                # de medicion: se salta y el total queda por debajo, que es el
                # lado correcto en el que equivocarse.
                continue
            entrada["bytes"] += tamano
            entrada["files"] += 1
            total_bytes += tamano
            total_archivos += 1

    return {
        "bytes": total_bytes,
        "files": total_archivos,
        "folders": {k: v for k, v in sorted(por_carpeta.items()) if v["files"]},
    }


def uso_actual(*, refrescar: bool = False) -> dict:
    """Lo que ocupan los archivos guardados."""
    global _medicion

    raiz = _raiz()
    if not raiz or not os.path.isdir(raiz):
        return {"bytes": 0, "files": 0, "folders": {}, "measured": False}

    ahora = time.monotonic()
    if not refrescar and _medicion is not None and ahora - _medicion[0] < SEGUNDOS_DE_CACHE:
        return _medicion[1]

    medido = {**_recorrer(raiz), "measured": True}
    _medicion = (ahora, medido)
    return medido


def limite_bytes() -> int | None:
    """El tope del plan en bytes, o None si el plan no fija ninguno."""
    from app.modules.plan import plan_actual

    gigas = plan_actual().limites.get("almacenamiento_gb")
    if gigas is None:
        return None
    try:
        return int(float(gigas) * BYTES_POR_GB)
    except (TypeError, ValueError):
        return None


def estado(*, refrescar: bool = False) -> dict:
    """Cuanto se usa, cuanto se puede y cuanto queda."""
    uso = uso_actual(refrescar=refrescar)
    tope = limite_bytes()
    usado = int(uso["bytes"])

    if tope is None:
        return {
            "used_bytes": usado,
            "used_gb": round(usado / BYTES_POR_GB, 3),
            "limit_gb": None,
            "limit_bytes": None,
            "available_bytes": None,
            "percent_used": None,
            "over_limit": False,
            "nearly_full": False,
            "files": uso["files"],
            "folders": uso["folders"],
        }

    porcentaje = round(usado * 100 / tope, 1) if tope else 0.0
    return {
        "used_bytes": usado,
        "used_gb": round(usado / BYTES_POR_GB, 3),
        "limit_gb": round(tope / BYTES_POR_GB, 3),
        "limit_bytes": tope,
        "available_bytes": max(0, tope - usado),
        "percent_used": porcentaje,
        "over_limit": usado >= tope,
        # Se avisa antes de llegar, no al llegar: al 100 por ciento la subida ya
        # fallo y quien la intentaba se queda a medias.
        "nearly_full": porcentaje >= 85,
        "files": uso["files"],
        "folders": uso["folders"],
    }


def exigir_espacio(bytes_entrantes: int = 0, *, motivo: str | None = None) -> None:
    """Rechaza la subida si no cabe en el tope del plan.

    Se llama antes de escribir el archivo, no despues: guardar y luego borrar
    deja el disco tocado y, si el proceso muere en medio, pasado de tope.

    `motivo` sirve para las excepciones documentadas -el XML de un comprobante ya
    timbrado- que se guardan aunque el tope quede rebasado.
    """
    if motivo == "comprobante_timbrado":
        return

    tope = limite_bytes()
    if tope is None:
        return

    usado = int(uso_actual()["bytes"])
    entrantes = max(0, int(bytes_entrantes or 0))
    if usado + entrantes <= tope:
        return

    raise AppError("errors.storage_limit_reached", 507, {
        "used_gb": round(usado / BYTES_POR_GB, 3),
        "limit_gb": round(tope / BYTES_POR_GB, 3),
        "incoming_bytes": entrantes,
    })
