"""Matriz de aislamiento por proyecto, sobre HTTP y con dos proyectos reales.

La auditoria externa marco este control como el hallazgo P0 y lo dejo sin
cubrir: "falta matriz HTTP con dos proyectos". Aqui esta.

Cada ruta se prueba en las DOS direcciones, y eso es lo que hace la prueba:
un 404 para el ajeno no demuestra nada si el dueno tambien recibe 404 -eso
seria un endpoint roto, no uno acotado-. Solo la pareja 200/404 prueba que el
filtro existe y que no se llevo por delante el caso legitimo.

Dos reglas conviven a proposito, porque cada modulo ya tenia la suya:

* **Facturacion**: igualdad estricta de proyecto. Es lo que ya hacian la
  descarga del XML y los cuatro flujos fiscales; faltaba en el CRUD.
* **Operaciones**: visibilidad por facultad. Quien autoriza ve todos los
  proyectos y sus tareas, decision que ya estaba tomada en `_scoped_query`.

Confundirlas al probar da falsos hallazgos: medir facturacion con un gerente
que autoriza parece una fuga cuando es la regla de operaciones.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

import jwt

from app.models import (
    Brand, CustomerSupplier, Incident, IncidentType, Invoice, Location,
    LocationType, Material, NmIncidentProduct, Product, ProductFamily, Proyect,
    Status, Task, Unit, User,
)
from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase


PRINCIPAL = 10
CLIENTE = 20

# Perfil de los dos responsables. Se le conceden los cuatro bits sobre las
# entidades que la matriz recorre, porque lo que se prueba aqui es el alcance
# por proyecto, no el permiso de entidad: si el perfil no pudiera leer, todo
# responderia 403 y la matriz daria verde sin haber medido el filtro.
PERFIL = 1
ENTIDADES = (
    "invoice", "task", "proyect", "product", "nm_incident_product",
    "incident", "location", "movement",
)

# Dos proyectos, cada uno con su propio responsable. Los ids se eligen
# separados para que un error de alcance salte a la vista en la aserion.
PROYECTO_A, LIDER_A = 30, 301
PROYECTO_B, LIDER_B = 40, 401

FACTURA_A, FACTURA_B = 50, 60
TAREA_A, TAREA_B = 70, 80
INCIDENCIA_A, INCIDENCIA_B = 90, 100
RENGLON_A, RENGLON_B = 110, 120
ALMACEN = 2
PRODUCTO_A, PRODUCTO_B = 130, 140


class ProjectScopeMatrix(BackendTestCase):
    """Dos proyectos completos y un responsable en cada uno."""

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=PRINCIPAL, name="Mi Empresa", tax_id="AAA010101AA1",
                    postal_code="37000", fiscal_type="601", type="supplier",
                    is_principal=True, id_user=1, created_by=1,
                ),
                CustomerSupplier(
                    id_customer_supplier=CLIENTE, name="Cliente", tax_id="BBB010101BB1",
                    postal_code="37100", fiscal_type="601", type="client",
                    id_user=1, created_by=1,
                ),
                LocationType(id_location_type=1, location_type_description="Almacen",
                             is_warehouse=True, created_by=1),
                Brand(id_brand=1, brand_description="Generica", created_by=1),
                ProductFamily(id_product_family=1, product_family_description="General", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True,
                     measurement_system="metric", created_by=1),
                IncidentType(id_incident_type=1, incident_type_description="Falla", created_by=1),
            ])
            # Lo que ve y edita un responsable de proyecto lo manda el Gestor
            # (`proyect.scope_read`/`scope_update`): Propios. Con Todos veria
            # los proyectos de los demas -desde 2026-10-16 el codigo respeta
            # esa celda-, que es justo la fuga que esta matriz vigila.
            db.add_all([
                EntityPermission(id_permission=PERFIL, entity_name=nombre,
                                 scope_create=4, scope_read=1 if nombre == "proyect" else 4,
                                 scope_update=1 if nombre == "proyect" else 4, scope_delete=4,
                                 created_by=1)
                for nombre in ENTIDADES
            ])
            db.flush()
            db.add_all([
                Status(id_status=40, status_description="Activo", category="invoice",
                       is_terminal=False, sort_order="asc", created_by=1),
                Location(id_location=ALMACEN, id_location_type=1,
                         location_description="Almacen Central", created_by=1),
                Material(id_material=1, material_description="Cemento", id_unit=1,
                         id_brand=1, id_product_family=1, created_by=1),
            ])
            db.flush()

            for id_proyect, id_lider in ((PROYECTO_A, LIDER_A), (PROYECTO_B, LIDER_B)):
                db.add(Proyect(
                    id_proyect=id_proyect, id_customer_supplier=CLIENTE, leader=id_lider,
                    proyect_description=f"Proyecto {id_proyect}", created_by=id_lider,
                ))
            db.flush()

            for (id_factura, id_tarea, id_incidencia, id_renglon, id_producto,
                 id_proyect, id_lider) in (
                (FACTURA_A, TAREA_A, INCIDENCIA_A, RENGLON_A, PRODUCTO_A, PROYECTO_A, LIDER_A),
                (FACTURA_B, TAREA_B, INCIDENCIA_B, RENGLON_B, PRODUCTO_B, PROYECTO_B, LIDER_B),
            ):
                db.add(Invoice(
                    id_invoice=id_factura, id_customer_supplier=CLIENTE,
                    id_issuer_customer_supplier=PRINCIPAL, id_proyect=id_proyect,
                    id_status=40, invoice_status="pendiente",
                    tax_certification_supplier=PRINCIPAL, apply_tax=False,
                    total=Decimal("116.00"), currency="MXN", created_by=id_lider,
                ))
                db.add(Task(
                    id_task=id_tarea, id_proyect=id_proyect, task_description="Tarea",
                    task_status="pendiente", owner=id_lider, validation=id_lider, dependency=0,
                    created_by=id_lider,
                ))
                db.add(Incident(
                    id_incident=id_incidencia, id_incident_type=1, id_user=id_lider,
                    id_lider=id_lider, incident_status="abierta", created_by=id_lider,
                ))
                db.flush()
                db.add(Product(
                    id_product=id_producto, id_invoice=id_factura, id_location=ALMACEN,
                    id_material=1, is_directly_related_to_product_service=False,
                    cantidad=5, created_by=id_lider,
                ))
                db.flush()
                db.add(NmIncidentProduct(
                    id_nm_incident_product=id_renglon, id_incident=id_incidencia,
                    id_product=id_producto, quantity=1, created_by=id_lider,
                ))

    def token(self, id_user, id_proyect, id_permission=1):
        """Un actor real: sin superusuario, que salta todas las comprobaciones.

        Probar el aislamiento con la cuenta de arranque es el error que dejo
        este hueco sin descubrir durante meses.
        """
        return jwt.encode(
            {
                "id_user": id_user,
                "id_proyect": id_proyect,
                "id_permission": id_permission,
                "user_type": "employee",
            },
            SECRET_KEY,
            algorithm="HS256",
        )

    def headers(self, id_user, id_proyect):
        return {"Authorization": f"Bearer {self.token(id_user, id_proyect)}"}

    def ambos_lados(self, ruta, metodo="GET", cuerpo=None):
        """Pide el recurso del proyecto A como dueno y como ajeno.

        Devuelve (codigo_del_dueno, codigo_del_ajeno).
        """
        llamar = getattr(self.client, metodo.lower())
        argumentos = {"json": cuerpo} if cuerpo is not None else {}
        dueno = llamar(ruta, headers=self.headers(LIDER_A, PROYECTO_A), **argumentos)
        ajeno = llamar(ruta, headers=self.headers(LIDER_B, PROYECTO_B), **argumentos)
        return dueno.status_code, ajeno.status_code

    def assertAcotado(self, ruta, metodo="GET", cuerpo=None):
        dueno, ajeno = self.ambos_lados(ruta, metodo, cuerpo)
        self.assertEqual(
            200, dueno,
            f"{metodo} {ruta}: el dueno no puede acceder a lo suyo, el filtro se paso de largo",
        )
        self.assertIn(
            ajeno, (403, 404),
            f"{metodo} {ruta}: el ajeno recibio {ajeno}; el recurso se esta filtrando",
        )


class TestFacturacion(ProjectScopeMatrix):
    """Igualdad estricta: una factura solo se toca desde su propio proyecto."""

    def test_reading_an_invoice_record(self):
        self.assertAcotado(f"/invoice/{FACTURA_A}")

    def test_modifying_an_invoice_record(self):
        """La fuga peor: no solo se leia una factura ajena, se podia cambiar."""
        self.assertAcotado(f"/invoice/{FACTURA_A}", "PUT", {"note": "cambiada"})

    def test_deleting_an_invoice_record(self):
        dueno, ajeno = self.ambos_lados(f"/invoice/{FACTURA_A}", "DELETE")
        self.assertIn(ajeno, (403, 404), f"el ajeno pudo borrar: {ajeno}")

    def test_reading_the_invoice_lines(self):
        self.assertAcotado(f"/invoice/{FACTURA_A}/lines")

    def test_the_invoice_list_only_shows_your_own(self):
        respuesta = self.client.get("/invoice/", headers=self.headers(LIDER_A, PROYECTO_A))

        self.assertEqual(200, respuesta.status_code)
        ids = {item.get("id_invoice") for item in self.json(respuesta).get("items", [])}
        self.assertIn(FACTURA_A, ids)
        self.assertNotIn(FACTURA_B, ids, "el listado incluye una factura de otro proyecto")

    def test_an_invoice_cannot_be_created_inside_another_project(self):
        respuesta = self.client.post("/invoice/", headers=self.headers(LIDER_B, PROYECTO_B), json={
            "id_proyect": PROYECTO_A,
            "id_customer_supplier": CLIENTE,
            "id_issuer_customer_supplier": PRINCIPAL,
            "id_status": 40,
            "tax_certification_supplier": PRINCIPAL,
        })

        self.assertIn(respuesta.status_code, (400, 403, 404),
                      "se creo una factura dentro de un proyecto ajeno")

    def test_an_invoice_does_not_end_up_in_another_project(self):
        """El traslado es la misma fuga por la puerta de atras.

        Se comprueba el resultado y no el codigo: hoy el filtro de campos
        descarta `id_proyect` antes de llegar al guardia, asi que la respuesta es
        200 y la factura no se mueve. Afirmar sobre el 200 ataria la prueba a
        cual de las dos defensas actuo primero; lo que importa es que la factura
        siga en su proyecto.
        """
        self.client.put(
            f"/invoice/{FACTURA_B}",
            headers=self.headers(LIDER_B, PROYECTO_B),
            json={"id_proyect": PROYECTO_A},
        )

        with transaction_context() as db:
            self.assertEqual(PROYECTO_B, db.get(Invoice, FACTURA_B).id_proyect,
                             "la factura acabo en un proyecto ajeno")

    def test_the_guard_refuses_a_foreign_project_on_its_own(self):
        """El guardia, aparte del filtro de campos.

        Si alguien concede `id_proyect` como campo escribible, el filtro deja
        de frenar el traslado y solo queda este guardia. Sin esta prueba seria
        codigo que nadie ejercita.
        """
        from app.services.invoice_service import InvoiceService
        from app.utils.errors import AppError

        actor = {"id_user": LIDER_B, "id_proyect": PROYECTO_B, "id_permission": PERFIL}

        with self.assertRaises(AppError) as raised:
            InvoiceService.require_project_for_write(PROYECTO_A, actor)
        self.assertEqual("errors.permission_denied", raised.exception.message_key)

        # Y el propio proyecto si pasa, para que el guardia no sea un muro.
        InvoiceService.require_project_for_write(PROYECTO_B, actor)

    def test_an_actor_without_a_project_is_refused(self):
        """Sin proyecto no hay como acotar, asi que no se entrega nada."""
        token = jwt.encode(
            {"id_user": LIDER_A, "id_permission": 1, "user_type": "employee"},
            SECRET_KEY, algorithm="HS256",
        )
        respuesta = self.client.get(f"/invoice/{FACTURA_A}",
                                    headers={"Authorization": f"Bearer {token}"})

        self.assertIn(respuesta.status_code, (403, 404))


class TestOperaciones(ProjectScopeMatrix):
    def test_reading_a_task(self):
        self.assertAcotado(f"/task/{TAREA_A}")

    def test_modifying_a_task(self):
        self.assertAcotado(f"/task/{TAREA_A}", "PUT", {"task_description": "cambiada"})

    def test_reading_a_project(self):
        self.assertAcotado(f"/proyect/{PROYECTO_A}")

    def test_the_products_of_an_incident_are_not_readable_from_outside(self):
        """`incident` devuelve 404 a quien no participa; su contenido no lo hacia.

        Se podia averiguar que productos se vieron afectados en cualquier
        incidencia pidiendo el renglon por su id. La incidencia quedaba cerrada
        y lo que contiene, abierto.
        """
        self.assertAcotado(f"/nm_incident_product/{RENGLON_A}")

    def test_the_incident_product_list_only_shows_your_own(self):
        respuesta = self.client.get("/nm_incident_product/",
                                    headers=self.headers(LIDER_A, PROYECTO_A))

        self.assertEqual(200, respuesta.status_code)
        ids = {item.get("id_nm_incident_product")
               for item in self.json(respuesta).get("items", [])}
        self.assertNotIn(RENGLON_B, ids,
                         "el listado incluye productos de una incidencia ajena")


class TestAlmacen(ProjectScopeMatrix):
    """Ya estaba cerrado; se fija para que no se abra."""

    def test_reading_a_product(self):
        self.assertAcotado(f"/product/{PRODUCTO_A}")

    def test_modifying_a_product(self):
        self.assertAcotado(f"/product/{PRODUCTO_A}", "PUT", {"cantidad": 6})

    def test_reading_the_stock_of_a_product(self):
        self.assertAcotado(f"/product/{PRODUCTO_A}/inventory-stock")

    def test_reading_the_ledger_of_a_product(self):
        self.assertAcotado(f"/product/{PRODUCTO_A}/inventory-movements")


class TestQueElFiltroNoSePasaDeLargo(ProjectScopeMatrix):
    """Que el arreglo no haya cerrado tambien el caso legitimo.

    Un filtro que niega a todo el mundo tambien da 404 al ajeno y pasaria las
    pruebas de arriba si solo se mirara ese lado. De ahi que cada aserion exija
    200 al dueno; estas lo dicen aparte para que quede explicito.
    """

    def test_each_leader_reaches_their_own_invoice(self):
        for id_user, id_proyect, id_factura in (
            (LIDER_A, PROYECTO_A, FACTURA_A),
            (LIDER_B, PROYECTO_B, FACTURA_B),
        ):
            with self.subTest(proyecto=id_proyect):
                respuesta = self.client.get(f"/invoice/{id_factura}",
                                            headers=self.headers(id_user, id_proyect))
                self.assertEqual(200, respuesta.status_code)

    def test_each_leader_reaches_their_own_task(self):
        for id_user, id_proyect, id_tarea in (
            (LIDER_A, PROYECTO_A, TAREA_A),
            (LIDER_B, PROYECTO_B, TAREA_B),
        ):
            with self.subTest(proyecto=id_proyect):
                respuesta = self.client.get(f"/task/{id_tarea}",
                                            headers=self.headers(id_user, id_proyect))
                self.assertEqual(200, respuesta.status_code)

    def test_the_bootstrap_account_still_reaches_everything(self):
        """La cuenta de arranque no debe quedar bloqueada por el filtro."""
        token = jwt.encode(
            {"id_user": 1, "id_proyect": PROYECTO_A, "is_bootstrap_admin": True},
            SECRET_KEY, algorithm="HS256",
        )
        cabeceras = {"Authorization": f"Bearer {token}"}

        for ruta in (f"/invoice/{FACTURA_A}", f"/invoice/{FACTURA_B}"):
            with self.subTest(ruta=ruta):
                self.assertEqual(200, self.client.get(ruta, headers=cabeceras).status_code)


if __name__ == "__main__":
    unittest.main()
