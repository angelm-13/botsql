"""Rastreo de piezas una por una: herramienta, equipo, activo de uso.

Que resuelve
------------
El inventario por cantidades no puede contestar donde esta el taladro A-014 ni
quien se lo llevo, porque un saldo es un numero. Aqui cada pieza tiene identidad,
estado y responsable, y cada cambio queda en su historia.

Dos reglas que sostienen todo lo demas
--------------------------------------
1. **El saldo y las piezas no se pueden separar.** Una pieza disponible en su
   ubicacion cuenta en `inventory_stock` igual que un insumo, y cada cambio de
   estado que la saca o la devuelve escribe su movimiento en el libro por la
   misma puerta que usa el resto del sistema
   (`inventory_service.apply_movement_in_session`). No hay un segundo camino que
   toque existencias: si lo hubiera, las dos vistas empezarian a discrepar y
   nadie sabria cual creer.

2. **La historia no se corrige, se continua.** `inventory_asset_event` es de
   solo agregado. Un dato equivocado se arregla con otro evento que dice lo que
   paso, no editando el anterior.

Sobre los prestamos
-------------------
El tipo de movimiento `loan` ya existia y descontaba existencia sin registrar a
quien: el prestamo se veia como una resta. Ahora un prestamo exige responsable y
fecha de regreso, y hay una consulta de vencidos, porque un prestamo sin fecha
es una baja disfrazada.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select

from app.models.inventory_asset import (
    DISPONIBLE, EN_REPARACION, EN_USO, ESTADOS, ESTADOS_EN_EXISTENCIA,
    ESTADOS_TERMINALES, EXTRAVIADA, InventoryAsset, PRESTADA, RETIRADA,
)
from app.models.inventory_asset_event import (
    ALTA, ASIGNACION, BAJA, DEVOLUCION, ENVIO_REPARACION, EXTRAVIO,
    InventoryAssetEvent, PRESTAMO, REGRESO_REPARACION, TRASLADO,
)
from app.models.product import Product
from app.models.session import transaction_context
from app.models.user import User
from app.services.inventory_service import (
    ADJUSTMENT_CAPABILITY, apply_movement_in_session, has_capability,
)
from app.utils.errors import AppError


# Modo de rastreo de un producto. `fungible` es el valor por omision y mantiene
# el comportamiento que el sistema ya tenia.
FUNGIBLE = "fungible"
SERIALIZADO = "serializado"
MODOS = (FUNGIBLE, SERIALIZADO)


# Transiciones permitidas. Se declara lo que si se puede en lugar de validar
# caso por caso, porque asi la regla se lee de un vistazo y agregar un estado
# obliga a decidir desde donde se llega a el.
TRANSICIONES = {
    DISPONIBLE: {EN_USO, PRESTADA, EN_REPARACION, EXTRAVIADA, RETIRADA},
    EN_USO: {DISPONIBLE, PRESTADA, EN_REPARACION, EXTRAVIADA, RETIRADA},
    PRESTADA: {DISPONIBLE, EN_REPARACION, EXTRAVIADA},
    EN_REPARACION: {DISPONIBLE, EXTRAVIADA, RETIRADA},
    EXTRAVIADA: {DISPONIBLE, RETIRADA},
    RETIRADA: set(),
}

# Que movimiento de existencia provoca cada evento. None significa que el saldo
# no se mueve: una asignacion interna o un traslado no cambian cuantas piezas
# tiene la empresa.
#
# El signo lo pone `inventory_service`; aqui solo se nombra el tipo, para que
# los movimientos de una pieza aparezcan en el libro con el mismo vocabulario
# que los de un insumo.
MOVIMIENTO_POR_EVENTO = {
    ALTA: "receive",
    PRESTAMO: "loan",
    DEVOLUCION: "return",
    ENVIO_REPARACION: "issue",
    REGRESO_REPARACION: "receive",
    EXTRAVIO: "loss",
    BAJA: "destroy",
    ASIGNACION: None,
    TRASLADO: None,
}

# Eventos que exigen un motivo escrito. Son los que cambian el saldo sin un
# documento detras: sin motivo, el descuadre no se puede auditar despues.
MOTIVO_OBLIGATORIO = frozenset({EXTRAVIO, BAJA, ENVIO_REPARACION})

# Dar de baja o declarar extraviada una pieza destruye existencia sin documento
# y por cualquier cantidad, igual que un ajuste. Se pide la misma capacidad, que
# es la que separa a quien mueve la mercancia de quien puede tapar un faltante.
CAPACIDAD_PARA_MERMA = ADJUSTMENT_CAPABILITY


def _hoy() -> date:
    # La fecha del servidor, no UTC: un vencimiento es un dia del calendario de
    # quien opera el almacen, y forzar UTC lo adelanta hasta 6 horas (la
    # diferencia con Mexico) antes de la medianoche real. Mismo criterio que
    # `inventory_lot_service.py` ya usa para vencimientos de lote.
    return date.today()


def _texto(valor, campo, *, largo=300, obligatorio=False):
    limpio = str(valor or "").strip()
    if not limpio:
        if obligatorio:
            raise AppError("errors.required_field", 400, {"field": campo})
        return None
    return limpio[:largo]


def _entero(valor, campo, *, obligatorio=False):
    if valor in (None, ""):
        if obligatorio:
            raise AppError("errors.required_field", 400, {"field": campo})
        return None
    try:
        return int(valor)
    except (TypeError, ValueError) as error:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from error


def _dinero(valor, campo):
    """Convierte un importe a Decimal.

    Se convierte aqui y no se deja pasar tal cual porque el valor llega del
    cuerpo de la peticion como cadena, y guardarlo sin convertir dejaba una
    cadena en un campo numerico: el modelo no reventaba al asignar, sino al
    serializar, lejos del origen. Se usa Decimal y no float porque es dinero.
    """
    if valor in (None, ""):
        return None
    try:
        importe = Decimal(str(valor))
    except (InvalidOperation, ValueError) as error:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from error
    if importe < 0:
        raise AppError("errors.invalid_field", 400, {"field": campo})
    return importe.quantize(Decimal("0.01"))


def _fecha(valor, campo):
    if valor in (None, ""):
        return None
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError as error:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from error


def _producto(db, id_product, user_data):
    """Carga el producto y comprueba el alcance con la regla del inventario."""
    from app.services.inventory_service import _authorize

    producto = db.get(Product, _entero(id_product, "id_product", obligatorio=True))
    if not producto or producto.deletion_date is not None:
        raise AppError("errors.not_found", 404, {"entity": "product"})
    _authorize(db, producto, user_data)
    return producto


def _pieza(db, id_asset, user_data, *, para_escribir=False):
    consulta = select(InventoryAsset).where(
        InventoryAsset.id_inventory_asset == _entero(id_asset, "id_inventory_asset", obligatorio=True),
        InventoryAsset.deletion_date.is_(None),
    )
    if para_escribir:
        # Se bloquea la fila: dos personas prestando la misma herramienta a la
        # vez terminarian con dos responsables y un solo taladro.
        consulta = consulta.with_for_update()
    pieza = db.scalars(consulta).first()
    if not pieza:
        raise AppError("errors.not_found", 404, {"entity": "inventory_asset"})
    _producto(db, pieza.id_product, user_data)
    return pieza


def _requiere_serializado(producto):
    if str(getattr(producto, "tracking_mode", FUNGIBLE) or FUNGIBLE) != SERIALIZADO:
        raise AppError(
            "errors.inventory_product_is_not_serialized",
            409,
            {"id_product": producto.id_product, "tracking_mode": FUNGIBLE},
        )


def _validar_transicion(pieza, destino):
    if destino not in ESTADOS:
        raise AppError("errors.invalid_field", 400, {"field": "status", "allowed": list(ESTADOS)})
    if pieza.status in ESTADOS_TERMINALES:
        raise AppError(
            "errors.inventory_asset_is_retired",
            409,
            {"asset_tag": pieza.asset_tag, "status": pieza.status},
        )
    if destino not in TRANSICIONES.get(pieza.status, set()):
        raise AppError(
            "errors.inventory_asset_transition_not_allowed",
            409,
            {
                "asset_tag": pieza.asset_tag,
                "from": pieza.status,
                "to": destino,
                "allowed": sorted(TRANSICIONES.get(pieza.status, set())),
            },
        )


def _mover_existencia(db, pieza, evento, user_data, *, id_location, reason, referencia):
    """Escribe el movimiento de existencia que corresponde al evento.

    Devuelve el renglon del libro, o None si el evento no mueve el saldo.
    """
    tipo = MOVIMIENTO_POR_EVENTO.get(evento)
    if tipo is None or id_location is None:
        return None

    # Una pieza es una unidad: nunca media herramienta.
    signo = 1 if evento in (ALTA, DEVOLUCION, REGRESO_REPARACION) else -1
    movimiento, _ = apply_movement_in_session(
        db,
        pieza.id_product,
        user_data,
        movement_type=tipo,
        quantity_delta=signo,
        # La llave amarra el movimiento al evento de la pieza: repetir la misma
        # operacion no descuenta dos veces.
        idempotency_key=f"asset-{pieza.id_inventory_asset}-{evento}-{referencia}",
        id_location=id_location,
        reference_type="inventory_asset",
        reference_id=str(pieza.id_inventory_asset),
        reason=reason or f"{evento} de la pieza {pieza.asset_tag}",
    )
    return movimiento


def _asentar(db, pieza, evento, *, antes, user_data, ledger=None, reason=None,
             referencia_tipo=None, referencia_id=None):
    """Escribe el evento en la historia de la pieza."""
    registro = InventoryAssetEvent(
        id_inventory_asset=pieza.id_inventory_asset,
        event_type=evento,
        status_before=antes["status"],
        status_after=pieza.status,
        id_location_before=antes["id_location"],
        id_location_after=pieza.id_location,
        id_holder_before=antes["id_holder"],
        id_holder_after=pieza.id_holder,
        due_date=pieza.due_date,
        id_inventory_ledger=(ledger or {}).get("id_inventory_ledger") if ledger else None,
        reference_type=referencia_tipo,
        reference_id=str(referencia_id)[:100] if referencia_id else None,
        reason=reason,
        created_by=int(user_data.get("id_user") or 0),
    )
    db.add(registro)
    db.flush()
    return registro


def _foto(pieza) -> dict:
    return {
        "status": pieza.status,
        "id_location": pieza.id_location,
        "id_holder": pieza.id_holder,
    }


# --- alta ----------------------------------------------------------------

def register_asset(payload, user_data) -> dict:
    """Da de alta una pieza rastreable y la deja disponible en su ubicacion."""
    payload = payload or {}
    with transaction_context() as db:
        producto = _producto(db, payload.get("id_product"), user_data)
        _requiere_serializado(producto)

        etiqueta = _texto(payload.get("asset_tag"), "asset_tag", largo=40, obligatorio=True)
        ya_existe = db.scalars(
            select(InventoryAsset).where(InventoryAsset.asset_tag == etiqueta)
        ).first()
        if ya_existe:
            # No se reutiliza la etiqueta ni se sobreescribe la pieza: dos
            # herramientas con la misma etiqueta vuelven inutil el rastreo.
            raise AppError(
                "errors.inventory_asset_tag_already_used",
                409,
                {"asset_tag": etiqueta, "id_inventory_asset": ya_existe.id_inventory_asset},
            )

        id_location = _entero(payload.get("id_location"), "id_location") or producto.id_location
        if not id_location:
            raise AppError("errors.required_field", 400, {"field": "id_location"})

        pieza = InventoryAsset(
            id_product=producto.id_product,
            asset_tag=etiqueta,
            serial_number=_texto(payload.get("serial_number"), "serial_number", largo=120),
            id_location=id_location,
            status=DISPONIBLE,
            acquired_on=_fecha(payload.get("acquired_on"), "acquired_on") or _hoy(),
            acquisition_cost=_dinero(payload.get("acquisition_cost"), "acquisition_cost"),
            note=_texto(payload.get("note"), "note"),
            created_by=int(user_data.get("id_user") or 0),
        )
        db.add(pieza)
        db.flush()

        antes = {"status": None, "id_location": None, "id_holder": None}
        ledger = _mover_existencia(
            db, pieza, ALTA, user_data,
            id_location=id_location,
            reason=_texto(payload.get("reason"), "reason") or f"Alta de la pieza {etiqueta}",
            referencia=pieza.id_inventory_asset,
        )
        evento = _asentar(
            db, pieza, ALTA, antes=antes, user_data=user_data, ledger=ledger,
            reason=_texto(payload.get("reason"), "reason"),
            referencia_tipo=_texto(payload.get("reference_type"), "reference_type", largo=50),
            referencia_id=payload.get("reference_id"),
        )
        return {"asset": pieza.serialize(), "event": evento.serialize()}


def _responsable(db, valor):
    """El usuario que se lleva la pieza, comprobado contra la tabla.

    Antes esto era `_entero(..., obligatorio=True)` y nada mas: un prestamo a
    `id_holder = 9999` se guardaba tal cual y la pieza quedaba PRESTADA a nadie
    -no sale en lo que debe ningun usuario, no se le puede reclamar, y el unico
    modo de notarla es ver que falta-.

    La base ya lo impide desde la llave ajena, pero una llave ajena diferida
    revienta en el COMMIT con un IntegrityError, que llega al usuario como un
    500. Esto lo convierte en el 404 que le corresponde, diciendo cual campo.
    """
    id_usuario = _entero(valor, "id_holder", obligatorio=True)
    existe = db.scalars(
        select(User.id_user).where(
            User.id_user == id_usuario,
            User.deletion_date.is_(None),
        ).limit(1)
    ).first()
    if existe is None:
        # Un usuario dado de baja tampoco sirve: la pieza quedaria a nombre de
        # alguien que ya no esta para devolverla.
        raise AppError("errors.not_found", 404,
                       {"entity": "user", "field": "id_holder"})
    return id_usuario


# --- movimientos de la pieza --------------------------------------------

def transicion_en_sesion(db, id_asset, payload, user_data, *, evento, destino,
                         exige_responsable=False, exige_fecha=False,
                         libera_responsable=False, vuelve_a_ubicacion=False):
    """Una transicion de pieza dentro de una transaccion que abre el llamador.

    Existe aparte para que el vale de almacen preste sus piezas por esta misma
    puerta. Un vale es una operacion de varios renglones y tiene que ser todo o
    nada -si el tercero falla, los dos primeros no se llevaron nada-, asi que no
    puede llamar a una funcion que abre su propia transaccion.

    Y sobre todo: no puede haber un SEGUNDO camino que cambie el estado de una
    pieza. La regla que sostiene este modulo es que el saldo y las piezas no se
    separan; un vale que escribiera el estado por su cuenta seria justamente ese
    segundo camino, y las dos vistas empezarian a discrepar sin que nadie sepa
    cual creer.
    """
    payload = payload or {}
    pieza = _pieza(db, id_asset, user_data, para_escribir=True)
    _validar_transicion(pieza, destino)

    if evento in MOTIVO_OBLIGATORIO:
        reason = _texto(payload.get("reason"), "reason", obligatorio=True)
    else:
        reason = _texto(payload.get("reason"), "reason")

    if evento in (EXTRAVIO, BAJA) and not has_capability(db, user_data, CAPACIDAD_PARA_MERMA):
        # Declarar una pieza perdida o darla de baja destruye existencia sin
        # documento: es la operacion con la que se tapa un faltante.
        raise AppError(
            "errors.inventory_adjustment_not_authorized",
            403,
            {"capability": CAPACIDAD_PARA_MERMA, "event": evento},
        )

    antes = _foto(pieza)
    ubicacion_del_movimiento = pieza.id_location

    if exige_responsable:
        pieza.id_holder = _responsable(db, payload.get("id_holder"))
    if libera_responsable:
        pieza.id_holder = None

    if exige_fecha:
        pieza.due_date = _fecha(payload.get("due_date"), "due_date")
        if pieza.due_date is None:
            # Un prestamo sin fecha de regreso es una baja disfrazada:
            # nadie lo reclama porque nunca esta vencido.
            raise AppError("errors.required_field", 400, {"field": "due_date"})
        if pieza.due_date < _hoy():
            raise AppError("errors.inventory_asset_due_date_in_the_past", 400,
                           {"field": "due_date"})
    elif destino != PRESTADA:
        pieza.due_date = None

    if destino in (PRESTADA, EXTRAVIADA):
        # Deja de estar en la empresa: decir que sigue en una ubicacion
        # seria falso, y ese es el dato que hace que nadie la busque.
        pieza.id_location = None
    elif vuelve_a_ubicacion:
        destino_ubicacion = _entero(payload.get("id_location"), "id_location")
        pieza.id_location = destino_ubicacion or antes["id_location"]
        if not pieza.id_location:
            raise AppError("errors.required_field", 400, {"field": "id_location"})
        ubicacion_del_movimiento = pieza.id_location

    pieza.status = destino
    db.flush()

    ledger = _mover_existencia(
        db, pieza, evento, user_data,
        id_location=ubicacion_del_movimiento,
        reason=reason,
        referencia=payload.get("idempotency_key") or pieza.last_update_date,
    )
    registro = _asentar(
        db, pieza, evento, antes=antes, user_data=user_data, ledger=ledger,
        reason=reason,
        referencia_tipo=_texto(payload.get("reference_type"), "reference_type", largo=50),
        referencia_id=payload.get("reference_id"),
    )
    return {"asset": pieza.serialize(), "event": registro.serialize()}


def _transicion(id_asset, payload, user_data, **kwargs):
    """La misma transicion, abriendo la transaccion. Es la entrada publica."""
    with transaction_context() as db:
        return transicion_en_sesion(db, id_asset, payload, user_data, **kwargs)


def assign_asset(id_asset, payload, user_data) -> dict:
    """Entrega la pieza a alguien de la empresa. No cambia el saldo."""
    return _transicion(id_asset, payload, user_data, evento=ASIGNACION, destino=EN_USO,
                       exige_responsable=True)


def lend_asset(id_asset, payload, user_data) -> dict:
    """Presta la pieza fuera de la empresa, con responsable y fecha de regreso."""
    return _transicion(id_asset, payload, user_data, evento=PRESTAMO, destino=PRESTADA,
                       exige_responsable=True, exige_fecha=True)


def return_asset(id_asset, payload, user_data) -> dict:
    """Recibe la pieza de vuelta y la deja disponible."""
    return _transicion(id_asset, payload, user_data, evento=DEVOLUCION, destino=DISPONIBLE,
                       libera_responsable=True, vuelve_a_ubicacion=True)


def send_to_repair(id_asset, payload, user_data) -> dict:
    return _transicion(id_asset, payload, user_data, evento=ENVIO_REPARACION,
                       destino=EN_REPARACION, libera_responsable=True)


def back_from_repair(id_asset, payload, user_data) -> dict:
    return _transicion(id_asset, payload, user_data, evento=REGRESO_REPARACION,
                       destino=DISPONIBLE, vuelve_a_ubicacion=True)


def report_lost(id_asset, payload, user_data) -> dict:
    return _transicion(id_asset, payload, user_data, evento=EXTRAVIO, destino=EXTRAVIADA)


def retire_asset(id_asset, payload, user_data) -> dict:
    return _transicion(id_asset, payload, user_data, evento=BAJA, destino=RETIRADA,
                       libera_responsable=True)


def move_asset(id_asset, payload, user_data) -> dict:
    """Cambia de ubicacion sin cambiar de estado.

    No pasa por `_transicion` porque el estado no cambia, y la maquina de
    estados rechazaria una transicion de un estado a si mismo -con razon, para
    que nadie use un traslado como forma de reescribir el estado-.
    """
    payload = payload or {}
    with transaction_context() as db:
        pieza = _pieza(db, id_asset, user_data, para_escribir=True)
        if pieza.status not in ESTADOS_EN_EXISTENCIA:
            raise AppError(
                "errors.inventory_asset_not_in_stock",
                409,
                {"asset_tag": pieza.asset_tag, "status": pieza.status},
            )
        destino = _entero(payload.get("id_location"), "id_location", obligatorio=True)
        if destino == pieza.id_location:
            raise AppError("errors.inventory_transfer_same_location", 400,
                           {"field": "id_location"})

        antes = _foto(pieza)
        reason = _texto(payload.get("reason"), "reason", obligatorio=True)

        # El traslado se hace con la maquinaria de traspaso del inventario, en
        # la MISMA sesion -`transfer_in_session`, no `transfer_inventory`-:
        # esta ultima abre su propia transaccion, y si algo fallaba despues
        # de que ya hubiera comprometido el traspaso, el rollback de aqui no
        # revertia nada (hallazgo de la auditoria de seguridad del
        # 2026-10-06). Escribe la salida y la entrada en la misma transaccion
        # que el evento de la pieza: todo o nada de verdad.
        from app.services.inventory_service import transfer_in_session

        transfer_in_session(db, pieza.id_product, {
            "id_location_from": antes["id_location"],
            "id_location_to": destino,
            "quantity": 1,
            "idempotency_key": payload.get("idempotency_key")
            or f"asset-{pieza.id_inventory_asset}-traslado-{destino}",
            "reason": reason,
            "reference_type": "inventory_asset",
            "reference_id": str(pieza.id_inventory_asset),
        }, user_data)

        pieza.id_location = destino
        db.flush()
        registro = _asentar(db, pieza, TRASLADO, antes=antes, user_data=user_data,
                            reason=reason)
        return {"asset": pieza.serialize(), "event": registro.serialize()}


# --- consultas ----------------------------------------------------------

def asset_history(id_asset, user_data) -> dict:
    """La pieza y todo lo que le paso, en orden."""
    with transaction_context() as db:
        pieza = _pieza(db, id_asset, user_data)
        eventos = db.scalars(
            select(InventoryAssetEvent)
            .where(InventoryAssetEvent.id_inventory_asset == pieza.id_inventory_asset)
            .order_by(InventoryAssetEvent.id_inventory_asset_event)
        ).all()
        return {
            "asset": pieza.serialize(),
            "events": [evento.serialize() for evento in eventos],
            "total": len(eventos),
        }


def find_asset_by_tag(asset_tag, user_data) -> dict:
    """Busca por la etiqueta pegada en la pieza.

    Es la consulta que se hace con la herramienta en la mano, asi que va por la
    etiqueta y no por el identificador interno, que nadie lleva encima.
    """
    etiqueta = _texto(asset_tag, "asset_tag", largo=40, obligatorio=True)
    with transaction_context() as db:
        pieza = db.scalars(
            select(InventoryAsset).where(
                InventoryAsset.asset_tag == etiqueta,
                InventoryAsset.deletion_date.is_(None),
            )
        ).first()
        if not pieza:
            raise AppError("errors.not_found", 404, {"entity": "inventory_asset"})
        id_asset = pieza.id_inventory_asset
    return asset_history(id_asset, user_data)


def list_assets(user_data, *, id_product=None, status=None, id_holder=None,
                id_location=None, overdue_only=False, page=1, per_page=50) -> dict:
    """Piezas, con los filtros que se usan de verdad."""
    try:
        page = max(int(page or 1), 1)
        per_page = min(max(int(per_page or 50), 1), 200)
    except (TypeError, ValueError):
        page, per_page = 1, 50

    with transaction_context() as db:
        consulta = select(InventoryAsset).where(InventoryAsset.deletion_date.is_(None))

        if id_product is not None:
            producto = _producto(db, id_product, user_data)
            consulta = consulta.where(InventoryAsset.id_product == producto.id_product)
        else:
            # Sin producto concreto hay que acotar igual: se limita a los
            # productos que el actor alcanza, con la misma regla del inventario.
            from app.services.inventory_service import _actor_project_id
            from app.models.invoice import Invoice

            proyecto = _actor_project_id(user_data)
            sin_limite = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
            if not sin_limite:
                if proyecto is None:
                    raise AppError("errors.project_scope_required", 403)
                consulta = consulta.where(
                    InventoryAsset.id_product.in_(
                        select(Product.id_product)
                        .join(Invoice, Product.id_invoice == Invoice.id_invoice)
                        .where(Invoice.id_proyect == proyecto)
                    )
                )

        if status:
            if status not in ESTADOS:
                raise AppError("errors.invalid_field", 400,
                               {"field": "status", "allowed": list(ESTADOS)})
            consulta = consulta.where(InventoryAsset.status == status)
        if id_holder is not None:
            consulta = consulta.where(InventoryAsset.id_holder == _entero(id_holder, "id_holder"))
        if id_location is not None:
            consulta = consulta.where(
                InventoryAsset.id_location == _entero(id_location, "id_location"))
        if overdue_only:
            consulta = consulta.where(
                InventoryAsset.status == PRESTADA,
                InventoryAsset.due_date.is_not(None),
                InventoryAsset.due_date < _hoy(),
            )

        total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
        filas = db.scalars(
            consulta.order_by(InventoryAsset.asset_tag)
            .offset((page - 1) * per_page).limit(per_page)
        ).all()
        return {
            "items": [fila.serialize() for fila in filas],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }


def resumen_de_estatus(user_data, *, proposito: str | None = None) -> dict:
    """Cuantas piezas hay en cada estado, ahora mismo.

    Por que existe
    --------------
    Habia resumen POR PRODUCTO -`product_asset_summary`- y la lista de
    prestamos vencidos, pero no el panorama: "de mis herramientas, cuantas
    estan prestadas, cuantas en reparacion y cuantas no aparecen". Es la
    pregunta que se hace al abrir el almacen por la manana, y para contestarla
    habia que abrir producto por producto.

    Se hace con UNA consulta agrupada y no con una por estado. Con seis estados
    serian seis idas a la base cada vez que alguien abre la pantalla, y ese es
    el patron que ya costo caro en el rastreo -271 consultas para pintar
    cuarenta renglones-.

    `proposito` acota a mercancia o a uso interno. Son dos preguntas distintas:
    de la herramienta importa quien la tiene, y de la mercancia el saldo.
    """
    from app.models.invoice import Invoice
    from app.models.product import Product
    from app.services.inventory_service import _actor_project_id

    with transaction_context() as db:
        # El mismo alcance que `list_assets`: el proyecto del actor, salvo
        # superusuario. Se reusa en vez de escribir otra regla, porque dos
        # reglas de alcance divergen y una pantalla acaba ensenando lo que la
        # otra esconde.
        alcanzables = None
        sin_limite = bool(user_data.get("is_superuser")
                          or user_data.get("is_bootstrap_admin"))
        if not sin_limite:
            proyecto = _actor_project_id(user_data)
            if proyecto is None:
                raise AppError("errors.project_scope_required", 403)
            alcanzables = (
                select(Product.id_product)
                .join(Invoice, Product.id_invoice == Invoice.id_invoice)
                .where(Invoice.id_proyect == proyecto)
            )

        base = [InventoryAsset.deletion_date.is_(None),
                Product.deletion_date.is_(None)]
        if proposito:
            base.append(Product.stock_purpose == proposito)
        if alcanzables is not None:
            base.append(InventoryAsset.id_product.in_(alcanzables))

        filas = db.execute(
            select(InventoryAsset.status, func.count().label("cuantas"))
            .join(Product, Product.id_product == InventoryAsset.id_product)
            .where(*base)
            .group_by(InventoryAsset.status)
        ).all()

        cuentas = {estado: 0 for estado in ESTADOS}
        for estado, cuantas in filas:
            cuentas[estado] = int(cuantas or 0)

        # Lo vencido va aparte y no como un estado mas: una pieza vencida esta
        # PRESTADA, asi que contarla como estado propio la sumaria dos veces y
        # el total dejaria de cuadrar con el numero de piezas.
        vencidos = db.scalar(
            select(func.count())
            .select_from(InventoryAsset)
            .join(Product, Product.id_product == InventoryAsset.id_product)
            .where(*base,
                   InventoryAsset.status == PRESTADA,
                   InventoryAsset.due_date.is_not(None),
                   InventoryAsset.due_date < _hoy())
        ) or 0

        return {
            "stock_purpose": proposito,
            "by_status": cuentas,
            "total": sum(cuentas.values()),
            "overdue": int(vencidos),
        }


def overdue_loans(user_data) -> dict:
    """Prestamos vencidos.

    Existe como consulta propia porque sin ella un prestamo se vuelve permanente
    por olvido: nadie revisa pieza por pieza si ya debio volver.
    """
    resultado = list_assets(user_data, overdue_only=True, per_page=200)
    hoy = _hoy()
    for pieza in resultado["items"]:
        vence = pieza.get("due_date")
        pieza["days_overdue"] = (hoy - date.fromisoformat(vence)).days if vence else None
    return resultado


def product_asset_summary(id_product, user_data) -> dict:
    """Cuantas piezas hay en cada estado, y si cuadran con la existencia.

    Es la consulta que responde "tengo diez taladros" con el detalle de que
    cuatro estan prestados y uno no aparece, que es la diferencia entre un
    inventario que sirve y un numero.
    """
    with transaction_context() as db:
        producto = _producto(db, id_product, user_data)
        filas = db.execute(
            select(InventoryAsset.status, func.count())
            .where(
                InventoryAsset.id_product == producto.id_product,
                InventoryAsset.deletion_date.is_(None),
            )
            .group_by(InventoryAsset.status)
        ).all()
        por_estado = {estado: 0 for estado in ESTADOS}
        for estado, cuantas in filas:
            por_estado[estado] = int(cuantas)

        en_existencia = sum(
            cuantas for estado, cuantas in por_estado.items()
            if estado in ESTADOS_EN_EXISTENCIA
        )

        from app.services.inventory_service import _product_total

        saldo = _product_total(db, producto.id_product)
        return {
            "id_product": producto.id_product,
            "tracking_mode": str(getattr(producto, "tracking_mode", FUNGIBLE) or FUNGIBLE),
            "by_status": por_estado,
            "total_assets": sum(por_estado.values()),
            "assets_in_stock": en_existencia,
            "stock_balance": saldo,
            # Si no cuadran, alguien movio existencia por fuera del rastreo de
            # piezas. Se reporta en lugar de corregirse en silencio.
            "is_reconciled": en_existencia == saldo,
            "difference": en_existencia - saldo,
        }
