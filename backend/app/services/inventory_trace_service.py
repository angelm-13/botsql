"""Localizar cualquier cosa del almacen y saber que le paso.

Por que existe
--------------
Los datos del rastreo ya estaban completos, pero repartidos: para saber donde
esta un producto habia que pedir `product_stock`; para ver que hay en un sitio,
`warehouse_stock`; para saber que le paso, `list_inventory_movements`; y para
una herramienta concreta, el rastreo de piezas. Cuatro consultas, y todas piden
saber de antemano que producto o que almacen se busca.

La pregunta que nadie podia hacer era la primera que se hace en un almacen:
"¿donde esta el taladro?". Este servicio la contesta: se escribe un texto y
devuelve, por cada coincidencia, su foto, cuanto hay, en que ubicaciones esta
repartido, que le ha pasado, y -si se rastrea pieza por pieza- en que estado
esta cada una y quien la tiene.

Como se cuenta "que le paso"
----------------------------
Del libro de inventario, agrupando por el tipo de movimiento y por de donde
venia. La distincion importa mas de lo que parece:

* **comprado** es una entrada con una compra o una factura detras;
* **vendido** es una salida con una venta o una factura detras;
* **prestado**, **danado**, **caducado** y **extraviado** son cada uno lo suyo.

Se cuentan por separado a proposito. Merma y caducidad juntas no dicen nada: la
merma se reduce operando mejor y la caducidad comprando mejor, y en el mismo
saco no hay forma de saber cual de los dos problemas se tiene.

Lo que este servicio no hace
----------------------------
**No mueve nada.** Es de lectura, y por eso puede ser generoso con lo que
devuelve sin arriesgar nada.

**No inventa el saldo.** Los totales por ubicacion salen de `inventory_stock`,
que es la tabla que el libro mantiene. Recalcularlos aqui sumando el libro daria
un segundo numero que discrepa del primero el dia que algo se descuadre, y dos
respuestas a "cuanto hay" es peor que una equivocada.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select

from app.models.inventory_ledger import InventoryLedger
from app.models.inventory_stock import InventoryStock
from app.models.invoice import Invoice
from app.models.location import Location
from app.models.product import Product
from app.models.session import transaction_context
from app.services.inventory_service import (
    _actor_project_id,
    _warehouse_payload,
)


# Como se lee cada movimiento del libro para contarlo. La llave es el
# `movement_type`; para las entradas y salidas se afina con el `reference_type`,
# porque "recibido" puede ser una compra o una devolucion de cliente.
COMPRAS = frozenset({"purchase", "invoice_line", "invoice"})
VENTAS = frozenset({"sale", "invoice_line", "invoice"})

MAXIMO_RESULTADOS = 40

# Cuantos movimientos se traen de UNA pieza. Los ultimos son los que
# contestan "donde esta"; el resto es historia y tiene su propia pantalla.
MAXIMO_EVENTOS_POR_PIEZA = 20


def _clasificar(movement_type: str, reference_type: str | None) -> str:
    """El nombre con el que se cuenta un renglon del libro."""
    referencia = reference_type or ""
    if movement_type == "receive":
        return "comprado" if referencia in COMPRAS else "recibido"
    if movement_type == "issue":
        return "vendido" if referencia in VENTAS else "entregado"
    return {
        "return": "devuelto",
        "loan": "prestado",
        "damage": "danado",
        "destroy": "destruido",
        "loss": "extraviado",
        "expiry": "caducado",
        "transfer": "trasladado",
        "adjustment": "ajustado",
    }.get(movement_type, movement_type)


def _historia(db, id_product) -> dict:
    """Cuanto se ha comprado, vendido, prestado... de este producto.

    Un traslado escribe DOS asientos con el mismo `transfer_group`: la salida
    del origen y la entrada al destino. Sumando valores absolutos, mover diez
    piezas se contaba como veinte -medido: un traslado de 10 aparecia como
    "trasladado 20"-. Se cuenta solo el lado de la salida, que es lo que se
    movio.
    """
    filas = db.execute(
        select(
            InventoryLedger.movement_type,
            InventoryLedger.reference_type,
            func.count().label("veces"),
            func.sum(func.abs(InventoryLedger.quantity_delta)).label("unidades"),
        )
        .where(
            InventoryLedger.id_product == id_product,
            # Del traslado, solo la salida.
            or_(
                InventoryLedger.movement_type != "transfer",
                InventoryLedger.quantity_delta < 0,
            ),
        )
        .group_by(InventoryLedger.movement_type, InventoryLedger.reference_type)
    ).all()

    resumen: dict[str, dict] = {}
    for movimiento, referencia, veces, unidades in filas:
        clave = _clasificar(movimiento, referencia)
        entrada = resumen.setdefault(clave, {"veces": 0, "unidades": 0})
        entrada["veces"] += int(veces or 0)
        entrada["unidades"] += int(unidades or 0)
    return resumen


def _ubicaciones(db, id_product) -> list[dict]:
    """Donde esta repartido, sin las ubicaciones donde ya no queda nada."""
    filas = db.scalars(
        select(InventoryStock)
        .where(InventoryStock.id_product == id_product, InventoryStock.quantity > 0)
        .order_by(InventoryStock.quantity.desc())
    ).all()
    salida = []
    for fila in filas:
        ubicacion = db.get(Location, fila.id_location)
        if ubicacion is None:
            continue
        salida.append({
            **_warehouse_payload(db, ubicacion),
            "id_module": ubicacion.id_module,
            "quantity": int(fila.quantity or 0),
        })
    return salida


def _piezas(db, id_product, *, consulta: str = "",
            codigo_del_producto: str = "") -> list[dict]:
    """Las piezas de un producto que se rastrea una por una.

    Solo para `tracking_mode = 'serializado'`. Es el caso que mas importa para
    herramienta: cual esta prestada, quien la tiene, cual no aparece.

    Al serializar la pieza se le suman el nombre del responsable y el de su
    ubicacion. El modelo solo guarda los identificadores, y resolverlos dentro
    de `serialize()` obligaria al modelo a consultar la base; aqui ya hay sesion
    abierta. Sin el nombre, la pantalla enseña "responsable 77", que no le dice
    a nadie quien tiene el taladro.
    """
    from app.models.inventory_asset import InventoryAsset
    from app.models.user import User

    filas = db.scalars(
        select(InventoryAsset)
        .where(InventoryAsset.id_product == id_product,
               InventoryAsset.deletion_date.is_(None))
        .order_by(InventoryAsset.asset_tag)
    ).all()

    texto = str(consulta or "").strip().lower()
    codigo = str(codigo_del_producto or "").strip().lower()
    # Las etiquetas suelen empezar por el codigo del producto -TAL-100-A, -B,
    # -C-, asi que "contiene el texto" marcaba las tres piezas al buscar el
    # producto y decia "coincide la pieza A, B y C" cuando no coincidia ninguna:
    # se pidio el producto. Buscar el producto es una pregunta y buscar una
    # pieza es otra, y la respuesta tiene que distinguirlas.
    #
    # Se marca pieza cuando el texto es MAS especifico que el codigo: o es la
    # etiqueta exacta, o no es algo que el codigo del producto ya explique.
    busca_una_pieza = bool(texto) and (codigo == "" or texto not in codigo)

    salida = []
    for fila in filas:
        pieza = fila.serialize()
        etiqueta = str(fila.asset_tag or "").lower()
        pieza["matched"] = texto == etiqueta or (busca_una_pieza and texto in etiqueta)
        if fila.id_holder:
            responsable = db.get(User, fila.id_holder)
            pieza["holder_name"] = (
                getattr(responsable, "full_name", None)
                or getattr(responsable, "username", None)
                # Si el responsable ya no existe se dice, en vez de dejar el
                # hueco: una pieza asignada a alguien que se fue de la empresa
                # es justo la que hay que ir a buscar.
                or f"#{fila.id_holder}"
            )
        if fila.id_location:
            ubicacion = db.get(Location, fila.id_location)
            pieza["location_description"] = getattr(ubicacion, "location_description", None)
        salida.append(pieza)
    # Las coincidentes primero: es lo que se vino a ver.
    salida.sort(key=lambda p: (not p["matched"], str(p.get("asset_tag") or "")))
    return salida


ETIQUETA_DE_EVENTO = {
    "alta": "dio de alta",
    "asignacion": "se asigno a",
    "prestamo": "se presto a",
    "devolucion": "la devolvio",
    "envio_reparacion": "se mando a reparacion",
    "regreso_reparacion": "volvio de reparacion",
    "extravio": "se reporto extraviada",
    "baja": "se retiro",
    "traslado": "se movio",
}


def _nombre_de_persona(db, id_usuario) -> str | None:
    """El nombre de quien tuvo la pieza; nunca el identificador a secas."""
    if not id_usuario:
        return None
    from app.models.user import User

    persona = db.get(User, id_usuario)
    return (
        getattr(persona, "full_name", None)
        or getattr(persona, "username", None)
        or f"#{id_usuario}"
    )


def _bitacora_de_pieza(db, id_asset) -> list[dict]:
    """Todo lo que le paso a UNA pieza, en orden y legible.

    Esta es la respuesta especifica: la historia del producto dice que de treinta
    taladros se prestaron cuatro, y eso no sirve cuando lo que se busca es el
    taladro que falta. Aqui se ve quien tuvo esta pieza, cuando, de donde salio y
    a donde fue.

    `InventoryAssetEvent` ya guardaba el antes y el despues completos, pero solo
    los identificadores. Un renglon que dice `id_holder_after: 7` obliga a ir a
    buscar quien es el 7, asi que los nombres se resuelven aqui, donde ya hay
    sesion abierta.
    """
    from app.models.inventory_asset_event import InventoryAssetEvent

    eventos = db.scalars(
        select(InventoryAssetEvent)
        .where(InventoryAssetEvent.id_inventory_asset == id_asset)
        .order_by(InventoryAssetEvent.id_inventory_asset_event.desc())
        .limit(MAXIMO_EVENTOS_POR_PIEZA)
    ).all()

    salida = []
    for evento in eventos:
        fila = evento.serialize()
        fila["etiqueta"] = ETIQUETA_DE_EVENTO.get(evento.event_type, evento.event_type)
        fila["holder_before_name"] = _nombre_de_persona(db, evento.id_holder_before)
        fila["holder_after_name"] = _nombre_de_persona(db, evento.id_holder_after)
        for lado in ("before", "after"):
            id_ubicacion = getattr(evento, f"id_location_{lado}")
            ubicacion = db.get(Location, id_ubicacion) if id_ubicacion else None
            fila[f"location_{lado}_description"] = getattr(
                ubicacion, "location_description", None
            )
        salida.append(fila)
    return salida


def _ultimo_movimiento(db, id_product) -> dict | None:
    fila = db.scalars(
        select(InventoryLedger)
        .where(InventoryLedger.id_product == id_product)
        .order_by(InventoryLedger.id_inventory_ledger.desc())
        .limit(1)
    ).first()
    if fila is None:
        return None
    return {
        "movement_type": fila.movement_type,
        "clasificacion": _clasificar(fila.movement_type, fila.reference_type),
        "quantity_delta": int(fila.quantity_delta or 0),
        "reason": fila.reason,
        "source_module": fila.source_module,
        "creation_date": fila.creation_date.isoformat() if fila.creation_date else None,
    }


def localizar(consulta: str, user_data: dict, *, proposito: str | None = None,
              con_piezas: bool = True) -> dict:
    """Busca en el almacen y devuelve todo lo que se sabe de cada coincidencia.

    Busca por codigo, descripcion y etiqueta de pieza. La etiqueta se incluye
    porque es lo que esta pegado en la herramienta: quien la tiene en la mano lee
    ese numero, no el codigo del producto.
    """
    texto = str(consulta or "").strip()
    sin_restriccion = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
    proyecto = _actor_project_id(user_data)

    with transaction_context() as db:
        from app.models.inventory_asset import InventoryAsset

        query = select(Product).where(Product.deletion_date.is_(None))
        productos_con_esa_etiqueta: set[int] = set()
        if texto:
            patron = f"%{texto}%"
            # Las etiquetas se resuelven aparte y se suman a la busqueda: un
            # `join` dejaria fuera los productos fungibles, que no tienen
            # piezas y son la mayoria del almacen.
            con_esa_etiqueta = db.scalars(
                select(InventoryAsset.id_product).where(
                    InventoryAsset.asset_tag.ilike(patron),
                    InventoryAsset.deletion_date.is_(None),
                )
            ).all()
            condiciones = [
                Product.product_code.ilike(patron),
                Product.descripcion.ilike(patron),
            ]
            productos_con_esa_etiqueta = set(con_esa_etiqueta)
            if con_esa_etiqueta:
                condiciones.append(Product.id_product.in_(list(productos_con_esa_etiqueta)))
            query = query.where(or_(*condiciones))
        if proposito:
            query = query.where(Product.stock_purpose == proposito)

        productos = db.scalars(query.order_by(Product.id_product)).all()

        resultados = []
        omitidos_por_alcance = 0
        for producto in productos:
            factura = db.get(Invoice, producto.id_invoice) if producto.id_invoice else None
            del_proyecto = getattr(factura, "id_proyect", None)
            if not sin_restriccion and del_proyecto != proyecto:
                # El almacen guarda mercancia de varios proyectos. Se cuenta lo
                # que se oculta en vez de callarlo: quien busca algo que existe
                # y no lo ve merece saber que hay resultados fuera de su alcance.
                omitidos_por_alcance += 1
                continue
            if len(resultados) >= MAXIMO_RESULTADOS:
                break

            serializado = str(producto.tracking_mode or "") == "serializado"
            ubicaciones = _ubicaciones(db, producto.id_product)
            piezas = _piezas(
                db, producto.id_product, consulta=texto,
                codigo_del_producto=producto.product_code or "",
            ) if (serializado and con_piezas) else []
            coincidentes = [p["asset_tag"] for p in piezas if p.get("matched")]
            for pieza in piezas:
                if pieza.get("matched"):
                    pieza["timeline"] = _bitacora_de_pieza(db, pieza["id_inventory_asset"])

            # Por que este producto salio en la busqueda. La pantalla lo usa
            # para saber si mostrar la pieza concreta o todas las unidades: son
            # dos preguntas distintas y hasta ahora se contestaban igual.
            if coincidentes:
                # Se pidio una pieza concreta.
                motivo = "asset_tag"
            elif texto and texto.lower() in str(producto.product_code or "").lower():
                # Se pidio el producto: todas sus unidades.
                motivo = "product_code"
            elif producto.id_product in productos_con_esa_etiqueta:
                # Salio por una etiqueta pero sin poder senalar cual, porque se
                # pidio el resumen sin piezas.
                motivo = "asset_tag"
            elif texto:
                motivo = "description"
            else:
                motivo = "all"

            resultados.append({
                "id_product": producto.id_product,
                "product_code": producto.product_code,
                "descripcion": producto.descripcion,
                "path_imagen": producto.path_imagen,
                "tracking_mode": producto.tracking_mode,
                "stock_purpose": producto.stock_purpose,
                "id_proyect": del_proyecto,
                "total": sum(u["quantity"] for u in ubicaciones),
                "stock_balance": int(producto.cantidad or 0),
                "locations": ubicaciones,
                "history": _historia(db, producto.id_product),
                "last_movement": _ultimo_movimiento(db, producto.id_product),
                "assets": piezas,
                "match_kind": motivo,
                "matched_asset_tags": coincidentes,
                # Cuantas unidades tiene el producto y cuantas estan
                # disponibles. Para lo serializado es la cuenta de piezas; para
                # lo fungible, el saldo, que ya es la respuesta.
                "unit_count": len(piezas) if serializado else None,
                "available_units": (
                    sum(1 for p in piezas if p.get("status") == "disponible")
                    if serializado else None
                ),
            })

        return {
            "query": texto,
            "stock_purpose": proposito,
            "items": resultados,
            "total": len(resultados),
            "hidden_by_scope": omitidos_por_alcance,
            "truncated": len(resultados) >= MAXIMO_RESULTADOS,
        }
