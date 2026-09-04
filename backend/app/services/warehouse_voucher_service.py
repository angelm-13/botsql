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

    direccion = _texto(carga.get("direction"), "direction", largo=20,
                       obligatorio=True).lower()
    if direccion not in DIRECCIONES:
        raise AppError("errors.invalid_field", 400,
                       {"field": "direction", "allowed": list(DIRECCIONES)})

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

    # El traslado exige destino: sin el no es un traslado, es una salida sin
    # registrar. Lo mismo lo garantiza un CHECK en la base.
    destino = ubicacion("id_location_to", direccion == TRASLADO)
    origen = ubicacion("id_location_from", False)

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

        validados = [_validar_renglon(db, linea) for linea in renglones]

        inicio = _ahora()
        vale = Incident(
            id_incident_type=id_tipo,
            id_user=id_responsable,
            incident_date=inicio,
            incident_status=ABIERTO,
            note=_texto(payload.get("note"), "note", largo=300),
            created_by=actor,
        )
        db.add(vale)
        db.flush()

        vence = payload.get("due_date")
        for datos in validados:
            db.add(NmIncidentProduct(
                id_incident=vale.id_incident,
                start_date=inicio,
                due_date=_fecha(vence) if vence else None,
                created_by=actor,
                **datos,
            ))
        db.flush()

        return {
            "voucher": vale.serialize(),
            "lines": [r.serialize() for r in _renglones(db, vale.id_incident)],
        }


def cerrar_renglon(id_line, payload: dict, user_data: dict) -> dict:
    """Cierra un renglon y actualiza el estado del vale.

    Cerrar el ultimo renglon cierra el vale. Es el unico camino: el estado del
    vale no se puede capturar a mano, justo para que no exista un vale
    "terminado" con herramienta todavia fuera.
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
        if renglon.close_date is not None:
            raise AppError("errors.voucher_line_already_closed", 409,
                           {"id_nm_incident_product": renglon.id_nm_incident_product,
                            "close_date": renglon.close_date.isoformat()})

        renglon.close_date = _ahora()
        nota = _texto(payload.get("note"), "note", largo=300)
        if nota:
            renglon.note = nota
        db.flush()

        vale = _vale(db, renglon.id_incident, para_actualizar=True)
        _sincronizar_estado(db, vale)

        return {
            "line": renglon.serialize(),
            "voucher": vale.serialize(),
            "closed_the_voucher": str(vale.incident_status or "") == CERRADO,
            "actor": actor,
        }


def consultar_vale(id_incident, user_data: dict) -> dict:
    """El vale con sus renglones y el estado derivado."""
    _actor(user_data)
    with transaction_context() as db:
        vale = _vale(db, id_incident)
        renglones = _renglones(db, vale.id_incident)
        abiertos = [r for r in renglones if r.close_date is None]
        return {
            "voucher": vale.serialize(),
            "lines": [r.serialize() for r in renglones],
            "open_lines": len(abiertos),
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
        return {"items": [r.serialize() for r in filas], "total": len(filas)}


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
