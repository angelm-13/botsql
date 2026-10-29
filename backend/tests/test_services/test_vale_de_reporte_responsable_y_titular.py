"""Un reporte de suceso es de quien lo levanta, y dice quien tenia la pieza.

Dañado, extraviado, destruccion y reparacion no se le pueden cargar a otro: el responsable
del reporte es SIEMPRE quien lo levanta, aunque la peticion diga otra cosa. Y en la baja de
algo prestado (destruccion, extravio) el sistema deja dicho quien la tenia, sacado de los
prestamos abiertos del producto y no tecleado: con uno solo se asigna solo; con varios, quien
reporta elige entre ellos y no se acepta a nadie mas.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.models import Incident, IncidentType, NmIncidentProduct
from app.models.session import transaction_context
from app.services.warehouse_voucher_service import crear_vale
from app.utils.errors import AppError
from tests.test_services.test_vale_de_almacen import ACTOR, CEMENTO, NAVE, TIPO_PRESTAMO
from tests.test_services.test_vale_de_baja_registra_lo_que_paso import (
    TIPO_DESTRUCCION, TIPO_EXTRAVIADO, BaseBaja)

TIPO_REPARACION = 93
QUIEN_LA_TENIA, OTRO_QUE_LA_TENIA = 2, 3


class BaseReporte(BaseBaja):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(IncidentType(id_incident_type=TIPO_REPARACION,
                                incident_type_description="Reparacion", created_by=1))
        self._otro_usuario(QUIEN_LA_TENIA)
        self._otro_usuario(OTRO_QUE_LA_TENIA)

    def presta_a(self, id_user, *, borrador=False):
        carga = {"id_incident_type": TIPO_PRESTAMO, "id_user": id_user, "note": "Obra Norte",
                 "lines": [self._linea_cantidad(1)],
                 "due_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")}
        return crear_vale(carga, ACTOR, como_borrador=borrador)

    def reporta(self, tipo, *, lineas=None, como_borrador=False, **extra):
        carga = {"id_incident_type": tipo, "note": "Se perdio en obra",
                 "lines": lineas or [{"id_product": CEMENTO, "quantity": 1}]}
        carga.update(extra)
        return crear_vale(carga, ACTOR, como_borrador=como_borrador)

    def responsable_de(self, resultado):
        with transaction_context() as db:
            return db.get(Incident, resultado["voucher"]["id_incident"]).id_user

    def titular_de(self, resultado):
        with transaction_context() as db:
            return db.get(NmIncidentProduct, self.linea(resultado)).held_by_user


class TestElResponsableEsQuienLoLevanta(BaseReporte):

    def test_el_reporte_no_se_le_carga_a_otro_aunque_la_peticion_lo_diga(self):
        self.surtir(5)
        reporte = self.reporta(TIPO_EXTRAVIADO, lineas=[self._linea_cantidad(1)],
                               id_user=QUIEN_LA_TENIA)
        self.assertEqual(ACTOR["id_user"], self.responsable_de(reporte))

    def test_el_responsable_no_hace_falta_mandarlo(self):
        self.surtir(5)
        reporte = self.reporta(TIPO_DESTRUCCION, lineas=[self._linea_cantidad(1)])
        self.assertEqual(ACTOR["id_user"], self.responsable_de(reporte))

    def test_tampoco_en_reparacion_ni_como_borrador(self):
        self.surtir(5)
        directo = self.reporta(TIPO_REPARACION, lineas=[self._linea_cantidad(1)],
                               id_user=QUIEN_LA_TENIA)
        borrador = self.reporta(TIPO_REPARACION, lineas=[self._linea_cantidad(1)],
                                id_user=OTRO_QUE_LA_TENIA, como_borrador=True)
        self.assertEqual(ACTOR["id_user"], self.responsable_de(directo))
        self.assertEqual(ACTOR["id_user"], self.responsable_de(borrador))

    def test_un_prestamo_si_sigue_pidiendo_el_responsable(self):
        self.surtir(5)
        with self.assertRaises(AppError) as contexto:
            crear_vale({"id_incident_type": TIPO_PRESTAMO, "note": "Obra Norte",
                        "lines": [self._linea_cantidad(1)],
                        "due_date": (datetime.now() + timedelta(days=30)).strftime(
                            "%Y-%m-%d %H:%M:%S")}, ACTOR)
        self.assertEqual("errors.required_field", contexto.exception.message_key)


class TestQuienLaTenia(BaseReporte):

    def test_con_un_solo_prestamo_se_asigna_solo_y_se_cierra_el_suyo(self):
        self.surtir(1)
        prestamo = self.presta_a(QUIEN_LA_TENIA)

        baja = self.reporta(TIPO_EXTRAVIADO)              # sin sitio de origen ni titular

        self.assertEqual(QUIEN_LA_TENIA, self.titular_de(baja))
        self.assertEqual(ACTOR["id_user"], self.responsable_de(baja))
        self.assertIsNotNone(self.cierre_de(self.linea(prestamo)))
        self.assertEqual(0, self._saldo(), "una pieza prestada no mueve el almacen")

    def test_si_estaba_en_el_almacen_no_hay_a_quien_senalar(self):
        self.surtir(5)
        baja = self.reporta(TIPO_DESTRUCCION, lineas=[self._linea_cantidad(1)])

        self.assertIsNone(self.titular_de(baja))
        self.assertEqual(4, self._saldo())

    def test_con_varios_hay_que_elegir_entre_ellos(self):
        self.surtir(2)
        de_uno = self.presta_a(QUIEN_LA_TENIA)
        de_otro = self.presta_a(OTRO_QUE_LA_TENIA)

        with self.assertRaises(AppError) as contexto:
            self.reporta(TIPO_EXTRAVIADO)
        self.assertEqual("errors.voucher_held_by_required", contexto.exception.message_key)

        baja = self.reporta(TIPO_EXTRAVIADO, lineas=[
            {"id_product": CEMENTO, "quantity": 1, "held_by_user": OTRO_QUE_LA_TENIA}])

        self.assertEqual(OTRO_QUE_LA_TENIA, self.titular_de(baja))
        self.assertIsNone(self.cierre_de(self.linea(de_uno)), "el de quien no es, intacto")
        self.assertIsNotNone(self.cierre_de(self.linea(de_otro)))

    def test_no_se_acepta_a_quien_no_la_tenia(self):
        self.surtir(1)
        self.presta_a(QUIEN_LA_TENIA)
        with self.assertRaises(AppError) as contexto:
            self.reporta(TIPO_EXTRAVIADO, lineas=[
                {"id_product": CEMENTO, "quantity": 1, "held_by_user": OTRO_QUE_LA_TENIA}])
        self.assertEqual("errors.voucher_held_by_invalid", contexto.exception.message_key)

    def test_ni_cuando_estaba_en_el_almacen(self):
        self.surtir(5)
        with self.assertRaises(AppError) as contexto:
            self.reporta(TIPO_DESTRUCCION, lineas=[
                {"id_product": CEMENTO, "quantity": 1, "id_location_from": NAVE,
                 "held_by_user": QUIEN_LA_TENIA}])
        self.assertEqual("errors.voucher_held_by_invalid", contexto.exception.message_key)

    def test_un_prevale_todavia_no_cuenta_como_tenerla(self):
        """Lo apartado sigue en el almacen: nadie lo "tiene" hasta que sale."""
        self.surtir(3)
        self.presta_a(QUIEN_LA_TENIA)
        self.presta_a(OTRO_QUE_LA_TENIA, borrador=True)

        baja = self.reporta(TIPO_EXTRAVIADO)              # no pregunta: un solo titular real

        self.assertEqual(QUIEN_LA_TENIA, self.titular_de(baja))

    def test_reportar_menos_de_lo_que_tiene_a_su_cargo_se_rechaza_claro(self):
        self.surtir(5)
        prestamo = self.presta_a(QUIEN_LA_TENIA)          # 1 unidad
        with transaction_context() as db:                 # ahora tiene 5 en un solo renglon
            db.get(NmIncidentProduct, self.linea(prestamo)).quantity = 5
        with self.assertRaises(AppError) as contexto:
            self.reporta(TIPO_EXTRAVIADO, lineas=[{"id_product": CEMENTO, "quantity": 2}])
        self.assertEqual("errors.voucher_report_partial_loan", contexto.exception.message_key)
        self.assertIsNone(self.cierre_de(self.linea(prestamo)))

    def test_el_titular_queda_en_el_renglon_del_borrador_tambien(self):
        self.surtir(1)
        self.presta_a(QUIEN_LA_TENIA)

        borrador = self.reporta(TIPO_EXTRAVIADO, como_borrador=True)

        self.assertEqual(QUIEN_LA_TENIA, self.titular_de(borrador))
        self.assertEqual(ACTOR["id_user"], self.responsable_de(borrador))
