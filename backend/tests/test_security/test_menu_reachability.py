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

* **toda entidad del modulo de inventario se alcanza.** Es la invariante que se
  rompio. Con entrada de menu propia, o -si vive dentro de la pantalla de otra-
  declarada abajo en `DENTRO_DE_OTRA_PANTALLA` con el motivo. Si alguien agrega
  una entidad al almacen y no hace ninguna de las dos, esto falla en vez de
  dejarla invisible;
* **dos entradas del mismo grupo no comparten etiqueta.** Un menu con dos
  "Movimientos" seguidos obliga a probar los dos para saber cual es cual.
"""

from __future__ import annotations

import collections
import unittest

from app.modules.registry import MENU, MODULO_POR_CLAVE, SOLO_ARRANQUE, filas_de_permisos


# Entidades del almacen sin entrada de menu PROPIA porque se trabajan desde la
# pantalla de otra. No es lo mismo que estar escondidas: se alcanzan, solo que
# por el sitio donde tienen sentido.
#
# Cada una lleva por que. Sin el motivo escrito, esto seria una lista donde
# esconder cualquier cosa que estorbe, y la invariante dejaria de valer.
DENTRO_DE_OTRA_PANTALLA = {
    # `material_type.id_product_family` hace que un tipo cuelgue de una familia
    # y no exista suelto: "Plano" no significa nada por si mismo, es un tipo DE
    # desarmador. Con entrada propia el menu mostraba "Familias de producto" y
    # "Tipos de material" seguidas, que leidas asi parecen la misma cosa dos
    # veces -se reporto justamente como un modulo duplicado-. Los tipos se
    # capturan dentro de su familia, en la pantalla de `product_family`.
    "material_type": "product_family",
    # Las caracteristicas que una familia declara -largo, calibre, acabado- se
    # configuran dentro de la familia, en la misma pantalla. Con entrada propia
    # el menu tendria "Caracteristicas de material" sin decir de que familia, y
    # una caracteristica sin su familia no significa nada: "largo" es el largo
    # DE un desarmador.
    "material_attribute": "product_family",
}


class TestElInventarioSeAlcanzaDesdeElMenu(unittest.TestCase):

    def test_every_inventory_entity_has_a_menu_name(self):
        """Sin etiqueta el registro la siembra escondida, y nadie la encuentra."""
        inventario = MODULO_POR_CLAVE["inventario"]
        sin_nombre = sorted(
            entidad for entidad in inventario.entidades
            if entidad not in SOLO_ARRANQUE
            and entidad not in MENU
            and entidad not in DENTRO_DE_OTRA_PANTALLA
        )
        self.assertEqual(
            [], sin_nombre,
            "Estas entidades del almacen no tienen entrada en MENU, asi que el "
            "registro las siembra con menu_location='hidden' y no aparecen en "
            "ningun menu para ningun rol: " + ", ".join(sin_nombre)
            + ". Se nombran en MENU o se documenta aqui por que estan escondidas.",
        )

    def test_the_host_screen_of_a_nested_entity_is_itself_in_the_menu(self):
        """Si la anfitriona pierde su entrada, la de dentro se queda sin puerta.

        Es el modo en que esta excepcion se romperia en silencio: alguien quita
        "Familias y tipos" del menu y `material_type` deja de alcanzarse sin que
        nada avise, porque su propia ausencia ya estaba declarada.
        """
        for entidad, anfitriona in DENTRO_DE_OTRA_PANTALLA.items():
            with self.subTest(entidad=entidad):
                self.assertIn(
                    anfitriona, MENU,
                    "%s se captura dentro de la pantalla de %s, y %s no tiene "
                    "entrada de menu: entre las dos no se alcanza ninguna."
                    % (entidad, anfitriona, anfitriona),
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


class TestElFlujoDeOperacionesSeLeeEnOrden(unittest.TestCase):
    """El grupo Operaciones tiene que leerse como el trabajo, no como el diccionario.

    El grupo se leia asi -orden real, porque una entrada sin `menu_order` cae en
    el 100 por omision y despues se ordena por etiqueta-:

        Calendario, Detalle de incidencias, Incidencias, Notas de tarea,
        Plantillas, Proyectos, Servicios, Tareas, Tipos de tarea

    Proyectos, que es por donde se entra -`task.id_proyect` es NOT NULL, ninguna
    tarea existe sin el- salia en sexto lugar y detras de las notas de sus
    propias tareas. Estas pruebas fijan lo que se corrigio.
    """

    def test_a_project_comes_before_its_tasks(self):
        """Se entra por el proyecto: `task.id_proyect` es NOT NULL."""
        self.assertLess(
            MENU["proyect"][1], MENU["task"][1],
            "Proyectos tiene que ir delante de Tareas: una tarea no existe sin "
            "su proyecto y el menu es lo que ensena ese orden",
        )

    def test_the_incident_type_a_incident_needs_is_reachable(self):
        """`incident.id_incident_type` es NOT NULL y no habia donde darlo de alta."""
        self.assertIn(
            "incident_type", MENU,
            "`incident_type` es obligatorio para levantar una incidencia. Sin "
            "entrada en MENU el registro lo siembra con menu_location='hidden' "
            "y no hay forma de dar de alta un tipo desde el menu: es el mismo "
            "fallo que tuvo `product_family` en inventario",
        )

    def test_a_child_row_has_no_menu_entry_of_its_own(self):
        """Un hijo se captura desde su padre, no en una tercera pantalla.

        `task_note.id_task` es NOT NULL, y `nm_incident_product` y
        `nm_template_task` son tablas puente. Con entrada propia habia que abrir
        otra lista y elegir el padre en un desplegable para escribir una nota,
        y la bitacora de una tarea no se leia junta en ningun sitio.
        """
        for entidad in ("task_note", "nm_incident_product", "nm_template_task"):
            with self.subTest(entidad=entidad):
                self.assertNotIn(
                    entidad, MENU,
                    f"`{entidad}` cuelga de otra fila y se captura desde ella. "
                    "Si vuelve al menu hay dos puertas al mismo registro, una "
                    "de ellas pidiendo el padre en un desplegable",
                )

    def test_no_operations_label_names_something_else(self):
        """"Detalle de incidencias" nombraba un catalogo de subtipos.

        `incident_detail.id_incident_type` apunta al TIPO, no a la incidencia, y
        la entrada estaba justo debajo de "Incidencias": quien buscaba el
        detalle de una incidencia abria un catalogo.
        """
        etiqueta = MENU["incident_detail"][0]
        self.assertNotIn(
            "Detalle", etiqueta,
            "`incident_detail` cuelga de `incident_type`, no de `incident`: su "
            f"etiqueta no puede leerse como el detalle de una incidencia "
            f"(ahora dice {etiqueta!r})",
        )

    def test_every_operations_entity_is_named_or_hangs_from_a_parent(self):
        """O tiene entrada, o esta en la lista de las que se abren desde su padre."""
        # Las que se capturan desde su dueno, con la razon en el propio nombre
        # de la columna que las ata: task_note.id_task, nm_*.id_*.
        desde_el_padre = {"task_note", "nm_incident_product", "nm_template_task"}
        operaciones = MODULO_POR_CLAVE["operaciones"]
        huerfanas = sorted(
            entidad for entidad in operaciones.entidades
            if entidad not in SOLO_ARRANQUE
            and entidad not in MENU
            and entidad not in desde_el_padre
        )
        self.assertEqual(
            [], huerfanas,
            "Estas entidades de operaciones no tienen entrada de menu y no "
            "estan declaradas como capturables desde su padre, asi que el "
            "registro las siembra escondidas y nadie las encuentra: "
            + ", ".join(huerfanas),
        )


if __name__ == "__main__":
    unittest.main()
