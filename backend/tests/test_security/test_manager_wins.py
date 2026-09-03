"""El gestor de roles manda; el registro solo siembra lo que falta.

Por que existe este archivo
---------------------------
Antes de este cambio, la matriz de permisos daba de baja todo lo vigente y
resembraba el mapa CRUD desde el registro, en cada arranque del pod. Medido:
un administrador subia el permiso de un rol sobre `product` de 2 a 15, se
reaplicaban las migraciones, y volvia a 2.

Eso contradecia lo que la interfaz promete. El gestor ofrece editar bits y
ubicacion por rol y por entidad; si el registro los reescribe en el siguiente
despliegue, el gestor es decorativo.

La decision fue que el gestor manda. El registro sigue dando el valor POR
OMISION -lo que recibe un modulo nuevo, una entidad nueva o un rol nuevo- y deja
de ser la fuente de la verdad sobre quien puede que.

Lo que estas pruebas fijan, en orden de importancia:

* **ninguna migracion pisa el mapa CRUD de una fila existente.** Es la
  invariante: si alguien vuelve a poner un `ON CONFLICT ... DO UPDATE SET
  control_type` en cualquier migracion, el gestor deja de mandar y nadie se
  entera hasta el despliegue siguiente;
* **ninguna migracion da de baja los permisos en masa**, por el mismo motivo;
* **quitar un permiso lo marca de baja, no borra la fila.** Con borrado fisico,
  una fila ausente significa a la vez "nueva" y "la quitaron", y el sembrado no
  puede distinguirlas: resucitaria en cada despliegue lo que alguien retiro;
* **el listado no muestra lo retirado.** Un gestor que ensena un permiso que el
  guardia niega manda a buscar el problema en el rol, donde no hay nada que
  arreglar.
"""

from __future__ import annotations

import pathlib
import re
import unittest

from sqlalchemy import select

from app.models import EntityPermission
from app.models.session import transaction_context
from tests.conftest import BackendTestCase

MIGRACIONES = pathlib.Path(__file__).resolve().parents[3] / "database" / "migrations"


class TestNingunaMigracionPisaAlGestor(unittest.TestCase):
    """La invariante, leida de los archivos.

    Se comprueba sobre el texto y no sobre la base a proposito: el efecto solo
    se ve reaplicando las migraciones sobre datos que alguien edito, y eso no se
    puede montar en una prueba unitaria. Lo que si se puede fijar es que la
    forma peligrosa no vuelva a aparecer.
    """

    def _archivos(self):
        archivos = sorted(MIGRACIONES.glob("*.sql"))
        self.assertGreater(len(archivos), 10, f"no se hallaron migraciones en {MIGRACIONES}")
        return archivos

    def test_no_migration_overwrites_an_existing_permission(self):
        """`DO UPDATE SET control_type` es la forma que revierte al gestor."""
        culpables = []
        for archivo in self._archivos():
            texto = archivo.read_text(encoding="utf-8", errors="replace")
            for bloque in re.finditer(
                r"ON CONFLICT \([^)]*entity_name[^)]*\)\s*DO UPDATE\s*SET(?:.|\n)*?;", texto
            ):
                if "control_type" in bloque.group(0):
                    culpables.append(archivo.name)
                    break
        self.assertEqual(
            [], culpables,
            "Estas migraciones pisan el mapa CRUD de una fila que ya existe, asi que "
            "revierten lo que el administrador configuro en el gestor: "
            + ", ".join(culpables),
        )

    def test_no_migration_revives_a_withdrawn_permission(self):
        """Reactivar una fila de baja devuelve un acceso que alguien retiro."""
        culpables = []
        for archivo in self._archivos():
            texto = archivo.read_text(encoding="utf-8", errors="replace")
            for bloque in re.finditer(
                r"ON CONFLICT \([^)]*entity_name[^)]*\)\s*DO UPDATE\s*SET(?:.|\n)*?;", texto
            ):
                if re.search(r"deletion_date\s*=\s*NULL", bloque.group(0), re.I):
                    culpables.append(archivo.name)
                    break
        self.assertEqual([], culpables, "\n" + "\n".join(culpables))

    def test_no_migration_withdraws_every_permission_at_once(self):
        """El borrado general es lo que hacia que nada del gestor durase."""
        culpables = []
        patron = re.compile(
            r"UPDATE\s+entity_permission\s+SET\s+deletion_date\s*=\s*now\(\)\s*"
            r"WHERE\s+deletion_date\s+IS\s+NULL",
            re.I | re.S,
        )
        for archivo in self._archivos():
            texto = " ".join(archivo.read_text(encoding="utf-8", errors="replace").split())
            if patron.search(texto):
                culpables.append(archivo.name)
        self.assertEqual(
            [], culpables,
            "Estas migraciones dan de baja todos los permisos vigentes antes de "
            "sembrar, asi que borran lo que el gestor configuro: " + ", ".join(culpables),
        )


class TestElServicioDeLaTablaDePermisos(unittest.TestCase):
    """Baja logica y listado, sin tocar la base."""

    def test_it_overrides_delete_and_list(self):
        """Si alguien quita estos metodos, vuelve el comportamiento del CRUD generico.

        El generico borra fisicamente -y entonces el sembrado no distingue una
        fila nueva de una retirada- y lista sin filtrar la baja -y entonces el
        gestor ensena permisos que el guardia niega-.
        """
        from app.services.base_service import CrudService
        from app.services.entity_permission_service import EntityPermissionService

        for metodo in ("delete", "list"):
            with self.subTest(metodo=metodo):
                self.assertIsNot(
                    EntityPermissionService.__dict__.get(metodo),
                    None,
                    f"EntityPermissionService debe definir su propio `{metodo}`",
                )
                self.assertIsNot(
                    getattr(EntityPermissionService, metodo).__func__,
                    getattr(CrudService, metodo).__func__,
                    f"`{metodo}` cayo al del CRUD generico",
                )


class TestRetirarUnPermiso(BackendTestCase):
    """El comportamiento, contra una base de verdad.

    La primera version de estas dos pruebas leia el codigo fuente buscando
    cadenas, y la de `delete` fallaba porque su propio comentario menciona
    `session.delete`. Buscar texto en el codigo prueba como esta escrito, no que
    funcione; esto prueba lo segundo.
    """

    def setUp(self):
        super().setUp()
        # No se crea la fila de `permission`: `Permission` exige departamento,
        # subdepartamento y nivel, y montar esa cadena no aporta nada a lo que
        # se prueba aqui, que es como se retira y como se lista un permiso de
        # entidad.
        with transaction_context() as db:
            db.add(EntityPermission(
                id_permission=90, entity_name="brand", control_type=7,
                menu_location="sidebar", created_by=1,
            ))
            db.flush()

    def _fila(self, db):
        return db.scalars(
            select(EntityPermission).where(
                EntityPermission.id_permission == 90,
                EntityPermission.entity_name == "brand",
            )
        ).first()

    def test_withdrawing_marks_it_instead_of_removing_it(self):
        """Con borrado fisico, el sembrado no puede distinguir "nueva" de "retirada"."""
        from app.services.entity_permission_service import EntityPermissionService

        with transaction_context() as db:
            id_fila = self._fila(db).id_entity_permission

        EntityPermissionService.delete(id_fila, user_id=1)

        with transaction_context() as db:
            fila = self._fila(db)
            self.assertIsNotNone(fila, "la fila se borro; tenia que quedar de baja")
            self.assertIsNotNone(fila.deletion_date)

    def test_withdrawing_twice_keeps_the_first_date(self):
        """Refechar la baja perderia cuando se retiro de verdad."""
        from app.services.entity_permission_service import EntityPermissionService

        with transaction_context() as db:
            id_fila = self._fila(db).id_entity_permission

        EntityPermissionService.delete(id_fila, user_id=1)
        with transaction_context() as db:
            primera = self._fila(db).deletion_date

        EntityPermissionService.delete(id_fila, user_id=1)
        with transaction_context() as db:
            self.assertEqual(primera, self._fila(db).deletion_date)

    def test_the_listing_hides_it_and_the_total_agrees(self):
        """Un permiso visible que el guardia niega manda a buscar donde no hay nada."""
        from app.services.entity_permission_service import EntityPermissionService

        antes = EntityPermissionService.list(page=1, per_page=500)
        with transaction_context() as db:
            id_fila = self._fila(db).id_entity_permission
        self.assertIn(id_fila, {i["id_entity_permission"] for i in antes["items"]})

        EntityPermissionService.delete(id_fila, user_id=1)

        despues = EntityPermissionService.list(page=1, per_page=500)
        self.assertNotIn(id_fila, {i["id_entity_permission"] for i in despues["items"]})
        # El total no puede seguir contandola: con paginacion, un total que no
        # coincide con lo que se ve cuesta una hora a quien lo cree.
        self.assertEqual(antes["total"] - 1, despues["total"])
        self.assertEqual(len(despues["items"]), despues["total"])


if __name__ == "__main__":
    unittest.main()
