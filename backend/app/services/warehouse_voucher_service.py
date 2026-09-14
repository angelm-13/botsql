"""El vale de almacen: quien se llevo que, de donde, y si ya lo devolvio.

Que es un vale
--------------
Un `incident` con renglones. No se invento una entidad nueva porque ya estaba
entera: el vale tiene TIPO -prestamo, salida a obra, devolucion- via
`incident_type`, tiene RESPONSABLE via `id_user`, tiene ESTADO en
`incident_status` y tiene fechas. Y sus renglones son `nm_incident_product`, que
ya unia el vale con el producto y la cantidad.

Lo que le faltaba al renglon para servir de rastro -y se agrego en la migracion
20260904090000- era donde, que pieza, desde cuando y hasta cuando.

Las dos formas de rastrear, y por que conviven
----------------------------------------------
El renglon nombra SIEMPRE un producto, y una pieza solo cuando el material se
rastrea una por una. Lo decide `product.tracking_mode`, que ya existia:

* **serializado** -herramienta de uso interno-: el renglon nombra la pieza.
  Devolver "un desarmador" no cierra el prestamo del desarmador que se llevaron,
  y sin saber cual, la bitacora de la pieza no puede decir quien la tuvo;
* **fungible** -mercancia de compra-venta-: el renglon nombra cantidad. Nadie
  etiqueta trescientos tornillos, y para un distribuidor lo que importa es el
  saldo, no la identidad de cada unidad.

Un mismo vale puede llevar renglones de los dos tipos. Es lo normal: el vale de
una obra saca dos desarmadores concretos y cincuenta metros de cable.

El cierre es automatico, y por que eso importa
----------------------------------------------
Un vale abierto es una deuda: alguien tiene algo del almacen. El estado del vale
NO se captura a mano, se deriva de sus renglones:

* queda un renglon sin cerrar -> el vale sigue abierto;
* se cierra el ultimo -> el vale pasa a cerrado, con su fecha.

Derivarlo en vez de capturarlo evita el estado que mas duele: un vale marcado
"terminado" con dos herramientas todavia fuera, o uno "abierto" con todo
devuelto. Con dos personas trabajando el almacen, eso pasa el primer dia.

Lo que este servicio NO hace
----------------------------
**No mueve la existencia por su cuenta.** El vale es el documento; quien mueve
el almacen es `inventory_service` -para lo fungible- y
`inventory_asset_service` -para las piezas-. Aqui se registra el vale y se
llama a ellos, en esa orden y en la misma transaccion logica, para que no exista
un vale que dice que salio algo que el libro no vio salir.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select

from app.models.incident import Incident
from app.models.incident_type import IncidentType
from app.models.inventory_asset import InventoryAsset
from app.models.location import Location
from app.models.nm_incident_product import NmIncidentProduct
from app.models.product import Product
from app.models.proyect import Proyect
from app.models.session import transaction_context
from app.models.inventory_asset_event import DEVOLUCION, PRESTAMO
from app.models.inventory_stock import InventoryStock
from app.models.user import User
from app.services.inventory_asset_service import (
    DISPONIBLE, PRESTADA, transicion_en_sesion,
)
from app.services.inventory_service import (
    apply_movement_in_session, has_capability,
)
from app.utils.errors import AppError


# Que le pasa a la existencia con este renglon.
SALIDA = "salida"
ENTRADA = "entrada"
TRASLADO = "traslado"
DIRECCIONES = (SALIDA, ENTRADA, TRASLADO)

# Estados del vale. Se derivan de los renglones, no se capturan -- salvo
# `borrador`, que es el unico que dice algo del PERMISO de quien lo escribio y
# no de lo que le paso al material.
#
# El borrador es el prevale: el material pedido, con su responsable y su fecha,
# pero SIN sacar nada del almacen. Quien solo tiene `warehouse_prevoucher`
# -- pedir -- deja el vale asi; quien tiene `warehouse_voucher_authorize`
# -- surtir -- lo autoriza, y es ese acto el que mueve la existencia.
#
# Separar las dos cosas es el control: quien pide el material no es quien decide
# que sale del almacen.
BORRADOR = "borrador"
ABIERTO = "abierto"
CERRADO = "cerrado"
CANCELADO = "cancelado"


def _ahora() -> datetime:
    return datetime.now()


def _entero(valor, campo, *, obligatorio=True):
    if valor in (None, ""):
        if obligatorio:
            raise AppError("errors.required_field", 400, {"field": campo})
        return None
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc


def _tal_vez_entero(valor):
    """El valor como entero si lo es, y None si no. Sin reventar.

    `_entero` esta para campos que TIENEN que ser numero: con basura tira 400,
    que es lo correcto ahi. Pero para preguntar "el texto que teclearon podria
    ser un folio numerico" hace falta lo contrario: buscar "MAXIMINO" no es un
    error de captura, es una busqueda por nombre.
    """
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return None


def _texto(valor, campo, *, largo, obligatorio=False):
    texto = str(valor or "").strip()
    if not texto:
        if obligatorio:
            raise AppError("errors.required_field", 400, {"field": campo})
        return None
    return texto[:largo]


def _actor(user_data: dict) -> int:
    id_usuario = _entero((user_data or {}).get("id_user"), "id_user", obligatorio=False)
    if not id_usuario:
        raise AppError("errors.auth_required", 401)
    return id_usuario


def _fecha_de_regreso(valor):
    """Cuando debe volver. No es opcional.

    Un vale sin fecha de regreso nunca esta vencido, asi que no sale en
    `vales_vencidos` y nadie lo reclama: es una baja disfrazada de prestamo. El
    modulo ya lo decia en un comentario y no lo exigia.
    """
    fecha = _fecha(valor)
    if fecha is None:
        raise AppError("errors.required_field", 400, {"field": "due_date"})
    if fecha.date() < _ahora().date():
        # Una fecha pasada nace vencida. Casi siempre es un dedazo en el ano, y
        # deja el vale en la lista de vencidos desde el primer dia.
        raise AppError("errors.voucher_due_date_in_the_past", 400,
                       {"field": "due_date"})
    return fecha


def _existencias(db, ids_productos: set[int]) -> dict:
    """Cuanto hay de cada producto, en una sola consulta.

    El vale tiene que decir con que existencia se firmo: "salen 5 de 40" y "salen
    5 de 5" son la misma linea con consecuencias distintas, y quien firma solo ve
    la primera cifra. Una consulta por renglon seria el patron de N+1 que ya
    costo caro en el rastreo.
    """
    if not ids_productos:
        return {}
    filas = db.execute(
        select(InventoryStock.id_product, func.sum(InventoryStock.quantity))
        .where(InventoryStock.id_product.in_(list(ids_productos)))
        .group_by(InventoryStock.id_product)
    ).all()
    return {int(id_producto): int(cantidad or 0) for id_producto, cantidad in filas}


def _con_existencias(db, renglones) -> list[dict]:
    """Los renglones serializados, con la existencia y los datos del producto.

    El renglon crudo solo trae `id_product`, y con eso la pantalla escribia
    "producto #6847": un numero que no dice si lo que salio fue un taladro o un
    saco de cemento. Quien mira un vale para reclamar material necesita saber
    QUE es, no su identificador.

    Se resuelve en lote -- una consulta para todos los renglones del vale, no
    una por renglon -- y se traen tambien la marca, el material y la unidad,
    que estan a dos saltos en la base y son lo que identifica una herramienta
    de verdad: "desarmador TRUPER punta plana, pieza".
    """
    ids = {int(r.id_product) for r in renglones}
    saldos = _existencias(db, ids)
    productos = _fichas_de_producto(db, ids)
    salida = []
    for renglon in renglones:
        fila = renglon.serialize()
        fila["stock_on_hand"] = saldos.get(int(renglon.id_product), 0)
        fila["product"] = productos.get(int(renglon.id_product))
        salida.append(fila)
    return salida


def _fichas_de_producto(db, ids) -> dict:
    """Que es cada producto: codigo, descripcion, foto y su clasificacion.

    En dos consultas y no en una por producto: un vale de veinte renglones es
    exactamente donde el N+1 se nota.
    """
    if not ids:
        return {}

    from app.models.brand import Brand
    from app.models.material import Material
    from app.models.unit import Unit

    filas = db.scalars(
        select(Product).where(Product.id_product.in_(list(ids)))
    ).all()
    ids_material = {int(p.id_material) for p in filas if p.id_material}
    materiales = {
        int(m.id_material): m for m in db.scalars(
            select(Material).where(Material.id_material.in_(list(ids_material)))
        ).all()
    } if ids_material else {}
    ids_marca = {int(m.id_brand) for m in materiales.values() if m.id_brand}
    ids_unidad = {int(m.id_unit) for m in materiales.values() if m.id_unit}
    marcas = {
        int(b.id_brand): b.brand_description for b in db.scalars(
            select(Brand).where(Brand.id_brand.in_(list(ids_marca)))
        ).all()
    } if ids_marca else {}
    unidades = {
        int(u.id_unit): u.unit_name for u in db.scalars(
            select(Unit).where(Unit.id_unit.in_(list(ids_unidad)))
        ).all()
    } if ids_unidad else {}

    salida = {}
    for p in filas:
        material = materiales.get(int(p.id_material)) if p.id_material else None
        salida[int(p.id_product)] = {
            "id_product": p.id_product,
            "product_code": p.product_code,
            "descripcion": p.descripcion,
            "path_imagen": p.path_imagen,
            "color": p.color,
            "product_status": p.product_status,
            "tracking_mode": p.tracking_mode,
            "material": getattr(material, "material_description", None),
            "brand": marcas.get(int(material.id_brand)) if material and material.id_brand else None,
            "unit": unidades.get(int(material.id_unit)) if material and material.id_unit else None,
        }
    return salida


def _vale(db, id_incident, *, para_actualizar=False) -> Incident:
    """El vale, por su identificador o por su FOLIO.

    El folio es el numero con el que la gente conoce el vale: en el sistema
    anterior era su propia llave -el vale 112- y aqui vive en `external_folio`
    porque `id_incident` tiene su propia secuencia. Ese mismo 112 es nuestro
    530, y pedirle a alguien que se acuerde del 530 es guardar el folio para
    nada.

    Asi que se busca por los dos. Primero por identificador -es lo que usan los
    enlaces internos y es unico sin discusion- y si no hay, por folio.
    """
    crudo = str(id_incident or "").strip()
    if not crudo:
        raise AppError("errors.required_field", 400, {"field": "id_incident"})

    def buscar(condicion):
        consulta = select(Incident).where(condicion,
                                          Incident.deletion_date.is_(None))
        if para_actualizar:
            consulta = consulta.with_for_update()
        return db.scalars(consulta.limit(1)).first()

    # `_tal_vez_entero` y no `_entero`: preguntar "esto podria ser un id" no es
    # lo mismo que exigir un numero. Con `_entero`, buscar por un folio que no
    # es numerico contestaba 400 en lugar de buscarlo.
    como_numero = _tal_vez_entero(crudo)
    vale = buscar(Incident.id_incident == como_numero) if como_numero else None
    if vale is None:
        vale = buscar(Incident.external_folio == crudo)
    if vale is None:
        raise AppError("errors.not_found", 404,
                       {"entity": "incident", "looked_up": crudo})
    return vale


def _renglones(db, id_incident, *, solo_abiertos=False) -> list[NmIncidentProduct]:
    consulta = select(NmIncidentProduct).where(
        NmIncidentProduct.id_incident == int(id_incident),
        NmIncidentProduct.deletion_date.is_(None),
    )
    if solo_abiertos:
        consulta = consulta.where(NmIncidentProduct.close_date.is_(None))
    return db.scalars(consulta.order_by(NmIncidentProduct.id_nm_incident_product)).all()


def _validar_renglon(db, carga: dict) -> dict:
    """Comprueba un renglon antes de escribirlo, y resuelve su forma.

    La regla de fondo: la pieza se exige cuando el producto se rastrea una por
    una, y se rechaza cuando no. Sin eso se puede capturar un vale de "una
    pieza" de cemento -que no tiene piezas- o un prestamo de herramienta sin
    decir cual, que es el vale que despues nadie puede cerrar.
    """
    id_producto = _entero(carga.get("id_product"), "id_product")
    producto = db.scalars(
        select(Product).where(
            Product.id_product == id_producto,
            Product.deletion_date.is_(None),
        )
    ).first()
    if producto is None:
        raise AppError("errors.not_found", 404, {"entity": "product",
                                                 "field": "id_product"})

    # La direccion no se captura: un vale es una SALIDA del almacen en calidad
    # de prestamo, y eso es todo lo que un vale es. Dejarla elegir permitia
    # capturar un traspaso entre racks como si fuera un vale, y entonces la
    # lista de lo que esta fuera contaba cosas que nunca salieron.
    #
    # Los renglones de ENTRADA existen, pero no los captura nadie: los escribe
    # la devolucion.
    direccion = SALIDA

    serializado = str(producto.tracking_mode or "") == "serializado"
    id_pieza = _entero(carga.get("id_inventory_asset"), "id_inventory_asset",
                       obligatorio=False)

    if serializado and id_pieza is None:
        raise AppError(
            "errors.voucher_asset_required", 400,
            {"field": "id_inventory_asset", "id_product": id_producto,
             "tracking_mode": producto.tracking_mode},
        )
    if not serializado and id_pieza is not None:
        raise AppError(
            "errors.voucher_asset_not_applicable", 400,
            {"field": "id_inventory_asset", "id_product": id_producto,
             "tracking_mode": producto.tracking_mode},
        )

    cantidad = 1
    pieza = None
    if id_pieza is not None:
        pieza = db.scalars(
            select(InventoryAsset).where(
                InventoryAsset.id_inventory_asset == id_pieza,
                InventoryAsset.deletion_date.is_(None),
            )
        ).first()
        if pieza is None:
            raise AppError("errors.not_found", 404,
                           {"entity": "inventory_asset",
                            "field": "id_inventory_asset"})
        if pieza.id_product != id_producto:
            # Una pieza de otro producto en el renglon deja el vale diciendo
            # que se llevaron un desarmador cuando se llevaron un martillo.
            raise AppError(
                "errors.voucher_asset_product_mismatch", 409,
                {"id_inventory_asset": id_pieza, "id_product": id_producto,
                 "asset_id_product": pieza.id_product},
            )
    else:
        cantidad = _entero(carga.get("quantity"), "quantity")
        if cantidad <= 0:
            raise AppError("errors.invalid_field", 400, {"field": "quantity"})

    def ubicacion(clave, obligatorio):
        id_ubicacion = _entero(carga.get(clave), clave, obligatorio=obligatorio)
        if id_ubicacion is None:
            return None
        existe = db.scalars(
            select(Location).where(
                Location.id_location == id_ubicacion,
                Location.deletion_date.is_(None),
            )
        ).first()
        if existe is None:
            raise AppError("errors.not_found", 404, {"entity": "location",
                                                     "field": clave})
        return id_ubicacion

    # De donde sale. Para una pieza se sabe -es donde esta-, pero para lo
    # fungible hay que decirlo: descontar 5 sacos "del almacen" sin decir de
    # cual deja el saldo por ubicacion mintiendo, y ese es el dato con el que
    # alguien va a buscarlos.
    origen = ubicacion("id_location_from", pieza is None)
    if pieza is not None and origen is None:
        origen = pieza.id_location
    # El destino de una salida es una persona, no un sitio, asi que va nulo. Lo
    # llena la devolucion con la ubicacion a la que vuelve.
    destino = None

    return {
        "id_product": id_producto,
        "id_inventory_asset": id_pieza,
        "quantity": cantidad,
        "direction": direccion,
        "id_location_from": origen,
        "id_location_to": destino,
        "note": _texto(carga.get("note"), "note", largo=300),
    }


def _estado_derivado(db, id_incident) -> tuple[str, datetime | None]:
    """El estado del vale segun sus renglones. No se captura, se deriva."""
    abiertos = db.scalar(
        select(func.count())
        .select_from(NmIncidentProduct)
        .where(
            NmIncidentProduct.id_incident == int(id_incident),
            NmIncidentProduct.deletion_date.is_(None),
            NmIncidentProduct.close_date.is_(None),
        )
    )
    if abiertos:
        return ABIERTO, None

    ultimo = db.scalar(
        select(func.max(NmIncidentProduct.close_date)).where(
            NmIncidentProduct.id_incident == int(id_incident),
            NmIncidentProduct.deletion_date.is_(None),
        )
    )
    return CERRADO, ultimo


def _sincronizar_estado(db, vale: Incident) -> None:
    """Deja el vale en el estado que dicen sus renglones.

    Un vale cancelado no se toca: cancelar es una decision de la persona y no
    algo que los renglones puedan revertir.
    """
    if str(vale.incident_status or "").lower() == CANCELADO:
        return
    estado, cierre = _estado_derivado(db, vale.id_incident)
    vale.incident_status = estado
    vale.close_date = cierre
    db.flush()


# --- operaciones ---------------------------------------------------------

def crear_vale(payload: dict, user_data: dict, *, como_borrador: bool = False) -> dict:
    """Abre un vale con sus renglones.

    Todo o nada: si un renglon no pasa la validacion, no se escribe ninguno ni
    el vale. Un vale a medias es peor que ninguno, porque dice que salio parte
    de lo que se pidio y nadie sabe que parte.
    """
    actor = _actor(user_data)
    renglones = payload.get("lines") or payload.get("renglones") or []
    if not renglones:
        raise AppError("errors.voucher_lines_required", 400, {"field": "lines"})

    id_tipo = _entero(payload.get("id_incident_type"), "id_incident_type")
    id_responsable = _entero(payload.get("id_user"), "id_user")
    # A que proyecto va el material. Opcional: no todo prestamo es de un
    # proyecto -- una herramienta para el taller no lo es --, y exigirlo
    # obligaria a inventar un proyecto para cada vale suelto.
    id_proyecto = _entero(payload.get("id_proyect"), "id_proyect", obligatorio=False)

    with transaction_context() as db:
        if db.scalars(select(IncidentType).where(
            IncidentType.id_incident_type == id_tipo,
            IncidentType.deletion_date.is_(None),
        )).first() is None:
            raise AppError("errors.not_found", 404,
                           {"entity": "incident_type", "field": "id_incident_type"})

        # El responsable, comprobado. `incident.id_user` tiene llave ajena
        # DIFERIDA, asi que un identificador inventado no falla al asignarlo:
        # falla en el COMMIT, fuera de todo manejo de errores, y le llega al
        # usuario como un 500. Aqui es el 404 que le toca.
        #
        # Y un usuario dado de baja tampoco sirve: el vale quedaria a nombre de
        # alguien que ya no esta para responder por lo que se llevo.
        if db.scalars(
            select(User.id_user).where(
                User.id_user == id_responsable,
                User.deletion_date.is_(None),
            ).limit(1)
        ).first() is None:
            raise AppError("errors.not_found", 404,
                           {"entity": "user", "field": "id_user"})

        # El proyecto, comprobado por el mismo motivo que el responsable: su
        # llave ajena tambien es diferida, asi que un identificador inventado
        # reventaria en el COMMIT como un 500 en vez de como el 404 que toca.
        if id_proyecto is not None and db.scalars(
            select(Proyect.id_proyect).where(
                Proyect.id_proyect == id_proyecto,
                Proyect.deletion_date.is_(None),
            ).limit(1)
        ).first() is None:
            raise AppError("errors.not_found", 404,
                           {"entity": "proyect", "field": "id_proyect"})

        validados = [_validar_renglon(db, linea) for linea in renglones]

        inicio = _ahora()
        vence = _fecha_de_regreso(payload.get("due_date"))
        motivo = _texto(payload.get("note"), "note", largo=300, obligatorio=True)

        # Borrador o vale. Lo decide la RUTA por la que se entro, no un campo
        # del cuerpo: `POST /prevouchers` esta guardada con
        # `warehouse_prevoucher` y `POST /vouchers` con `warehouse_voucher`,
        # asi que el permiso ya quedo comprobado en la puerta. Si el estado
        # viniera en la peticion, cualquiera que supiera escribir "abierto" se
        # surtiria a si mismo.
        estado = BORRADOR if como_borrador else ABIERTO

        vale = Incident(
            id_incident_type=id_tipo,
            id_user=id_responsable,
            id_proyect=id_proyecto,
            incident_date=inicio,
            incident_status=estado,
            note=motivo,
            created_by=actor,
        )
        db.add(vale)
        db.flush()

        renglones_escritos = []
        for datos in validados:
            renglon = NmIncidentProduct(
                id_incident=vale.id_incident,
                start_date=inicio,
                due_date=vence,
                created_by=actor,
                **datos,
            )
            db.add(renglon)
            renglones_escritos.append(renglon)
        db.flush()

        # Y ahora lo que faltaba: que el vale MUEVA el almacen.
        #
        # Hasta aqui el vale escribia sus renglones y no tocaba nada mas: la
        # pieza seguia diciendo "disponible" mientras estaba en la camioneta de
        # alguien, y el saldo seguia contando cinco sacos que ya no estaban. Dos
        # vistas del mismo hecho, en desacuerdo, y ninguna forma de saber cual
        # creer. Un vale que no descuenta es un papel.
        #
        # Un BORRADOR no mueve nada, y es la razon de que exista: es lo pedido,
        # no lo entregado. La existencia sale cuando alguien lo autoriza, y se
        # vuelve a comprobar entonces -- entre que se pide y se surte pueden
        # haberse llevado la ultima pieza.
        if not como_borrador:
            for renglon in renglones_escritos:
                _sacar_del_almacen(db, renglon, user_data,
                                   id_responsable=id_responsable, vence=vence,
                                   motivo=motivo)
            db.flush()

        return {
            "voucher": vale.serialize(),
            "lines": _con_existencias(db, _renglones(db, vale.id_incident)),
        }


def _sacar_del_almacen(db, renglon, user_data, *, id_responsable, vence, motivo):
    """Descuenta lo que el renglon se lleva, por la puerta de siempre.

    Las dos formas de rastrear salen por caminos distintos y a proposito:

    * la PIEZA pasa por `transicion_en_sesion`, la misma funcion que usa el
      prestamo suelto. Queda PRESTADA, con responsable y con fecha de regreso, y
      su bitacora recibe el evento. No hay un segundo camino que escriba el
      estado de una pieza;
    * lo FUNGIBLE pasa por `apply_movement_in_session` con `movement_type`
      "loan", que es la unica puerta que mueve existencias en todo el sistema.

    La referencia de los dos apunta al vale, asi que desde un movimiento del
    libro se llega al papel que lo justifica.
    """
    if renglon.id_inventory_asset is not None:
        transicion_en_sesion(
            db, renglon.id_inventory_asset,
            {
                "id_holder": id_responsable,
                "due_date": vence.date().isoformat(),
                "reason": motivo,
                "reference_type": "incident",
                "reference_id": str(renglon.id_incident),
                # La clave de idempotencia cuelga del renglon: reintentar el
                # alta del vale no puede prestar la pieza dos veces.
                "idempotency_key": "voucher:%s:line:%s:out" % (
                    renglon.id_incident, renglon.id_nm_incident_product),
            },
            user_data,
            evento=PRESTAMO, destino=PRESTADA,
            exige_responsable=True, exige_fecha=True,
        )
        return

    apply_movement_in_session(
        db, renglon.id_product, user_data,
        movement_type="loan",
        quantity_delta=-int(renglon.quantity),
        idempotency_key="voucher:%s:line:%s:out" % (
            renglon.id_incident, renglon.id_nm_incident_product),
        id_location=renglon.id_location_from,
        reference_type="incident",
        reference_id=str(renglon.id_incident),
        reason=motivo,
    )


def devolver_renglon(id_line, payload: dict, user_data: dict) -> dict:
    """Recibe de vuelta lo que salio en un renglon del vale.

    Como queda el rastro
    --------------------
    La devolucion no borra ni reescribe la salida: **agrega** un renglon de
    ENTRADA. Si salieron dos vales, hay dos renglones de salida; cuando vuelven,
    hay dos de entrada. El papel entero se puede leer despues sin adivinar que
    paso, y es la misma regla que ya sigue la bitacora de la pieza: la historia
    no se corrige, se continua.

    La salida se marca ademas con su `close_date`. No es informacion repetida:
    es lo que hace que "que sigue fuera" y "que esta vencido" sean una consulta
    con indice en lugar de una suma de salidas menos entradas por producto.

    Y la existencia vuelve por la misma puerta por la que salio: la pieza con
    `transicion_en_sesion`, lo fungible con `apply_movement_in_session`.
    """
    actor = _actor(user_data)
    with transaction_context() as db:
        renglon = db.scalars(
            select(NmIncidentProduct).where(
                NmIncidentProduct.id_nm_incident_product == _entero(
                    id_line, "id_nm_incident_product"),
                NmIncidentProduct.deletion_date.is_(None),
            ).with_for_update()
        ).first()
        if renglon is None:
            raise AppError("errors.not_found", 404,
                           {"entity": "nm_incident_product"})
        # La direccion se mira ANTES de la fecha de cierre. Un renglon de
        # entrada nace saldado, asi que la comprobacion de "ya cerrado" saltaria
        # primero y contestaria que se devolvio dos veces cuando el problema es
        # otro: eso no es un prestamo, es la devolucion de uno.
        if str(renglon.direction or "") != SALIDA:
            raise AppError("errors.voucher_line_not_a_loan", 409,
                           {"id_nm_incident_product": renglon.id_nm_incident_product,
                            "direction": renglon.direction})
        if renglon.close_date is not None:
            raise AppError("errors.voucher_line_already_closed", 409,
                           {"id_nm_incident_product": renglon.id_nm_incident_product,
                            "close_date": renglon.close_date.isoformat()})

        nota = _texto(payload.get("note"), "note", largo=300)
        # A donde vuelve. Por omision al sitio de donde salio, que es lo que
        # pasa casi siempre; se puede decir otro, porque a veces se devuelve en
        # otra nave.
        vuelve_a = _entero(payload.get("id_location"), "id_location",
                           obligatorio=False) or renglon.id_location_from
        if vuelve_a is None:
            raise AppError("errors.required_field", 400, {"field": "id_location"})

        ahora = _ahora()
        renglon.close_date = ahora
        if nota:
            renglon.note = nota
        db.flush()

        entrada = NmIncidentProduct(
            id_incident=renglon.id_incident,
            id_product=renglon.id_product,
            id_inventory_asset=renglon.id_inventory_asset,
            quantity=renglon.quantity,
            direction=ENTRADA,
            id_location_from=None,
            id_location_to=vuelve_a,
            start_date=ahora,
            # Una entrada nace saldada: es el hecho de que volvio, no algo
            # pendiente. Si quedara abierta, el vale nunca se cerraria.
            close_date=ahora,
            due_date=None,
            note=nota,
            created_by=actor,
        )
        db.add(entrada)
        db.flush()

        _devolver_al_almacen(db, renglon, user_data, vuelve_a=vuelve_a,
                             motivo=nota, id_entrada=entrada.id_nm_incident_product)
        db.flush()

        vale = _vale(db, renglon.id_incident, para_actualizar=True)
        _sincronizar_estado(db, vale)

        return {
            "line": renglon.serialize(),
            "entry": entrada.serialize(),
            "voucher": vale.serialize(),
            "closed_the_voucher": str(vale.incident_status or "") == CERRADO,
            "actor": actor,
        }


def _devolver_al_almacen(db, renglon, user_data, *, vuelve_a, motivo, id_entrada):
    """Repone lo que el renglon se habia llevado, por la puerta de siempre."""
    if renglon.id_inventory_asset is not None:
        transicion_en_sesion(
            db, renglon.id_inventory_asset,
            {
                "id_location": vuelve_a,
                "reason": motivo,
                "reference_type": "incident",
                "reference_id": str(renglon.id_incident),
                "idempotency_key": "voucher:%s:line:%s:in" % (
                    renglon.id_incident, id_entrada),
            },
            user_data,
            evento=DEVOLUCION, destino=DISPONIBLE,
            libera_responsable=True, vuelve_a_ubicacion=True,
        )
        return

    apply_movement_in_session(
        db, renglon.id_product, user_data,
        movement_type="return",
        quantity_delta=int(renglon.quantity),
        idempotency_key="voucher:%s:line:%s:in" % (
            renglon.id_incident, id_entrada),
        id_location=vuelve_a,
        reference_type="incident",
        reference_id=str(renglon.id_incident),
        reason=motivo,
    )


def cerrar_renglon(id_line, payload: dict, user_data: dict) -> dict:
    """Cerrar un renglon de vale ES devolver lo que salio.

    Se conserva el nombre porque es el de la ruta `/close`, pero no son dos
    operaciones: un renglon de prestamo no se puede dar por terminado sin que la
    herramienta vuelva al almacen. Cuando estaban separadas, cerrar dejaba el
    vale "terminado" con la pieza todavia marcada como prestada.
    """
    return devolver_renglon(id_line, payload, user_data)


def consultar_vale(id_incident, user_data: dict) -> dict:
    """El vale con sus renglones y el estado derivado."""
    _actor(user_data)
    with transaction_context() as db:
        vale = _vale(db, id_incident)
        renglones = _renglones(db, vale.id_incident)
        abiertos = [r for r in renglones if r.close_date is None]
        # Las salidas y las entradas se cuentan aparte. Desde que la
        # devolucion AGREGA un renglon en vez de reescribir el de salida, un
        # vale de dos renglones devuelto tiene cuatro, y un solo "total" leido
        # en pantalla parece que se llevaron el doble.
        salidas = [r for r in renglones if str(r.direction or "") == SALIDA]
        entradas = [r for r in renglones if str(r.direction or "") == ENTRADA]
        # El proyecto al que va el material, con su nombre: en pantalla un
        # "#7" no dice a que obra se lo llevaron.
        proyecto = None
        if vale.id_proyect:
            fila = db.execute(
                select(Proyect.id_proyect, Proyect.folio, Proyect.title,
                       Proyect.proyect_description)
                .where(Proyect.id_proyect == vale.id_proyect)
            ).first()
            if fila is not None:
                proyecto = {"id_proyect": fila[0], "folio": fila[1],
                            "title": fila[2], "description": fila[3]}

        return {
            "voucher": vale.serialize(),
            "proyect": proyecto,
            "lines": _con_existencias(db, renglones),
            "open_lines": len(abiertos),
            "exit_lines": len(salidas),
            "entry_lines": len(entradas),
            "total_lines": len(renglones),
        }


def vales_vencidos(user_data: dict) -> dict:
    """Lo que ya debio volver y no ha vuelto.

    Es la razon de llevar vales. Sin `due_date` en el renglon esto no se podia
    preguntar, y un prestamo sin fecha de regreso es una baja disfrazada: nunca
    esta vencido, asi que nadie lo reclama.
    """
    _actor(user_data)
    ahora = _ahora()
    with transaction_context() as db:
        filas = db.scalars(
            select(NmIncidentProduct).where(
                NmIncidentProduct.deletion_date.is_(None),
                NmIncidentProduct.close_date.is_(None),
                NmIncidentProduct.due_date.isnot(None),
                NmIncidentProduct.due_date < ahora,
            ).order_by(NmIncidentProduct.due_date)
        ).all()
        return {"items": _con_existencias(db, filas), "total": len(filas)}


def _fecha(valor):
    """Una fecha del cliente, o un error que dice cual campo."""
    if isinstance(valor, datetime):
        return valor
    texto = str(valor or "").strip()
    if not texto:
        return None
    for formato in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    raise AppError("errors.invalid_field", 400, {"field": "due_date"})

# --- las tres preguntas que se le hacen a un almacen de herramienta ------
#
# Las tres salen de `nm_incident_product`, que es el registro de entradas y
# salidas de los vales. Y las tres respetan el mismo alcance: quien opera el
# almacen ve todo; quien solo pide material ve lo suyo.
#
# Ese alcance no es cortesia, es la regla que se pidio: el supervisor tiene que
# poder ver que material esta a su nombre, y nada mas.

def _puede_autorizar(db, user_data) -> bool:
    """Si este actor puede convertir un borrador en un vale.

    Es una capacidad APARTE de `warehouse_voucher` a proposito. Con una sola,
    quien escribe el prevale y quien lo autoriza serian el mismo permiso, y la
    separacion no separaria nada: el control es que el borrador lo abra alguien
    distinto del que lo pidio.
    """
    if _sin_restriccion(user_data):
        return True
    return has_capability(db, user_data, "warehouse_voucher_authorize")


def autorizar_vale(id_incident, payload: dict, user_data: dict) -> dict:
    """Convierte un borrador en un vale: lo abre y saca el material.

    Es el acto que mueve el almacen. Antes de esto el borrador es una peticion:
    dice que se pidieron dos taladros, no que salieran.

    La existencia se vuelve a comprobar AQUI y no se confia en la del borrador:
    entre que alguien pide y alguien surte puede haberse llevado la ultima
    pieza, y autorizar contra un saldo viejo dejaria el almacen en negativo.
    Eso lo hace `_sacar_del_almacen`, que es la misma puerta de siempre.

    Solo desde borrador. Autorizar un vale ya abierto sacaria el material dos
    veces, y autorizar uno cerrado o cancelado sacaria lo que ya volvio.
    """
    actor = _actor(user_data)
    with transaction_context() as db:
        if not _puede_autorizar(db, user_data):
            raise AppError("errors.forbidden", 403,
                           {"capability": "warehouse_voucher_authorize"})

        vale = _vale(db, id_incident)
        estado = str(vale.incident_status or "").lower()
        if estado != BORRADOR:
            raise AppError("errors.voucher_not_a_draft", 409,
                           {"id_incident": vale.id_incident, "status": estado})

        # Quien lo pidio no lo autoriza. Es el control entero: sin esto, un rol
        # con las dos capacidades -- o la misma persona con dos sombreros --
        # cerraria el circulo y el borrador seria un tramite.
        if not _sin_restriccion(user_data) and int(vale.created_by or 0) == int(actor):
            raise AppError("errors.voucher_self_authorization", 409,
                           {"id_incident": vale.id_incident})

        renglones = _renglones(db, vale.id_incident)
        if not renglones:
            raise AppError("errors.voucher_lines_required", 400,
                           {"field": "lines"})

        motivo = _texto(payload.get("note"), "note", largo=300,
                        obligatorio=False) or vale.note
        for renglon in renglones:
            if str(renglon.direction or "").lower() != SALIDA:
                continue
            _sacar_del_almacen(db, renglon, user_data,
                               id_responsable=vale.id_user,
                               vence=renglon.due_date, motivo=motivo)

        vale.incident_status = ABIERTO
        vale.last_update_date = _ahora()
        db.flush()

        return {
            "voucher": vale.serialize(),
            "lines": _con_existencias(db, _renglones(db, vale.id_incident)),
        }


def _ve_todo_el_almacen(db, user_data) -> bool:
    """Si este actor ve el almacen completo o solo lo que esta a su nombre.

    Lo decide la capacidad de levantar vales, no el rol: quien surte necesita
    ver quien tiene que para poder reclamarlo, y quien solo pide no.
    """
    if _sin_restriccion(user_data):
        return True
    return has_capability(db, user_data, "warehouse_voucher")


def _sin_restriccion(user_data) -> bool:
    datos = user_data or {}
    return bool(datos.get("is_superuser") or datos.get("is_bootstrap_admin")
                or str(datos.get("user_type") or "").lower() == "admin")


def _renglones_con_contexto(db, filas) -> list[dict]:
    """Los renglones con el nombre del producto, del vale y de su responsable.

    En lote: tres consultas para toda la lista, no tres por renglon. Con ~2 787
    renglones importados del sistema anterior, una consulta por fila es la
    diferencia entre una pantalla que abre y una que no.
    """
    if not filas:
        return []

    ids_productos = {int(f.id_product) for f in filas}
    ids_vales = {int(f.id_incident) for f in filas}

    productos = {
        int(x.id_product): x for x in db.scalars(
            select(Product).where(Product.id_product.in_(list(ids_productos)))
        ).all()
    }
    vales = {
        int(x.id_incident): x for x in db.scalars(
            select(Incident).where(Incident.id_incident.in_(list(ids_vales)))
        ).all()
    }
    ids_usuarios = {
        int(v.id_user) for v in vales.values() if v.id_user is not None
    }
    usuarios = {
        int(x.id_user): x for x in db.scalars(
            select(User).where(User.id_user.in_(list(ids_usuarios) or [0]))
        ).all()
    } if ids_usuarios else {}
    # El TIPO del vale -"Prestamo Material", "Reparacion"-, que el sistema
    # anterior mostraba en su tabla de historial y esta no traia.
    ids_tipos = {
        int(v.id_incident_type) for v in vales.values() if v.id_incident_type
    }
    tipos = {
        int(x.id_incident_type): x for x in db.scalars(
            select(IncidentType).where(
                IncidentType.id_incident_type.in_(list(ids_tipos) or [0]))
        ).all()
    } if ids_tipos else {}

    ahora = _ahora()
    salida = []
    for fila in filas:
        producto = productos.get(int(fila.id_product))
        vale = vales.get(int(fila.id_incident))
        usuario = usuarios.get(int(vale.id_user)) if vale and vale.id_user else None
        tipo = tipos.get(int(vale.id_incident_type)) if vale and vale.id_incident_type else None
        renglon = fila.serialize()
        renglon.update({
            "product_code": getattr(producto, "product_code", None),
            "product_description": getattr(producto, "descripcion", None),
            # El folio con el que la gente conoce el vale. Para lo importado del
            # sistema anterior es su numero de siempre; para lo nuevo, el id.
            "voucher_folio": (getattr(vale, "external_folio", None)
                              or (str(vale.id_incident) if vale else None)),
            "voucher_status": getattr(vale, "incident_status", None),
            "id_user": getattr(vale, "id_user", None),
            "holder_name": getattr(usuario, "full_name", None),
            "returned": fila.close_date is not None,
            "overdue": bool(fila.close_date is None and fila.due_date
                            and fila.due_date < ahora),
            # Del VALE, no del renglon: la nota, el tipo y las dos fechas que
            # el sistema anterior mostraba son las del vale completo -un vale
            # de dos renglones tiene una sola nota y una sola fecha de cierre,
            # no una por renglon.
            "voucher_note": getattr(vale, "note", None),
            "voucher_type": getattr(tipo, "incident_type_description", None),
            "voucher_creation_date": (vale.creation_date.isoformat()
                                      if vale and vale.creation_date else None),
            "voucher_close_date": (vale.close_date.isoformat()
                                   if vale and vale.close_date else None),
        })
        salida.append(renglon)
    return salida


def quien_tiene_que(user_data: dict, *, id_user=None) -> dict:
    """Que trae cada persona AHORA MISMO, y desde cuando.

    Es la pregunta de la manana en un almacen de herramienta, y hasta ahora habia
    que abrirla vale por vale.

    Solo los renglones de SALIDA sin cerrar: una salida cerrada ya volvio, y un
    renglon de entrada es el hecho de que volvio. Contarlos aqui diria que
    alguien tiene algo que devolvio la semana pasada.
    """
    actor = _actor(user_data)
    with transaction_context() as db:
        consulta = (
            select(NmIncidentProduct)
            .join(Incident,
                  Incident.id_incident == NmIncidentProduct.id_incident)
            .where(
                NmIncidentProduct.deletion_date.is_(None),
                NmIncidentProduct.direction == SALIDA,
                NmIncidentProduct.close_date.is_(None),
                Incident.deletion_date.is_(None),
            )
        )

        # El alcance. Quien no opera el almacen ve lo que esta a SU nombre.
        pedido = _entero(id_user, "id_user", obligatorio=False)
        if not _ve_todo_el_almacen(db, user_data):
            pedido = actor
        if pedido is not None:
            consulta = consulta.where(Incident.id_user == pedido)

        filas = db.scalars(
            consulta.order_by(Incident.id_user,
                              NmIncidentProduct.start_date)
        ).all()
        renglones = _renglones_con_contexto(db, filas)

        # Agrupado por persona, que es como se lee: "Juan trae 3 cosas".
        por_persona: dict = {}
        for renglon in renglones:
            clave = renglon["id_user"]
            grupo = por_persona.setdefault(clave, {
                "id_user": clave,
                "holder_name": renglon["holder_name"],
                "items": [],
                "total_items": 0,
                "overdue_items": 0,
            })
            grupo["items"].append(renglon)
            grupo["total_items"] += 1
            if renglon["overdue"]:
                grupo["overdue_items"] += 1

        personas = sorted(
            por_persona.values(),
            key=lambda g: (-g["overdue_items"], -g["total_items"],
                           str(g["holder_name"] or "")),
        )
        return {
            "holders": personas,
            "total_holders": len(personas),
            "total_items": len(renglones),
            "overdue_items": sum(1 for r in renglones if r["overdue"]),
            "scoped_to_actor": not _ve_todo_el_almacen(db, user_data),
        }


def lo_que_ha_pedido(user_data: dict, id_user=None) -> dict:
    """Todo lo que una persona ha pedido, historico.

    Lo devuelto tambien: el historial es lo que contesta "cuantas veces se ha
    llevado esto y cuantas lo ha devuelto tarde", y con solo lo abierto esa
    pregunta no se puede hacer.
    """
    actor = _actor(user_data)
    with transaction_context() as db:
        pedido = _entero(id_user, "id_user", obligatorio=False)
        if not _ve_todo_el_almacen(db, user_data):
            pedido = actor
        if pedido is None:
            pedido = actor

        filas = db.scalars(
            select(NmIncidentProduct)
            .join(Incident,
                  Incident.id_incident == NmIncidentProduct.id_incident)
            .where(
                NmIncidentProduct.deletion_date.is_(None),
                NmIncidentProduct.direction == SALIDA,
                Incident.id_user == pedido,
                Incident.deletion_date.is_(None),
            )
            .order_by(NmIncidentProduct.start_date.desc())
        ).all()
        renglones = _renglones_con_contexto(db, filas)

        return {
            "id_user": pedido,
            "items": renglones,
            "total": len(renglones),
            "still_out": sum(1 for r in renglones if not r["returned"]),
            "overdue": sum(1 for r in renglones if r["overdue"]),
        }


def historial_del_producto(id_product, user_data: dict) -> dict:
    """Quien se ha llevado este producto, historico.

    Es la otra mitad de la trazabilidad: `quien_tiene_que` entra por la persona
    y esto entra por la cosa. La misma tabla contesta las dos, y por eso los
    renglones son de solo agregado: si la devolucion reescribiera la salida, esta
    consulta solo podria decir el ultimo que se lo llevo.
    """
    _actor(user_data)
    with transaction_context() as db:
        id_producto = _entero(id_product, "id_product")
        consulta = (
            select(NmIncidentProduct)
            .join(Incident,
                  Incident.id_incident == NmIncidentProduct.id_incident)
            .where(
                NmIncidentProduct.deletion_date.is_(None),
                NmIncidentProduct.direction == SALIDA,
                NmIncidentProduct.id_product == id_producto,
                Incident.deletion_date.is_(None),
            )
        )
        if not _ve_todo_el_almacen(db, user_data):
            consulta = consulta.where(Incident.id_user == _actor(user_data))

        filas = db.scalars(
            consulta.order_by(NmIncidentProduct.start_date.desc())
        ).all()
        renglones = _renglones_con_contexto(db, filas)

        # Quien lo tiene ahora, que es lo primero que se pregunta.
        fuera = [r for r in renglones if not r["returned"]]
        return {
            "id_product": id_producto,
            "items": renglones,
            "total": len(renglones),
            "currently_out": fuera,
            "times_taken": len(renglones),
            "distinct_holders": len({r["id_user"] for r in renglones
                                     if r["id_user"] is not None}),
        }

def buscar_vales(user_data: dict, *, texto=None, estado=None, id_user=None,
                 id_proyect=None, solo_con_pendientes=False,
                 pagina=1, por_pagina=25) -> dict:
    """La lista de vales, buscable por folio o por responsable.

    Antes solo habia `GET /vouchers/<id>`: para ver los vales de alguien habia
    que ir adivinando identificadores. Y el folio -el numero con el que la gente
    conoce el vale- no se podia buscar.

    El texto busca por FOLIO y por NOMBRE del responsable a la vez, porque son
    las dos formas en que alguien llega a un vale: con el papel en la mano
    -"vale 112"- o preguntando "que trae Maximino".

    El alcance es el mismo que el del resto: quien opera el almacen ve todos;
    quien solo pide material ve los suyos.
    """
    actor = _actor(user_data)
    numero = max(1, _entero(pagina, "page", obligatorio=False) or 1)
    tamano = min(100, max(1, _entero(por_pagina, "per_page",
                                     obligatorio=False) or 25))

    with transaction_context() as db:
        consulta = select(Incident).where(Incident.deletion_date.is_(None))

        # El material de UN proyecto. Es la pregunta que hace el jefe de obra:
        # "que se llevo esta obra y que sigue fuera".
        del_proyecto = _tal_vez_entero(id_proyect)
        if del_proyecto is not None:
            consulta = consulta.where(Incident.id_proyect == del_proyecto)

        if not _ve_todo_el_almacen(db, user_data):
            consulta = consulta.where(Incident.id_user == actor)
        else:
            pedido = _entero(id_user, "id_user", obligatorio=False)
            if pedido is not None:
                consulta = consulta.where(Incident.id_user == pedido)

        limpio = _texto(texto, "q", largo=60)
        if limpio:
            # El folio primero: quien teclea "112" tiene el papel delante y
            # espera ESE vale, no todos los que contienen 112 en algun sitio.
            condiciones = [Incident.external_folio == limpio]
            como_numero = _tal_vez_entero(limpio)
            if como_numero is not None:
                condiciones.append(Incident.id_incident == como_numero)
            condiciones.append(Incident.external_folio.ilike("%%%s%%" % limpio))
            condiciones.append(User.full_name.ilike("%%%s%%" % limpio))
            consulta = consulta.outerjoin(
                User, User.id_user == Incident.id_user).where(or_(*condiciones))

        limpio_estado = _texto(estado, "status", largo=20)
        if limpio_estado:
            consulta = consulta.where(
                func.lower(Incident.incident_status) == limpio_estado.lower())

        if solo_con_pendientes:
            # Los que tienen algo fuera. Es la vista que importa a diario: un
            # vale cerrado ya no se reclama.
            consulta = consulta.where(
                Incident.id_incident.in_(
                    select(NmIncidentProduct.id_incident).where(
                        NmIncidentProduct.direction == SALIDA,
                        NmIncidentProduct.close_date.is_(None),
                        NmIncidentProduct.deletion_date.is_(None),
                    )
                )
            )

        total = db.scalar(
            select(func.count()).select_from(consulta.subquery())) or 0
        paginas = max(1, -(-total // tamano))
        numero = min(numero, paginas)

        vales = db.scalars(
            consulta.order_by(Incident.incident_date.desc(),
                              Incident.id_incident.desc())
            .offset((numero - 1) * tamano).limit(tamano)
        ).all()

        # Los renglones de la pagina, en dos consultas y no dos por vale.
        ids = [int(v.id_incident) for v in vales]
        pendientes: dict[int, int] = {}
        renglones: dict[int, int] = {}
        if ids:
            for id_vale, abiertos, todos in db.execute(
                select(
                    NmIncidentProduct.id_incident,
                    func.count().filter(
                        (NmIncidentProduct.direction == SALIDA)
                        & NmIncidentProduct.close_date.is_(None)),
                    func.count(),
                )
                .where(NmIncidentProduct.id_incident.in_(ids),
                       NmIncidentProduct.deletion_date.is_(None))
                .group_by(NmIncidentProduct.id_incident)
            ).all():
                pendientes[int(id_vale)] = int(abiertos or 0)
                renglones[int(id_vale)] = int(todos or 0)

        nombres = {}
        ids_usuarios = {int(v.id_user) for v in vales if v.id_user}
        if ids_usuarios:
            nombres = dict(db.execute(
                select(User.id_user, User.full_name)
                .where(User.id_user.in_(list(ids_usuarios)))
            ).all())

        items = []
        for vale in vales:
            fila = vale.serialize()
            fila.update({
                # El folio con el que la gente lo conoce; si no lo trae, su id.
                "folio": vale.external_folio or str(vale.id_incident),
                "holder_name": nombres.get(int(vale.id_user)) if vale.id_user else None,
                "open_lines": pendientes.get(int(vale.id_incident), 0),
                "total_lines": renglones.get(int(vale.id_incident), 0),
            })
            items.append(fila)

        return {
            "items": items,
            "total": total,
            "page": numero,
            "per_page": tamano,
            "pages": paginas,
            "scoped_to_actor": not _ve_todo_el_almacen(db, user_data),
        }


# --- los 4 reportes que ya usaba Adser en el sistema anterior ------------
#
# El sistema anterior (adser-almacen.torredigital.mx) ya tenia estos 4
# reportes; aqui se replican sobre `nm_incident_product` + `incident`, que es
# donde vive el mismo dato en este sistema. Los cuatro comparten renglon y
# columnas (codigo, descripcion, estado, solicitante, fecha de creacion, fecha
# de cierre) -- solo cambia el criterio de agrupacion, salvo el de pendientes,
# que es una lista plana a proposito.
#
# El sentinela heredado
# ----------------------
# `close_date` en los vales migrados de Adser NO es NULL cuando un renglon
# sigue abierto: es `1990-01-01`, el mismo sentinela que
# `migrate_adser.py` SI limpio en `product.fecha_baja` (via
# `normalizar_fecha()`, en `migration_toolkit.py`) pero que se le olvido pasar
# a `migrar_incident`/`migrar_nm_incident_product`. Se lee bien aqui -- NULL o
# el sentinela cuentan igual como "sin cerrar" -- sin tocar el dato ni el resto
# del modulo (`vales_vencidos`, `_estado_derivado`, etc. siguen comparando solo
# contra NULL; ese es un problema aparte, ya en produccion, que no se corrige
# en esta tarea).
CIERRE_SENTINELA = datetime(1990, 1, 1)


def _sin_cerrar(fecha_cierre) -> bool:
    return fecha_cierre is None or fecha_cierre == CIERRE_SENTINELA


def _rango_de_fechas(fecha_inicio, fecha_fin):
    inicio = _fecha(fecha_inicio) if fecha_inicio else None
    fin = _fecha(fecha_fin) if fecha_fin else None
    return (inicio.date() if inicio else None, fin.date() if fin else None)


def _estado_del_renglon(direction, tipo_descripcion) -> str:
    """Danado/Destruccion pisan a Entrada/Salida cuando el VALE es de ese
    tipo: ahi lo que importa no es si el material entro o salio, es lo que le
    paso. El catalogo real trae "Destruccion" y "Dañado" (`incident_type`,
    ids 8 y 9 en lo migrado de Adser) -- se usa la descripcion tal como esta
    en la base, no una constante propia, para no desincronizarse del catalogo.
    """
    especial = str(tipo_descripcion or "").strip().lower()
    if especial in ("destruccion", "dañado"):
        return str(tipo_descripcion).strip()
    return "Entrada" if str(direction or "").lower() == ENTRADA else "Salida"


def _renglones_de_reporte(db, *, fecha_inicio=None, fecha_fin=None, id_user=None,
                          solo_salidas_abiertas=False, user_data=None) -> list[dict]:
    """Los renglones de vale con las 6 columnas de los 4 reportes, en una sola
    consulta -- el patron de todo este archivo, y no una por renglon: esto lee
    sobre lo migrado de Adser, ~2 787 renglones.

    El "proyecto/almacen" de un vale no sale de `incident.id_proyect` ni de
    `nm_incident_product.id_location_*` -- estan en NULL en el 100% de lo
    migrado de Adser, verificado contra la base real. Vive en `incident.note`,
    texto libre ("ALUMINIUM-EXPANCION DE NAVE", "APELSA") capturado al abrir
    el vale en el sistema anterior. Se agrupa por ese texto recortado
    (`strip()`), sin tocar mayusculas ni ortografia: es la normalizacion
    minima que no fusiona ni separa de mas.
    """
    consulta = (
        select(NmIncidentProduct, Incident, Product, IncidentType, User)
        .select_from(NmIncidentProduct)
        .join(Incident, Incident.id_incident == NmIncidentProduct.id_incident)
        .join(Product, Product.id_product == NmIncidentProduct.id_product)
        .outerjoin(IncidentType,
                   IncidentType.id_incident_type == Incident.id_incident_type)
        .outerjoin(User, User.id_user == Incident.id_user)
        .where(
            NmIncidentProduct.deletion_date.is_(None),
            Incident.deletion_date.is_(None),
        )
    )

    inicio, fin = _rango_de_fechas(fecha_inicio, fecha_fin)
    fecha_col = func.date(Incident.incident_date)
    if inicio is not None:
        consulta = consulta.where(fecha_col >= inicio)
    if fin is not None:
        consulta = consulta.where(fecha_col <= fin)

    # El alcance es el mismo que el resto del modulo: quien opera el almacen
    # ve todo; quien solo pide material ve lo suyo (ver `_ve_todo_el_almacen`).
    pedido = _entero(id_user, "id_user", obligatorio=False)
    if user_data is not None and not _ve_todo_el_almacen(db, user_data):
        pedido = _actor(user_data)
    if pedido is not None:
        consulta = consulta.where(Incident.id_user == pedido)

    if solo_salidas_abiertas:
        consulta = consulta.where(
            NmIncidentProduct.direction == SALIDA,
            or_(NmIncidentProduct.close_date.is_(None),
                NmIncidentProduct.close_date == CIERRE_SENTINELA),
        )

    filas = db.execute(
        consulta.order_by(Incident.incident_date,
                          NmIncidentProduct.id_nm_incident_product)
    ).all()

    salida = []
    for renglon, vale, producto, tipo, usuario in filas:
        salida.append({
            "id_nm_incident_product": renglon.id_nm_incident_product,
            "id_incident": vale.id_incident,
            "folio": vale.external_folio or str(vale.id_incident),
            "product_code": producto.product_code,
            "product_description": producto.descripcion,
            "status": _estado_del_renglon(
                renglon.direction,
                getattr(tipo, "incident_type_description", None)),
            "requester": getattr(usuario, "full_name", None),
            "id_user": vale.id_user,
            "project_or_site": (vale.note or "").strip() or None,
            "creation_date": (vale.incident_date.isoformat()
                              if vale.incident_date else None),
            "close_date": (None if _sin_cerrar(renglon.close_date)
                          else renglon.close_date.isoformat()),
        })
    return salida


def _agrupar(renglones, clave, *, sin_grupo):
    """Los renglones agrupados por `clave`, en el orden en que aparece cada
    grupo por primera vez -- no alfabetico: es el mismo orden cronologico de
    la consulta (`incident_date`), que es como se lee un reporte de almacen.
    """
    grupos: dict = {}
    orden = []
    for renglon in renglones:
        llave = clave(renglon) or sin_grupo
        if llave not in grupos:
            grupos[llave] = []
            orden.append(llave)
        grupos[llave].append(renglon)
    return [{"group": llave, "items": grupos[llave], "total": len(grupos[llave])}
            for llave in orden]


def reporte_por_producto(user_data, *, fecha_inicio=None, fecha_fin=None,
                         id_user=None) -> dict:
    """a) Vales agrupados por codigo de producto."""
    _actor(user_data)
    with transaction_context() as db:
        renglones = _renglones_de_reporte(
            db, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
            id_user=id_user, user_data=user_data)
    grupos = _agrupar(renglones, lambda r: r["product_code"],
                      sin_grupo="(sin codigo)")
    return {"groups": grupos, "total_items": len(renglones)}


def reporte_por_almacen(user_data, *, fecha_inicio=None, fecha_fin=None,
                        id_user=None) -> dict:
    """b) Vales agrupados por proyecto/sitio (`incident.note` recortado --
    ver el docstring de `_renglones_de_reporte` para por que ahi y no en
    `id_proyect` ni en `location`)."""
    _actor(user_data)
    with transaction_context() as db:
        renglones = _renglones_de_reporte(
            db, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
            id_user=id_user, user_data=user_data)
    grupos = _agrupar(renglones, lambda r: r["project_or_site"],
                      sin_grupo="(sin proyecto)")
    return {"groups": grupos, "total_items": len(renglones)}


def reporte_por_persona(user_data, *, fecha_inicio=None, fecha_fin=None,
                        id_user=None) -> dict:
    """d) Vales agrupados por solicitante/responsable."""
    _actor(user_data)
    with transaction_context() as db:
        renglones = _renglones_de_reporte(
            db, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
            id_user=id_user, user_data=user_data)
    grupos = _agrupar(renglones, lambda r: r["requester"],
                      sin_grupo="(sin responsable)")
    return {"groups": grupos, "total_items": len(renglones)}


def reporte_vales_pendientes(user_data, *, fecha_inicio=None, fecha_fin=None,
                             id_user=None) -> dict:
    """c) Lista plana de renglones de SALIDA sin cerrar -- NULL o el
    sentinela heredado (ver CIERRE_SENTINELA). A proposito sin agrupar: es
    la lista de "huecos" que se revisa de corrido, no un resumen."""
    _actor(user_data)
    with transaction_context() as db:
        renglones = _renglones_de_reporte(
            db, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
            id_user=id_user, solo_salidas_abiertas=True, user_data=user_data)
    return {"items": renglones, "total": len(renglones)}


# --- el vale en papel ----------------------------------------------------

def _persona(db, id_user):
    """El nombre de quien firma, o None.

    Un vale impreso sin nombres no sirve para lo unico que se imprime: que
    alguien lo firme y quede constancia de quien se llevo que.
    """
    if not id_user:
        return None
    return db.scalars(
        select(User.full_name).where(User.id_user == int(id_user))
    ).first()


def folio_del_vale(id_incident, user_data: dict) -> str:
    """El numero con el que la gente conoce el vale.

    El del sistema anterior cuando lo trae, y el id interno cuando no. Es el
    mismo criterio que usan la lista, la pantalla del vale y el propio PDF: un
    vale que en pantalla es el 95 no puede descargarse como "Vale-513.pdf".
    """
    _actor(user_data)
    with transaction_context() as db:
        vale = _vale(db, id_incident)
        return str(vale.external_folio or vale.id_incident)


def documento_del_vale(id_incident, user_data: dict) -> dict:
    """Arma la ficha que la plantilla del PDF pinta.

    Reusa `consultar_vale` en lugar de volver a consultar: el PDF tiene que
    decir exactamente lo que la pantalla muestra. Si fueran dos consultas
    distintas acabarian discrepando, y un papel firmado que no coincide con el
    sistema es peor que no tener papel.

    Lo unico que agrega son los NOMBRES -- de quien se lo llevo, de quien lo
    capturo y de las ubicaciones -- porque en pantalla se ven al pasar el raton
    y en papel no hay raton.
    """
    datos = consultar_vale(id_incident, user_data)
    vale = datos["voucher"]

    with transaction_context() as db:
        ubicaciones = {}
        ids_ubicacion = {
            int(v) for renglon in datos["lines"]
            for v in (renglon.get("id_location_from"), renglon.get("id_location_to"))
            if v
        }
        if ids_ubicacion:
            ubicaciones = dict(db.execute(
                select(Location.id_location, Location.location_description)
                .where(Location.id_location.in_(list(ids_ubicacion)))
            ).all())

        responsable = _persona(db, vale.get("id_user"))
        capturo = _persona(db, vale.get("created_by"))
        tipo = db.scalars(
            select(IncidentType.incident_type_description)
            .where(IncidentType.id_incident_type == vale.get("id_incident_type"))
        ).first()

    salidas, entradas = [], []
    for renglon in datos["lines"]:
        producto = renglon.get("product") or {}
        fila = {
            "cantidad": renglon.get("quantity"),
            "codigo": producto.get("code") or None,
            "descripcion": producto.get("descripcion") or "Producto %s" % renglon.get("id_product"),
            "material": producto.get("material"),
            "marca": producto.get("brand"),
            "unidad": producto.get("unit"),
            "desde": ubicaciones.get(renglon.get("id_location_from")),
            "hasta": ubicaciones.get(renglon.get("id_location_to")),
            "nota": renglon.get("note"),
            "vence": _solo_fecha(renglon.get("due_date")),
            "cerrado": _solo_fecha(renglon.get("close_date")),
            # Devuelto o no: es la unica pregunta que alguien le hace a un vale
            # viejo, asi que va en su propia columna y no escondida en la fecha.
            "devuelto": renglon.get("close_date") is not None,
        }
        (entradas if str(renglon.get("direction") or "") == ENTRADA else salidas).append(fila)

    return {
        "folio": vale.get("external_folio") or str(vale.get("id_incident")),
        "id_incident": vale.get("id_incident"),
        "fecha": _solo_fecha(vale.get("incident_date")),
        "estado": vale.get("incident_status"),
        "tipo": tipo,
        "nota": vale.get("note"),
        "responsable": responsable,
        "capturo": capturo,
        "cierre": _solo_fecha(vale.get("close_date")),
        "salidas": salidas,
        "entradas": entradas,
        "pendientes": datos["open_lines"],
        # Un vale en borrador no ha sacado nada del almacen todavia. El papel lo
        # dice en grande para que nadie lo confunda con uno autorizado.
        "es_borrador": vale.get("incident_status") == BORRADOR,
    }


def _solo_fecha(valor):
    if not valor:
        return None
    return str(valor)[:10]


def _motor_de_documentos():
    """El renderizador de PDFs, con su paquete en la ruta.

    El paquete `documents` vive fuera de `backend/` -- se monta aparte -- y hasta
    ahora entraba en `sys.path` como efecto secundario de registrar su blueprint
    al crear la aplicacion. Eso hacia que importarlo funcionara o no segun que
    hubiera pasado antes: una tarea de Celery o un script fallaban con
    `ModuleNotFoundError` mientras la misma llamada desde una peticion HTTP
    funcionaba.
    """
    import os
    import sys

    ruta = os.getenv("DOCUMENTS_REPORTS_APP_PATH", "/documents-reports/app")
    if ruta not in sys.path:
        sys.path.insert(0, ruta)
    try:
        from documents.service import DocumentService
    except ImportError as fallo:
        raise AppError("errors.pdf_renderer_unavailable", 503,
                       {"reason": str(fallo)}) from fallo
    return DocumentService(
        os.getenv("DOCUMENTS_TEMPLATES_DIR", "/documents-reports/templates"))


def _expediente_del_vale(db, vale, actor_id: int):
    """El `document` donde se archivan las versiones de este vale.

    Uno por vale, no uno por descarga: las versiones cuelgan de el. Se vincula
    por `business_reference_type`/`business_reference_value`, el puntero
    generico de la tabla -- `document_relation` no tiene columna para
    incidencias y agregarsela seria cambiar el esquema por un caso.
    """
    from app.models.document import Document, DocumentCategory

    categoria = db.scalars(
        select(DocumentCategory).where(
            DocumentCategory.code == "warehouse_voucher",
            DocumentCategory.deletion_date.is_(None),
        )
    ).first()
    if categoria is None:
        raise AppError("documents.category_not_configured", 500,
                       {"code": "warehouse_voucher"})

    expediente = db.scalars(
        select(Document).where(
            Document.business_reference_type == "incident",
            Document.business_reference_value == str(vale.id_incident),
            Document.id_document_category == categoria.id_document_category,
            Document.deletion_date.is_(None),
        ).with_for_update()
    ).first()
    if expediente is not None:
        return expediente

    # `document.id_proyect` es obligatorio y el vale no lo lleva: `incident` no
    # tiene proyecto. Se toma el del usuario responsable, que es de quien es el
    # vale; si no lo tuviera, el del actor.
    id_proyect = db.scalars(
        select(User.id_proyect).where(User.id_user == vale.id_user)
    ).first() or db.scalars(
        select(User.id_proyect).where(User.id_user == actor_id)
    ).first()
    if not id_proyect:
        raise AppError("errors.resource_scope_missing", 409, {"entity": "proyect"})

    expediente = Document(
        id_proyect=int(id_proyect),
        id_document_category=categoria.id_document_category,
        title="Vale de almacen %s" % (vale.external_folio or vale.id_incident),
        status="issued",
        business_reference_type="incident",
        business_reference_value=str(vale.id_incident),
        issue_date=(vale.incident_date.date() if vale.incident_date else None),
        created_by=actor_id,
    )
    db.add(expediente)
    db.flush()
    return expediente


def pdf_del_vale(id_incident, user_data: dict, *, storage=None) -> bytes:
    """El vale en PDF, archivado para tenerlo a la mano siempre.

    Que hace distinto a generarlo al vuelo
    --------------------------------------
    Guarda cada PDF como una version de un `document`, el mismo mecanismo del
    reporte de laboratorio. Eso trae el sha256, el tamano, el historial y que el
    vale aparezca en el modulo de Documentos como cualquier otro papel -- sin
    inventar una carpeta ni una columna.

    Cuando NO se vuelve a generar
    -----------------------------
    Si el CONTENIDO del vale es identico al de la ultima version archivada, se
    devuelve esa misma. No es solo por ahorrar trabajo: un vale CAMBIA -- los
    renglones se devuelven uno a uno y el estado pasa a cerrado --, asi que
    regenerar en cada descarga entrega un papel distinto cada vez y ninguno
    coincide con el que alguien firmo. Archivar por version deja ver que decia el
    del dia de la entrega y que dice el de hoy.

    Se compara el contenido y NO la fecha de modificacion del vale, que fue el
    primer intento: los 141 vales que vinieron del sistema anterior tienen
    `creation_date` y `last_update_date` NULAS, asi que sin fecha con que
    comparar se archivaba una version nueva en cada descarga -- justo de los
    vales mas viejos, que son los que mas se consultan. Comparar el contenido
    ademas detecta un cambio que no haya tocado la fecha.

    Si no hay almacenamiento se genera sin archivar: preferible un PDF sin
    historial que ninguno.
    """
    import hashlib
    import json

    from app.models.document import DocumentVersion

    actor_id = _actor(user_data)

    if storage is None:
        return _motor_de_documentos().render_pdf_bytes(
            "warehouse_voucher", documento_del_vale(id_incident, user_data))

    # La ficha es determinista: sale solo de los datos del vale, sin fechas de
    # generacion. Por eso sirve para decidir si algo cambio.
    ficha = documento_del_vale(id_incident, user_data)
    huella = json.dumps(ficha, sort_keys=True, default=str)

    with transaction_context() as db:
        vale = _vale(db, id_incident)
        expediente = _expediente_del_vale(db, vale, actor_id)
        ultima = db.scalars(
            select(DocumentVersion).where(
                DocumentVersion.id_document == expediente.id_document,
                DocumentVersion.deletion_date.is_(None),
            ).order_by(DocumentVersion.version.desc())
        ).first()
        id_expediente = expediente.id_document
        id_proyect = expediente.id_proyect
        siguiente = (ultima.version if ultima else 0) + 1
        vigente = (ultima is not None and ultima.source_snapshot is not None
                   and json.dumps(ultima.source_snapshot, sort_keys=True,
                                  default=str) == huella)
        ruta_vigente = ultima.file_path if vigente else None

    if ruta_vigente:
        try:
            return storage.resolve(ruta_vigente).read_bytes()
        except AppError:
            # El archivo se perdio -- volumen nuevo, limpieza -- pero la fila
            # sigue. Se regenera en vez de fallar: el vale se puede reconstruir
            # entero desde la base.
            pass

    pdf = _motor_de_documentos().render_pdf_bytes("warehouse_voucher", ficha)

    ruta = storage.write(pdf, id_proyect, id_expediente, siguiente, "pdf")
    with transaction_context() as db:
        db.add(DocumentVersion(
            id_document=id_expediente,
            version=siguiente,
            file_path=ruta,
            original_filename="Vale-%s-v%s.pdf" % (ficha["folio"], siguiente),
            extension="pdf",
            mime_type="application/pdf",
            file_size=len(pdf),
            sha256=hashlib.sha256(pdf).hexdigest(),
            source="generated",
            status="issued",
            # La ficha completa queda guardada con la version: permite ver que
            # decia el vale sin volver a abrir el PDF, y sobrevive aunque el
            # archivo se pierda.
            source_snapshot=ficha,
            generated_by=actor_id,
        ))
    return pdf
