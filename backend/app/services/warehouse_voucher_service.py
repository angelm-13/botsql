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

from sqlalchemy import func, select

from app.models.incident import Incident
from app.models.incident_type import IncidentType
from app.models.inventory_asset import InventoryAsset
from app.models.location import Location
from app.models.nm_incident_product import NmIncidentProduct
from app.models.product import Product
from app.models.session import transaction_context
from app.models.inventory_asset_event import DEVOLUCION, PRESTAMO
from app.models.inventory_stock import InventoryStock
from app.models.user import User
from app.services.inventory_asset_service import (
    DISPONIBLE, PRESTADA, transicion_en_sesion,
)
from app.services.inventory_service import apply_movement_in_session
from app.utils.errors import AppError


# Que le pasa a la existencia con este renglon.
SALIDA = "salida"
ENTRADA = "entrada"
TRASLADO = "traslado"
DIRECCIONES = (SALIDA, ENTRADA, TRASLADO)

# Estados del vale. Se derivan de los renglones, no se capturan.
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
    """Los renglones serializados, cada uno con la existencia de su producto."""
    saldos = _existencias(db, {int(r.id_product) for r in renglones})
    salida = []
    for renglon in renglones:
        fila = renglon.serialize()
        fila["stock_on_hand"] = saldos.get(int(renglon.id_product), 0)
        salida.append(fila)
    return salida


def _vale(db, id_incident, *, para_actualizar=False) -> Incident:
    consulta = select(Incident).where(
        Incident.id_incident == _entero(id_incident, "id_incident"),
        Incident.deletion_date.is_(None),
    )
    if para_actualizar:
        consulta = consulta.with_for_update()
    vale = db.scalars(consulta).first()
    if vale is None:
        raise AppError("errors.not_found", 404, {"entity": "incident"})
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

def crear_vale(payload: dict, user_data: dict) -> dict:
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

        validados = [_validar_renglon(db, linea) for linea in renglones]

        inicio = _ahora()
        vence = _fecha_de_regreso(payload.get("due_date"))
        motivo = _texto(payload.get("note"), "note", largo=300, obligatorio=True)

        vale = Incident(
            id_incident_type=id_tipo,
            id_user=id_responsable,
            incident_date=inicio,
            incident_status=ABIERTO,
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
        return {
            "voucher": vale.serialize(),
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
