"""Catalogo de dimensiones de KPI: una sola declaracion por dimension.

Por que existe
--------------
Antes una dimension vivia repartida en tres tablas de `registry.py`
(`DIMENSIONES`, `DIMENSION_JSON_KEY`, `ETIQUETA_DIMENSION_POR_OMISION`) y,
fuera del backend, en el criterio con que el Dashboard decidia como ponerle
nombre a cada id (todo lo que no era producto/familia/estado/global se trataba
como un usuario). Aqui cada dimension se declara UNA vez, con todo lo que las
demas capas necesitan saber de ella:

* `clave`: el nombre con que un KPI la declara en `KpiDefinition.dimensiones`.
* `json_key`: la llave de `kpi_snapshot.dimension_key` donde se guarda la
  entidad (`None` para "global": no hay entidad).
* `etiqueta`: como se llama, por omision, en el selector "Agrupar por".
* `abierta`: si el catalogo de valores puede crecer sin limite (empleados,
  platillos...). El Dashboard solo agrupa en "Otros" las abiertas.
* `tipo`: `persona` (los ids son `user.id_user`, asi que aplican el filtro por
  empleados, el de departamentos y el alcance Propios/Mis grupos),
  `catalogo` (ids de otra tabla: mesero, platillo, mesa, cliente, unidad,
  operador, producto, familia, equipo), `categoria` (el valor ES el nombre: "abierta",
  "Entrada") o `global` (sin desglose).
* `resolver_etiquetas(db, ids)`: los nombres legibles de esos ids. Los calcula el
  backend, para que el frontend no tenga que cargar catalogos enteros
  (`GET /user/`, `GET /product/`) solo para poner nombres.

Un mesero NO es `persona` aunque lo sea en la vida real: `restaurant_waiter`
tiene su propio id y su `id_user` puede ser nulo, asi que filtrarlo con ids de
usuario compararia cosas distintas.

"Sin asignar"
-------------
Una fila de snapshot cuya entidad es NULL (un pedido sin mesero, un viaje sin
unidad) se agrupa bajo `SIN_ASIGNAR` en `routes/kpi.py` y `etiquetas_de_dimension`
le pone la etiqueta, pero SOLO si el KPI lo pide (`KpiDefinition.sin_asignar`):
los 24 KPIs de siempre la descartan, como hacian antes. La etiqueta es "Sin asignar" salvo que
la dimension declare otra (`etiqueta_sin_asignar`: los equipos dicen "Sin equipo").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

# Llave bajo la que `routes/kpi.py` agrupa las filas sin entidad.
SIN_ASIGNAR = "sin_asignar"
ETIQUETA_SIN_ASIGNAR = "Sin asignar"

# `familia` guarda 0 cuando el producto no tiene familia (ver `registry.py`).
FAMILIA_SIN_ASIGNAR_ID = 0

TIPOS = ("persona", "catalogo", "categoria", "global")


@dataclass(frozen=True)
class Dimension:
    clave: str
    json_key: Optional[str]
    etiqueta: str
    abierta: bool
    tipo: str
    resolver_etiquetas: Optional[Callable] = None
    # Como se llama la fila sin entidad cuando el KPI la pide (`KpiDefinition.sin_asignar`). "Sin asignar" salvo que la
    # dimension tenga un nombre mas claro ("Sin equipo"). La llave que viaja es siempre `SIN_ASIGNAR`.
    etiqueta_sin_asignar: str = ETIQUETA_SIN_ASIGNAR

    def __post_init__(self):
        if self.tipo not in TIPOS:
            raise RuntimeError(f"La dimension '{self.clave}' declara el tipo desconocido '{self.tipo}'.")
        if (self.tipo == "global") != (self.json_key is None):
            raise RuntimeError(f"La dimension '{self.clave}': solo 'global' no lleva json_key.")

    def serializar(self) -> dict:
        """Lo que expone `GET /kpi_dimension/` (el frontend no necesita el resolver)."""
        return {
            "clave": self.clave,
            "json_key": self.json_key,
            "etiqueta": self.etiqueta,
            "abierta": self.abierta,
            "tipo": self.tipo,
            "con_etiquetas": self.resolver_etiquetas is not None,
        }


def _ids_enteros(ids) -> list[int]:
    enteros = []
    for valor in ids:
        try:
            enteros.append(int(valor))
        except (TypeError, ValueError):
            continue
    return enteros


def _por_tabla(db, columna_id, columna_texto, ids, respaldo=None) -> dict:
    """`{str(id): texto}` de las filas que existan; el que falte cae a `#id`."""
    from sqlalchemy import select

    enteros = _ids_enteros(ids)
    nombres = {}
    if enteros:
        for id_fila, texto, *resto in db.execute(
            select(columna_id, columna_texto, *([respaldo] if respaldo is not None else []))
            .where(columna_id.in_(enteros))
        ).all():
            nombres[str(id_fila)] = texto or (resto[0] if resto else None) or f"#{id_fila}"
    return {str(i): nombres.get(str(i), f"#{i}") for i in ids}


def _usuarios(db, ids):
    from app.models.user import User

    return _por_tabla(db, User.id_user, User.full_name, ids, User.username)


def _productos(db, ids):
    from app.models.product import Product

    return _por_tabla(db, Product.id_product, Product.descripcion, ids, Product.product_code)


def _familias(db, ids):
    from app.models.product_family import ProductFamily

    reales = [i for i in ids if str(i) != str(FAMILIA_SIN_ASIGNAR_ID)]
    nombres = _por_tabla(db, ProductFamily.id_product_family, ProductFamily.product_family_description, reales)
    nombres[str(FAMILIA_SIN_ASIGNAR_ID)] = "Sin familia"
    return {str(i): nombres.get(str(i), f"#{i}") for i in ids}


def _meseros(db, ids):
    from app.models.restaurant import RestaurantWaiter

    return _por_tabla(db, RestaurantWaiter.id_restaurant_waiter, RestaurantWaiter.name, ids)


def _platillos(db, ids):
    from app.models.restaurant import RestaurantDish

    return _por_tabla(db, RestaurantDish.id_restaurant_dish, RestaurantDish.title, ids)


def _mesas(db, ids):
    from sqlalchemy import select

    from app.models.restaurant import RestaurantTable

    enteros = _ids_enteros(ids)
    numeros = {}
    if enteros:
        numeros = {
            str(id_mesa): numero
            for id_mesa, numero in db.execute(
                select(RestaurantTable.id_restaurant_table, RestaurantTable.number)
                .where(RestaurantTable.id_restaurant_table.in_(enteros))
            ).all()
        }
    return {str(i): (f"Mesa {numeros[str(i)]}" if str(i) in numeros else f"#{i}") for i in ids}


def _clientes(db, ids):
    from app.models.customer_supplier import CustomerSupplier

    return _por_tabla(db, CustomerSupplier.id_customer_supplier, CustomerSupplier.name, ids)


def _unidades(db, ids):
    from app.models.logistics_unit import LogisticsUnit

    return _por_tabla(db, LogisticsUnit.id_logistics_unit, LogisticsUnit.plate, ids)


def _operadores(db, ids):
    from app.models.logistics_operator import LogisticsOperator

    return _por_tabla(db, LogisticsOperator.id_logistics_operator, LogisticsOperator.full_name, ids)


def _equipos(db, ids):
    from app.models.team import Team

    return _por_tabla(db, Team.id_team, Team.team_description, ids)


# El orden es el de siempre para las cinco primeras (`DIMENSIONES` lo deriva).
CATALOGO = (
    Dimension("empleado", "id_user", "Empleado", True, "persona", _usuarios),
    Dimension("producto", "id_product", "Producto", True, "catalogo", _productos),
    Dimension("global", None, "Total", False, "global"),
    Dimension("estado", "estado", "Estado", False, "categoria"),
    Dimension("familia", "id_familia", "Familia", True, "catalogo", _familias),
    Dimension("mesero", "id_restaurant_waiter", "Mesero", True, "catalogo", _meseros),
    Dimension("platillo", "id_restaurant_dish", "Platillo", True, "catalogo", _platillos),
    Dimension("mesa", "id_restaurant_table", "Mesa", True, "catalogo", _mesas),
    Dimension("cliente", "id_customer_supplier", "Cliente", True, "catalogo", _clientes),
    Dimension("unidad", "id_logistics_unit", "Unidad", True, "catalogo", _unidades),
    Dimension("operador", "id_logistics_operator", "Operador", True, "catalogo", _operadores),
    # Un equipo (`team`) es un grupo de usuarios (`nm_team_user`); en Comala, un parque. NO es `persona`:
    # su id es `team.id_team`, no `user.id_user`. No es `abierta`: son pocos y cada uno importa, asi que
    # el Dashboard no los agrupa en "Otros".
    Dimension("equipo", "id_team", "Equipo", False, "catalogo", _equipos, etiqueta_sin_asignar="Sin equipo"),
)

DIMENSION_POR_CLAVE = {d.clave: d for d in CATALOGO}

if len(DIMENSION_POR_CLAVE) != len(CATALOGO):
    raise RuntimeError("Hay dos dimensiones con la misma clave.")


def etiquetas_de_dimension(db, clave: str, rangos, con_sin_asignar: bool = False) -> Optional[dict]:
    """Los nombres de los ids que aparecen en `rangos` (los dos lados de la consulta).

    `None` si la dimension no tiene resolver (estado, global): el valor ya es el
    nombre o no hay entidad. Incluye "Sin asignar" solo si el KPI lo pidio
    (`KpiDefinition.sin_asignar`): en los demas esa fila no existe.
    """
    dimension = DIMENSION_POR_CLAVE.get(clave)
    if dimension is None or dimension.resolver_etiquetas is None:
        return None
    ids = sorted({
        llave
        for rango in rangos if rango
        for llave in rango.get("por_empleado", {})
        if llave != SIN_ASIGNAR
    })
    etiquetas = dimension.resolver_etiquetas(db, ids) if ids else {}
    if con_sin_asignar:
        etiquetas[SIN_ASIGNAR] = dimension.etiqueta_sin_asignar
    return etiquetas
