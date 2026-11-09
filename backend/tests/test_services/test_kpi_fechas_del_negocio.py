"""El "hoy" de los KPIs y de sus jobs es el del negocio (America/Mexico_City), no el del contenedor (UTC).

A las 20:00 locales ya son las 02:00 UTC del dia siguiente: con `date.today()`/`datetime.now()` "hoy" saltaba un dia
antes de tiempo. Se congela el reloj con `tests/reloj.py` y no hace falta base de datos: las consultas se compilan
con los valores a la vista y los jobs corren con una sesion de mentira.
"""

from __future__ import annotations

import unittest
from datetime import date, datetime
from unittest import mock

from app.jobs import tasks_kpis, tasks_warehouse
from app.kpis import registry
from tests.reloj import ahora_local

A_LAS_20 = datetime(2026, 10, 28, 20, 0)


class _Resultado:
    def all(self):
        return []

    def scalars(self):
        return self

    def __iter__(self):
        return iter([])


class _SesionQueSoloMira:
    """Guarda las sentencias que recibe; no ejecuta nada."""

    def __init__(self):
        self.sentencias = []

    def execute(self, sentencia, *args, **kwargs):
        self.sentencias.append(sentencia)
        return _Resultado()

    def scalars(self, sentencia, *args, **kwargs):
        self.sentencias.append(sentencia)
        return _Resultado()


def _sql(sesion):
    return " ".join(str(s.compile(compile_kwargs={"literal_binds": True})) for s in sesion.sentencias)


class FechasDelNegocioTest(unittest.TestCase):
    def test_documentos_vencidos_compara_contra_el_dia_local(self):
        sesion = _SesionQueSoloMira()
        with ahora_local(A_LAS_20):
            registry.documentos_vencidos_por_responsable_query(sesion, date(2026, 10, 1), date(2026, 10, 31), {}, None)
        self.assertIn("expiration_date < '2026-10-28'", _sql(sesion))

    def test_vales_vencidos_compara_contra_la_hora_de_pared(self):
        sesion = _SesionQueSoloMira()
        with ahora_local(A_LAS_20):
            registry.vales_vencidos_por_responsable_query(sesion, date(2026, 10, 1), date(2026, 10, 31), {}, None)
        self.assertIn("2026-10-28 20:00:00", _sql(sesion))

    def test_prestamos_vencidos_compara_contra_la_hora_de_pared(self):
        sesion = _SesionQueSoloMira()
        with ahora_local(A_LAS_20):
            registry.prestamos_vencidos_por_responsable_query(sesion, date(2026, 10, 1), date(2026, 10, 31), {}, None)
        self.assertIn("2026-10-28 20:00:00", _sql(sesion))

    def test_la_corrida_nocturna_termina_en_el_dia_local(self):
        with ahora_local(A_LAS_20), \
                mock.patch.object(tasks_kpis, "transaction_context"), \
                mock.patch.object(tasks_kpis, "_recalcular_kpi_snapshots_en_sesion", return_value=0) as recalcular:
            resultado = tasks_kpis.recalculate_kpi_snapshots()
        self.assertEqual(date(2026, 10, 28), recalcular.call_args.args[2])
        self.assertEqual("2026-10-28", resultado["fecha_fin"])

    def test_el_aviso_de_vencidos_filtra_con_la_hora_de_pared(self):
        sesion = _SesionQueSoloMira()
        contexto = mock.MagicMock()
        contexto.__enter__.return_value = sesion
        with ahora_local(A_LAS_20), mock.patch.object(tasks_warehouse, "transaction_context", return_value=contexto):
            tasks_warehouse.notify_overdue_vouchers()
        self.assertIn("2026-10-28 20:00:00", _sql(sesion))


if __name__ == "__main__":
    unittest.main()
