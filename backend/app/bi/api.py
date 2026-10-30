"""El blueprint de Flask. Es la unica parte que sabe de HTTP.

Se entrega como fabrica (`crear_blueprint`) y no como blueprint global para
que integrarlo en una aplicacion existente sea una linea, sin variables de
entorno de por medio y sin heredar el `Engine` del modulo:

    app.register_blueprint(crear_blueprint(engine=mi_engine, ajustes=mis_ajustes))

Los dos ganchos de integracion
------------------------------
Son lo que hace que este modulo se pueda montar dentro de un ERP real y no
solo en una demo:

  `contexto`     se llama por peticion y devuelve lo que el anfitrion sepa de
                 quien pregunta (su token ya validado, su inquilino, su rol).
                 Por omision devuelve {} y no hay autenticacion: el modulo
                 suelto no inventa un esquema de sesion propio.

  `gancho_sql`   recibe (conexion, contexto) antes de cada consulta. Es donde
                 una aplicacion multiinquilino fija el alcance del usuario en
                 la sesion de base de datos, para que lo lean las vistas. El
                 SQL que escribio el modelo no puede verlo ni cambiarlo.

  `relaciones`   recibe el contexto y devuelve que puede leer ESE usuario.
                 Sin esto, cualquiera que llegue al endpoint lee todo lo que
                 el extractor expuso.
"""

from __future__ import annotations

import logging
import os
import threading

from flask import Blueprint, current_app, jsonify, request

from . import prompt as prompt_mod, service
from .schema_extractor import CacheDeEsquema
from .security import advertencias_de_despliegue


def crear_blueprint(
    *,
    engine,
    ajustes,
    proveedor,
    cache_esquema: CacheDeEsquema | None = None,
    cache_preguntas: "service.CacheDePreguntas | None" = None,
    contexto=None,
    gancho_sql=None,
    relaciones=None,
    acceso=None,
    requiere_sesion: bool = False,
    nombre: str = "bi",
) -> Blueprint:
    bp = Blueprint(nombre, __name__, url_prefix=ajustes.prefijo_api)
    cache = cache_esquema or CacheDeEsquema(engine, ajustes)
    cache_preg = (cache_preguntas if cache_preguntas is not None
                  else service.CacheDePreguntas(ajustes.ttl_preguntas_s))

    def _precalentar():
        """Deja listo lo caro antes de la primera pregunta: el esquema inspeccionado y, en
        Ollama, el modelo en memoria con la parte fija del prompt ya leida."""
        log = logging.getLogger(__name__)  # en un hilo no hay contexto de Flask: current_app no sirve
        try:
            esquema = cache.obtener()
            if hasattr(proveedor, "calentar"):
                ms = proveedor.calentar(prompt_mod.prefijo_estable(esquema, limite_filas=ajustes.limite_filas))
                if ms is None:
                    log.info("[BI] no se pudo precalentar el modelo (se cargara con la primera pregunta)")
                else:
                    log.info("[BI] modelo precalentado en %s ms", ms)
        except Exception as exc:  # una cortesia: nunca debe tumbar el arranque
            log.info("[BI] precalentamiento omitido: %s", str(exc)[:200])

    # Solo con un modelo que se pueda calentar, fuera de pruebas (TESTING) y de quien lo
    # apague (BI_WARMUP=0), en un hilo aparte.
    if (hasattr(proveedor, "calentar") and os.environ.get("TESTING") != "1"
            and os.environ.get("BI_WARMUP", "1") != "0"):
        threading.Thread(target=_precalentar, daemon=True, name="bi-warmup").start()

    def _contexto() -> dict:
        return contexto() if contexto is not None else {}

    def _acceso(ctx: dict):
        return acceso(ctx).con_usuario(ctx) if acceso is not None else None

    @bp.before_request
    def _exige_sesion():
        # /health queda abierto (lo usan el healthcheck y el despliegue).
        if requiere_sesion and not (request.endpoint or "").endswith(".salud") and not _contexto():
            return jsonify({"ok": False, "error": {
                "tipo": "no_autenticado", "mensaje": "Inicia sesion para consultar."}}), 401

    @bp.post("/query")
    def consultar():
        """El endpoint del contrato: recibe {"prompt": "..."} y devuelve datos."""
        cuerpo = request.get_json(silent=True) or {}
        pregunta = (cuerpo.get("prompt") or cuerpo.get("pregunta") or "").strip()

        if len(pregunta) > 1000:
            return jsonify({
                "ok": False,
                "error": {"tipo": "peticion_invalida",
                          "mensaje": "La pregunta no puede pasar de 1000 caracteres."},
            }), 400

        ctx = _contexto()
        gancho = (lambda con: gancho_sql(con, ctx)) if gancho_sql is not None else None
        permitidas = relaciones(ctx) if relaciones is not None else None

        # Extraer departamento del contexto para filtrado horizontal
        from .config import departamento_del_usuario
        id_department = departamento_del_usuario(ctx)

        acc = _acceso(ctx)
        # El SQL solo se devuelve a un administrador que lo pide a proposito.
        exponer = bool(acc and acc.es_admin and request.args.get("debug_sql") in ("1", "true"))

        respuesta = service.responder(
            pregunta,
            engine=engine,
            proveedor=proveedor,
            ajustes=ajustes,
            cache_esquema=cache,
            gancho=gancho,
            relaciones_permitidas=permitidas,
            cache_preguntas=cache_preg,
            id_department=id_department,
            acceso=acc,
            exponer_sql=exponer,
            usuario=ctx,
        )
        return jsonify(respuesta.a_dict()), respuesta.http

    @bp.get("/schema")
    def esquema():
        """Que ve el modelo. Es la primera pantalla que se mira cuando el
        asistente contesta mal: casi siempre la tabla que hacia falta estaba
        filtrada, o la columna se llama distinto."""
        forzar = request.args.get("refresh") in ("1", "true", "True")
        acc = _acceso(_contexto())
        if acc is not None and not acc.es_admin:
            return jsonify({"ok": False, "error": {
                "tipo": "sin_permiso",
                "mensaje": "Solo un administrador puede ver el esquema."}}), 403

        # Extraer departamento del contexto para filtrado horizontal
        from .config import departamento_del_usuario
        ctx = _contexto()
        id_department = departamento_del_usuario(ctx)

        actual = cache.obtener(forzar=forzar, id_department=id_department, acceso=acc)
        salida = actual.resumen()
        salida["cache"] = cache.estado
        if request.args.get("ddl") in ("1", "true", "True"):
            salida["ddl"] = actual.a_ddl()
        return jsonify(salida)

    @bp.get("/health")
    def salud():
        """Estado real, no un 200 vacio.

        Dice tres cosas que son justo las que fallan al estrenar el modulo:
        si la base responde, si el modelo esta descargado, y si la conexion
        se esta haciendo con un usuario demasiado privilegiado.
        """
        estado_bd, error_bd = True, ""
        try:
            with engine.connect() as con:
                con.exec_driver_sql("SELECT 1")
        except Exception as exc:
            estado_bd, error_bd = False, str(exc)[:300]

        modelo_ok = proveedor.disponible()
        return jsonify({
            "ok": estado_bd,
            "base_de_datos": {"conecta": estado_bd, "error": error_bd,
                              "motor": engine.dialect.name},
            "modelo": {"proveedor": proveedor.nombre,
                       "nombre": getattr(proveedor, "modelo", ""),
                       "disponible": modelo_ok},
            "esquema": cache.estado,
            "cache_preguntas": cache_preg.estado,
            "advertencias": advertencias_de_despliegue(ajustes.database_url),
        }), (200 if estado_bd else 503)

    @bp.errorhandler(Exception)
    def _error_no_previsto(exc):
        # Nunca se devuelve la traza: puede llevar fragmentos de la consulta y
        # de la cadena de conexion. Al log si, completa.
        current_app.logger.exception("Fallo no previsto en el modulo de BI")
        return jsonify({
            "ok": False,
            "error": {"tipo": "error_interno",
                      "mensaje": "Ocurrio un error inesperado procesando la consulta."},
        }), 500

    return bp
