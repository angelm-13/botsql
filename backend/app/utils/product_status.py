"""El estado de un producto tiene dos escrituras y una sola verdad.

`product.id_inventory_status` es el estado contra catalogo (nuevo, usado,
en_reparacion, danado, retirado, extraviado). `product.product_status` es el
texto que dejo el sistema anterior (ENTRADA, SALIDA, DAÑADO, EQ. DAÑADOS,
DESTRUCCION, EXTRAVIADO...) y que el formulario de producto sigue escribiendo con
el codigo del catalogo. Cuando se escribia solo uno, el otro se quedaba con el
valor viejo y el producto decia dos cosas a la vez: MARR4 aparecia como "usado" con
el catalogo en "extraviado".

Aqui vive la unica traduccion texto -> codigo de catalogo. La usan el guardado del
producto (`ProductService`) y el script que corrige lo que ya quedo contradictorio.
"""
from __future__ import annotations

import unicodedata

# Lo que dice cada texto historico, ya normalizado (ver `clave`).
CODIGO_POR_TEXTO = {
    "nuevo": "nuevo",
    "usado": "usado",
    "en_reparacion": "en_reparacion",
    "en reparacion": "en_reparacion",
    "danado": "danado",
    "danados": "danado",
    "eq. danados": "danado",
    "retirado": "retirado",
    "destruccion": "retirado",
    "extraviado": "extraviado",
}


def clave(texto) -> str:
    """El texto sin mayusculas, acentos ni espacios de sobra."""
    limpio = unicodedata.normalize("NFD", str(texto or "").strip().lower())
    return "".join(c for c in limpio if unicodedata.category(c) != "Mn")


def codigo_de_catalogo(texto) -> str | None:
    """El codigo de `inventory_status` que dice ese texto, o None si no dice ninguno.

    ENTRADA y SALIDA no son estados: dicen si algo esta o no en el almacen, y eso
    lo sabe el libro de movimientos, no un texto.
    """
    return CODIGO_POR_TEXTO.get(clave(texto))
