"""El rastreo no puede hacer una consulta por producto.

Por que existe este archivo
---------------------------
Medido con 5000 productos en Postgres, antes de agrupar en lote: **271
consultas para devolver 40 resultados** -siete por producto- y casi un segundo
de reloj, del que solo un tercio era SQL; el resto era el coste de dar 271
vueltas a la base. En una pantalla que busca mientras se escribe eso no se
sostiene: cada pausa al teclear costaba un segundo.

Despues de agruparlo: **13 consultas y 134 ms**, y sin depender de cuantos
productos coincidan.

El problema con este tipo de arreglo es que se deshace solo. Anadir un dato al
resultado -"y de paso, el proveedor de cada producto"- con un `db.get` dentro
del bucle es lo natural, no falla ninguna prueba, y devuelve el N+1 sin que
nadie se entere hasta que un cliente con inventario de verdad se queja de que la
busqueda tarda. Estas pruebas convierten eso en un fallo inmediato.

Lo que fijan, en orden de importancia:

* **el numero de consultas no crece con el numero de productos.** Es la
  invariante: con tres productos y con treinta tiene que hacer las mismas. Si
  crece, hay un N+1;
* **tampoco crece con el numero de piezas** de un producto serializado, ni con
  el de movimientos;
* **hay un techo absoluto.** Aunque no crezca, veinte consultas por busqueda ya
  serian demasiadas para una pantalla que busca al teclear.

Como se cuenta
--------------
Con el evento `after_cursor_execute` del motor, que dispara una vez por
sentencia enviada a la base. Cuenta lo que de verdad viaja, no lo que uno cree
que viaja: el `db.get` que resuelve por la cache de identidad no dispara, y el
que va a la base si.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from sqlalchemy import event

from app.models import (
    Brand,
    CustomerSupplier,
    Invoice,
    Location,
    LocationType,
    Material,
    Product,
    ProductFamily,
    Proyect,
    Status,
    Unit,
)
from app.models.session import transaction_context
from app.services.inventory_service import apply_inventory_movement
from app.services.inventory_trace_service import localizar
from tests.conftest import BackendTestCase
from tests.model_factory import dar_capacidad


ACTOR = {"id_user": 1, "id_proyect": 70, "id_permission": 910}

# El techo. No es el numero medido -13 en Postgres con la pagina llena- sino
# margen sobre el: subirlo tiene que ser una decision consciente, no algo que
# pase solo.
TECHO_DE_CONSULTAS = 20


class ContadorDeConsultas:
    """Cuenta sentencias enviadas a la base mientras esta activo."""

    def __init__(self):
        self.total = 0
        self.sentencias: list[str] = []

    def __enter__(self):
        from app.models.session import engine

        self._engine = engine
        event.listen(engine, "after_cursor_execute", self._contar)
        return self

    def __exit__(self, *_):
        event.remove(self._engine, "after_cursor_execute", self._contar)
        return False

    def _contar(self, conn, cursor, statement, parameters, context, executemany):
        self.total += 1
        self.sentencias.append(" ".join(str(statement).split())[:110])

    def informe(self) -> str:
        return "\n".join(f"  {i + 1:3d}. {s}" for i, s in enumerate(self.sentencias))


class BaseDelAlmacen(BackendTestCase):
    """El almacen que las dos clases necesitan: una nave con un rack dentro."""

    ALMACEN = 9001
    RACK = 9002
    COMPRA = 9003

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            dar_capacidad(db, 910)
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=9010, name="Mi Empresa",
                    tax_id="AAA010101AA1", postal_code="37000", fiscal_type="601",
                    type="supplier", is_principal=True, id_user=1, created_by=1),
                CustomerSupplier(
                    id_customer_supplier=9011, name="Cliente", tax_id="BBB010101BB1",
                    postal_code="37100", fiscal_type="601", type="client",
                    id_user=1, created_by=1),
                LocationType(id_location_type=1, location_type_description="Nave",
                             is_warehouse=True, created_by=1),
                LocationType(id_location_type=2, location_type_description="Rack",
                             is_warehouse=False, created_by=1),
                Brand(id_brand=1, brand_description="Generica", created_by=1),
                ProductFamily(id_product_family=1,
                              product_family_description="General", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True,
                     measurement_system="metric", created_by=1),
            ])
            db.flush()
            db.add_all([
                Status(id_status=40, status_description="Activo", category="invoice",
                       is_terminal=False, sort_order="asc", created_by=1),
                Proyect(id_proyect=70, id_customer_supplier=9011, leader=1,
                        proyect_description="Proyecto", created_by=1),
                Location(id_location=self.ALMACEN, id_location_type=1,
                         location_description="Nave A", created_by=1),
                Material(id_material=1, material_description="Generico", id_unit=1,
                         id_brand=1, id_product_family=1, created_by=1),
            ])
            db.flush()
            # Un rack dentro de la nave: la rama tiene dos niveles, asi que la
            # cache de ubicaciones tiene que subir, y se nota si no lo hace en
            # lote.
            db.add(Location(id_location=self.RACK, id_location_type=2,
                            location_description="Rack A-1",
                            id_location_reference=self.ALMACEN, created_by=1))
            db.add(Invoice(
                id_invoice=self.COMPRA, id_customer_supplier=9010,
                id_issuer_customer_supplier=9011, id_proyect=70, id_status=40,
                invoice_status="timbrada", tax_certification_supplier=9011,
                apply_tax=False, created_by=1))
            db.flush()

    def _sembrar_productos(self, cuantos, *, desde=9100, serializado=False):
        with transaction_context() as db:
            db.add_all([
                Product(
                    id_product=desde + i, id_invoice=self.COMPRA,
                    id_location=self.RACK, id_material=1,
                    is_directly_related_to_product_service=True,
                    product_code=f"CARGA-{desde + i}",
                    descripcion=f"Tornillo hexagonal {desde + i}",
                    stock_purpose="mercancia",
                    tracking_mode="serializado" if serializado else "fungible",
                    gross_price=Decimal("10.00"), created_by=1,
                )
                for i in range(cuantos)
            ])
        for i in range(cuantos):
            apply_inventory_movement(desde + i, {
                "movement_type": "receive", "quantity": 10,
                "id_location": self.RACK, "reference_type": "purchase",
                "reference_id": str(self.COMPRA), "reason": "Compra",
                "idempotency_key": f"carga-{desde + i}",
            }, ACTOR)

    def _consultas_de(self, **kwargs):
        # Un tiro en vacio primero: la primera busqueda de un proceso paga la
        # compilacion de sentencias, y eso no es una consulta por producto.
        localizar("zzz-nada-coincide", ACTOR)
        with ContadorDeConsultas() as contador:
            resultado = localizar(kwargs.pop("consulta", ""), ACTOR, **kwargs)
        return contador, resultado


class TestElRastreoNoConsultaPorProducto(BaseDelAlmacen):

    def test_the_query_count_does_not_grow_with_the_number_of_products(self):
        """Es la invariante. Si crece, alguien metio un `db.get` en el bucle."""
        self._sembrar_productos(3, desde=9100)
        pocos, r_pocos = self._consultas_de(consulta="Tornillo")
        self.assertEqual(3, r_pocos["matches"])

        self._sembrar_productos(27, desde=9200)
        muchos, r_muchos = self._consultas_de(consulta="Tornillo", por_pagina=40)
        self.assertEqual(30, r_muchos["matches"])
        self.assertEqual(30, r_muchos["total"], "los 30 tienen que caber en la pagina")

        self.assertEqual(
            pocos.total, muchos.total,
            "Con 3 productos hizo %d consultas y con 30 hizo %d: hay una consulta "
            "por producto en alguna parte.\n\nCon 30 productos:\n%s"
            % (pocos.total, muchos.total, muchos.informe()),
        )

    def test_the_query_count_does_not_grow_with_the_number_of_pieces(self):
        """Treinta piezas de un taladro no son treinta lecturas."""
        from app.services.inventory_asset_service import register_asset

        self._sembrar_productos(1, desde=9300, serializado=True)
        with_one, _ = self._consultas_de(consulta="Tornillo")

        for i in range(12):
            register_asset({"id_product": 9300, "asset_tag": f"PZA-{i:03d}",
                            "id_location": self.RACK}, ACTOR)
        with_twelve, resultado = self._consultas_de(consulta="Tornillo")
        self.assertEqual(12, len(resultado["items"][0]["assets"]))

        self.assertEqual(
            with_one.total, with_twelve.total,
            "Con 0 piezas hizo %d consultas y con 12 hizo %d.\n\n%s"
            % (with_one.total, with_twelve.total, with_twelve.informe()),
        )

    def test_the_query_count_does_not_grow_with_the_number_of_movements(self):
        """La historia se agrega en la base, no recorriendo el libro en Python."""
        # Entran 50 y salen 15: con las 10 de `_sembrar_productos` la propia
        # prueba se topaba con el guardia de existencia insuficiente, que es el
        # guardia haciendo su trabajo.
        self._sembrar_productos(1, desde=9400)
        apply_inventory_movement(9400, {
            "movement_type": "receive", "quantity": 50, "id_location": self.RACK,
            "reference_type": "purchase", "reference_id": str(self.COMPRA),
            "reason": "Compra", "idempotency_key": "carga-extra-9400",
        }, ACTOR)
        uno, _ = self._consultas_de(consulta="Tornillo")

        for i in range(15):
            apply_inventory_movement(9400, {
                "movement_type": "issue", "quantity": 1, "id_location": self.RACK,
                "reference_type": "sale", "reference_id": f"V-{i}",
                "idempotency_key": f"venta-{i}",
            }, ACTOR)
        muchos, _ = self._consultas_de(consulta="Tornillo")

        self.assertEqual(
            uno.total, muchos.total,
            "Con 1 movimiento hizo %d consultas y con 16 hizo %d.\n\n%s"
            % (uno.total, muchos.total, muchos.informe()),
        )

    def test_there_is_an_absolute_ceiling_too(self):
        """Aunque no crezca, veinte por busqueda ya son demasiadas al teclear."""
        self._sembrar_productos(30, desde=9500)
        contador, _ = self._consultas_de(consulta="Tornillo", por_pagina=40)
        self.assertLessEqual(
            contador.total, TECHO_DE_CONSULTAS,
            "El rastreo hizo %d consultas, por encima del techo de %d.\n\n%s"
            % (contador.total, TECHO_DE_CONSULTAS, contador.informe()),
        )


class TestLaPaginacion(BaseDelAlmacen):
    """Antes se cortaba en cuarenta y se decia "afina la busqueda".

    No es una respuesta cuando el filtro ya esta puesto y aun quedan doscientas
    coincidencias: no hay nada que afinar y no hay forma de ver el resto.
    """

    def test_it_walks_the_pages_without_repeating_or_losing_anything(self):
        self._sembrar_productos(25, desde=9600)

        vistos = []
        for numero in (1, 2, 3):
            pagina = localizar("Tornillo", ACTOR, pagina=numero, por_pagina=10)
            self.assertEqual(25, pagina["matches"])
            self.assertEqual(3, pagina["pages"])
            self.assertEqual(numero, pagina["page"])
            vistos.extend(i["id_product"] for i in pagina["items"])

        self.assertEqual(25, len(vistos), "se repitio o se perdio algo al paginar")
        self.assertEqual(25, len(set(vistos)))

    def test_it_clamps_a_page_past_the_end_instead_of_returning_nothing(self):
        """Pedir la pagina 99 de tres es lo que pasa al filtrar estando en la 3."""
        self._sembrar_productos(5, desde=9700)

        pagina = localizar("Tornillo", ACTOR, pagina=99, por_pagina=2)
        self.assertEqual(3, pagina["page"])
        self.assertEqual(1, len(pagina["items"]))

    def test_it_caps_the_page_size_because_it_comes_from_the_client(self):
        """Sin tope, `per_page=100000` arma cien mil diccionarios."""
        self._sembrar_productos(3, desde=9800)

        from app.services.inventory_trace_service import TOPE_POR_PAGINA

        pagina = localizar("Tornillo", ACTOR, por_pagina=100000)
        self.assertEqual(TOPE_POR_PAGINA, pagina["per_page"])

    def test_the_default_page_size_is_not_the_cap(self):
        """El selector de "cuantos ver" necesita que sean numeros distintos.

        Eran el mismo 40: pedir 100 se recortaba a 40 sin avisar, asi que la
        opcion aparecia en la pantalla y no hacia nada.
        """
        self._sembrar_productos(3, desde=9700)

        from app.services.inventory_trace_service import (
            RESULTADOS_POR_PAGINA, TOPE_POR_PAGINA,
        )

        self.assertLess(RESULTADOS_POR_PAGINA, TOPE_POR_PAGINA)
        # Sin pedir nada, el valor por omision.
        self.assertEqual(RESULTADOS_POR_PAGINA,
                         localizar("Tornillo", ACTOR)["per_page"])
        # Y pidiendo mas que el default, se respeta.
        pedido = RESULTADOS_POR_PAGINA + 20
        self.assertEqual(pedido,
                         localizar("Tornillo", ACTOR, por_pagina=pedido)["per_page"])

    def test_the_card_gets_the_status_the_old_system_wrote(self):
        """`product_status` viaja en la respuesta, crudo.

        Es el unico sitio donde estan los seis valores completos del sistema
        anterior. El catalogo `inventory_status` no tiene fila para EXTRAVIADO,
        asi que 65 productos reales lo traen aqui y con el FK en nulo: pintar la
        tarjeta desde el catalogo los habria dejado sin color.
        """
        with transaction_context() as db:
            db.add(Product(
                id_product=9600, id_invoice=self.COMPRA, id_location=self.RACK,
                id_material=1, is_directly_related_to_product_service=True,
                product_code="CARGA-9600",
                descripcion="Tornillo hexagonal extraviado",
                stock_purpose="mercancia", tracking_mode="fungible",
                product_status="EXTRAVIADO", id_inventory_status=None,
                gross_price=Decimal("10.00"), created_by=1,
            ))

        encontrado = localizar("Tornillo hexagonal extraviado", ACTOR)["items"]
        self.assertEqual(1, len(encontrado))
        self.assertEqual("EXTRAVIADO", encontrado[0]["product_status"])

    def test_a_garbage_page_is_treated_as_the_first_one(self):
        self._sembrar_productos(3, desde=9900)

        for basura in ("abc", "", None, "-4"):
            with self.subTest(valor=basura):
                self.assertEqual(1, localizar("Tornillo", ACTOR, pagina=basura)["page"])


if __name__ == "__main__":
    unittest.main()
