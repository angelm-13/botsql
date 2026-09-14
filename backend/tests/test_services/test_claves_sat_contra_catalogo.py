"""La ClaveProdServ se valida contra el catalogo, no solo contra el formato.

Por que existe este archivo
---------------------------
Se validaba el formato -ocho digitos- y nada mas, asi que `00000000` pasaba y la
factura llegaba al PAC para que el PAC la rechazara. Medido: una factura con
`sat_product_key = "00000000"` y `sat_unit_key = "ZZZ"` daba `can_stamp = True`,
sin errores ni avisos.

El catalogo oficial c_ClaveProdServ son 52,514 claves de ocho digitos. Teclear
una que no existe es facil, y el error se descubria al timbrar, en el viaje al
PAC, con el mensaje que el PAC quisiera dar.

Lo que estas pruebas fijan, y el orden importa:

* **sin catalogo cargado NO se rechaza nada.** Es lo primero porque es lo que
  puede tumbar un despliegue: si la validacion diera por inexistente lo que no
  puede comprobar, un cliente que todavia no importo el catalogo se quedaria sin
  poder facturar. Sin catalogo se valida el formato, como siempre;
* **con catalogo cargado, una clave que no esta se rechaza** antes de timbrar, y
  el error dice cual concepto;
* **una clave que si esta pasa**, aunque no sea de las de uso frecuente: el
  catalogo manda, no la lista curada;
* **la clave de unidad solo avisa.** De c_ClaveUnidad no hay catalogo oficial en
  el repositorio -solo veinte claves frecuentes- asi que no se puede afirmar que
  una clave no exista. Rechazar `KGM` por no estar en una lista curada seria
  rechazar una clave valida del SAT.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.models import CustomerSupplier, Invoice, Proyect, Status
from app.models.session import transaction_context
from app.services.sat_catalog_service import (
    catalogo_cargado,
    claves_fuera_del_catalogo,
    import_product_keys,
)
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30, "is_superuser": True}
EMISOR, CLIENTE, PROYECTO, ESTATUS = 10, 20, 30, 40

# Dos claves de verdad del catalogo del SAT, y una que no existe.
CEMENTO = "30111601"
CONSULTORIA = "81111500"
INVENTADA = "00000002"


class BaseClaves(BackendTestCase):

    HEADER = "c_ClaveProdServ,Descripción,Palabras similares\n"

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=EMISOR, name="EMISOR DEMO SA DE CV",
                    tax_id="AAA010101AA1", postal_code="37000", fiscal_type="601",
                    type="supplier", is_principal=True, id_user=1, created_by=1),
                CustomerSupplier(
                    id_customer_supplier=CLIENTE, name="CLIENTE DEMO SA DE CV",
                    tax_id="BBB010101BB1", postal_code="37100", fiscal_type="601",
                    type="client", id_user=1, created_by=1),
            ])
            db.flush()
            db.add_all([
                Status(id_status=ESTATUS, status_description="Activo",
                       category="invoice", is_terminal=False, sort_order="asc",
                       created_by=1),
                Proyect(id_proyect=PROYECTO, id_customer_supplier=CLIENTE, leader=1,
                        proyect_description="Proyecto demo", created_by=1),
            ])

    def cargar_catalogo(self, filas=None):
        """Importa un catalogo minimo. No hacen falta las 52,514 para probar la regla."""
        cuerpo = filas or (
            f"{CEMENTO},Cemento,cal mortero\n"
            f"{CONSULTORIA},Servicios de programacion,software\n"
        )
        directorio = TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        ruta = Path(directorio.name) / "catalogo.csv"
        ruta.write_text(self.HEADER + cuerpo, encoding="utf-8")
        return import_product_keys(ruta)

    def preflight(self, clave_producto=CEMENTO, clave_unidad="E48"):
        from app.services.manual_invoice_service import create_manual_invoice
        from app.services.stamping import preflight_invoice

        r = create_manual_invoice({
            "id_proyect": PROYECTO, "id_customer_supplier": CLIENTE,
            "id_issuer_customer_supplier": EMISOR, "id_status": ESTATUS,
            "forma_pago": "03", "metodo_pago": "PUE", "uso_cfdi": "G03",
            "tipo_de_comprobante": "I",
            "concepts": [{"description": "Servicio", "quantity": "1",
                          "unit_price": "100",
                          "sat_product_key": clave_producto,
                          "sat_unit_key": clave_unidad}],
        }, ACTOR)
        return preflight_invoice(r["invoice"]["id_invoice"], ACTOR)


class TestSinCatalogoNoSeRechazaNada(BaseClaves):
    """Lo primero, porque es lo que puede dejar a un cliente sin facturar."""

    def test_the_catalogue_reports_itself_as_not_loaded(self):
        self.assertFalse(catalogo_cargado())

    def test_no_key_is_reported_as_unknown(self):
        self.assertEqual(set(), claves_fuera_del_catalogo([INVENTADA, CEMENTO]))

    def test_an_invented_key_still_passes_the_preflight(self):
        """Es el comportamiento de antes, y tiene que sobrevivir."""
        v = self.preflight(clave_producto=INVENTADA)
        self.assertNotIn("invoice.concepts.0.sat_product_key_not_in_catalog",
                         v["errors"])
        self.assertTrue(v["can_stamp"], f"errores: {v['errors']}")


class TestConCatalogoSeRechazaLoQueNoExiste(BaseClaves):

    def setUp(self):
        super().setUp()
        self.cargar_catalogo()

    def test_the_catalogue_reports_itself_as_loaded(self):
        self.assertTrue(catalogo_cargado())

    def test_it_names_only_the_keys_that_are_missing(self):
        self.assertEqual({INVENTADA},
                         claves_fuera_del_catalogo([CEMENTO, INVENTADA, CONSULTORIA]))

    def test_blanks_and_nones_are_ignored(self):
        """La clave vacia ya la reporta el guardia de campo obligatorio."""
        self.assertEqual(set(), claves_fuera_del_catalogo(["", None, "   "]))

    def test_an_invented_key_cannot_be_stamped(self):
        v = self.preflight(clave_producto=INVENTADA)
        self.assertFalse(v["can_stamp"])
        self.assertIn("invoice.concepts.0.sat_product_key_not_in_catalog",
                      v["errors"])

    def test_a_key_from_the_catalogue_is_accepted(self):
        v = self.preflight(clave_producto=CEMENTO)
        self.assertTrue(v["can_stamp"], f"errores: {v['errors']}")

    def test_the_catalogue_wins_over_the_curated_list(self):
        """`30111601` no esta entre las frecuentes y aun asi es valida."""
        from app.services.invoice_catalogs import CLAVE_PROD_SERV_FRECUENTES

        self.assertNotIn(CEMENTO, CLAVE_PROD_SERV_FRECUENTES)
        self.assertTrue(self.preflight(clave_producto=CEMENTO)["can_stamp"])

    def test_the_error_points_at_the_concept(self):
        """Con veinte partidas, "una clave esta mal" no sirve de nada."""
        from app.services.manual_invoice_service import create_manual_invoice
        from app.services.stamping import preflight_invoice

        r = create_manual_invoice({
            "id_proyect": PROYECTO, "id_customer_supplier": CLIENTE,
            "id_issuer_customer_supplier": EMISOR, "id_status": ESTATUS,
            "forma_pago": "03", "metodo_pago": "PUE", "uso_cfdi": "G03",
            "tipo_de_comprobante": "I",
            "concepts": [
                {"description": "Uno", "quantity": "1", "unit_price": "100",
                 "sat_product_key": CEMENTO, "sat_unit_key": "E48"},
                {"description": "Dos", "quantity": "1", "unit_price": "100",
                 "sat_product_key": INVENTADA, "sat_unit_key": "E48"},
            ],
        }, ACTOR)
        errores = preflight_invoice(r["invoice"]["id_invoice"], ACTOR)["errors"]
        self.assertIn("invoice.concepts.1.sat_product_key_not_in_catalog", errores)
        self.assertNotIn("invoice.concepts.0.sat_product_key_not_in_catalog", errores)

    def test_a_malformed_key_is_still_reported_as_malformed(self):
        """Cuatro digitos no es "no esta en el catalogo": es formato."""
        v = self.preflight(clave_producto="3011")
        self.assertIn("invoice.concepts.0.sat_product_key_invalid", v["errors"])
        self.assertNotIn("invoice.concepts.0.sat_product_key_not_in_catalog",
                         v["errors"])


class TestLaClaveDeUnidadSoloAvisa(BaseClaves):
    """No hay catalogo oficial de c_ClaveUnidad, asi que no se puede rechazar."""

    def test_a_frequent_unit_key_says_nothing(self):
        v = self.preflight(clave_unidad="E48")
        self.assertNotIn("invoice.concepts.0.sat_unit_key_not_in_frequent_list",
                         v["warnings"])

    def test_an_unusual_unit_key_warns_but_does_not_block(self):
        """`GLI` es una clave real del SAT que no esta en la lista curada."""
        v = self.preflight(clave_unidad="GLI")
        self.assertIn("invoice.concepts.0.sat_unit_key_not_in_frequent_list",
                      v["warnings"])
        self.assertTrue(v["can_stamp"], f"errores: {v['errors']}")

    def test_a_malformed_unit_key_is_still_an_error(self):
        v = self.preflight(clave_unidad="DEMASIADO")
        self.assertIn("invoice.concepts.0.sat_unit_key_invalid", v["errors"])
        self.assertFalse(v["can_stamp"])


if __name__ == "__main__":
    unittest.main()
