"""Lo que el registro concede tiene que poderse alcanzar desde el menu.

Por que existe este archivo
---------------------------
Preguntando "y para anadir nuevos productos o familias de productos como le
hago?" salio que no habia forma de hacerlo desde el menu.

La causa: el registro decide la ubicacion de cada fila asi:

    "sidebar" if etiqueta else "hidden"

y `product_family`, `brand`, `unit` e `inventory_status` no tenian entrada en el
mapa `MENU`. No fue una decision de ocultarlos -no hay ningun comentario que lo
justifique, y las cuatro pantallas existen con su ruta-: fue no haberlos
nombrado. El efecto medido en la base fue que `product_family` estaba en
`hidden` para los cinco roles y sin etiqueta, asi que nadie podia dar de alta
una familia de producto aunque tuviera el permiso concedido.

Un permiso concedido a una pantalla a la que solo se llega escribiendo la
direccion a mano no es una funcionalidad: es una funcionalidad que nadie
encuentra. Y el fallo es silencioso por construccion -no hay error, no hay 403,
simplemente no aparece la entrada- asi que solo se descubre cuando alguien va a
usarla.

Lo que estas pruebas fijan:

* **toda entidad del modulo de inventario tiene nombre de menu.** Es la
  invariante que se rompio. Si alguien agrega una entidad al almacen y no la
  nombra, esto falla en vez de dejarla invisible;
* **dos entradas del mismo grupo no comparten etiqueta.** Un menu con dos
  "Movimientos" seguidos obliga a probar los dos para saber cual es cual.
"""

from __future__ import annotations

import collections
import unittest

from app.modules.registry import MENU, MODULO_POR_CLAVE, SOLO_ARRANQUE, filas_de_permisos


class TestElInventarioSeAlcanzaDesdeElMenu(unittest.TestCase):

    def test_every_inventory_entity_has_a_menu_name(self):
        """Sin etiqueta el registro la siembra escondida, y nadie la encuentra."""
        inventario = MODULO_POR_CLAVE["inventario"]
        sin_nombre = sorted(
            entidad for entidad in inventario.entidades
            if entidad not in SOLO_ARRANQUE and entidad not in MENU
        )
        self.assertEqual(
            [], sin_nombre,
            "Estas entidades del almacen no tienen entrada en MENU, asi que el "
            "registro las siembra con menu_location='hidden' y no aparecen en "
            "ningun menu para ningun rol: " + ", ".join(sin_nombre)
            + ". Se nombran en MENU o se documenta aqui por que estan escondidas.",
        )

    def test_the_five_catalogues_a_product_hangs_from_are_reachable(self):
        """Dar de alta un producto pide recorrer estos cinco, en este orden."""
        for entidad in ("product_family", "brand", "unit", "material", "product"):
            with self.subTest(entidad=entidad):
                self.assertIn(
                    entidad, MENU,
                    f"`{entidad}` hace falta para dar de alta un producto y no "
                    "tiene entrada de menu",
                )

    def test_no_two_entries_of_a_group_share_a_label(self):
        """Dos "Movimientos" seguidos obligan a abrir los dos para saber cual es cual."""
        por_grupo: dict[str, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for _, entidad, _, ubicacion, grupo, _, etiqueta, _, _ in filas_de_permisos():
            if ubicacion == "sidebar" and etiqueta:
                # Se cuentan entidades distintas, no filas: la misma entidad
                # aparece una vez por rol y eso no es una repeticion.
                por_grupo[grupo][(etiqueta, entidad)] += 1

        repetidas = {}
        for grupo, cuenta in por_grupo.items():
            etiquetas = [etiqueta for etiqueta, _ in cuenta]
            duplicadas = sorted(e for e in set(etiquetas) if etiquetas.count(e) > 1)
            if duplicadas:
                repetidas[grupo] = duplicadas
        self.assertEqual({}, repetidas, f"etiquetas repetidas por grupo: {repetidas}")


if __name__ == "__main__":
    unittest.main()
