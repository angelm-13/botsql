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

from flask import Blueprint, current_app, jsonify, request

from bi import service
from bi.schema_extractor import CacheDeEsquema
from bi.security import advertencias_de_despliegue


def crear_blueprint(
    *,
    engine,
    ajustes,
    proveedor,
    cache_esquema: CacheDeEsquema | None = None,
    contexto=None,
    gancho_sql=None,
    relaciones=None,
    nombre: str = "bi",
) -> Blueprint:
    bp = Blueprint(nombre, __name__, url_prefix=ajustes.prefijo_api)
    cache = cache_esquema or CacheDeEsquema(engine, ajustes)

    def _contexto() -> dict:
        return contexto() if contexto is not None else {}

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

        respuesta = service.responder(
            pregunta,
            engine=engine,
            proveedor=proveedor,
            ajustes=ajustes,
            cache_esquema=cache,
            gancho=gancho,
            relaciones_permitidas=permitidas,
        )
        return jsonify(respuesta.a_dict()), respuesta.http

    @bp.get("/schema")
    def esquema():
        """Que ve el modelo. Es la primera pantalla que se mira cuando el
        asistente contesta mal: casi siempre la tabla que hacia falta estaba
        filtrada, o la columna se llama distinto."""
        forzar = request.args.get("refresh") in ("1", "true", "True")
        actual = cache.obtener(forzar=forzar)
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
