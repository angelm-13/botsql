"""Rutas del vale de almacen.

Cuelgan de `/vouchers` y el permiso es la capacidad `warehouse_voucher`.
Capacidad y no entidad porque esta pantalla no es el CRUD de una tabla: escribe
en `incident` -el vale- y en `nm_incident_product` -sus renglones-, y esa
segunda esta fuera del menu a proposito, por ser tabla puente que se edita desde
su dueno. Es el mismo mecanismo de `inventory_adjustment`.

Cada accion es una ruta propia -abrir el vale, cerrar un renglon- en lugar de un
PUT que reciba el estado destino. El estado del vale se DERIVA de sus renglones
y no se puede capturar: es lo que evita un vale "terminado" con herramienta
todavia fuera. Una ruta que aceptara el estado abriria justo ese camino.
"""

from __future__ import annotations

from functools import wraps
from io import BytesIO

from flask import Blueprint, current_app, jsonify, request, send_file

from app.services.warehouse_voucher_service import (
    _sin_restriccion,
    asignar_entrega_de_renglon,
    confirmar_recepcion_de_renglon,
    documento_del_historial_de_persona,
    folio_del_vale,
    pdf_del_vale,
    autorizar_vale,
    buscar_vales,
    cerrar_renglon,
    consultar_vale,
    crear_vale,
    historial_del_producto,
    lo_que_ha_pedido,
    notificar_custodia_asignada,
    notificar_custodia_confirmada,
    notificar_material_entregado,
    notificar_prevale_creado,
    pdf_del_historial_de_persona,
    quien_tiene_que,
    reporte_por_almacen,
    reporte_por_persona,
    reporte_por_producto,
    reporte_vales_pendientes,
    vales_vencidos,
)
from app.services.inventory_service import has_capability
from app.utils.auth import require_entity_permission, token_required


bp_warehouse_voucher = Blueprint("warehouse_voucher", __name__)


def _cuerpo():
    return request.get_json(silent=True) or {}


def require_warehouse_read(fn):
    """Lee vales quien puede crearlos (`warehouse_voucher`) O quien solo
    puede pedirlos (`warehouse_prevoucher`).

    `require_entity_permission` no soporta "cualquiera de N permisos basta",
    asi que esto es una pieza nueva y chica -- no existe en el repo un
    decorador de OR de permisos reusable. `_ve_todo_el_almacen` (en el
    servicio) SIGUE exigiendo `warehouse_voucher` especificamente para
    decidir "ve todo vs. ve solo lo suyo"; esto solo abre la puerta de
    lectura, no cambia ese alcance. Un Supervisor (solo `warehouse_prevoucher`)
    pasa este guard pero sigue viendo nada mas lo que tiene a su nombre.
    """
    from app.modules.plan import entidad_habilitada
    from app.models.session import transaction_context

    @wraps(fn)
    def wrapper(user_data, *args, **kwargs):
        if not entidad_habilitada("warehouse_voucher"):
            return jsonify({
                'error_key': 'errors.module_not_in_plan',
                'meta': {'entity': 'warehouse_voucher'},
            }), 403
        with transaction_context() as db:
            permitido = (
                _sin_restriccion(user_data)
                or has_capability(db, user_data, "warehouse_voucher")
                or has_capability(db, user_data, "warehouse_prevoucher")
            )
        if not permitido:
            return jsonify({
                'error_key': 'errors.permission_denied',
                'meta': {'entity': 'warehouse_voucher', 'action': 'read'},
            }), 403
        return fn(user_data, *args, **kwargs)
    return wrapper


def _avisar_si_hay_pickup(cuerpo: dict, resultado: dict, user_data: dict) -> None:
    """Si el vale nacio con `id_user_pickup` distinto del responsable, avisa
    por la campanita -- DESPUES de que `crear_vale` ya cerro su transaccion
    (ver `notificar_custodia_asignada`)."""
    id_pickup = cuerpo.get("id_user_pickup")
    if id_pickup is None:
        return
    try:
        notificar_custodia_asignada(
            resultado["voucher"]["id_incident"], id_pickup,
            user_data.get("id_user"))
    except Exception:
        pass


@bp_warehouse_voucher.route("/vouchers", methods=["POST"])
@token_required
@require_entity_permission("warehouse_voucher", "create")
def abrir_vale(user_data):
    """Abre un vale con sus renglones. Todo o nada."""
    cuerpo = _cuerpo()
    resultado = crear_vale(cuerpo, user_data)
    _avisar_si_hay_pickup(cuerpo, resultado, user_data)
    # Un vale directo saca el material AL CREARSE -- no hay un "autorizar"
    # aparte, asi que el aviso de "ya puedes pasar por el" va aqui.
    try:
        notificar_material_entregado(
            resultado["voucher"]["id_incident"], user_data.get("id_user"))
    except Exception:
        pass
    return jsonify(resultado), 201


@bp_warehouse_voucher.route("/prevouchers", methods=["POST"])
@token_required
@require_entity_permission("warehouse_prevoucher", "create")
def abrir_prevale(user_data):
    """Deja un PREVALE: el material pedido, en borrador, sin mover el almacen.

    Ruta aparte y no un campo en el cuerpo de `POST /vouchers` a proposito. Con
    un campo, la puerta seria la misma para pedir y para surtir -- habria que
    guardar la ruta con la capacidad mas permisiva de las dos -- y el permiso
    dejaria de decir nada. Asi cada camino lleva su llave: esta
    `warehouse_prevoucher`, la otra `warehouse_voucher`.
    """
    cuerpo = _cuerpo()
    resultado = crear_vale(cuerpo, user_data, como_borrador=True)
    _avisar_si_hay_pickup(cuerpo, resultado, user_data)
    try:
        notificar_prevale_creado(
            resultado["voucher"]["id_incident"], user_data.get("id_user"))
    except Exception:
        pass
    return jsonify(resultado), 201


@bp_warehouse_voucher.route("/vouchers", methods=["GET"])
@token_required
@require_warehouse_read
def listar_vales(user_data):
    """La lista de vales, buscable por folio o por responsable.

    `q` busca por las dos cosas a la vez, porque son las dos formas en que
    alguien llega a un vale: con el papel en la mano -"vale 112"- o preguntando
    "que trae Maximino". El folio exacto gana sobre la coincidencia parcial.
    """
    return jsonify(buscar_vales(
        user_data,
        texto=request.args.get("q"),
        estado=request.args.get("status"),
        id_user=request.args.get("id_user"),
        # El material de una obra concreta.
        id_proyect=request.args.get("id_proyect"),
        solo_con_pendientes=str(
            request.args.get("only_open") or "").strip().lower()
        in ("1", "true", "si", "yes"),
        pagina=request.args.get("page"),
        por_pagina=request.args.get("per_page"),
    ))


@bp_warehouse_voucher.route("/vouchers/overdue", methods=["GET"])
@token_required
@require_warehouse_read
def vencidos(user_data):
    """Lo que ya debio volver y no ha vuelto. Es la razon de llevar vales."""
    return jsonify(vales_vencidos(user_data))


@bp_warehouse_voucher.route("/vouchers/<id_incident>", methods=["GET"])
@token_required
@require_warehouse_read
def leer_vale(user_data, id_incident):
    return jsonify(consultar_vale(id_incident, user_data))


@bp_warehouse_voucher.route("/vouchers/<id_incident>/pdf", methods=["GET"])
@token_required
@require_warehouse_read
def vale_en_pdf(user_data, id_incident):
    """El vale para imprimir y firmar.

    Se pide `read` y no una capacidad nueva: quien puede ver el vale en pantalla
    puede imprimirlo, porque es el mismo dato. Exigir mas aqui solo conseguiria
    que alguien lo copiara a mano.

    El PDF queda archivado como version de un `document`, asi que despues se
    puede recuperar tal cual desde el modulo de Documentos -- incluido el que se
    firmo el dia de la entrega, aunque el vale haya cambiado desde entonces.
    """
    from app.services.document_service import SecureDocumentStorage

    ficha = pdf_del_vale(
        id_incident, user_data,
        storage=SecureDocumentStorage(current_app.config["UPLOAD_ROOT"]))
    return send_file(
        BytesIO(ficha),
        mimetype="application/pdf",
        as_attachment=False,
        # Con el FOLIO, no con el id interno: un vale que la pantalla llama 95
        # no debe descargarse como "Vale-513.pdf". Es el mismo numero que
        # aparece dentro del documento.
        download_name="Vale-%s.pdf" % folio_del_vale(id_incident, user_data),
    )


@bp_warehouse_voucher.route("/vouchers/<id_incident>/authorize", methods=["POST"])
@token_required
@require_entity_permission("warehouse_voucher_authorize", "create")
def autorizar(user_data, id_incident):
    """Convierte un borrador en vale: lo abre y saca el material.

    Se guarda con `warehouse_voucher_authorize` y no con `warehouse_voucher`
    porque son dos derechos distintos: escribir el prevale y soltar el
    material. El servicio lo vuelve a comprobar -- la ruta protege la puerta,
    pero la regla vive donde vive la operacion.
    """
    resultado = autorizar_vale(id_incident, _cuerpo(), user_data)
    try:
        notificar_material_entregado(id_incident, user_data.get("id_user"))
    except Exception:
        pass
    return jsonify(resultado), 200


@bp_warehouse_voucher.route("/vouchers/lines/<id_line>/return", methods=["POST"])
@bp_warehouse_voucher.route("/vouchers/lines/<id_line>/close", methods=["POST"])
@token_required
@require_entity_permission("warehouse_voucher", "update")
def devolver_linea(user_data, id_line):
    """Recibe de vuelta lo que salio en ese renglon.

    Dos direcciones para una operacion porque no son dos operaciones: cerrar un
    renglon de prestamo ES devolver lo que salio. `/close` se conserva para lo
    que ya estaba escrito contra ella; `/return` es el nombre de lo que hace.

    El cuerpo acepta `id_location` -a donde vuelve, por omision de donde salio- y
    `note`.
    """
    return jsonify(cerrar_renglon(id_line, _cuerpo(), user_data))


@bp_warehouse_voucher.route("/vouchers/lines/<id_line>/deliver-to", methods=["POST"])
@token_required
def entregar_renglon_a(user_data, id_line):
    """A que operador u otro supervisor se le entrega esta pieza.

    Sin `require_entity_permission`: el candado real vive en el servicio
    (`_puede_gestionar_custodia`) porque quien debe poder hacer esto es el
    RESPONSABLE del vale -normalmente Supervisor, que solo tiene
    `warehouse_prevoucher`, nunca `warehouse_voucher`- o quien opera el
    almacen. Cuerpo: `{"id_user": <operador>}`.
    """
    cuerpo = _cuerpo()
    resultado = asignar_entrega_de_renglon(id_line, cuerpo, user_data)
    try:
        notificar_custodia_asignada(
            resultado["id_incident"], cuerpo.get("id_user"),
            user_data.get("id_user"))
    except Exception:
        pass
    return jsonify(resultado)


@bp_warehouse_voucher.route("/vouchers/lines/<id_line>/confirm-custody", methods=["POST"])
@token_required
def confirmar_custodia_de_renglon(user_data, id_line):
    """El supervisor dueño del vale confirma que recupero la pieza del
    operador al que se la habia entregado.

    Mismo candado que `/deliver-to`, y por el mismo motivo: es SU vale.
    """
    resultado = confirmar_recepcion_de_renglon(id_line, user_data)
    try:
        notificar_custodia_confirmada(
            resultado["id_incident"], resultado["id_user_delivered_to"],
            user_data.get("id_user"))
    except Exception:
        pass
    return jsonify(resultado)


# --- la trazabilidad, por la cosa y por la persona ---
#
# Las tres consultas existian como servicio desde que se cargo el sistema
# anterior -son las que contestan "quien tiene que", "que ha pedido cada uno" y
# "quien se ha llevado esto"- pero NINGUNA estaba expuesta: sin ruta, el front no
# tenia por donde preguntarlas, asi que el dato estaba en la base y no habia
# forma de verlo. Eran codigo muerto medido desde el navegador.
#
# Cuelgan de `/vouchers` y no de `/product` porque salen de `nm_incident_product`
# -los renglones del vale-, no del libro de inventario. Son cosas distintas y la
# ficha del producto ensena las dos por separado: el libro dice cuanto entro y
# salio; esto dice QUIEN se lo llevo.


@bp_warehouse_voucher.route("/vouchers/products/<id_product>/history",
                            methods=["GET"])
@token_required
@require_warehouse_read
def historial_de_producto(user_data, id_product):
    """Quien se ha llevado este producto, historico.

    Los renglones son de solo agregado -la devolucion ANADE una entrada en vez
    de reescribir la salida-, asi que esto puede contestar por todos los que se
    lo llevaron y no solo por el ultimo.
    """
    return jsonify(historial_del_producto(id_product, user_data))


@bp_warehouse_voucher.route("/vouchers/holders", methods=["GET"])
@token_required
@require_warehouse_read
def quien_tiene(user_data):
    """Quien tiene que, ahora mismo. Con `id_user`, solo el de esa persona."""
    return jsonify(quien_tiene_que(user_data,
                                   id_user=request.args.get("id_user")))


@bp_warehouse_voucher.route("/vouchers/requests", methods=["GET"])
@token_required
@require_warehouse_read
def lo_pedido(user_data):
    """Que ha pedido cada persona, historico."""
    return jsonify(lo_que_ha_pedido(user_data, request.args.get("id_user")))


@bp_warehouse_voucher.route("/vouchers/requests/pdf", methods=["GET"])
@token_required
@require_warehouse_read
def lo_pedido_pdf(user_data):
    """El historial de una persona en PDF -- el boton que traia el sistema
    anterior y que la ficha nueva (`EmployeeVoucherHistory`) no tenia.

    Mismo alcance que `/vouchers/requests`: `lo_que_ha_pedido` ya resuelve que
    quien solo puede pedir material (sin `warehouse_voucher`) solo ve lo
    suyo, sin importar que `id_user` se mande.
    """
    id_user = request.args.get("id_user")
    ficha = documento_del_historial_de_persona(user_data, id_user)
    pdf = pdf_del_historial_de_persona(user_data, id_user)
    return send_file(
        BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=False,
        download_name="Historial-%s.pdf" % ficha["empleado"],
    )


# --- los 4 reportes de almacen que ya existian en el sistema anterior ---
#
# Los cuatro aceptan el mismo par de filtros: `fecha_inicio`/`fecha_fin`
# (sobre `incident_date`, el mismo nombre que ya usa `routes/kpi.py` para su
# rango) e `id_user` (el solicitante/responsable). Guardados con
# `warehouse_voucher` en modo lectura, igual que el resto de las consultas de
# este archivo -- no son CRUD de una tabla, son la misma pregunta de siempre
# ("que ha salido, a nombre de quien") vista de otras 4 formas.

def _filtros_de_reporte():
    return {
        "fecha_inicio": request.args.get("fecha_inicio"),
        "fecha_fin": request.args.get("fecha_fin"),
        "id_user": request.args.get("id_user"),
    }


@bp_warehouse_voucher.route("/vouchers/reports/by-product", methods=["GET"])
@token_required
@require_warehouse_read
def reporte_producto(user_data):
    """a) Vales agrupados por codigo de producto."""
    return jsonify(reporte_por_producto(user_data, **_filtros_de_reporte()))


@bp_warehouse_voucher.route("/vouchers/reports/by-project", methods=["GET"])
@token_required
@require_warehouse_read
def reporte_proyecto(user_data):
    """b) Vales agrupados por proyecto/sitio -- el texto libre de la nota del
    vale, que es donde vive ese dato en lo migrado de Adser."""
    return jsonify(reporte_por_almacen(user_data, **_filtros_de_reporte()))


@bp_warehouse_voucher.route("/vouchers/reports/pending", methods=["GET"])
@token_required
@require_warehouse_read
def reporte_pendientes(user_data):
    """c) Vales de salida sin cerrar -- NULL o el sentinela heredado del
    sistema anterior (1990-01-01). Lista plana, sin agrupar."""
    return jsonify(reporte_vales_pendientes(user_data, **_filtros_de_reporte()))


@bp_warehouse_voucher.route("/vouchers/reports/by-requester", methods=["GET"])
@token_required
@require_warehouse_read
def reporte_solicitante(user_data):
    """d) Vales agrupados por solicitante/responsable."""
    return jsonify(reporte_por_persona(user_data, **_filtros_de_reporte()))
