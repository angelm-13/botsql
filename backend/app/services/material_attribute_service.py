"""Las caracteristicas de una familia, y los valores de un material.

Que resuelve
------------
Con familia, tipo y marca se llega hasta "desarmador Truper plano". El resto -el
largo, el mango, el calibre, los litros- vivia dentro del texto de la
descripcion, asi que se podia escribir y no se podia usar: nada de agrupar,
filtrar ni contestar "cuantos de 6 pulgadas tengo".

Las reglas que este modulo sostiene
-----------------------------------
1. **Una caracteristica pertenece a una familia.** El alta de un material solo
   ofrece las de SU familia, y capturar un valor de otra se rechaza. Sin eso se
   podria poner "litros" en un desarmador y el dato quedaria donde nadie lo
   busca.

2. **El tipo de dato decide la forma del valor.** Un `numero` se guarda ademas
   como numero, para que "6 o mas" sea una comparacion y no una comparacion de
   cadenas donde "10" queda por debajo de "6". Una `lista` solo acepta los
   valores declarados, que es lo que impide que "mate", "Mate" y "MATE" acaben
   siendo tres acabados.

3. **Lo obligatorio es obligatorio al guardar el juego completo.** Se comprueba
   cuando se guardan los valores de un material, no caracteristica por
   caracteristica: si se comprobara una por una, el orden de captura decidiria
   si pasa.

4. **Se lee en lote.** `valores_de_materiales` resuelve N materiales en dos
   consultas. Una por material es el patron de N+1 que ya costo 271 consultas en
   el rastreo, y una lista de materiales con sus caracteristicas es exactamente
   donde volveria a aparecer.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select

from app.models.material import Material
from app.models.material_attribute import (
    LISTA, MaterialAttribute, MaterialAttributeOption, NUMERO, TEXTO,
    TIPOS_DE_DATO, NmMaterialAttribute,
)
from app.models.product_family import ProductFamily
from app.models.session import transaction_context
from app.utils.errors import AppError


def _actor(user_data: dict) -> int:
    id_usuario = (user_data or {}).get("id_user")
    if not id_usuario:
        raise AppError("errors.auth_required", 401)
    return int(id_usuario)


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


def _familia(db, id_product_family):
    """La familia, comprobada. Una caracteristica suelta no significa nada."""
    id_familia = _entero(id_product_family, "id_product_family")
    existe = db.scalars(
        select(ProductFamily.id_product_family).where(
            ProductFamily.id_product_family == id_familia,
            ProductFamily.deletion_date.is_(None),
        ).limit(1)
    ).first()
    if existe is None:
        raise AppError("errors.not_found", 404,
                       {"entity": "product_family", "field": "id_product_family"})
    return id_familia


def _atributo(db, id_material_attribute, *, para_escribir=False):
    consulta = select(MaterialAttribute).where(
        MaterialAttribute.id_material_attribute == _entero(
            id_material_attribute, "id_material_attribute"),
        MaterialAttribute.deletion_date.is_(None),
    )
    if para_escribir:
        consulta = consulta.with_for_update()
    atributo = db.scalars(consulta).first()
    if atributo is None:
        raise AppError("errors.not_found", 404, {"entity": "material_attribute"})
    return atributo


def _opciones_de(db, ids_atributos: set[int]) -> dict:
    """Las opciones de cada caracteristica de lista, en una consulta."""
    if not ids_atributos:
        return {}
    filas = db.scalars(
        select(MaterialAttributeOption).where(
            MaterialAttributeOption.id_material_attribute.in_(list(ids_atributos)),
            MaterialAttributeOption.deletion_date.is_(None),
        ).order_by(
            MaterialAttributeOption.sort_order,
            MaterialAttributeOption.option_value,
        )
    ).all()
    salida: dict[int, list] = {}
    for fila in filas:
        salida.setdefault(int(fila.id_material_attribute), []).append(fila)
    return salida


# --- el catalogo de caracteristicas de una familia ------------------------

def atributos_de_la_familia(id_product_family, user_data) -> dict:
    """Lo que esta familia declara, con sus opciones y cuantos materiales lo usan.

    El conteo va porque es lo que hace falta para decidir si se puede borrar una
    caracteristica: "usada por 14 materiales" es una respuesta, "no se pudo
    eliminar" no.
    """
    _actor(user_data)
    with transaction_context() as db:
        id_familia = _familia(db, id_product_family)
        atributos = db.scalars(
            select(MaterialAttribute).where(
                MaterialAttribute.id_product_family == id_familia,
                MaterialAttribute.deletion_date.is_(None),
            ).order_by(MaterialAttribute.sort_order, MaterialAttribute.attribute_name)
        ).all()

        ids = {int(a.id_material_attribute) for a in atributos}
        opciones = _opciones_de(db, ids)
        usos = dict(db.execute(
            select(NmMaterialAttribute.id_material_attribute, func.count())
            .where(
                NmMaterialAttribute.id_material_attribute.in_(list(ids) or [0]),
                NmMaterialAttribute.deletion_date.is_(None),
            )
            .group_by(NmMaterialAttribute.id_material_attribute)
        ).all()) if ids else {}

        salida = []
        for atributo in atributos:
            fila = atributo.serialize()
            fila["options"] = [
                o.serialize() for o in opciones.get(int(atributo.id_material_attribute), [])
            ]
            fila["materials_using_it"] = int(
                usos.get(int(atributo.id_material_attribute), 0))
            salida.append(fila)
        return {"id_product_family": id_familia, "items": salida,
                "total": len(salida)}


def crear_atributo(payload: dict, user_data) -> dict:
    """Declara una caracteristica en una familia, con sus opciones si es lista."""
    actor = _actor(user_data)
    payload = payload or {}
    nombre = _texto(payload.get("attribute_name"), "attribute_name",
                    largo=80, obligatorio=True)
    tipo = str(payload.get("data_type") or TEXTO).strip().lower()
    if tipo not in TIPOS_DE_DATO:
        raise AppError("errors.invalid_field", 400,
                       {"field": "data_type", "allowed": list(TIPOS_DE_DATO)})

    opciones = [
        v for v in (
            _texto(o, "option_value", largo=120)
            for o in (payload.get("options") or [])
        ) if v
    ]
    if tipo == LISTA and not opciones:
        # Una lista sin valores es un campo de texto con otro nombre, y pierde
        # justo lo que la hace util: que los valores esten acotados.
        raise AppError("errors.material_attribute_options_required", 400,
                       {"field": "options", "data_type": LISTA})
    if tipo != LISTA and opciones:
        raise AppError("errors.material_attribute_options_not_applicable", 400,
                       {"field": "options", "data_type": tipo})

    with transaction_context() as db:
        id_familia = _familia(db, payload.get("id_product_family"))
        repetido = db.scalars(
            select(MaterialAttribute).where(
                MaterialAttribute.id_product_family == id_familia,
                func.lower(MaterialAttribute.attribute_name) == nombre.lower(),
                MaterialAttribute.deletion_date.is_(None),
            ).limit(1)
        ).first()
        if repetido is not None:
            raise AppError(
                "errors.material_attribute_already_exists", 409,
                {"id_material_attribute": repetido.id_material_attribute,
                 "attribute_name": repetido.attribute_name},
            )

        atributo = MaterialAttribute(
            id_product_family=id_familia,
            attribute_name=nombre,
            data_type=tipo,
            unit_label=_texto(payload.get("unit_label"), "unit_label", largo=20),
            is_required=bool(payload.get("is_required")),
            sort_order=_entero(payload.get("sort_order"), "sort_order",
                               obligatorio=False) or 0,
            created_by=actor,
        )
        db.add(atributo)
        db.flush()

        for orden, valor in enumerate(dict.fromkeys(opciones), start=1):
            db.add(MaterialAttributeOption(
                id_material_attribute=atributo.id_material_attribute,
                option_value=valor,
                sort_order=orden * 10,
                created_by=actor,
            ))
        db.flush()

        fila = atributo.serialize()
        fila["options"] = [
            o.serialize()
            for o in _opciones_de(db, {int(atributo.id_material_attribute)}).get(
                int(atributo.id_material_attribute), [])
        ]
        return {"attribute": fila}


def actualizar_atributo(id_material_attribute, payload: dict, user_data) -> dict:
    """Renombra o reordena. El tipo de dato NO se cambia.

    Cambiar el tipo dejaria los valores ya capturados en la forma del tipo
    viejo: un "largo" de texto que pasa a numero se queda con "seis pulgadas" en
    `value_text` y nada en `value_number`, asi que la comparacion numerica
    empezaria a mentir en silencio. Para eso se declara otra caracteristica.
    """
    _actor(user_data)
    payload = payload or {}
    with transaction_context() as db:
        atributo = _atributo(db, id_material_attribute, para_escribir=True)

        if "data_type" in payload:
            nuevo = str(payload.get("data_type") or "").strip().lower()
            if nuevo and nuevo != atributo.data_type:
                raise AppError("errors.material_attribute_type_is_fixed", 409,
                               {"field": "data_type",
                                "data_type": atributo.data_type})

        nombre = _texto(payload.get("attribute_name"), "attribute_name", largo=80)
        if nombre and nombre.lower() != (atributo.attribute_name or "").lower():
            repetido = db.scalars(
                select(MaterialAttribute).where(
                    MaterialAttribute.id_product_family == atributo.id_product_family,
                    func.lower(MaterialAttribute.attribute_name) == nombre.lower(),
                    MaterialAttribute.deletion_date.is_(None),
                ).limit(1)
            ).first()
            if repetido is not None:
                raise AppError(
                    "errors.material_attribute_already_exists", 409,
                    {"id_material_attribute": repetido.id_material_attribute,
                     "attribute_name": repetido.attribute_name},
                )
        if nombre:
            atributo.attribute_name = nombre
        if "unit_label" in payload:
            atributo.unit_label = _texto(payload.get("unit_label"), "unit_label",
                                         largo=20)
        if "is_required" in payload:
            atributo.is_required = bool(payload.get("is_required"))
        if "sort_order" in payload:
            atributo.sort_order = _entero(payload.get("sort_order"), "sort_order",
                                          obligatorio=False) or 0
        db.flush()
        return {"attribute": atributo.serialize()}


def eliminar_atributo(id_material_attribute, user_data) -> dict:
    """Retira una caracteristica, si ningun material la esta usando.

    Con valores capturados no se borra: esos valores quedarian apuntando a un
    campo que ya no existe, y la pantalla del material los mostraria sin nombre
    o no los mostraria en absoluto. Se dice cuantos son, que es lo que hace
    falta para decidir.
    """
    _actor(user_data)
    with transaction_context() as db:
        atributo = _atributo(db, id_material_attribute, para_escribir=True)
        usos = db.scalar(
            select(func.count()).select_from(NmMaterialAttribute).where(
                NmMaterialAttribute.id_material_attribute == atributo.id_material_attribute,
                NmMaterialAttribute.deletion_date.is_(None),
            )
        )
        if usos:
            raise AppError(
                "errors.material_attribute_in_use", 409,
                {"id_material_attribute": atributo.id_material_attribute,
                 "materials_using_it": int(usos)},
            )
        atributo.deletion_date = func.now()
        db.flush()
        return {"deleted": True,
                "id_material_attribute": atributo.id_material_attribute}


def agregar_opcion(id_material_attribute, payload: dict, user_data) -> dict:
    """Agrega un valor permitido a una caracteristica de lista."""
    actor = _actor(user_data)
    valor = _texto((payload or {}).get("option_value"), "option_value",
                   largo=120, obligatorio=True)
    with transaction_context() as db:
        atributo = _atributo(db, id_material_attribute)
        if atributo.data_type != LISTA:
            raise AppError("errors.material_attribute_options_not_applicable", 400,
                           {"field": "options", "data_type": atributo.data_type})
        repetido = db.scalars(
            select(MaterialAttributeOption).where(
                MaterialAttributeOption.id_material_attribute == atributo.id_material_attribute,
                func.lower(MaterialAttributeOption.option_value) == valor.lower(),
                MaterialAttributeOption.deletion_date.is_(None),
            ).limit(1)
        ).first()
        if repetido is not None:
            raise AppError("errors.material_attribute_option_already_exists", 409,
                           {"option_value": repetido.option_value})

        siguiente = db.scalar(
            select(func.coalesce(func.max(MaterialAttributeOption.sort_order), 0))
            .where(MaterialAttributeOption.id_material_attribute
                   == atributo.id_material_attribute)
        )
        opcion = MaterialAttributeOption(
            id_material_attribute=atributo.id_material_attribute,
            option_value=valor,
            sort_order=int(siguiente or 0) + 10,
            created_by=actor,
        )
        db.add(opcion)
        db.flush()
        return {"option": opcion.serialize()}


def eliminar_opcion(id_option, user_data) -> dict:
    """Retira un valor permitido, si ningun material lo eligio."""
    _actor(user_data)
    with transaction_context() as db:
        opcion = db.scalars(
            select(MaterialAttributeOption).where(
                MaterialAttributeOption.id_material_attribute_option == _entero(
                    id_option, "id_material_attribute_option"),
                MaterialAttributeOption.deletion_date.is_(None),
            ).with_for_update()
        ).first()
        if opcion is None:
            raise AppError("errors.not_found", 404,
                           {"entity": "material_attribute_option"})
        usos = db.scalar(
            select(func.count()).select_from(NmMaterialAttribute).where(
                NmMaterialAttribute.id_material_attribute_option
                == opcion.id_material_attribute_option,
                NmMaterialAttribute.deletion_date.is_(None),
            )
        )
        if usos:
            raise AppError("errors.material_attribute_option_in_use", 409,
                           {"option_value": opcion.option_value,
                            "materials_using_it": int(usos)})
        opcion.deletion_date = func.now()
        db.flush()
        return {"deleted": True,
                "id_material_attribute_option": opcion.id_material_attribute_option}


# --- los valores de un material ------------------------------------------

def _material(db, id_material, *, para_escribir=False) -> Material:
    consulta = select(Material).where(
        Material.id_material == _entero(id_material, "id_material"),
        Material.deletion_date.is_(None),
    )
    if para_escribir:
        consulta = consulta.with_for_update()
    material = db.scalars(consulta).first()
    if material is None:
        raise AppError("errors.not_found", 404, {"entity": "material"})
    return material


def _resolver_valor(atributo, crudo, opciones_por_valor) -> dict:
    """La forma del valor segun el tipo de la caracteristica.

    Devuelve las tres columnas. `value_text` se llena siempre, sea del tipo que
    sea: es el valor como se muestra, y tenerlo evita que pintar una lista de
    caracteristicas dependa de resolver antes de que tipo era cada una.
    """
    if atributo.data_type == NUMERO:
        try:
            numero = Decimal(str(crudo).strip())
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise AppError("errors.invalid_field", 400,
                           {"field": atributo.attribute_name,
                            "data_type": NUMERO}) from exc
        # Normalizado: "6.0" y "6" son el mismo largo, y guardados distinto
        # aparecerian como dos valores en cualquier agrupacion.
        texto = format(numero.normalize(), "f")
        return {"value_text": texto, "value_number": numero,
                "id_material_attribute_option": None}

    if atributo.data_type == LISTA:
        elegido = str(crudo).strip()
        opcion = opciones_por_valor.get(elegido.lower())
        if opcion is None:
            raise AppError(
                "errors.material_attribute_value_not_allowed", 400,
                {"field": atributo.attribute_name,
                 "value": elegido,
                 "allowed": sorted(o.option_value
                                   for o in opciones_por_valor.values())},
            )
        return {"value_text": opcion.option_value, "value_number": None,
                "id_material_attribute_option": opcion.id_material_attribute_option}

    texto = str(crudo).strip()[:200]
    return {"value_text": texto, "value_number": None,
            "id_material_attribute_option": None}


def guardar_valores(id_material, payload: dict, user_data) -> dict:
    """Guarda el juego completo de caracteristicas de un material.

    Es un reemplazo y no una edicion campo por campo: se manda lo que el
    material tiene, y lo que no venga se retira. Con actualizaciones parciales,
    quitar una caracteristica exigiria una llamada aparte y quedaria a medias en
    cuanto una de las dos fallara.

    Lo obligatorio se comprueba aqui, sobre el juego completo. Comprobarlo campo
    por campo dejaria que el orden de captura decidiera si pasa.
    """
    actor = _actor(user_data)
    crudos = (payload or {}).get("values")
    if crudos is None:
        raise AppError("errors.required_field", 400, {"field": "values"})
    if not isinstance(crudos, dict):
        # Se acepta {id_atributo: valor}: es lo que un formulario produce sin
        # tener que inventar un orden.
        raise AppError("errors.invalid_field", 400, {"field": "values"})

    with transaction_context() as db:
        material = _material(db, id_material, para_escribir=True)

        atributos = db.scalars(
            select(MaterialAttribute).where(
                MaterialAttribute.id_product_family == material.id_product_family,
                MaterialAttribute.deletion_date.is_(None),
            )
        ).all()
        por_id = {int(a.id_material_attribute): a for a in atributos}

        # Un valor de otra familia se rechaza en vez de ignorarse: ignorarlo
        # dejaria al usuario creyendo que se guardo.
        pedidos = {}
        for clave, valor in crudos.items():
            id_atributo = _entero(clave, "id_material_attribute")
            if id_atributo not in por_id:
                raise AppError(
                    "errors.material_attribute_not_in_family", 400,
                    {"id_material_attribute": id_atributo,
                     "id_product_family": material.id_product_family},
                )
            if valor is None or str(valor).strip() == "":
                continue
            pedidos[id_atributo] = valor

        faltan = sorted(
            a.attribute_name for a in atributos
            if a.is_required and int(a.id_material_attribute) not in pedidos
        )
        if faltan:
            raise AppError("errors.material_attribute_required", 400,
                           {"missing": faltan})

        opciones = _opciones_de(db, set(pedidos))
        vigentes = {
            int(f.id_material_attribute): f
            for f in db.scalars(
                select(NmMaterialAttribute).where(
                    NmMaterialAttribute.id_material == material.id_material,
                    NmMaterialAttribute.deletion_date.is_(None),
                ).with_for_update()
            ).all()
        }

        for id_atributo, crudo in pedidos.items():
            atributo = por_id[id_atributo]
            por_valor = {
                o.option_value.lower(): o for o in opciones.get(id_atributo, [])
            }
            resuelto = _resolver_valor(atributo, crudo, por_valor)
            fila = vigentes.get(id_atributo)
            if fila is None:
                db.add(NmMaterialAttribute(
                    id_material=material.id_material,
                    id_material_attribute=id_atributo,
                    created_by=actor,
                    **resuelto,
                ))
            else:
                for campo, valor in resuelto.items():
                    setattr(fila, campo, valor)

        # Lo que no vino se retira. Es lo que hace de esto un reemplazo.
        for id_atributo, fila in vigentes.items():
            if id_atributo not in pedidos:
                fila.deletion_date = func.now()

        db.flush()
        return {
            "id_material": material.id_material,
            "values": valores_de_materiales(db, [material.id_material]).get(
                int(material.id_material), []),
        }


def valores_de_materiales(db, ids_materiales) -> dict:
    """Las caracteristicas de N materiales, en dos consultas.

    Recibe la sesion en lugar de abrirla porque se usa desde dentro de otras
    operaciones -el alta de un material, la lista del rastreo- y una funcion que
    abre su propia transaccion no se puede componer.

    Dos consultas y no una por material: una lista de cuarenta materiales con
    sus caracteristicas es exactamente donde el N+1 vuelve a aparecer.
    """
    ids = [int(x) for x in (ids_materiales or [])]
    if not ids:
        return {}

    filas = db.scalars(
        select(NmMaterialAttribute).where(
            NmMaterialAttribute.id_material.in_(ids),
            NmMaterialAttribute.deletion_date.is_(None),
        )
    ).all()
    if not filas:
        return {}

    atributos = {
        int(a.id_material_attribute): a
        for a in db.scalars(
            select(MaterialAttribute).where(
                MaterialAttribute.id_material_attribute.in_(
                    [int(f.id_material_attribute) for f in filas]),
            )
        ).all()
    }

    salida: dict[int, list] = {}
    for fila in filas:
        atributo = atributos.get(int(fila.id_material_attribute))
        salida.setdefault(int(fila.id_material), []).append({
            "id_material_attribute": int(fila.id_material_attribute),
            "attribute_name": atributo.attribute_name if atributo else None,
            "data_type": atributo.data_type if atributo else None,
            "unit_label": atributo.unit_label if atributo else None,
            "sort_order": atributo.sort_order if atributo else 0,
            "value_text": fila.value_text,
            "value_number": (
                float(fila.value_number) if fila.value_number is not None else None
            ),
            "id_material_attribute_option": fila.id_material_attribute_option,
        })
    for lista in salida.values():
        lista.sort(key=lambda x: (x["sort_order"] or 0, x["attribute_name"] or ""))
    return salida


def caracteristicas_de(id_material, user_data) -> dict:
    """Lo que este material tiene, junto a lo que su familia declara.

    Van las dos cosas porque la pantalla necesita las dos: los campos de la
    familia para saber que preguntar, y los valores para saber que ya se
    contesto.
    """
    _actor(user_data)
    with transaction_context() as db:
        material = _material(db, id_material)
        declaradas = db.scalars(
            select(MaterialAttribute).where(
                MaterialAttribute.id_product_family == material.id_product_family,
                MaterialAttribute.deletion_date.is_(None),
            ).order_by(MaterialAttribute.sort_order, MaterialAttribute.attribute_name)
        ).all()
        opciones = _opciones_de(
            db, {int(a.id_material_attribute) for a in declaradas})
        return {
            "id_material": material.id_material,
            "id_product_family": material.id_product_family,
            "attributes": [
                {**a.serialize(),
                 "options": [o.serialize()
                             for o in opciones.get(int(a.id_material_attribute), [])]}
                for a in declaradas
            ],
            "values": valores_de_materiales(db, [material.id_material]).get(
                int(material.id_material), []),
        }


def materiales_que_cumplen(payload: dict, user_data) -> dict:
    """"Cuantos desarmadores Truper planos de 6 pulgadas tengo."

    Es el motivo de todo lo anterior. Cada criterio es una caracteristica con su
    valor -o su rango, si es numero-, y se aplican como interseccion: un material
    tiene que cumplir todos.

    Se resuelve con una consulta por criterio y una interseccion de conjuntos en
    Python, no con un JOIN por criterio. Con cuatro criterios, cuatro JOINs sobre
    la misma tabla hacen un plan que el planificador resuelve mal, y el numero de
    criterios es de quien pregunta: no se puede acotar.
    """
    _actor(user_data)
    payload = payload or {}
    criterios = payload.get("criteria") or []
    if not isinstance(criterios, list):
        raise AppError("errors.invalid_field", 400, {"field": "criteria"})

    with transaction_context() as db:
        base = select(Material.id_material).where(Material.deletion_date.is_(None))
        id_familia = _entero(payload.get("id_product_family"), "id_product_family",
                             obligatorio=False)
        if id_familia is not None:
            base = base.where(Material.id_product_family == id_familia)
        id_tipo = _entero(payload.get("id_material_type"), "id_material_type",
                          obligatorio=False)
        if id_tipo is not None:
            base = base.where(Material.id_material_type == id_tipo)
        id_marca = _entero(payload.get("id_brand"), "id_brand", obligatorio=False)
        if id_marca is not None:
            base = base.where(Material.id_brand == id_marca)

        encontrados = {int(x) for x in db.scalars(base).all()}

        for criterio in criterios:
            if not encontrados:
                break
            id_atributo = _entero((criterio or {}).get("id_material_attribute"),
                                  "id_material_attribute")
            consulta = select(NmMaterialAttribute.id_material).where(
                NmMaterialAttribute.id_material_attribute == id_atributo,
                NmMaterialAttribute.deletion_date.is_(None),
                NmMaterialAttribute.id_material.in_(list(encontrados)),
            )
            if "value" in (criterio or {}):
                consulta = consulta.where(
                    func.lower(NmMaterialAttribute.value_text)
                    == str(criterio["value"]).strip().lower())
            if (criterio or {}).get("min") is not None:
                consulta = consulta.where(
                    NmMaterialAttribute.value_number >= Decimal(str(criterio["min"])))
            if (criterio or {}).get("max") is not None:
                consulta = consulta.where(
                    NmMaterialAttribute.value_number <= Decimal(str(criterio["max"])))
            encontrados &= {int(x) for x in db.scalars(consulta).all()}

        if not encontrados:
            return {"items": [], "total": 0}

        materiales = db.scalars(
            select(Material).where(Material.id_material.in_(list(encontrados)))
            .order_by(Material.material_description)
        ).all()
        valores = valores_de_materiales(db, list(encontrados))
        return {
            "items": [
                {"id_material": int(m.id_material),
                 "material_description": m.material_description,
                 "id_product_family": m.id_product_family,
                 "id_material_type": m.id_material_type,
                 "id_brand": m.id_brand,
                 "attributes": valores.get(int(m.id_material), [])}
                for m in materiales
            ],
            "total": len(materiales),
        }
