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

from datetime import datetime

from sqlalchemy import func, or_, select

from app.models.incident import Incident
from app.models.inventory_ledger import InventoryLedger
from app.models.inventory_stock import InventoryStock
from app.models.invoice import Invoice
from app.models.location import Location
from app.models.location_type import LocationType
from app.models.material_type import MaterialType
from app.models.nm_incident_product import NmIncidentProduct
from app.models.product import Product
from app.models.user import User
from app.models.session import transaction_context
from app.services.inventory_service import (
    MAX_LOCATION_DEPTH,
    _actor_project_id,
    _warehouse_payload,
)


# Como se lee cada movimiento del libro para contarlo. La llave es el
# `movement_type`; para las entradas y salidas se afina con el `reference_type`,
# porque "recibido" puede ser una compra o una devolucion de cliente.
COMPRAS = frozenset({"purchase", "invoice_line", "invoice"})
VENTAS = frozenset({"sale", "invoice_line", "invoice"})

# Cuantos resultados trae una pagina si nadie pide otra cosa.
RESULTADOS_POR_PAGINA = 40

# Y cuantos como maximo, cuando la pantalla si lo pide.
#
# Eran el mismo numero, y por eso el selector de "cuantos ver" de Localizar no
# podia ofrecer mas de 40: `per_page=100` se recortaba a 40 sin decirlo, asi que
# la opcion existia y no hacia nada. El tope sigue existiendo -el valor llega
# del cliente y sin cota `per_page=100000` arma cien mil diccionarios y tumba el
# proceso-, solo deja de ser tambien el default.
TOPE_POR_PAGINA = 200

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
        # La carga del sistema anterior. Sin nombre propio caia en el
        # `.get(..., movement_type)` de abajo y la tarjeta enseñaba "opening"
        # tal cual -- en 2 201 de los 2 427 asientos del libro, que es casi
        # todo lo que hay.
        "opening": "inicial",
        "damage": "danado",
        "destroy": "destruido",
        "loss": "extraviado",
        "expiry": "caducado",
        "transfer": "trasladado",
        "adjustment": "ajustado",
    }.get(movement_type, movement_type)


def _historia_en_lote(db, ids_productos) -> dict[int, dict]:
    """Cuanto se ha comprado, vendido, prestado... de cada producto.

    Una consulta para toda la pagina. Antes era una por producto: cuarenta
    resultados, cuarenta agregaciones sobre la misma tabla.

    Un traslado escribe DOS asientos con el mismo `transfer_group`: la salida
    del origen y la entrada al destino. Sumando valores absolutos, mover diez
    piezas se contaba como veinte -medido: un traslado de 10 aparecia como
    "trasladado 20"-. Se cuenta solo el lado de la salida, que es lo que se
    movio.
    """
    if not ids_productos:
        return {}

    filas = db.execute(
        select(
            InventoryLedger.id_product,
            InventoryLedger.movement_type,
            InventoryLedger.reference_type,
            func.count().label("veces"),
            func.sum(func.abs(InventoryLedger.quantity_delta)).label("unidades"),
        )
        .where(
            InventoryLedger.id_product.in_(list(ids_productos)),
            # Del traslado, solo la salida.
            or_(
                InventoryLedger.movement_type != "transfer",
                InventoryLedger.quantity_delta < 0,
            ),
        )
        .group_by(
            InventoryLedger.id_product,
            InventoryLedger.movement_type,
            InventoryLedger.reference_type,
        )
    ).all()

    por_producto: dict[int, dict] = {}
    for id_producto, movimiento, referencia, veces, unidades in filas:
        resumen = por_producto.setdefault(id_producto, {})
        clave = _clasificar(movimiento, referencia)
        entrada = resumen.setdefault(clave, {"veces": 0, "unidades": 0})
        entrada["veces"] += int(veces or 0)
        entrada["unidades"] += int(unidades or 0)
    return por_producto


def _existencias_en_lote(db, ids_productos, ubicaciones: "CacheDeUbicaciones") -> dict[int, list]:
    """Donde esta repartido cada producto, sin los sitios donde ya no queda nada.

    Una consulta para toda la pagina, y las ramas salen de la cache, que ya se
    precargo. Antes eran dos consultas por producto mas una por nivel del arbol
    de cada ubicacion.
    """
    if not ids_productos:
        return {}

    filas = db.scalars(
        select(InventoryStock)
        .where(
            InventoryStock.id_product.in_(list(ids_productos)),
            InventoryStock.quantity > 0,
        )
        .order_by(InventoryStock.id_product, InventoryStock.quantity.desc())
    ).all()

    ubicaciones.precargar({f.id_location for f in filas})
    from app.services.warehouse_voucher_service import apartado_por_sitio
    apartado = apartado_por_sitio(db, {f.id_product for f in filas})

    por_producto: dict[int, list] = {}
    for fila in filas:
        ubicacion = ubicaciones.ubicacion(fila.id_location)
        if ubicacion is None:
            continue
        ruta = ubicaciones.ruta(fila.id_location)
        por_producto.setdefault(fila.id_product, []).append({
            "id_location": ubicacion.id_location,
            "location_description": ubicacion.location_description,
            "id_warehouse": ruta["id_warehouse"],
            "warehouse_description": ruta["warehouse_description"],
            "id_module": ubicacion.id_module,
            "quantity": int(fila.quantity or 0),
            # Lo que otros prevales ya apartaron aqui, y lo que de verdad se
            # puede pedir: la existencia fisica no cambia hasta que sale.
            "reserved": apartado.get((fila.id_product, fila.id_location), 0),
            "available": max(0, int(fila.quantity or 0)
                             - apartado.get((fila.id_product, fila.id_location), 0)),
            "path": ruta["segments"],
            "path_label": ruta["label"],
        })
    return por_producto


def _piezas_en_lote(db, productos, ubicaciones: "CacheDeUbicaciones",
                    *, consulta: str = "") -> dict[int, list]:
    """Las piezas de los productos que se rastrean una por una.

    Solo para `tracking_mode = 'serializado'`. Es el caso que mas importa para
    herramienta: cual esta prestada, quien la tiene, cual no aparece.

    A cada pieza se le suman el nombre de su responsable y su ubicacion con la
    rama entera. El modelo solo guarda los identificadores, y sin el nombre la
    pantalla ensena "responsable 77", que no le dice a nadie quien tiene el
    taladro. Los usuarios se traen en una sola consulta, no uno por pieza.

    Que cuenta como coincidencia
    ----------------------------
    Las etiquetas suelen empezar por el codigo del producto -TAL-100-A, -B, -C-,
    asi que "contiene el texto" marcaba las tres al buscar el producto y decia
    "coincide la pieza A, B y C" cuando no coincidia ninguna: se pidio el
    producto. Se marca pieza cuando el texto es MAS especifico que el codigo: o
    es la etiqueta exacta, o no es algo que el codigo ya explique.
    """
    from app.models.inventory_asset import InventoryAsset

    serializados = {
        pr.id_product: (pr.product_code or "")
        for pr in productos
        if str(pr.tracking_mode or "") == "serializado"
    }
    if not serializados:
        return {}

    filas = db.scalars(
        select(InventoryAsset)
        .where(
            InventoryAsset.id_product.in_(list(serializados)),
            InventoryAsset.deletion_date.is_(None),
        )
        .order_by(InventoryAsset.id_product, InventoryAsset.asset_tag)
    ).all()

    ubicaciones.precargar({f.id_location for f in filas if f.id_location})
    responsables = _nombres_de_personas(db, {f.id_holder for f in filas if f.id_holder})

    texto = str(consulta or "").strip().lower()
    por_producto: dict[int, list] = {}
    for fila in filas:
        codigo = str(serializados.get(fila.id_product) or "").strip().lower()
        busca_una_pieza = bool(texto) and (codigo == "" or texto not in codigo)
        etiqueta = str(fila.asset_tag or "").lower()

        pieza = fila.serialize()
        pieza["matched"] = texto == etiqueta or (busca_una_pieza and texto in etiqueta)
        if fila.id_holder:
            pieza["holder_name"] = responsables.get(fila.id_holder)
        if fila.id_location:
            ubicacion = ubicaciones.ubicacion(fila.id_location)
            pieza["location_description"] = getattr(ubicacion, "location_description", None)
            ruta = ubicaciones.ruta(fila.id_location)
            pieza["location_path"] = ruta["segments"]
            pieza["location_path_label"] = ruta["label"]
        por_producto.setdefault(fila.id_product, []).append(pieza)

    # Las coincidentes primero: es lo que se vino a ver.
    for piezas in por_producto.values():
        piezas.sort(key=lambda p: (not p["matched"], str(p.get("asset_tag") or "")))
    return por_producto


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


def _nombres_de_personas(db, ids_usuarios) -> dict[int, str]:
    """Los nombres de quienes tienen o tuvieron algo, en una consulta.

    Si el usuario ya no existe se devuelve `#<id>` en vez del hueco: una pieza
    asignada a alguien que se fue de la empresa es justo la que hay que ir a
    buscar, y un espacio en blanco la esconde.
    """
    ids = {int(i) for i in ids_usuarios if i}
    if not ids:
        return {}

    from app.models.user import User

    encontrados = {}
    for persona in db.scalars(select(User).where(User.id_user.in_(list(ids)))).all():
        encontrados[persona.id_user] = (
            getattr(persona, "full_name", None)
            or getattr(persona, "username", None)
            or f"#{persona.id_user}"
        )
    for id_usuario in ids - set(encontrados):
        encontrados[id_usuario] = f"#{id_usuario}"
    return encontrados


def _bitacoras_en_lote(db, ids_piezas, ubicaciones: "CacheDeUbicaciones") -> dict[int, list]:
    """Todo lo que les paso a UNAS piezas, en orden y legible.

    Esta es la respuesta especifica: la historia del producto dice que de treinta
    taladros se prestaron cuatro, y eso no sirve cuando lo que se busca es el
    taladro que falta. Aqui se ve quien tuvo esta pieza, cuando, de donde salio y
    a donde fue.

    `InventoryAssetEvent` ya guardaba el antes y el despues completos, pero solo
    los identificadores. Un renglon que dice `id_holder_after: 7` obliga a ir a
    buscar quien es el 7, asi que los nombres se resuelven aqui.

    Solo se piden las bitacoras de las piezas que coincidieron con la busqueda:
    traer la de las treinta piezas de un producto para ver una son treinta
    lecturas que nadie mira.
    """
    from app.models.inventory_asset_event import InventoryAssetEvent

    ids = [int(i) for i in ids_piezas if i]
    if not ids:
        return {}

    eventos = db.scalars(
        select(InventoryAssetEvent)
        .where(InventoryAssetEvent.id_inventory_asset.in_(ids))
        .order_by(
            InventoryAssetEvent.id_inventory_asset,
            InventoryAssetEvent.id_inventory_asset_event.desc(),
        )
    ).all()

    ubicaciones.precargar(
        {e.id_location_before for e in eventos if e.id_location_before}
        | {e.id_location_after for e in eventos if e.id_location_after}
    )
    personas = _nombres_de_personas(db, (
        {e.id_holder_before for e in eventos if e.id_holder_before}
        | {e.id_holder_after for e in eventos if e.id_holder_after}
    ))

    por_pieza: dict[int, list] = {}
    for evento in eventos:
        acumulado = por_pieza.setdefault(evento.id_inventory_asset, [])
        # El tope se aplica aqui y no en el SQL: un LIMIT por pieza obligaria a
        # una consulta por pieza, que es lo que se vino a quitar.
        if len(acumulado) >= MAXIMO_EVENTOS_POR_PIEZA:
            continue
        fila = evento.serialize()
        fila["etiqueta"] = ETIQUETA_DE_EVENTO.get(evento.event_type, evento.event_type)
        fila["holder_before_name"] = personas.get(evento.id_holder_before)
        fila["holder_after_name"] = personas.get(evento.id_holder_after)
        for lado in ("before", "after"):
            id_ubicacion = getattr(evento, f"id_location_{lado}")
            ubicacion = ubicaciones.ubicacion(id_ubicacion) if id_ubicacion else None
            fila[f"location_{lado}_description"] = getattr(
                ubicacion, "location_description", None)
        acumulado.append(fila)
    return por_pieza


def _prestado_en_lote(db, ids_productos) -> dict[int, dict]:
    """Que hay fuera de cada producto y quien lo tiene.

    Un producto fungible prestado se veia con cero en todo y sin ubicacion: el
    saldo bajo -correctamente, salio del almacen- y nada decia donde fue. La
    pieza serializada si se veia, porque tiene su fila con estado y responsable;
    lo fungible no tiene piezas.

    Una consulta para toda la pagina. Una por producto es el patron de N+1 que
    ya costo 271 consultas en esta misma pantalla.

    Solo las SALIDAS sin cerrar: una salida cerrada ya volvio, y un renglon de
    entrada es el hecho de que volvio. Contarlos aqui diria que alguien tiene
    algo que devolvio el mes pasado.
    """
    if not ids_productos:
        return {}

    # Import local: el servicio de vales ya importa de inventario, y arriba se
    # cerraria un circulo.
    from app.services.warehouse_voucher_service import _vales_de_baja

    filas = db.execute(
        select(
            NmIncidentProduct.id_product,
            NmIncidentProduct.quantity,
            NmIncidentProduct.start_date,
            NmIncidentProduct.due_date,
            Incident.id_incident,
            Incident.external_folio,
            Incident.id_user,
            User.full_name,
        )
        .join(Incident, Incident.id_incident == NmIncidentProduct.id_incident)
        .outerjoin(User, User.id_user == Incident.id_user)
        .where(
            NmIncidentProduct.id_product.in_(list(ids_productos)),
            NmIncidentProduct.direction == "salida",
            NmIncidentProduct.close_date.is_(None),
            NmIncidentProduct.deletion_date.is_(None),
            Incident.deletion_date.is_(None),
            # Un prevale o un vale en espera sigue en el almacen (apartado):
            # nadie lo "tiene" todavia.
            func.coalesce(func.lower(Incident.incident_status), "")
            .notin_(("borrador", "en_espera", "cancelado")),
            # Quien "tiene" el producto ahora: una baja no esta con nadie.
            NmIncidentProduct.id_incident.notin_(_vales_de_baja()),
        )
        .order_by(NmIncidentProduct.start_date)
    ).all()

    ahora = datetime.now()
    salida: dict[int, dict] = {}
    for (id_producto, cantidad, desde, vence, id_vale, folio, id_usuario,
         nombre) in filas:
        grupo = salida.setdefault(int(id_producto), {"quantity": 0, "holders": []})
        grupo["quantity"] += int(cantidad or 0)
        grupo["holders"].append({
            "id_user": id_usuario,
            "holder_name": nombre,
            # El folio con el que la gente conoce el vale: el del sistema
            # anterior cuando lo trae, y si no el identificador.
            "voucher_folio": folio or str(id_vale),
            "id_incident": id_vale,
            "quantity": int(cantidad or 0),
            "since": desde.isoformat() if desde else None,
            "due_date": vence.isoformat() if vence else None,
            "overdue": bool(vence and vence < ahora),
        })
    for grupo in salida.values():
        grupo["overdue"] = any(h["overdue"] for h in grupo["holders"])
    return salida


def _ultimo_movimiento_en_lote(db, ids_productos) -> dict[int, dict]:
    """El ultimo asiento de cada producto, en dos consultas.

    Se hace en dos pasos -primero el id maximo por producto, luego esas filas-
    en lugar de un `DISTINCT ON`, que es de Postgres: las pruebas corren sobre
    SQLite y una consulta que solo funciona en produccion no se puede probar.
    """
    if not ids_productos:
        return {}

    ultimos = db.execute(
        select(
            InventoryLedger.id_product,
            func.max(InventoryLedger.id_inventory_ledger).label("id_ultimo"),
        )
        .where(InventoryLedger.id_product.in_(list(ids_productos)))
        .group_by(InventoryLedger.id_product)
    ).all()
    if not ultimos:
        return {}

    filas = db.scalars(
        select(InventoryLedger).where(
            InventoryLedger.id_inventory_ledger.in_([u.id_ultimo for u in ultimos]))
    ).all()
    return {
        fila.id_product: {
            "movement_type": fila.movement_type,
            "clasificacion": _clasificar(fila.movement_type, fila.reference_type),
            "quantity_delta": int(fila.quantity_delta or 0),
            "reason": fila.reason,
            "source_module": fila.source_module,
            "creation_date": fila.creation_date.isoformat() if fila.creation_date else None,
        }
        for fila in filas
    }


class CacheDeUbicaciones:
    """Las ubicaciones y sus ramas, cargadas de golpe.

    Por que existe
    --------------
    Cada rama se resolvia subiendo por `id_location_reference` con un `db.get`
    por nivel, y cada resultado del rastreo tiene su ubicacion de ficha mas una
    por cada sitio donde tiene existencia. Con cuarenta resultados eran del
    orden de cien viajes a la base para leer una tabla que en un almacen entero
    tiene decenas de filas.

    Aqui se cargan por niveles: los ids que se piden, luego sus padres, luego
    los padres de esos. Son tantas consultas como profundidad tenga el arbol
    -dos o tres en la practica- en vez de una por ubicacion y nivel.
    """

    def __init__(self, db):
        self._db = db
        self._ubicaciones: dict[int, object] = {}
        self._tipos: dict[int, object] = {}
        self._rutas: dict[int, dict] = {}

    def precargar(self, ids) -> None:
        """Trae esas ubicaciones, sus ancestros y los tipos de todas."""
        pendientes = {int(i) for i in ids if i} - set(self._ubicaciones)
        for _ in range(MAX_LOCATION_DEPTH):
            if not pendientes:
                break
            filas = self._db.scalars(
                select(Location).where(Location.id_location.in_(list(pendientes)))
            ).all()
            for fila in filas:
                self._ubicaciones[fila.id_location] = fila
            # El siguiente nivel: los padres que todavia no estan.
            pendientes = {
                fila.id_location_reference for fila in filas
                if fila.id_location_reference
                and fila.id_location_reference not in self._ubicaciones
            }

        faltan_tipos = {
            u.id_location_type for u in self._ubicaciones.values()
            if u.id_location_type and u.id_location_type not in self._tipos
        }
        if faltan_tipos:
            for tipo in self._db.scalars(
                select(LocationType).where(
                    LocationType.id_location_type.in_(list(faltan_tipos)))
            ).all():
                self._tipos[tipo.id_location_type] = tipo

    def ubicacion(self, id_location):
        if not id_location:
            return None
        if id_location not in self._ubicaciones:
            # Una que no se precargo: se trae sola en vez de devolver None y
            # dejar la pantalla sin sitio, que seria un dato perdido por una
            # optimizacion.
            self.precargar([id_location])
        return self._ubicaciones.get(int(id_location))

    def ruta(self, id_location) -> dict:
        """La rama completa, del almacen a la balda.

        "Rack A-1" no dice donde esta el rack. Con dos naves hay un Rack A-1 en
        cada una, asi que la descripcion sola es una pista y no una respuesta.

        Se sube con el mismo tope y la misma guardia contra ciclos que
        `resolve_warehouse`: un padre mal capturado que apunte a su propio hijo
        colgaria la consulta en vez de dar un dato raro.
        """
        vacia = {"segments": [], "label": None, "id_warehouse": None,
                 "warehouse_description": None}
        if not id_location:
            return vacia
        id_location = int(id_location)
        if id_location in self._rutas:
            return self._rutas[id_location]

        actual = self.ubicacion(id_location)
        if actual is None:
            return vacia

        segmentos = []
        id_almacen = None
        descripcion_almacen = None
        vistos = set()
        for _ in range(MAX_LOCATION_DEPTH):
            if actual is None or actual.id_location in vistos:
                break
            vistos.add(actual.id_location)
            tipo = self._tipos.get(actual.id_location_type)
            es_almacen = bool(getattr(tipo, "is_warehouse", False))
            if es_almacen and id_almacen is None:
                id_almacen = actual.id_location
                descripcion_almacen = actual.location_description
            segmentos.append({
                "id_location": actual.id_location,
                "location_description": actual.location_description,
                "location_type": getattr(tipo, "location_type_description", None),
                "is_warehouse": es_almacen,
            })
            if actual.id_location_reference is None:
                break
            actual = self.ubicacion(actual.id_location_reference)

        # Se recorrio de la hoja a la raiz; se lee al contrario.
        segmentos.reverse()
        ruta = {
            "segments": segmentos,
            "label": " > ".join(s["location_description"] or "" for s in segmentos) or None,
            "id_warehouse": id_almacen,
            "warehouse_description": descripcion_almacen,
        }
        self._rutas[id_location] = ruta
        return ruta


def _descendientes(db, id_location) -> list[int]:
    """La ubicacion pedida y todo lo que cuelga de ella.

    Filtrar por "Almacen Central" tiene que traer lo que esta en sus racks, no
    solo lo asentado contra el almacen a secas. Sin esto, el filtro por almacen
    devuelve casi nada y parece que el almacen esta vacio cuando lo que pasa es
    que todo esta un nivel mas abajo.
    """
    encontrados = [int(id_location)]
    frontera = [int(id_location)]
    for _ in range(MAX_LOCATION_DEPTH):
        if not frontera:
            break
        hijos = db.scalars(
            select(Location.id_location).where(
                Location.id_location_reference.in_(frontera),
                Location.deletion_date.is_(None),
            )
        ).all()
        # Sin esto, un padre que se apunta a si mismo repite para siempre.
        nuevos = [h for h in hijos if h not in encontrados]
        encontrados.extend(nuevos)
        frontera = nuevos
    return encontrados


def _clasificacion_en_lote(db, productos) -> dict[int, dict]:
    """A que familia pertenece cada producto, de que marca es y en que se mide.

    Todo eso ya estaba en la base, a dos saltos: `product.id_material` lleva a
    `material`, y de ahi salen la familia, la marca y la unidad. El rastreo
    devolvia el codigo y la descripcion, asi que para saber la familia de lo que
    se acababa de encontrar habia que abrir la pantalla de Producto, y de ahi la
    de Material.

    Se resuelve con un `join` para toda la pagina. Antes eran hasta cuatro
    `db.get` por material distinto.

    Sobre las dos familias
    ----------------------
    `product` tiene ademas `id_familia` e `id_marca` propios, sin llave ajena,
    que usa el catalogo publico para agrupar la tienda. Son otra cosa que la
    familia del material: una puede decir "Promociones" y la otra "Herramienta
    electrica".

    No se elige una en silencio. Manda la del material -es la que el almacen usa
    y la unica obligatoria- y si la del catalogo apunta a otra parte se dice, en
    `catalog_mismatch`. Una discrepancia asi es un dato mal capturado y
    esconderla es como no tenerla.
    """
    from app.models.brand import Brand
    from app.models.material import Material
    from app.models.product_family import ProductFamily
    from app.models.unit import Unit

    if not productos:
        return {}

    ids_materiales = {pr.id_material for pr in productos if pr.id_material}
    por_material: dict[int, dict] = {}
    if ids_materiales:
        filas = db.execute(
            select(
                Material.id_material, Material.material_description,
                ProductFamily.id_product_family, ProductFamily.product_family_description,
                Brand.id_brand, Brand.brand_description,
                Unit.id_unit, Unit.unit_name,
                # El tipo. Faltaba, asi que la clasificacion se leia
                # "familia > marca > material" y el segundo nivel -el que
                # distingue un desarmador plano de uno de cruz- no aparecia en
                # ningun sitio.
                MaterialType.id_material_type,
                MaterialType.material_type_description,
                # La foto del material, que heredan los productos sin foto propia.
                Material.path_imagen,
            )
            .select_from(Material)
            .outerjoin(ProductFamily,
                       ProductFamily.id_product_family == Material.id_product_family)
            .outerjoin(Brand, Brand.id_brand == Material.id_brand)
            .outerjoin(Unit, Unit.id_unit == Material.id_unit)
            .outerjoin(MaterialType,
                       MaterialType.id_material_type == Material.id_material_type)
            .where(Material.id_material.in_(list(ids_materiales)))
        ).all()
        for (id_material, material, id_familia, familia,
             id_marca, marca, id_unidad, unidad,
             id_tipo, tipo, foto_material) in filas:
            por_material[id_material] = {
                "material_path_imagen": foto_material,
                "id_material": id_material, "material": material,
                "id_product_family": id_familia, "family": familia,
                "id_material_type": id_tipo, "material_type": tipo,
                "id_brand": id_marca, "brand": marca,
                "id_unit": id_unidad, "unit": unidad,
            }

    # Las familias y marcas del catalogo publico, solo las que hacen falta para
    # decidir si discrepan.
    otras_familias = {pr.id_familia for pr in productos if pr.id_familia}
    otras_marcas = {pr.id_marca for pr in productos if pr.id_marca}
    nombre_familia = {}
    if otras_familias:
        nombre_familia = dict(db.execute(
            select(ProductFamily.id_product_family,
                   ProductFamily.product_family_description)
            .where(ProductFamily.id_product_family.in_(list(otras_familias)))
        ).all())
    nombre_marca = {}
    if otras_marcas:
        nombre_marca = dict(db.execute(
            select(Brand.id_brand, Brand.brand_description)
            .where(Brand.id_brand.in_(list(otras_marcas)))
        ).all())

    VACIA = {
        "id_material": None, "material": None,
        "material_path_imagen": None,
        "id_material_type": None, "material_type": None,
        "id_product_family": None, "family": None,
        "id_brand": None, "brand": None,
        "id_unit": None, "unit": None,
    }
    salida = {}
    for producto in productos:
        base = dict(por_material.get(producto.id_material) or VACIA)
        discrepancias = {}
        if producto.id_familia and producto.id_familia != base["id_product_family"]:
            discrepancias["family"] = {
                "id_product_family": producto.id_familia,
                "family": nombre_familia.get(producto.id_familia),
            }
        if producto.id_marca and producto.id_marca != base["id_brand"]:
            discrepancias["brand"] = {
                "id_brand": producto.id_marca,
                "brand": nombre_marca.get(producto.id_marca),
            }
        base["catalog_mismatch"] = discrepancias or None
        salida[producto.id_product] = base
    return salida


def _catalogos(db, ids_productos, ubicaciones: "CacheDeUbicaciones") -> dict:
    """Las familias, marcas y almacenes que de verdad tienen algo.

    Alimenta los filtros de la pantalla. Se calculan sobre lo que el usuario
    puede ver, no sobre los catalogos completos, para que ninguna opcion del
    desplegable devuelva cero resultados: un filtro que ofrece treinta familias
    y veintiocho estan vacias hace perder mas tiempo del que ahorra.
    """
    from app.models.brand import Brand
    from app.models.material import Material
    from app.models.product_family import ProductFamily

    if not ids_productos:
        return {"families": [], "brands": [], "warehouses": [],
                "materials": [], "locations": []}

    filas = db.execute(
        select(
            ProductFamily.id_product_family, ProductFamily.product_family_description,
            Brand.id_brand, Brand.brand_description,
            func.count(Product.id_product),
        )
        .select_from(Product)
        .join(Material, Material.id_material == Product.id_material)
        .join(ProductFamily, ProductFamily.id_product_family == Material.id_product_family)
        .join(Brand, Brand.id_brand == Material.id_brand)
        .where(Product.id_product.in_(list(ids_productos)))
        .group_by(
            ProductFamily.id_product_family, ProductFamily.product_family_description,
            Brand.id_brand, Brand.brand_description,
        )
    ).all()

    familias: dict[int, dict] = {}
    marcas: dict[int, dict] = {}
    for id_familia, familia, id_marca, marca, cuantos in filas:
        entrada = familias.setdefault(
            id_familia, {"id_product_family": id_familia, "family": familia, "products": 0})
        entrada["products"] += int(cuantos or 0)
        entrada = marcas.setdefault(
            id_marca, {"id_brand": id_marca, "brand": marca, "products": 0})
        entrada["products"] += int(cuantos or 0)

    # Los almacenes salen de donde hay existencia, subiendo por el arbol: una
    # nave sin nada dentro no es un sitio donde buscar.
    almacenes: dict[int, dict] = {}
    con_existencia = db.scalars(
        select(InventoryStock.id_location)
        .where(InventoryStock.id_product.in_(list(ids_productos)),
               InventoryStock.quantity > 0)
        .distinct()
    ).all()
    ubicaciones.precargar(con_existencia)
    for id_ubicacion in con_existencia:
        ruta = ubicaciones.ruta(id_ubicacion)
        if ruta["id_warehouse"] is None:
            continue
        almacenes.setdefault(ruta["id_warehouse"], {
            "id_location": ruta["id_warehouse"],
            "location_description": ruta["warehouse_description"],
        })

    # Los materiales que de verdad tienen producto. El servidor ya aceptaba
    # `id_material` y el catalogo no lo ofrecia, asi que la pantalla no podia
    # filtrar por el nivel por el que la gente busca: "ARCO CON SEGUETA" y no
    # "familia 37".
    materiales = [
        {"id_material": int(id_material), "material": descripcion,
         "products": int(cuantos or 0)}
        for id_material, descripcion, cuantos in db.execute(
            select(Material.id_material, Material.material_description,
                   func.count(Product.id_product))
            .select_from(Product)
            .join(Material, Material.id_material == Product.id_material)
            .where(Product.id_product.in_(list(ids_productos)))
            .group_by(Material.id_material, Material.material_description)
        ).all()
    ]

    # Todas las ubicaciones con existencia, no solo el almacen de arriba. El
    # filtro del servidor ya incluye lo que cuelga debajo de la que se elija, asi
    # que ofrecer solo las dos naves dejaba 23 ubicaciones sin poder pedirse.
    sitios = []
    for id_ubicacion in con_existencia:
        nodo = ubicaciones.ubicacion(id_ubicacion)
        if nodo is None:
            continue
        ruta = ubicaciones.ruta(id_ubicacion)
        sitios.append({
            "id_location": int(id_ubicacion),
            "location_description": nodo.location_description,
            # La ruta entera: "B1-P2-D-E1" no dice de que nave es, y con dos
            # naves hay un E1 en cada una.
            "path_label": ruta.get("path_label") or nodo.location_description,
            "id_warehouse": ruta.get("id_warehouse"),
            "warehouse_description": ruta.get("warehouse_description"),
        })

    return {
        "families": sorted(familias.values(), key=lambda x: (x["family"] or "").lower()),
        "brands": sorted(marcas.values(), key=lambda x: (x["brand"] or "").lower()),
        "warehouses": sorted(
            almacenes.values(), key=lambda x: (x["location_description"] or "").lower()),
        "materials": sorted(materiales, key=lambda x: (x["material"] or "").lower()),
        "locations": sorted(sitios, key=lambda x: (x["path_label"] or "").lower()),
    }


def _entero_o_nada(valor):
    """Un filtro vacio no filtra; uno mal escrito tampoco debe reventar.

    Los filtros llegan de la barra de direcciones -"", "3", "abc"- y un 500 por
    un parametro con basura es peor que ignorarlo: la pantalla se queda en
    blanco sin decir por que.
    """
    try:
        return int(str(valor).strip()) if str(valor or "").strip() else None
    except (TypeError, ValueError):
        return None


def _pagina(pagina, por_pagina) -> tuple[int, int]:
    """La pagina pedida, acotada.

    `por_pagina` tiene tope porque llega del cliente: sin el, `per_page=100000`
    convierte una consulta barata en una que arma cien mil diccionarios y tumba
    el proceso. El tope y el valor por omision son numeros distintos: la pantalla
    puede pedir mas de lo normal, pero no cualquier cosa.
    """
    numero = _entero_o_nada(pagina) or 1
    tamano = _entero_o_nada(por_pagina) or RESULTADOS_POR_PAGINA
    return max(1, numero), max(1, min(tamano, TOPE_POR_PAGINA))


def localizar(consulta: str, user_data: dict, *, proposito: str | None = None,
              con_piezas: bool = True, id_familia=None, id_marca=None,
              id_material=None, id_ubicacion=None, estado_pieza: str | None = None,
              pagina=1, por_pagina=None) -> dict:
    """Busca en el almacen y devuelve todo lo que se sabe de cada coincidencia.

    Busca por codigo, descripcion y etiqueta de pieza. La etiqueta se incluye
    porque es lo que esta pegado en la herramienta: quien la tiene en la mano lee
    ese numero, no el codigo del producto.

    Los filtros
    -----------
    `id_familia`, `id_marca` e `id_material` recortan por la clasificacion, que
    vive en `material`. `id_ubicacion` recorta por sitio e incluye lo que cuelga
    de el -filtrar por una nave tiene que traer lo de sus racks-. `estado_pieza`
    deja solo los productos con al menos una pieza en ese estado.

    Se filtra en el servidor y no en la pantalla a proposito: filtrando despues,
    el conteo, el aviso de "hay mas resultados" y los desplegables hablan de un
    conjunto distinto del que se ve, y no hay forma de saber cual de los tres
    numeros es el bueno.

    Como esta escrita, y por que asi
    --------------------------------
    Todo lo que cuelga de un producto se pide EN LOTE para la pagina completa.
    Medido antes de reescribirla, con 5000 productos en la base: 271 consultas
    para devolver 40 resultados -siete por producto- y casi un segundo de reloj,
    del que solo un tercio era SQL; el resto era el coste de dar 271 vueltas a
    la base. En una pantalla que busca mientras se escribe eso no se sostiene.

    El alcance se resuelve en el `join` con la factura, no con un `db.get` por
    producto: en una base donde cada producto tiene su factura, aquello era una
    consulta por coincidencia -miles- antes incluso de recortar a la pagina.
    """
    texto = str(consulta or "").strip()
    id_familia = _entero_o_nada(id_familia)
    id_marca = _entero_o_nada(id_marca)
    id_material = _entero_o_nada(id_material)
    id_ubicacion = _entero_o_nada(id_ubicacion)
    estado_pieza = (estado_pieza or "").strip() or None
    numero_de_pagina, tamano_de_pagina = _pagina(pagina, por_pagina)

    sin_restriccion = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
    proyecto = _actor_project_id(user_data)

    with transaction_context() as db:
        from app.models.inventory_asset import InventoryAsset

        # Solo identificador y proyecto, no el producto entero.
        #
        # Medido: buscar algo que coincide con mil productos tardaba 458 ms de
        # los que 108 eran SQL. El resto era construir mil objetos ORM completos
        # para acabar pintando cuarenta. Aqui se traen tuplas -baratas- y se
        # hidratan solo los de la pagina.
        #
        # El proyecto de la factura viaja en la misma fila. Es lo que decide el
        # alcance, y traerlo aqui evita una consulta por coincidencia.
        query = (
            select(Product.id_product, Invoice.id_proyect)
            .outerjoin(Invoice, Invoice.id_invoice == Product.id_invoice)
            .where(Product.deletion_date.is_(None))
        )
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
            productos_con_esa_etiqueta = set(con_esa_etiqueta)
            condiciones = [
                Product.product_code.ilike(patron),
                Product.descripcion.ilike(patron),
            ]
            if con_esa_etiqueta:
                condiciones.append(Product.id_product.in_(list(productos_con_esa_etiqueta)))
            query = query.where(or_(*condiciones))
        if proposito:
            query = query.where(Product.stock_purpose == proposito)

        # El orden es por descripcion y no por identificador: la pantalla es
        # una lista que se lee, y el orden de captura no significa nada para
        # quien la lee.
        encontrados = db.execute(
            query.order_by(Product.descripcion, Product.id_product)
        ).all()

        ubicaciones = CacheDeUbicaciones(db)

        # El alcance se aplica antes que los filtros: los desplegables no deben
        # ofrecer una familia que solo existe en proyectos ajenos.
        visibles: list[int] = []
        proyecto_de: dict[int, int | None] = {}
        omitidos_por_alcance = 0
        for id_producto, del_proyecto in encontrados:
            if not sin_restriccion and del_proyecto != proyecto:
                # El almacen guarda mercancia de varios proyectos. Se cuenta lo
                # que se oculta en vez de callarlo: quien busca algo que existe
                # y no lo ve merece saber que hay resultados fuera de su alcance.
                omitidos_por_alcance += 1
                continue
            visibles.append(id_producto)
            proyecto_de[id_producto] = del_proyecto

        # Los desplegables, sobre lo que encontro el texto y antes de recortar
        # por familia, marca o sitio. Calculados despues, elegir una familia
        # vaciaba las otras listas -y la propia, cuando la eleccion se quedaba
        # sin resultados-, asi que el filtro activo desaparecia del desplegable
        # que lo mostraba.
        catalogo = _catalogos(db, visibles, ubicaciones)

        # Los filtros, cada uno como un conjunto de identificadores. Se
        # intersectan en Python en vez de encadenarse en el SQL porque el
        # alcance ya recorto la lista y volver a la base por cada filtro
        # devolveria tambien lo que el alcance escondio.
        permitidos: set[int] | None = None

        def _recortar(ids):
            nonlocal permitidos
            nuevos = set(int(i) for i in ids)
            permitidos = nuevos if permitidos is None else (permitidos & nuevos)

        if id_familia or id_marca or id_material:
            from app.models.material import Material

            por_clasificacion = select(Product.id_product).join(
                Material, Material.id_material == Product.id_material)
            if id_familia:
                por_clasificacion = por_clasificacion.where(
                    Material.id_product_family == id_familia)
            if id_marca:
                por_clasificacion = por_clasificacion.where(Material.id_brand == id_marca)
            if id_material:
                por_clasificacion = por_clasificacion.where(Material.id_material == id_material)
            _recortar(db.scalars(por_clasificacion).all())

        if id_ubicacion:
            # Con existencia ahi, no "asentado ahi": un producto cuya ficha dice
            # Nave A pero cuyas unidades estan todas en Nave B no esta en Nave
            # A, y buscarlo ahi es ir a un sitio donde no hay nada.
            dentro = _descendientes(db, id_ubicacion)
            _recortar(db.scalars(
                select(InventoryStock.id_product).where(
                    InventoryStock.id_location.in_(dentro),
                    InventoryStock.quantity > 0,
                )
            ).all())

        if estado_pieza:
            _recortar(db.scalars(
                select(InventoryAsset.id_product).where(
                    InventoryAsset.status == estado_pieza,
                    InventoryAsset.deletion_date.is_(None),
                )
            ).all())

        if permitidos is not None:
            visibles = [i for i in visibles if i in permitidos]

        # La pagina. Antes se cortaba en cuarenta y se avisaba "afina la
        # busqueda", que no es una respuesta cuando el filtro ya esta puesto y
        # aun hay doscientas coincidencias.
        total_de_coincidencias = len(visibles)
        paginas = max(1, -(-total_de_coincidencias // tamano_de_pagina))
        numero_de_pagina = min(numero_de_pagina, paginas)
        desde = (numero_de_pagina - 1) * tamano_de_pagina
        ids = visibles[desde:desde + tamano_de_pagina]

        # Ahora si, los productos completos: solo los de la pagina.
        por_id = {
            pr.id_product: pr for pr in db.scalars(
                select(Product).where(Product.id_product.in_(ids))
            ).all()
        } if ids else {}
        # Se recorre `ids`, que conserva el orden de la consulta; el `IN` no
        # promete ninguno.
        productos = [por_id[i] for i in ids if i in por_id]

        # Todo lo que cuelga de la pagina, en lote.
        ubicaciones.precargar(
            {pr.id_location for pr in productos if pr.id_location})
        clasificaciones = _clasificacion_en_lote(db, productos)
        existencias = _existencias_en_lote(db, ids, ubicaciones)
        historias = _historia_en_lote(db, ids)
        ultimos = _ultimo_movimiento_en_lote(db, ids)
        prestados = _prestado_en_lote(db, ids)
        piezas_por_producto = (
            _piezas_en_lote(db, productos, ubicaciones, consulta=texto)
            if con_piezas else {}
        )
        # Solo las bitacoras de las piezas que coincidieron: la de las treinta
        # piezas de un producto para ver una son treinta lecturas que nadie mira.
        bitacoras = _bitacoras_en_lote(db, [
            pieza["id_inventory_asset"]
            for piezas in piezas_por_producto.values()
            for pieza in piezas
            if pieza.get("matched")
        ], ubicaciones)

        resultados = []
        for producto in productos:
            del_proyecto = proyecto_de.get(producto.id_product)
            sitios = existencias.get(producto.id_product, [])
            serializado = str(producto.tracking_mode or "") == "serializado"
            piezas = piezas_por_producto.get(producto.id_product, [])
            for pieza in piezas:
                if pieza.get("matched"):
                    pieza["timeline"] = bitacoras.get(pieza["id_inventory_asset"], [])
            coincidentes = [p["asset_tag"] for p in piezas if p.get("matched")]

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
                "path_imagen": producto.path_imagen or (
                    clasificaciones.get(producto.id_product) or {}
                ).get("material_path_imagen"),
                "tracking_mode": producto.tracking_mode,
                "stock_purpose": producto.stock_purpose,
                # El estatus tal como lo escribio el sistema anterior --
                # ENTRADA, SALIDA, DANADO, DESTRUCCION, EXTRAVIADO--, que es el
                # unico sitio donde estan los seis valores completos: el
                # catalogo `inventory_status` no tiene fila para EXTRAVIADO, asi
                # que 65 productos lo traen aqui y con el FK en nulo.
                "product_status": producto.product_status,
                "id_proyect": del_proyecto,
                # A que familia pertenece, de que marca es, de que material y en
                # que unidad se mide. Estaba a dos saltos en la base y obligaba a
                # abrir dos pantallas mas para saber que se habia encontrado.
                "classification": clasificaciones.get(producto.id_product),
                # Donde vive segun su ficha, con la rama completa. Es distinto de
                # `locations`, que es donde estan de verdad las unidades: cuando
                # no coinciden, eso es exactamente lo que hay que ver.
                "home_location": ubicaciones.ruta(producto.id_location),
                "total": sum(u["quantity"] for u in sitios),
                "stock_balance": int(producto.cantidad or 0),
                # Lo que esta fuera y quien lo tiene. Sin esto un producto
                # prestado se veia con cero en todo y sin ubicacion: el saldo
                # bajo -correctamente- y nada decia donde fue.
                "on_loan": prestados.get(producto.id_product),
                "locations": sitios,
                "history": historias.get(producto.id_product, {}),
                "last_movement": ultimos.get(producto.id_product),
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
            # Lo que se aplico, devuelto tal cual. La pantalla lo usa para
            # pintar los filtros activos sin tener que confiar en su propio
            # estado, que es lo que se desincroniza al recargar con la
            # direccion escrita a mano.
            "filters": {
                "id_product_family": id_familia,
                "id_brand": id_marca,
                "id_material": id_material,
                "id_location": id_ubicacion,
                "asset_status": estado_pieza,
            },
            # Con que se puede filtrar y cuanto hay detras de cada opcion. Se
            # calcula sobre todo lo visible -no sobre la pagina- para que un
            # desplegable no ofrezca opciones vacias.
            "catalog": catalogo,
            "items": resultados,
            "total": len(resultados),
            # Cuantos coinciden en total, aunque solo se pinte una pagina.
            "matches": total_de_coincidencias,
            "page": numero_de_pagina,
            "per_page": tamano_de_pagina,
            "pages": paginas,
            "hidden_by_scope": omitidos_por_alcance,
            # Se conserva por compatibilidad con la pantalla anterior: ahora
            # significa "hay mas paginas", no "se perdieron resultados".
            "truncated": numero_de_pagina < paginas,
        }
