"""Freno a los intentos de inicio de sesion.

El portal publico ya limitaba los intentos, pero el login interno -el que usa
el personal- no tenia ninguno: se podian probar contrasenas sin limite y sin
dejar mas rastro que la bitacora. Con un diccionario y unos minutos, cualquier
cuenta con contrasena debil cae.

Se cuenta por dos llaves a la vez, y ambas tienen que ceder para dejar pasar:

* por **usuario**, para que no se pueda machacar una cuenta concreta;
* por **origen**, para que no se pueda barrer muchas cuentas desde el mismo
  lugar.

Solo cuentan los intentos fallidos: entrar bien limpia el contador del usuario,
de modo que quien trabaja normal nunca lo nota.

El almacenamiento vive en memoria del proceso, igual que el limitador que ya
existia en el portal publico. Con varios procesos cada uno lleva su cuenta, asi
que el limite efectivo se multiplica por el numero de procesos; sigue acotando
el ataque, pero conviene moverlo a un almacen compartido cuando el sistema
crezca. Queda anotado para no darlo por resuelto de mas.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque


def _entero(nombre: str, por_omision: int) -> int:
    try:
        return max(int(os.getenv(nombre, str(por_omision))), 1)
    except (TypeError, ValueError):
        return por_omision


def max_intentos_por_usuario() -> int:
    return _entero("LOGIN_MAX_ATTEMPTS_PER_USER", 8)


def max_intentos_por_origen() -> int:
    return _entero("LOGIN_MAX_ATTEMPTS_PER_IP", 30)


def ventana_segundos() -> int:
    return _entero("LOGIN_ATTEMPT_WINDOW_SECONDS", 900)


_fallos: dict[str, deque] = defaultdict(deque)


def _podar(llave: str, ahora: float) -> deque:
    intentos = _fallos[llave]
    ventana = ventana_segundos()
    while intentos and ahora - intentos[0] >= ventana:
        intentos.popleft()
    return intentos


def esta_bloqueado(usuario: str, origen: str) -> bool:
    """Si el usuario o el origen agotaron sus intentos en la ventana."""
    ahora = time.time()
    por_usuario = len(_podar(f"user:{(usuario or '').strip().lower()}", ahora))
    por_origen = len(_podar(f"ip:{origen or ''}", ahora))
    return por_usuario >= max_intentos_por_usuario() or por_origen >= max_intentos_por_origen()


def registrar_fallo(usuario: str, origen: str) -> None:
    ahora = time.time()
    for llave in (f"user:{(usuario or '').strip().lower()}", f"ip:{origen or ''}"):
        _podar(llave, ahora).append(ahora)


def registrar_exito(usuario: str) -> None:
    """Entrar bien limpia el contador del usuario.

    El del origen NO se limpia: si desde un mismo lugar se probaron veinte
    cuentas y la vigesimo primera acerto, eso no vuelve inocente al resto.
    """
    _fallos.pop(f"user:{(usuario or '').strip().lower()}", None)


def segundos_para_reintentar(usuario: str, origen: str) -> int:
    """Cuanto falta para que se libere el intento mas antiguo."""
    ahora = time.time()
    ventana = ventana_segundos()
    esperas = []
    for llave, limite in (
        (f"user:{(usuario or '').strip().lower()}", max_intentos_por_usuario()),
        (f"ip:{origen or ''}", max_intentos_por_origen()),
    ):
        intentos = _podar(llave, ahora)
        if len(intentos) >= limite:
            esperas.append(int(ventana - (ahora - intentos[0])) + 1)
    return max(esperas) if esperas else 0


def reiniciar() -> None:
    """Limpia todo. Solo para las pruebas."""
    _fallos.clear()
