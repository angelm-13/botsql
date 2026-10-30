"""La lista de necesidades de un proyecto, y lo que falta comprar.

Dos vistas de la misma tabla (`proyect_material_need`):

* **Por proyecto**: el supervisor declara lo que necesita su proyecto con sus
  propias palabras y ve, si lo vinculo al catalogo, cuanto hay en el almacen.
* **Por comprar**: quien compra ve las necesidades de TODOS los proyectos juntas.
  Un mismo material pedido por tres proyectos es una sola compra.

Texto libre, y el catalogo como ayuda
-------------------------------------
El catalogo de Adser es de herramienta y equipo; lo que una obra consume casi
nunca esta ahi. Por eso un renglon se describe con texto y el vinculo al catalogo
es opcional. Al capturar, `suggest_materials` ofrece lo que parece existir; si el
supervisor no lo vincula, el renglon sale "por revisar" en `to_buy` hasta que
alguien que conoce el almacen lo vincule (`link_need`) o confirme la compra
(`confirm_buy`).

Buscar por texto NO decide nada
-------------------------------
Las sugerencias son eso, sugerencias: el texto del supervisor casi nunca coincide
palabra por palabra con el catalogo ("esmeril angular" puede estar como
"amoladora"). Por eso ningun renglon se oculta ni se da por cubierto por
parecerse a algo; el peor caso es una revision de mas, nunca una compra de mas.

La existencia no se reserva
---------------------------
"Hay N" es la existencia de hoy, sin descontar lo que piden otros proyectos.
Reservar seria decidir quien se queda con que, y eso es del almacen.
"""
from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime, timezone

from sqlalchemy import func, or_, select

from app.models import (
    EntityPermission, InventoryStock, Material, Product, Proyect,
    ProyectMaterialNeed, PurchaseOrder, PurchaseOrderLine, Unit,
)
from app.models.session import transaction_context
from app.models.user import User
from app.services.inventory_service import has_capability
from app.services.project_management_service import avisar_material_solicitado, require_project_access
from app.utils.errors import AppError

# Un proyecto cerrado o negado ya no compra: sus necesidades abiertas son
# residuo, y contarlas inflaria lo que parece faltar.
PROYECTOS_QUE_YA_NO_COMPRAN = ("denied", "collected", "completed")

PURCHASE_CAPABILITY = "purchase_planning"
# Quien compra NO autoriza ni recibe lo comprado (separacion de funciones que el
# servicio de ordenes hace cumplir): las dos capacidades separan a Compras de
# Gerencia y de Almacen, que tambien ven "Por comprar".
NOT_A_BUYER_CAPABILITIES = ("purchase_authorize", "purchase_receive")
# Una orden cancelada suelta lo que sostenia; todo lo demas -incluida una rechazada,
# que quien la armo puede corregir y reenviar- lo sigue sosteniendo.
ORDER_STATES_THAT_RELEASE_NEEDS = ("cancelled",)
NOTE_MAX = 300
DESCRIPTION_MAX = 200
UNIT_MAX = 40
# Una cantidad absurda ("9999999") es casi siempre un error de dedo, no una necesidad.
MAX_QUANTITY = 100000
RETURN_NOTE_MIN = 5

# Las unidades que se aceptan, en vez de texto libre: "kg", "kilo" y "kgs" son lo
# mismo y asi no se agrupan aparte. Se guarda la clave en minusculas.
UNIDADES = (
    "pza", "kg", "g", "m", "cm", "mm", "m2", "m3", "lt", "ml", "galon", "cubeta",
    "caja", "bolsa", "saco", "rollo", "juego", "par", "paquete", "tramo",
)

# Palabras que no distinguen nada al buscar ("disco DE corte").
_PALABRAS_VACIAS = frozenset({
    "los", "las", "del", "con", "sin", "para", "por", "una", "uno", "unos", "unas",
    "que", "mas", "pza", "pzas", "pieza", "piezas",
})


# --- validacion de lo que llega ----------------------------------------------

def _actor(user_data: dict) -> int:
    try:
        id_user = int(user_data.get("id_user") or 0)
    except (TypeError, ValueError):
        id_user = 0
    if not id_user:
        raise AppError("errors.permission_denied", 403)
    return id_user


def _entero_positivo(valor, campo: str) -> int:
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError):
        raise AppError("errors.invalid_field", 400, {"field": campo})
    if numero <= 0:
        raise AppError("errors.invalid_field", 400, {"field": campo})
    return numero


def _fecha_o_nada(valor, campo: str) -> date | None:
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return date.fromisoformat(str(valor).strip()[:10])
    except ValueError:
        raise AppError("errors.invalid_field", 400, {"field": campo})


def _texto(valor, campo: str, largo: int, *, obligatorio: bool = False) -> str | None:
    texto = " ".join(str(valor or "").split())
    if not texto:
        if obligatorio:
            raise AppError("errors.invalid_field", 400, {"field": campo})
        return None
    if len(texto) > largo:
        raise AppError("errors.field_too_long", 400, {
            "field": campo, "max_length": largo, "actual_length": len(texto)})
    return texto


def _cantidad(valor) -> int:
    cantidad = _entero_positivo(valor, "quantity")
    if cantidad > MAX_QUANTITY:
        raise AppError("errors.invalid_field", 400, {
            "field": "quantity", "max": MAX_QUANTITY})
    return cantidad


def _unidad(valor) -> str | None:
    """Una unidad de la lista, o nada. Texto libre no: se presta a tres escrituras."""
    texto = _texto(valor, "unit", UNIT_MAX)
    if texto is None:
        return None
    clave = texto.lower()
    if clave not in UNIDADES:
        raise AppError("errors.invalid_field", 400, {
            "field": "unit", "allowed": list(UNIDADES)})
    return clave


_VOCALES = frozenset("aeiou")


def descripcion_sospechosa(texto) -> str | None:
    """Por que el texto no parece una descripcion, o None si parece una.

    Solo atrapa lo EVIDENTE -"12o3pifsfjg", "asdfgh", "aaaaa"-: sin letras, de menos
    de tres caracteres, con un caracter repetido en serie, o con un tramo de letras
    de cinco o mas sin vocales casi ("pifsfjg"). Probada contra 26 pedidos reales
    (soldadura 6013, tuerca M8x1.25, cable THW calibre 12, electrodo E7018...): no
    rechaza ninguno. NO detecta texto que parece palabra ("hjkl") ni errores de
    dedo: de eso se encarga quien revisa. Ni "THW" ni "THHN" -cables reales- tienen
    vocales, por eso el tramo tiene que ser de cinco y no menos.

    Se repite en el frontend (`utils/descripcionDeNecesidad.js`) para avisar al
    instante; esta es la que cuenta.
    """
    t = _normalizar(texto)
    if len(t.replace(" ", "")) < 3:
        return "too_short"
    if not re.search(r"[a-z]", t):
        return "no_letters"
    if re.search(r"([a-z])\1{3,}", t.replace(" ", "")):
        return "repeated"
    for tramo in re.findall(r"[a-z]+", t):
        if len(tramo) < 5:
            continue
        if sum(1 for c in tramo if c in _VOCALES) / len(tramo) < 0.2:
            return "few_vowels"
        if re.search(r"[^aeiou]{5,}", tramo):
            return "consonants"
    return None


def _descripcion_valida(texto) -> str:
    motivo = descripcion_sospechosa(texto)
    if motivo is not None:
        raise AppError("errors.need_description_invalid", 400, {
            "field": "description", "reason": motivo})
    return texto


# --- buscar por texto --------------------------------------------------------

def _normalizar(texto) -> str:
    """Minusculas, sin acentos ni signos, un solo espacio entre palabras."""
    sin_acentos = unicodedata.normalize("NFD", str(texto or "")).encode(
        "ascii", "ignore").decode("ascii")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sin_acentos.lower()).split())


def _raiz(palabra: str) -> str:
    """Quita el plural mas comun: "taladros" -> "taladro", "discos" -> "disco"."""
    if len(palabra) > 5 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) > 4 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def _palabras(texto) -> list[str]:
    vistas, resultado = set(), []
    for palabra in _normalizar(texto).split():
        if len(palabra) < 3 or palabra in _PALABRAS_VACIAS:
            continue
        raiz = _raiz(palabra)
        if raiz not in vistas:
            vistas.add(raiz)
            resultado.append(raiz)
    return resultado


def _sugerir(db, texto, *, limite: int = 5) -> list[dict]:
    """Lo del catalogo que parece ser lo que el texto describe, con su existencia.

    Una palabra del texto coincide con una del material si esta empieza igual
    ("tornillo" con "TORNILLOS"), no por estar contenida en cualquier parte
    ("arco" no es "marco"). Entran los que coinciden en todas las palabras y, si el
    texto trae dos o mas, los que coinciden en al menos la mitad; primero los
    completos y, entre iguales, el de nombre mas corto (el mas especifico).
    """
    palabras = _palabras(texto)
    if not palabras:
        return []
    minimo = len(palabras) if len(palabras) == 1 else math.ceil(len(palabras) / 2)

    candidatos = []
    filas = db.execute(
        select(Material.id_material, Material.material_description)
        .where(Material.deletion_date.is_(None))
    ).all()
    for id_material, descripcion in filas:
        del_material = _normalizar(descripcion).split()
        aciertos = sum(
            1 for p in palabras if any(w.startswith(p) for w in del_material))
        if aciertos < minimo:
            continue
        candidatos.append((aciertos != len(palabras), -aciertos, len(descripcion or ""),
                           id_material, descripcion))
    candidatos.sort()
    elegidos = candidatos[:limite]

    ids = [c[3] for c in elegidos]
    existencias = _existencias(db, ids)
    unidades = _unidades(db, ids)
    return [
        {"id_material": id_material, "material_description": descripcion,
         "unit": unidades.get(int(id_material)),
         "in_stock": existencias.get(int(id_material), 0),
         "complete_match": not incompleto}
        for incompleto, _a, _l, id_material, descripcion in elegidos
    ]


def _previas(db, texto, *, limite: int = 5) -> list[dict]:
    """Descripciones que alguien ya confirmo como compra y contienen lo que escribe.

    Es vocabulario que ya paso por una revision: sugerirlo hace que lo mismo se escriba
    igual en todos los proyectos y se agrupe en "Por comprar".
    """
    palabras = _palabras(texto)
    if not palabras:
        return []
    filas = db.execute(
        select(ProyectMaterialNeed.description, ProyectMaterialNeed.unit)
        .where(ProyectMaterialNeed.id_material.is_(None),
               ProyectMaterialNeed.review_result == "buy",
               ProyectMaterialNeed.deletion_date.is_(None))
        # La primera escritura confirmada queda como la buena: es la que las demas imitan.
        .order_by(ProyectMaterialNeed.reviewed_date.asc())
    ).all()
    vistas: dict[str, dict] = {}
    for descripcion, unidad in filas:
        clave = _normalizar(descripcion)
        if clave:
            grupo = vistas.setdefault(
                clave, {"description": descripcion, "unit": unidad, "times": 0})
            grupo["times"] += 1
    resultado = [
        g for clave, g in vistas.items()
        if all(any(w.startswith(p) for w in clave.split()) for p in palabras)
    ]
    resultado.sort(key=lambda g: (-g["times"], len(g["description"])))
    return resultado[:limite]


def suggest_materials(texto, user_data: dict) -> dict:
    """Sugerencias para el que captura: el catalogo y lo que ya se pidio antes."""
    _actor(user_data)
    with transaction_context() as db:
        return {"materials": _sugerir(db, texto), "previous": _previas(db, texto)}


# --- existencias y catalogo --------------------------------------------------

def _existencias(db, ids_material) -> dict[int, int]:
    """Cuanto hay de cada material, sumando todos sus productos y todos sus sitios."""
    ids = {int(i) for i in ids_material}
    if not ids:
        return {}
    filas = db.execute(
        select(Product.id_material, func.coalesce(func.sum(InventoryStock.quantity), 0))
        .join(InventoryStock, InventoryStock.id_product == Product.id_product)
        .where(Product.id_material.in_(ids), Product.deletion_date.is_(None))
        .group_by(Product.id_material)
    ).all()
    return {int(id_material): int(total or 0) for id_material, total in filas}


def _material(db, id_material) -> Material:
    material = db.scalars(
        select(Material).where(
            Material.id_material == id_material,
            Material.deletion_date.is_(None),
        )
    ).first()
    if material is None:
        raise AppError("errors.not_found", 404,
                       {"entity": "material", "field": "id_material"})
    return material


def _unidades(db, ids_material) -> dict[int, str | None]:
    ids = {int(i) for i in ids_material}
    if not ids:
        return {}
    filas = db.execute(
        select(Material.id_material, Unit.unit_name)
        .outerjoin(Unit, Unit.id_unit == Material.id_unit)
        .where(Material.id_material.in_(ids))
    ).all()
    return {int(i): nombre for i, nombre in filas}


def _datos_de_materiales(db, ids_material) -> dict[int, dict]:
    ids = {int(i) for i in ids_material}
    if not ids:
        return {}
    descripciones = dict(db.execute(
        select(Material.id_material, Material.material_description)
        .where(Material.id_material.in_(ids))
    ).all())
    unidades = _unidades(db, ids)
    return {
        i: {"id_material": i,
            "material_description": descripciones.get(i),
            "unit": unidades.get(i)}
        for i in ids
    }


def _renglon(need: ProyectMaterialNeed, materiales: dict, existencias: dict) -> dict:
    vinculado = need.id_material is not None
    material = materiales.get(int(need.id_material)) if vinculado else None
    hay = existencias.get(int(need.id_material), 0) if vinculado else None
    fila = need.serialize()
    fila.update({
        "linked": vinculado,
        # Lo que se muestra: el nombre del catalogo si esta vinculado; si no, las
        # palabras del supervisor.
        "display_name": (material or {}).get("material_description") if vinculado
        else need.description,
        "material": material,
        "in_stock": hay,
        # Informativo: contra la existencia de HOY, sin descontar a otros
        # proyectos. Solo tiene sentido si esta vinculado al catalogo.
        "covered_by_stock": (hay >= int(need.quantity)) if vinculado else None,
        # Texto libre que nadie ha revisado todavia.
        "needs_review": (not vinculado) and need.review_result is None,
        # El que reviso no lo entendio: espera a que el supervisor lo corrija.
        "returned": need.review_result == "returned",
    })
    return fila


# --- por proyecto ------------------------------------------------------------

def _necesidad(db, id_need, *, for_update=False) -> ProyectMaterialNeed:
    consulta = select(ProyectMaterialNeed).where(
        ProyectMaterialNeed.id_proyect_material_need == _entero_positivo(id_need, "id"),
        ProyectMaterialNeed.deletion_date.is_(None),
    )
    if for_update:
        consulta = consulta.with_for_update()
    need = db.scalars(consulta).first()
    if need is None:
        raise AppError("errors.resource_not_found", 404)
    return need


def _duplicada(db, id_proyecto, *, id_material=None, descripcion=None, excepto=None):
    """Otro renglon ABIERTO del mismo proyecto que dice lo mismo, o None.

    Dos renglones iguales son una lista que miente: no se sabe cual vale. Se edita
    el que ya esta. Lo vinculado se compara por material; el texto libre, por sus
    palabras normalizadas ("Tornillo " y "tornillo" son lo mismo).
    """
    consulta = select(ProyectMaterialNeed).where(
        ProyectMaterialNeed.id_proyect == id_proyecto,
        ProyectMaterialNeed.need_status == "open",
        ProyectMaterialNeed.deletion_date.is_(None),
    )
    if excepto is not None:
        consulta = consulta.where(
            ProyectMaterialNeed.id_proyect_material_need != excepto)
    if id_material is not None:
        return db.scalars(
            consulta.where(ProyectMaterialNeed.id_material == id_material).limit(1)
        ).first()
    buscada = _normalizar(descripcion)
    for otra in db.scalars(consulta.where(ProyectMaterialNeed.id_material.is_(None))).all():
        if _normalizar(otra.description) == buscada:
            return otra
    return None


def _rechazar_duplicada(otra, **meta):
    raise AppError("errors.need_duplicate_material", 409, {
        "id_proyect_material_need": otra.id_proyect_material_need, **meta})


def needs_on_orders(db, ids_necesidad, *, excepto_orden: int | None = None) -> dict:
    """Que necesidades estan en una orden de compra viva: id -> (id_orden, folio, estado).

    Una necesidad esta en UNA orden a la vez: por eso la pregunta tiene una sola
    respuesta, y por eso quien la pide al capturar una orden nueva se entera de cual
    la tiene.
    """
    ids = {int(i) for i in ids_necesidad if i}
    if not ids:
        return {}
    consulta = (
        select(PurchaseOrderLine.id_proyect_material_need,
               PurchaseOrder.id_purchase_order, PurchaseOrder.folio,
               PurchaseOrder.order_status)
        .join(PurchaseOrder,
              PurchaseOrder.id_purchase_order == PurchaseOrderLine.id_purchase_order)
        .where(
            PurchaseOrderLine.id_proyect_material_need.in_(ids),
            PurchaseOrderLine.deletion_date.is_(None),
            PurchaseOrder.deletion_date.is_(None),
            PurchaseOrder.order_status.notin_(ORDER_STATES_THAT_RELEASE_NEEDS),
        )
    )
    if excepto_orden is not None:
        consulta = consulta.where(PurchaseOrder.id_purchase_order != excepto_orden)
    return {int(n): (int(o), f, e) for n, o, f, e in db.execute(consulta).all()}


def _orden_de(en_orden: dict, id_need) -> dict | None:
    orden = en_orden.get(int(id_need))
    if orden is None:
        return None
    return {"id_purchase_order": orden[0], "folio": orden[1], "order_status": orden[2]}


def list_needs(id_proyect, user_data: dict, *, incluir_canceladas: bool = False) -> dict:
    """Las necesidades de UN proyecto, solo si el actor puede ver ese proyecto."""
    id_proyecto = _entero_positivo(id_proyect, "id_proyect")
    require_project_access(id_proyecto, user_data)
    with transaction_context() as db:
        consulta = select(ProyectMaterialNeed).where(
            ProyectMaterialNeed.id_proyect == id_proyecto,
            ProyectMaterialNeed.deletion_date.is_(None),
        ).order_by(ProyectMaterialNeed.id_proyect_material_need)
        if not incluir_canceladas:
            consulta = consulta.where(ProyectMaterialNeed.need_status == "open")
        necesidades = db.scalars(consulta).all()
        ids = {int(n.id_material) for n in necesidades if n.id_material is not None}
        materiales = _datos_de_materiales(db, ids)
        existencias = _existencias(db, ids)
        # Lo que Compras ya esta comprando, para que el supervisor lo vea sin
        # preguntar: la orden y su estado, no el dinero.
        en_orden = needs_on_orders(db, [n.id_proyect_material_need for n in necesidades])
        items = []
        for n in necesidades:
            fila = _renglon(n, materiales, existencias)
            fila["order"] = _orden_de(en_orden, n.id_proyect_material_need)
            items.append(fila)
        return {"id_proyect": id_proyecto, "items": items}


def create_need(id_proyect, payload: dict, user_data: dict) -> dict:
    actor = _actor(user_data)
    id_proyecto = _entero_positivo(id_proyect, "id_proyect")
    require_project_access(id_proyecto, user_data)
    cantidad = _cantidad(payload.get("quantity"))
    necesaria_para = _fecha_o_nada(payload.get("needed_by"), "needed_by")
    nota = _texto(payload.get("note"), "note", NOTE_MAX)

    hay_material = str(payload.get("id_material") or "").strip() != ""
    id_material = _entero_positivo(payload.get("id_material"), "id_material") if hay_material else None
    # Vinculado: el nombre es el del catalogo. Libre: las palabras del supervisor.
    descripcion = None if hay_material else _descripcion_valida(_texto(
        payload.get("description"), "description", DESCRIPTION_MAX, obligatorio=True))
    # Lo vinculado toma su unidad del catalogo; la lista cerrada es para el texto libre.
    unidad = None if hay_material else _unidad(payload.get("unit"))

    with transaction_context() as db:
        if id_material is not None:
            _material(db, id_material)
        otra = _duplicada(db, id_proyecto, id_material=id_material, descripcion=descripcion)
        if otra is not None:
            _rechazar_duplicada(otra, id_material=id_material, description=descripcion)

        need = ProyectMaterialNeed(
            id_proyect=id_proyecto, id_material=id_material, description=descripcion,
            unit=unidad, quantity=cantidad, needed_by=necesaria_para, note=nota,
            need_status="open", created_by=actor,
            # Una necesidad que ya nombra un material del catalogo no hay que
            # revisarla: nace vinculada, y asi se puede meter en una orden.
            review_result="linked" if id_material is not None else None,
        )
        db.add(need)
        db.flush()
        ids = {id_material} if id_material is not None else set()
        fila = _renglon(need, _datos_de_materiales(db, ids), _existencias(db, ids))
        compradores = _quien_compra(db)
    # Ya cerrada la transaccion: el aviso abre la suya. Compras se entera de que
    # hay algo nuevo por comprar sin tener que abrir la lista a ver si hay.
    avisar_material_solicitado(
        id_proyecto, "%s x %s" % (fila["display_name"], cantidad), compradores, user_data)
    return fila


def _usuarios_con(db, capacidades) -> set[int]:
    permisos = db.scalars(
        select(EntityPermission.id_permission).where(
            EntityPermission.entity_name.in_(list(capacidades)),
            EntityPermission.scope_read != 0,
            EntityPermission.deletion_date.is_(None))).all()
    if not permisos:
        return set()
    return {int(i) for i in db.scalars(
        select(User.id_user).where(User.id_permission.in_(list(permisos)),
                                   User.deletion_date.is_(None))).all()}


def _quien_compra(db) -> set[int]:
    """Quienes ven "Por comprar" y no son de Gerencia ni de Almacen.

    Gerente y Almacenista tambien llevan `purchase_planning`, pero el aviso de
    "se pidio material" es para Compras: a Gerencia le toca despues, cuando
    Compras hace la orden.
    """
    return (_usuarios_con(db, [PURCHASE_CAPABILITY])
            - _usuarios_con(db, NOT_A_BUYER_CAPABILITIES))


def _exigir_que_no_este_en_una_orden(db, need) -> None:
    """Lo que ya esta en una orden viva no cambia ni se devuelve: la orden se
    quedaria con la cantidad o las palabras de antes."""
    orden = needs_on_orders(db, [need.id_proyect_material_need]).get(
        int(need.id_proyect_material_need))
    if orden is not None:
        raise AppError("errors.need_already_in_order", 409, {
            "id_proyect_material_need": need.id_proyect_material_need,
            "id_purchase_order": orden[0], "folio": orden[1]})


def update_need(id_need, payload: dict, user_data: dict) -> dict:
    """Cantidad, unidad, fecha, nota y -si es texto libre- su descripcion."""
    _actor(user_data)
    with transaction_context() as db:
        need = _necesidad(db, id_need, for_update=True)
        require_project_access(need.id_proyect, user_data)
        _exigir_que_no_este_en_una_orden(db, need)
        if need.need_status != "open":
            raise AppError("errors.need_not_open", 409, {
                "id_proyect_material_need": need.id_proyect_material_need,
                "need_status": need.need_status})
        if "quantity" in payload:
            need.quantity = _cantidad(payload.get("quantity"))
        if "needed_by" in payload:
            need.needed_by = _fecha_o_nada(payload.get("needed_by"), "needed_by")
        if "note" in payload:
            need.note = _texto(payload.get("note"), "note", NOTE_MAX)
        if "unit" in payload:
            need.unit = _unidad(payload.get("unit"))
        if "description" in payload and need.id_material is None:
            nueva = _descripcion_valida(_texto(
                payload.get("description"), "description", DESCRIPTION_MAX,
                obligatorio=True))
            if _normalizar(nueva) != _normalizar(need.description):
                otra = _duplicada(db, need.id_proyect, descripcion=nueva,
                                  excepto=need.id_proyect_material_need)
                if otra is not None:
                    _rechazar_duplicada(otra, description=nueva)
                need.description = nueva
                # Otras palabras, otra pregunta: lo que se reviso ya no aplica.
                need.review_result = None
                need.reviewed_by = None
                need.reviewed_date = None
                need.review_note = None
        # "Corregir y reenviar": el supervisor ya atendio el motivo de la devolucion
        # -aunque sea para explicar que si era eso- y vuelve a quedar por revisar.
        if (payload.get("resubmit") and need.id_material is None
                and need.review_result == "returned"):
            need.review_result = None
            need.reviewed_by = None
            need.reviewed_date = None
            need.review_note = None
        db.flush()
        ids = {int(need.id_material)} if need.id_material is not None else set()
        return _renglon(need, _datos_de_materiales(db, ids), _existencias(db, ids))


def cancel_need(id_need, user_data: dict) -> dict:
    """Ya no se necesita. No se borra: queda dicho que se pidio."""
    _actor(user_data)
    with transaction_context() as db:
        need = _necesidad(db, id_need, for_update=True)
        require_project_access(need.id_proyect, user_data)
        if need.need_status == "cancelled":
            return need.serialize()
        # Lo que Compras ya esta comprando no se cancela desde el proyecto: la orden
        # se cancela primero (con su motivo) y la necesidad queda libre.
        orden = needs_on_orders(db, [need.id_proyect_material_need]).get(
            need.id_proyect_material_need)
        if orden is not None:
            raise AppError("errors.need_in_purchase_order", 409, {
                "id_proyect_material_need": need.id_proyect_material_need,
                "order_folio": orden[1], "order_status": orden[2]})
        need.need_status = "cancelled"
        db.flush()
        return need.serialize()


# --- revisar el texto libre --------------------------------------------------

def _puede_revisar(db, user_data: dict) -> bool:
    """Vincular o confirmar exige EDITAR la capacidad, no solo verla."""
    datos = user_data or {}
    if datos.get("is_superuser") or datos.get("is_bootstrap_admin"):
        return True
    try:
        id_permission = int(datos.get("id_permission") or datos.get("permission_id") or 0)
    except (TypeError, ValueError):
        return False
    if not id_permission:
        return False
    fila = db.scalars(
        select(EntityPermission).where(
            EntityPermission.id_permission == id_permission,
            EntityPermission.entity_name == PURCHASE_CAPABILITY,
            EntityPermission.deletion_date.is_(None),
        ).limit(1)
    ).first()
    return bool(fila and int(fila.scope_update or 0) != 0)


def _necesidad_por_revisar(db, id_need, user_data: dict, *,
                           desde=(None,)) -> ProyectMaterialNeed:
    """El renglon de texto libre abierto que se va a revisar.

    A diferencia de editarlo, revisarlo NO pide ver el proyecto: quien compra
    revisa lo de todas las obras sin poder abrirlas.
    """
    if not _puede_revisar(db, user_data):
        raise AppError("errors.permission_denied", 403,
                       {"capability": PURCHASE_CAPABILITY, "action": "update"})
    need = _necesidad(db, id_need, for_update=True)
    if need.need_status != "open":
        raise AppError("errors.need_not_open", 409, {
            "id_proyect_material_need": need.id_proyect_material_need,
            "need_status": need.need_status})
    _exigir_que_no_este_en_una_orden(db, need)
    if need.id_material is not None:
        raise AppError("errors.need_already_linked", 409, {
            "id_proyect_material_need": need.id_proyect_material_need,
            "id_material": need.id_material})
    # Un renglon devuelto espera al supervisor: no se revisa hasta que lo reenvie.
    if need.review_result not in desde:
        raise AppError("errors.need_not_reviewable", 409, {
            "id_proyect_material_need": need.id_proyect_material_need,
            "review_result": need.review_result})
    return need


def link_need(id_need, id_material, user_data: dict) -> dict:
    """"Ya existe en el almacen": se vincula al catalogo y se acaba la duda."""
    actor = _actor(user_data)
    id_del_material = _entero_positivo(id_material, "id_material")
    with transaction_context() as db:
        # Vincular tambien se puede despues de confirmar la compra: se descubrio que si habia.
        need = _necesidad_por_revisar(db, id_need, user_data, desde=(None, "buy"))
        _material(db, id_del_material)
        otra = _duplicada(db, need.id_proyect, id_material=id_del_material,
                          excepto=need.id_proyect_material_need)
        if otra is not None:
            _rechazar_duplicada(otra, id_material=id_del_material)
        need.id_material = id_del_material
        need.review_result = "linked"
        need.review_note = None
        need.reviewed_by = actor
        need.reviewed_date = datetime.now(timezone.utc).replace(tzinfo=None)
        db.flush()
        ids = {id_del_material}
        return _renglon(need, _datos_de_materiales(db, ids), _existencias(db, ids))


def confirm_buy(id_need, user_data: dict) -> dict:
    """"Si hay que comprarlo": alguien que conoce el almacen lo confirmo."""
    actor = _actor(user_data)
    with transaction_context() as db:
        need = _necesidad_por_revisar(db, id_need, user_data)
        need.review_result = "buy"
        need.reviewed_by = actor
        need.reviewed_date = datetime.now(timezone.utc).replace(tzinfo=None)
        db.flush()
        return _renglon(need, {}, {})


def return_need(id_need, nota, user_data: dict) -> dict:
    """"No se entiende": vuelve al supervisor con un motivo y NO se compra.

    Es lo que faltaba: quien revisa podia vincular o confirmar, pero no rechazar, asi
    que un texto sin sentido solo tenia salida hacia la compra. El motivo es
    obligatorio: el supervisor tiene que saber que corregir.
    """
    actor = _actor(user_data)
    motivo = _texto(nota, "note", NOTE_MAX, obligatorio=True)
    if len(motivo) < RETURN_NOTE_MIN:
        raise AppError("errors.invalid_field", 400, {"field": "note"})
    with transaction_context() as db:
        need = _necesidad_por_revisar(db, id_need, user_data)
        need.review_result = "returned"
        need.review_note = motivo
        need.reviewed_by = actor
        need.reviewed_date = datetime.now(timezone.utc).replace(tzinfo=None)
        db.flush()
        return _renglon(need, {}, {})


# --- por comprar -------------------------------------------------------------

def _puede_ver_lo_que_falta(db, user_data: dict) -> bool:
    datos = user_data or {}
    if datos.get("is_superuser") or datos.get("is_bootstrap_admin"):
        return True
    return has_capability(db, user_data, PURCHASE_CAPABILITY)


def to_buy(user_data: dict, *, solo_faltantes: bool = True) -> dict:
    """Las necesidades de todos los proyectos, agrupadas.

    Lo vinculado al catalogo se agrupa por material y se compara con la existencia.
    El texto libre se agrupa por sus palabras normalizadas, sin comparar con nada,
    y mientras nadie lo revise sale "por revisar" con lo que el catalogo sugiere.
    """
    _actor(user_data)
    with transaction_context() as db:
        if not _puede_ver_lo_que_falta(db, user_data):
            raise AppError("errors.permission_denied", 403,
                           {"capability": PURCHASE_CAPABILITY})

        filas = db.execute(
            select(ProyectMaterialNeed, Proyect.folio, Proyect.title,
                   Proyect.proyect_status)
            .join(Proyect, Proyect.id_proyect == ProyectMaterialNeed.id_proyect)
            .where(
                ProyectMaterialNeed.need_status == "open",
                ProyectMaterialNeed.deletion_date.is_(None),
                # Lo devuelto espera al supervisor: todavia no es una compra.
                or_(ProyectMaterialNeed.review_result.is_(None),
                    ProyectMaterialNeed.review_result != "returned"),
                Proyect.deletion_date.is_(None),
                Proyect.proyect_status.notin_(PROYECTOS_QUE_YA_NO_COMPRAN),
                or_(Proyect.management_status.is_(None), Proyect.management_status != "cancelado"),
            )
        ).all()

        ids = {int(n.id_material) for n, *_ in filas if n.id_material is not None}
        materiales = _datos_de_materiales(db, ids)
        existencias = _existencias(db, ids)
        en_orden = needs_on_orders(db, [n.id_proyect_material_need for n, *_ in filas])

        grupos: dict[tuple, dict] = {}
        for need, folio, titulo, estatus in filas:
            # Lo que ya llego (su orden esta recibida completa) deja de ser una
            # compra pendiente; el supervisor lo sigue viendo en su lista, con la
            # orden recibida.
            en_su_orden = en_orden.get(int(need.id_proyect_material_need))
            if en_su_orden is not None and en_su_orden[2] == "received":
                continue
            if need.id_material is not None:
                llave = ("m", int(need.id_material))
                base = {
                    "material": materiales.get(int(need.id_material)),
                    "description": None,
                    "unit": (materiales.get(int(need.id_material)) or {}).get("unit"),
                    "linked": True,
                    "in_stock": existencias.get(int(need.id_material), 0),
                }
            else:
                llave = ("d", _normalizar(need.description))
                base = {"material": None, "description": need.description,
                        "unit": need.unit, "linked": False, "in_stock": None}
            grupo = grupos.setdefault(llave, {
                **base, "key": "%s:%s" % llave, "required": 0, "needed_by": None,
                "needs_review": False, "suggestions": [], "projects": [],
            })
            grupo["required"] += int(need.quantity)
            if need.needed_by and (grupo["needed_by"] is None
                                   or need.needed_by < grupo["needed_by"]):
                grupo["needed_by"] = need.needed_by
            por_revisar = need.id_material is None and need.review_result is None
            grupo["needs_review"] = grupo["needs_review"] or por_revisar
            grupo["projects"].append({
                "id_proyect": need.id_proyect,
                "folio": folio,
                "title": titulo,
                "proyect_status": estatus,
                "quantity": int(need.quantity),
                "needed_by": need.needed_by.isoformat() if need.needed_by else None,
                "id_proyect_material_need": need.id_proyect_material_need,
                "needs_review": por_revisar,
                # Se puede meter en una orden de compra solo lo que ya se confirmo
                # que se entiende: vinculado al catalogo o con la compra confirmada.
                "purchasable": need.review_result in ("buy", "linked"),
                # La orden que ya lo tiene, si la hay: no se compra dos veces.
                "order": _orden_de(en_orden, need.id_proyect_material_need),
            })

        items = []
        for grupo in grupos.values():
            if grupo["linked"]:
                grupo["missing"] = max(0, grupo["required"] - grupo["in_stock"])
                if solo_faltantes and grupo["missing"] == 0:
                    continue
            else:
                # No se compara con nada: se pide completo hasta que alguien diga
                # que ya existe.
                grupo["missing"] = grupo["required"]
                if grupo["needs_review"]:
                    grupo["suggestions"] = _sugerir(db, grupo["description"], limite=3)
            fecha = grupo["needed_by"]
            grupo["needed_by"] = fecha.isoformat() if fecha else None
            items.append(grupo)

        # Lo que se necesita antes, primero; sin fecha al final; y a igual fecha,
        # lo que mas falta.
        items.sort(key=lambda g: (g["needed_by"] is None, g["needed_by"] or "",
                                  -g["missing"]))
        return {
            "items": items,
            "total": len(items),
            "to_review": sum(1 for g in items if g["needs_review"]),
            "only_missing": bool(solo_faltantes),
            "can_review": _puede_revisar(db, user_data),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
