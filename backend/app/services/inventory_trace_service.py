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
from app.models.location_type import LocationType
from app.models.product import Product
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


def _ubicaciones(db, id_product, cache: dict | None = None) -> list[dict]:
    """Donde esta repartido, sin las ubicaciones donde ya no queda nada.

    Cada renglon lleva la rama completa -"Almacen Central > Pasillo 3 > Rack
    A-1"-. Antes solo llevaba el almacen y la ubicacion final, que en un almacen
    de dos niveles alcanza y en uno de cuatro deja a medias.
    """
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
        ruta = _ruta_de_ubicacion(db, ubicacion, cache)
        salida.append({
            **_warehouse_payload(db, ubicacion),
            "id_module": ubicacion.id_module,
            "quantity": int(fila.quantity or 0),
            "path": ruta["segments"],
            "path_label": ruta["label"],
        })
    return salida


def _piezas(db, id_product, *, consulta: str = "", codigo_del_producto: str = "",
            cache_ruta: dict | None = None) -> list[dict]:
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
            # La rama completa: una pieza en "Rack A-1" no se encuentra si hay
            # un Rack A-1 en cada nave.
            ruta = _ruta_de_ubicacion(db, ubicacion, cache_ruta)
            pieza["location_path"] = ruta["segments"]
            pieza["location_path_label"] = ruta["label"]
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


def _ruta_de_ubicacion(db, location, cache: dict | None = None) -> dict:
    """La ubicacion con su rama completa, del almacen hacia abajo.

    "Rack A-1" no dice donde esta el rack. Con cuatro naves y dieciocho racks,
    la descripcion sola obliga a saberse el almacen de memoria, y quien va a
    buscar la pieza no se lo sabe. Se devuelve la rama entera -"Almacen Central
    > Pasillo 3 > Rack A-1"- porque es la unica forma de que "lugar" sea una
    respuesta y no una pista.

    Se sube por `id_location_reference` con el mismo tope y la misma guardia
    contra ciclos que `resolve_warehouse`: un padre mal capturado que apunte a
    su propio hijo colgaria la consulta en vez de dar un dato raro.
    """
    if location is None:
        return {"segments": [], "label": None, "id_warehouse": None,
                "warehouse_description": None}

    if cache is not None and location.id_location in cache:
        return cache[location.id_location]

    segmentos = []
    id_almacen = None
    descripcion_almacen = None
    actual = location
    vistos = set()
    for _ in range(MAX_LOCATION_DEPTH):
        if actual is None or actual.id_location in vistos:
            break
        vistos.add(actual.id_location)
        tipo = db.get(LocationType, actual.id_location_type)
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
        actual = db.get(Location, actual.id_location_reference)

    # Se recorrio de la hoja a la raiz; se lee al contrario.
    segmentos.reverse()
    ruta = {
        "segments": segmentos,
        "label": " > ".join(s["location_description"] or "" for s in segmentos) or None,
        "id_warehouse": id_almacen,
        "warehouse_description": descripcion_almacen,
    }
    if cache is not None:
        cache[location.id_location] = ruta
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


def _clasificacion(db, producto, cache: dict | None = None) -> dict:
    """A que familia pertenece, de que marca es y en que unidad se mide.

    Todo eso ya estaba en la base, a dos saltos: `product.id_material` lleva a
    `material`, y de ahi salen la familia, la marca y la unidad. El rastreo
    devolvia el codigo y la descripcion, asi que para saber la familia de lo que
    se acababa de encontrar habia que abrir la pantalla de Producto, y de ahi la
    de Material.

    Sobre las dos familias
    ----------------------
    `product` tiene ademas `id_familia` e `id_marca` propios, sin llave ajena,
    que usa el catalogo publico para agrupar la tienda. Son otra cosa que la
    familia del material: una puede decir "Promociones" y la otra "Herramienta
    electrica".

    No se elige una en silencio. Manda la del material -es la que el almacen
    usa y la unica obligatoria- y si la del catalogo apunta a otra parte se
    dice, en `catalog_mismatch`. Un discrepancia asi es un dato mal capturado y
    esconderla es como no tenerla.
    """
    from app.models.brand import Brand
    from app.models.material import Material
    from app.models.product_family import ProductFamily
    from app.models.unit import Unit

    llave = producto.id_material
    if cache is not None and llave in cache:
        base = dict(cache[llave])
    else:
        material = db.get(Material, producto.id_material) if producto.id_material else None
        familia = (
            db.get(ProductFamily, material.id_product_family)
            if material and material.id_product_family else None
        )
        marca = db.get(Brand, material.id_brand) if material and material.id_brand else None
        unidad = db.get(Unit, material.id_unit) if material and material.id_unit else None
        base = {
            "id_material": getattr(material, "id_material", None),
            "material": getattr(material, "material_description", None),
            "id_product_family": getattr(familia, "id_product_family", None),
            "family": getattr(familia, "product_family_description", None),
            "id_brand": getattr(marca, "id_brand", None),
            "brand": getattr(marca, "brand_description", None),
            "id_unit": getattr(unidad, "id_unit", None),
            "unit": getattr(unidad, "unit_name", None),
        }
        if cache is not None:
            cache[llave] = dict(base)

    # La familia y la marca del catalogo publico, solo cuando discrepan.
    discrepancias = {}
    if producto.id_familia and producto.id_familia != base["id_product_family"]:
        otra = db.get(ProductFamily, producto.id_familia)
        discrepancias["family"] = {
            "id_product_family": producto.id_familia,
            "family": getattr(otra, "product_family_description", None),
        }
    if producto.id_marca and producto.id_marca != base["id_brand"]:
        otra = db.get(Brand, producto.id_marca)
        discrepancias["brand"] = {
            "id_brand": producto.id_marca,
            "brand": getattr(otra, "brand_description", None),
        }
    base["catalog_mismatch"] = discrepancias or None
    return base


def _catalogos(db, ids_productos: list[int]) -> dict:
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
        return {"families": [], "brands": [], "warehouses": []}

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
        .where(Product.id_product.in_(ids_productos))
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
    cache: dict = {}
    con_existencia = db.scalars(
        select(InventoryStock.id_location)
        .where(InventoryStock.id_product.in_(ids_productos), InventoryStock.quantity > 0)
        .distinct()
    ).all()
    for id_ubicacion in con_existencia:
        ruta = _ruta_de_ubicacion(db, db.get(Location, id_ubicacion), cache)
        if ruta["id_warehouse"] is None:
            continue
        almacenes.setdefault(ruta["id_warehouse"], {
            "id_location": ruta["id_warehouse"],
            "location_description": ruta["warehouse_description"],
        })

    return {
        "families": sorted(familias.values(), key=lambda x: (x["family"] or "").lower()),
        "brands": sorted(marcas.values(), key=lambda x: (x["brand"] or "").lower()),
        "warehouses": sorted(
            almacenes.values(), key=lambda x: (x["location_description"] or "").lower()),
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


def localizar(consulta: str, user_data: dict, *, proposito: str | None = None,
              con_piezas: bool = True, id_familia=None, id_marca=None,
              id_material=None, id_ubicacion=None, estado_pieza: str | None = None) -> dict:
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
    """
    texto = str(consulta or "").strip()
    id_familia = _entero_o_nada(id_familia)
    id_marca = _entero_o_nada(id_marca)
    id_material = _entero_o_nada(id_material)
    id_ubicacion = _entero_o_nada(id_ubicacion)
    estado_pieza = (estado_pieza or "").strip() or None
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

        # El orden es por descripcion y no por identificador: la pantalla es
        # una lista que se lee, y el orden de captura no significa nada para
        # quien la lee.
        encontrados = db.scalars(
            query.order_by(Product.descripcion, Product.id_product)
        ).all()

        # Caches por consulta. Sin ellas, cuarenta productos del mismo material
        # resuelven cuarenta veces la misma familia, marca y unidad.
        cache_clasificacion: dict = {}
        cache_ruta: dict = {}

        # El alcance se aplica antes que los filtros: los desplegables no deben
        # ofrecer una familia que solo existe en proyectos ajenos.
        visibles = []
        omitidos_por_alcance = 0
        for producto in encontrados:
            factura = db.get(Invoice, producto.id_invoice) if producto.id_invoice else None
            del_proyecto = getattr(factura, "id_proyect", None)
            if not sin_restriccion and del_proyecto != proyecto:
                # El almacen guarda mercancia de varios proyectos. Se cuenta lo
                # que se oculta en vez de callarlo: quien busca algo que existe
                # y no lo ve merece saber que hay resultados fuera de su alcance.
                omitidos_por_alcance += 1
                continue
            visibles.append((producto, del_proyecto))

        # Los desplegables, sobre lo que encontro el texto y antes de recortar
        # por familia, marca o sitio. Calculados despues, elegir una familia
        # vaciaba las otras listas -y la propia, cuando la eleccion se quedaba
        # sin resultados-, asi que el filtro activo desaparecia del desplegable
        # que lo mostraba.
        catalogo = _catalogos(db, [pr.id_product for pr, _ in visibles])

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
            from app.models.inventory_asset import InventoryAsset

            _recortar(db.scalars(
                select(InventoryAsset.id_product).where(
                    InventoryAsset.status == estado_pieza,
                    InventoryAsset.deletion_date.is_(None),
                )
            ).all())

        if permitidos is not None:
            visibles = [par for par in visibles if par[0].id_product in permitidos]

        resultados = []
        for producto, del_proyecto in visibles:
            if len(resultados) >= MAXIMO_RESULTADOS:
                break

            serializado = str(producto.tracking_mode or "") == "serializado"
            ubicaciones = _ubicaciones(db, producto.id_product, cache=cache_ruta)
            piezas = _piezas(
                db, producto.id_product, consulta=texto,
                codigo_del_producto=producto.product_code or "",
                cache_ruta=cache_ruta,
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
                # A que familia pertenece, de que marca es, de que material y en
                # que unidad se mide. Estaba a dos saltos en la base y obligaba a
                # abrir dos pantallas mas para saber que se habia encontrado.
                "classification": _clasificacion(db, producto, cache_clasificacion),
                # Donde vive segun su ficha, con la rama completa. Es distinto de
                # `locations`, que es donde estan de verdad las unidades: cuando
                # no coinciden, eso es exactamente lo que hay que ver.
                "home_location": _ruta_de_ubicacion(
                    db, db.get(Location, producto.id_location) if producto.id_location else None,
                    cache_ruta,
                ),
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
            # Cuantos coinciden en total, aunque solo se pinten los primeros.
            "matches": len(visibles),
            "hidden_by_scope": omitidos_por_alcance,
            "truncated": len(resultados) >= MAXIMO_RESULTADOS,
        }
