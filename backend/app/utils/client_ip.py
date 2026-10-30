"""IP del cliente detras de uno o varios proxys.

`X-Forwarded-For` lo escribe quien quiera: lo que el cliente manda va al principio y cada
proxy agrega al FINAL a quien le hablo. Con `TRUSTED_PROXY_HOPS=N` (los proxys propios
entre internet y el backend) se toma la entrada N-esima desde la derecha, que es la que
agrego nuestra infraestructura y el cliente no puede falsificar. Sin la variable se
conserva el comportamiento anterior (la primera entrada), porque ajustar N a ciegas
agruparia a todos los usuarios bajo la IP del ingress.
"""
import os

from flask import request


def client_ip() -> str:
    entradas = [e.strip() for e in request.headers.get('X-Forwarded-For', '').split(',') if e.strip()]
    try:
        saltos = int(os.getenv('TRUSTED_PROXY_HOPS') or 0)
    except ValueError:
        saltos = 0
    if entradas and saltos > 0:
        elegida = entradas[-saltos] if len(entradas) >= saltos else entradas[0]
    else:
        elegida = entradas[0] if entradas else ''
    return (elegida or request.remote_addr or '')[:45]
