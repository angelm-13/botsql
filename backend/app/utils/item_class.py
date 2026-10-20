"""La clase de un articulo del almacen: herramienta, consumible, sobrante o recargable.

Una sola lista, aqui. El material (catalogo) trae la clase por omision, cada producto la
hereda y puede cambiarla, y el renglon de una orden de compra la lleva hasta el producto.
La pantalla repite la lista en `frontend/src/utils/clasesDeProducto.js`; si se agrega una,
va en los dos y en el CHECK de la migracion `20261020120000`.

Es una etiqueta para clasificar y filtrar: no cambia como se rastrea (`tracking_mode`) ni
si se vende (`stock_purpose`).
"""
from __future__ import annotations

from app.utils.errors import AppError

# herramienta: se presta y vuelve. consumible: se gasta. sobrante: lo que no se ocupo al
# terminar un proyecto. recargable: extintores, tanques, baterias -se rellenan, no se tiran-.
ITEM_CLASSES = ("herramienta", "consumible", "sobrante", "recargable")


def normalize_item_class(valor, campo: str = "item_class") -> str | None:
    """La clase en minusculas, `None` si viene vacia, o un 400 que nombra el campo."""
    texto = str(valor or "").strip().lower()
    if not texto:
        return None
    if texto not in ITEM_CLASSES:
        raise AppError("errors.invalid_field", 400, {"field": campo, "allowed": list(ITEM_CLASSES)})
    return texto


def effective_item_class(producto, material=None) -> str | None:
    """La clase del producto o, si no la tiene, la de su material."""
    return (getattr(producto, "item_class", None)
            or getattr(material, "item_class", None) or None)
