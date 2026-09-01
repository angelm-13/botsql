"""Puente de sesion con el punto de venta.

El problema
-----------
El POS corre su propio backend contra su propia base y con su propia
autenticacion. Sin puente, usarlo desde la aplicacion unificada obligaria a un
segundo inicio de sesion, y un cajero tendria dos contrasenas para lo que es un
solo trabajo.

Como se resuelve
----------------
El usuario entra una sola vez, en TYAKXA. El nucleo comprueba que su rol tenga
la capacidad del punto de venta y, por detras, habla con el POS usando una
cuenta de servicio. El token del POS lo administra este modulo: lo pide cuando
hace falta, lo guarda mientras sirve y lo renueva cuando caduca.

Lo que este puente NO es
------------------------
No es un proxy abierto. Reenviar cualquier ruta que llegue seria dar acceso a
todo el POS -incluida su administracion de usuarios- a cualquiera que tenga la
capacidad mas basica. Solo se reenvia lo que esta declarado en `RUTAS`, y cada
entrada dice que capacidad exige.

Limitacion conocida, dicha aqui porque no se ve desde fuera
-----------------------------------------------------------
El POS registra las operaciones a nombre de la cuenta de servicio, no de la
persona que las hizo: su bitacora dira "puente" en todas. Se manda el actor real
en la cabecera `X-Tyakxa-Actor` para que el POS pueda adoptarlo cuando se
quiera, pero hoy no lo lee. Mientras tanto, la atribucion real vive en la
bitacora del nucleo.
"""

from __future__ import annotations

import os
import threading
import time

import requests
from flask import current_app

from app.utils.errors import AppError


# Cuanto se espera al POS antes de rendirse. Corto a proposito: una caja que se
# queda pensando medio minuto es una fila de gente esperando.
TIEMPO_LIMITE = float(os.getenv("POS_API_TIMEOUT_SECONDS", "8"))

# Margen antes de que el token caduque de verdad. Renovar justo en el limite
# deja peticiones a medio camino con un token que expiro entre el envio y la
# llegada.
MARGEN_DE_RENOVACION = 60


def _url_base() -> str:
    return (os.getenv("POS_API_URL") or "http://pos_backend:5000").rstrip("/")


def _credenciales() -> tuple[str, str]:
    usuario = os.getenv("POS_SERVICE_USER") or ""
    clave = os.getenv("POS_SERVICE_PASSWORD") or ""
    if not usuario or not clave:
        raise AppError(
            "errors.pos_gateway_not_configured",
            503,
            {"missing": [n for n, v in (("POS_SERVICE_USER", usuario),
                                        ("POS_SERVICE_PASSWORD", clave)) if not v]},
        )
    return usuario, clave


# --- rutas que se pueden reenviar ---------------------------------------
#
# (metodo, patron) -> capacidad exigida. El patron se compara por prefijo
# despues de normalizar, asi que `sales/` cubre `sales/<id>` y `sales/open`.
#
# `pos_terminal` es lo que hace un cajero en su turno. `pos_admin` es todo lo
# que configura o consulta el negocio. Un cajero no deberia poder listar la
# nomina de usuarios del POS solo porque el puente existe.
RUTAS = (
    # --- caja: lo que hace un cajero ---
    ("GET", "products", "pos_terminal"),
    ("GET", "products/barcode/", "pos_terminal"),
    ("GET", "products/categories", "pos_terminal"),
    ("POST", "checkout", "pos_terminal"),
    ("GET", "sales/open", "pos_terminal"),
    ("GET", "sales/", "pos_terminal"),
    ("POST", "sales/", "pos_terminal"),
    ("GET", "cash/sessions/open", "pos_terminal"),
    ("POST", "cash/sessions/open", "pos_terminal"),
    ("POST", "cash/sessions/", "pos_terminal"),
    ("GET", "cash/sessions/", "pos_terminal"),
    ("GET", "customers", "pos_terminal"),

    # --- administracion del punto de venta ---
    ("POST", "products", "pos_admin"),
    ("PUT", "products/", "pos_admin"),
    ("POST", "products/categories", "pos_admin"),
    ("PUT", "products/categories/", "pos_admin"),
    ("GET", "inventory/", "pos_admin"),
    ("POST", "inventory/", "pos_admin"),
    ("GET", "reports/", "pos_admin"),
    ("GET", "dashboard/", "pos_admin"),
    ("GET", "expenses", "pos_admin"),
    ("POST", "expenses", "pos_admin"),
    ("GET", "promotions", "pos_admin"),
    ("GET", "suppliers", "pos_admin"),
    ("GET", "invoicing/", "pos_admin"),
    ("GET", "audit", "pos_admin"),
)


def capacidad_para(metodo: str, ruta: str) -> str | None:
    """Que capacidad exige esta ruta, o None si no se puede reenviar.

    Se compara el patron mas largo que encaje, para que `products/categories`
    -que es del cajero- no quede tapado por `products/` de administracion.
    """
    metodo = (metodo or "").upper()
    ruta = (ruta or "").strip("/")
    mejor = None
    for verbo, patron, capacidad in RUTAS:
        if verbo != metodo:
            continue
        limpio = patron.strip("/")
        if ruta == limpio or (patron.endswith("/") and ruta.startswith(limpio + "/")):
            if mejor is None or len(limpio) > mejor[0]:
                mejor = (len(limpio), capacidad)
    return mejor[1] if mejor else None


# --- token de la cuenta de servicio -------------------------------------

class _Sesion:
    """Guarda el token del POS y lo renueva cuando caduca.

    Vive en memoria del proceso. Con varios procesos cada uno pide el suyo, que
    es aceptable: son unas cuantas autenticaciones mas, no un problema de
    correccion. Se anota para no darlo por resuelto de mas.
    """

    def __init__(self):
        self._token = None
        self._vence_en = 0.0
        self._candado = threading.Lock()

    def _pedir_token(self) -> str:
        usuario, clave = _credenciales()
        try:
            respuesta = requests.post(
                f"{_url_base()}/api/v1/auth/login",
                json={"username": usuario, "password": clave},
                timeout=TIEMPO_LIMITE,
            )
        except requests.RequestException as error:
            raise AppError("errors.pos_unreachable", 503, {"reason": str(error)[:200]}) from error

        if respuesta.status_code != 200:
            # Se distingue del resto: una credencial mal puesta se arregla en la
            # configuracion, no reintentando.
            raise AppError(
                "errors.pos_gateway_credentials_rejected",
                502,
                {"status": respuesta.status_code},
            )

        datos = respuesta.json() if respuesta.content else {}
        token = datos.get("access_token")
        if not token:
            raise AppError("errors.pos_gateway_unexpected_response", 502)

        # El POS no dice cuanto dura; se asume una hora y se renueva con margen.
        # Si se equivoca, el 401 de abajo lo corrige en la siguiente llamada.
        self._vence_en = time.time() + 3600 - MARGEN_DE_RENOVACION
        self._token = token
        return token

    def token(self, *, forzar=False) -> str:
        with self._candado:
            if forzar or not self._token or time.time() >= self._vence_en:
                return self._pedir_token()
            return self._token

    def olvidar(self):
        with self._candado:
            self._token = None
            self._vence_en = 0.0


_sesion = _Sesion()


def reiniciar_sesion():
    """Olvida el token. Solo para las pruebas."""
    _sesion.olvidar()


# --- reenvio -------------------------------------------------------------

def reenviar(metodo, ruta, *, actor, params=None, cuerpo=None):
    """Manda la peticion al POS con la sesion de servicio.

    Devuelve (cuerpo, codigo). No levanta excepcion por un error del POS: su
    respuesta se devuelve tal cual para que el usuario vea lo que el POS dijo y
    no un mensaje generico del puente.
    """
    metodo = (metodo or "GET").upper()
    ruta_limpia = (ruta or "").strip("/")
    url = f"{_url_base()}/api/v1/{ruta_limpia}"

    def _llamar(token):
        return requests.request(
            metodo,
            url,
            params=params or None,
            json=cuerpo if metodo in {"POST", "PUT", "PATCH"} else None,
            headers={
                "Authorization": f"Bearer {token}",
                # El actor real de TYAKXA. El POS todavia no lo lee, pero se
                # manda para que pueda adoptarlo sin cambiar este puente.
                "X-Tyakxa-Actor": str(actor or ""),
            },
            timeout=TIEMPO_LIMITE,
        )

    try:
        respuesta = _llamar(_sesion.token())
        if respuesta.status_code == 401:
            # El token caduco antes de lo previsto: se pide otro y se reintenta
            # una sola vez. Reintentar en bucle ante un 401 persistente seria
            # castigar al POS por una credencial mal puesta.
            respuesta = _llamar(_sesion.token(forzar=True))
    except requests.RequestException as error:
        raise AppError("errors.pos_unreachable", 503, {"reason": str(error)[:200]}) from error

    try:
        datos = respuesta.json() if respuesta.content else {}
    except ValueError:
        current_app.logger.warning(
            "El punto de venta respondio algo que no es JSON en %s %s", metodo, ruta_limpia
        )
        datos = {"error": "respuesta no interpretable del punto de venta"}

    return datos, respuesta.status_code


def esta_configurado() -> bool:
    return bool(os.getenv("POS_SERVICE_USER") and os.getenv("POS_SERVICE_PASSWORD"))


def estado() -> dict:
    """Si el puente puede hablar con el POS. Para diagnosticar sin adivinar."""
    if not esta_configurado():
        return {
            "configured": False,
            "reachable": False,
            "detail": "Faltan POS_SERVICE_USER y POS_SERVICE_PASSWORD.",
        }
    try:
        respuesta = requests.get(f"{_url_base()}/health", timeout=TIEMPO_LIMITE)
        return {
            "configured": True,
            "reachable": respuesta.status_code == 200,
            "url": _url_base(),
        }
    except requests.RequestException as error:
        return {
            "configured": True,
            "reachable": False,
            "url": _url_base(),
            "detail": str(error)[:200],
        }
