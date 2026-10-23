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
  control_type` (o, desde que `control_type` se partio en las 4 columnas
  `scope_create`/`scope_read`/`scope_update`/`scope_delete`, cualquiera de
  esas) en cualquier migracion, el gestor deja de mandar y nadie se entera
  hasta el despliegue siguiente;
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
        """`DO UPDATE SET control_type` (o su sucesor scope_*) revierte al gestor."""
        # `control_type` en entity_permission se partio en 4 columnas de
        # alcance; una migracion que pise cualquiera de ellas en un
        # `ON CONFLICT ... DO UPDATE` es exactamente el mismo problema que
        # pisar el `control_type` viejo, asi que se vigilan las 5 formas.
        columnas_prohibidas = (
            "control_type", "scope_create", "scope_read", "scope_update", "scope_delete",
        )
        culpables = []
        for archivo in self._archivos():
            texto = archivo.read_text(encoding="utf-8", errors="replace")
            for bloque in re.finditer(
                r"ON CONFLICT \([^)]*entity_name[^)]*\)\s*DO UPDATE\s*SET(?:.|\n)*?;", texto
            ):
                if any(columna in bloque.group(0) for columna in columnas_prohibidas):
                    culpables.append(archivo.name)
                    break
        self.assertEqual(
            [], culpables,
            "Estas migraciones pisan el mapa CRUD de una fila que ya existe, asi que "
            "revierten lo que el administrador configuro en el gestor: "
            + ", ".join(culpables),
        )

    # Deuda conocida, sin resolver a proposito -- ver el comentario de abajo.
    # Cada archivo pisa scope_create/read/update/delete de una fila EXISTENTE
    # con un UPDATE incondicional (clona los permisos de una entidad "fuente"
    # hacia una entidad nueva y los reafirma en cada reinicio del pod), el
    # mismo problema que 20260908100000_roles_con_los_ids_de_la_base.sql tenia
    # para Supervisor -- solo que acotado a las entidades que cada uno crea,
    # no a un rol entero. Detectado 2026-09-23 al escribir la prueba de abajo;
    # no se toco: son 10 archivos de altas de modulo (logistica, proyectos,
    # citas) mas la migracion de Fase 1 de equipos y alcance, cada uno con su
    # propio conjunto de entidades/roles, y corregirlos de fondo es trabajo
    # aparte del pedido que motivo esta prueba (Supervisor). Si se retira uno
    # de esta lista sin corregir el archivo, esta prueba lo va a atrapar.
    _DEUDA_UPDATE_INCONDICIONAL = frozenset({
        "20260822123000_logistics_contacts.sql",
        "20260822130000_logistics_addresses_contracts_rates.sql",
        "20260822140000_logistics_fleet.sql",
        "20260822150000_logistics_wms.sql",
        "20260822160000_logistics_workflow.sql",
        "20260822170000_logistics_remaining_entities.sql",
        "20260822190000_project_management.sql",
        "20260822210000_appointments.sql",
        "20260910110000_el_prevale_lo_autoriza_el_jefe_de_almacen.sql",
        "20260914110000_equipos_y_alcance_por_accion.sql",
    })

    def test_no_migration_overwrites_scope_columns_via_plain_update(self):
        """La misma invariante, pero fuera de un `ON CONFLICT`.

        `20260908100000_roles_con_los_ids_de_la_base.sql` pisaba el mapa CRUD
        con un `UPDATE entity_permission ... FROM <temp> WHERE ...` comun y
        corriente -- sin `ON CONFLICT` de por medio -- asi que la prueba de
        arriba (que solo busca ese patron) nunca lo vio. Corria en cada
        arranque del pod igual que un `ON CONFLICT DO UPDATE` lo haria.

        Los archivos en `_DEUDA_UPDATE_INCONDICIONAL` tienen el mismo defecto
        y siguen sin corregirse (ver el comentario de esa lista); esta prueba
        no los vuelve a fallar para no bloquear trabajo que no los toca, pero
        tampoco deja que aparezca uno nuevo sin que alguien se entere.
        """
        columnas_prohibidas = ("scope_create", "scope_read", "scope_update", "scope_delete")
        culpables = []
        for archivo in self._archivos():
            if archivo.name in self._DEUDA_UPDATE_INCONDICIONAL:
                continue
            texto = archivo.read_text(encoding="utf-8", errors="replace")
            # Un UPDATE de una sola vez, protegido por una marca en `migration_once`,
            # no se reaplica en cada arranque: el gestor puede cambiarlo despues.
            if "migration_once" in texto:
                continue
            for bloque in re.finditer(
                r"UPDATE\s+entity_permission\b(?:(?!;).)*?\bSET\b(?:(?!;).)*?;",
                texto, re.I | re.S,
            ):
                # Solo importa una columna prohibida del lado del SET, no de un
                # WHERE/IS DISTINCT FROM que solo la lee para decidir si tocar
                # la fila -- de eso trata precisamente el patron que se quito.
                set_clause = re.split(
                    r"\bFROM\b|\bWHERE\b", bloque.group(0), maxsplit=1, flags=re.I
                )[0]
                if any(f"{columna} =" in set_clause.replace("  ", " ") for columna in columnas_prohibidas):
                    culpables.append(archivo.name)
                    break
        self.assertEqual(
            [], culpables,
            "Estas migraciones pisan el mapa CRUD de una fila existente con un "
            "UPDATE directo (sin ON CONFLICT), mismo problema que revierte al "
            "gestor de roles: " + ", ".join(culpables),
        )

    def test_no_migration_withdraws_rows_absent_from_its_own_matrix(self):
        """Dar de baja por ausencia en una matriz vieja tambien revierte al gestor.

        Distinto del `test_no_migration_withdraws_every_permission_at_once` de
        abajo (que busca un borrado masivo sin condicion): este es el mismo
        problema pero acotado a un `NOT EXISTS` contra una tabla temporal --
        cualquier fila que el gestor haya agregado despues, y que esa tabla no
        conozca, se da de baja en el siguiente reinicio del pod.
        """
        culpables = []
        for archivo in self._archivos():
            texto = " ".join(archivo.read_text(encoding="utf-8", errors="replace").split())
            for bloque in re.finditer(
                r"UPDATE\s+entity_permission\b(?:(?!;).)*?\bSET\b(?:(?!;).)*?;",
                texto, re.I,
            ):
                cuerpo = bloque.group(0)
                if re.search(r"deletion_date\s*=\s*now\(\)", cuerpo, re.I) and re.search(
                    r"NOT\s+EXISTS", cuerpo, re.I
                ):
                    culpables.append(archivo.name)
                    break
        self.assertEqual(
            [], culpables,
            "Estas migraciones dan de baja filas de entity_permission ausentes "
            "de su propia matriz temporal, en cada reinicio del pod: "
            + ", ".join(culpables),
        )

    def test_no_migration_recreates_a_role_that_was_withdrawn(self):
        """Un NOT EXISTS que solo mira roles activos resucita el que se retiro.

        `20260828150000_warehouse_roles.sql` creaba "Jefe de almacen" si no
        veia una fila ACTIVA con ese nombre en `permission`. Una vez que
        `20260921120000_fusionar_jefe_de_almacen_en_almacenista.sql` lo dio de
        baja logica, cada reinicio del pod volvia a ver "no existe" (porque
        la unica fila que habia estaba de baja), creaba una fila nueva, y esa
        migracion la volvia a dar de baja en la misma pasada -- una fila
        fantasma nueva en cada despliegue, para siempre. Medido en tyakxa-dev:
        9 filas acumuladas en dos dias de deploys normales.
        """
        culpables = []
        for archivo in self._archivos():
            texto = " ".join(archivo.read_text(encoding="utf-8", errors="replace").split())
            for bloque in re.finditer(
                r"INSERT\s+INTO\s+permission\b(?:(?!;).)*?;", texto, re.I,
            ):
                cuerpo = bloque.group(0)
                if re.search(r"NOT\s+EXISTS\s*\(", cuerpo, re.I) and re.search(
                    r"deletion_date\s+IS\s+NULL", cuerpo, re.I
                ):
                    culpables.append(archivo.name)
                    break
        self.assertEqual(
            [], culpables,
            "Estas migraciones solo comprueban roles ACTIVOS antes de crear "
            "uno por nombre, asi que resucitan en cada reinicio del pod "
            "cualquier rol que se haya retirado a proposito: "
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
                id_permission=90, entity_name="brand",
                scope_create=4, scope_read=4, scope_update=4, scope_delete=0,
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
