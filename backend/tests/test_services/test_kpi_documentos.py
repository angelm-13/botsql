from __future__ import annotations

import unittest
from datetime import date, timedelta

from sqlalchemy import delete

from app.kpis.registry import documentos_vencidos_por_responsable_query
from app.models import Document, DocumentCategory, Proyect, User
from app.models.session import engine, transaction_context

ADMIN_ID = 1
RESPONSABLE_A = 990
RESPONSABLE_B = 991
PROYECTO_ACTOR = 990
PROYECTO_OTRO = 991
CATEGORIA = 990

HOY = date.today()
AYER = HOY - timedelta(days=1)


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class DocumentosVencidosQueryTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            for user_id in (RESPONSABLE_A, RESPONSABLE_B):
                db.add(User(
                    id_user=user_id, created_by=ADMIN_ID, full_name=f"Responsable {user_id}",
                    id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                    user_type="employee", is_employee=True, username=f"kpi-doc-test-{user_id}",
                ))
            db.add(DocumentCategory(
                id_document_category=CATEGORIA, code=f"kpi-test-{CATEGORIA}", name="KPI test", created_by=ADMIN_ID,
            ))
            db.flush()
            for proyect_id in (PROYECTO_ACTOR, PROYECTO_OTRO):
                db.add(Proyect(
                    id_proyect=proyect_id, id_customer_supplier=1, leader=ADMIN_ID,
                    proyect_description=f"Proyecto KPI documentos {proyect_id}", created_by=ADMIN_ID,
                ))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(Document).where(Document.id_proyect.in_([PROYECTO_ACTOR, PROYECTO_OTRO])))
            db.execute(delete(Proyect).where(Proyect.id_proyect.in_([PROYECTO_ACTOR, PROYECTO_OTRO])))
            db.execute(delete(DocumentCategory).where(DocumentCategory.id_document_category == CATEGORIA))
            db.execute(delete(User).where(User.id_user.in_([RESPONSABLE_A, RESPONSABLE_B])))

    def _documento(self, id_document, id_proyect, created_by, status, expiration_date, title=None):
        return Document(
            id_document=id_document, id_proyect=id_proyect, id_document_category=CATEGORIA,
            title=title or f"Documento {id_document}", status=status,
            expiration_date=expiration_date, created_by=created_by,
        )

    def test_solo_signed_vencido_cuenta(self):
        with transaction_context() as db:
            db.add_all([
                self._documento(9901, PROYECTO_ACTOR, RESPONSABLE_A, "signed", AYER),
                self._documento(9902, PROYECTO_ACTOR, RESPONSABLE_A, "draft", AYER),
                self._documento(9903, PROYECTO_ACTOR, RESPONSABLE_A, "issued", AYER),
                self._documento(9904, PROYECTO_ACTOR, RESPONSABLE_A, "rejected", AYER),
                self._documento(9905, PROYECTO_ACTOR, RESPONSABLE_A, "cancelled", AYER),
            ])

        with transaction_context() as db:
            filas = documentos_vencidos_por_responsable_query(
                db, AYER - timedelta(days=3), AYER + timedelta(days=3), {}, PROYECTO_ACTOR,
            )

        self.assertEqual([(RESPONSABLE_A, AYER, 1)], [tuple(f) for f in filas])

    def test_signed_pero_no_vencido_no_cuenta(self):
        with transaction_context() as db:
            db.add(self._documento(9906, PROYECTO_ACTOR, RESPONSABLE_A, "signed", HOY + timedelta(days=30)))

        with transaction_context() as db:
            filas = documentos_vencidos_por_responsable_query(
                db, HOY, HOY + timedelta(days=60), {}, PROYECTO_ACTOR,
            )

        self.assertEqual([], [tuple(f) for f in filas])

    def test_alcance_por_proyecto(self):
        with transaction_context() as db:
            db.add_all([
                self._documento(9907, PROYECTO_ACTOR, RESPONSABLE_A, "signed", AYER),
                self._documento(9908, PROYECTO_OTRO, RESPONSABLE_A, "signed", AYER),
            ])

        with transaction_context() as db:
            solo_actor = documentos_vencidos_por_responsable_query(
                db, AYER, AYER, {}, PROYECTO_ACTOR,
            )
            solo_otro = documentos_vencidos_por_responsable_query(
                db, AYER, AYER, {}, PROYECTO_OTRO,
            )

        self.assertEqual([(RESPONSABLE_A, AYER, 1)], [tuple(f) for f in solo_actor])
        self.assertEqual([(RESPONSABLE_A, AYER, 1)], [tuple(f) for f in solo_otro])

    def test_filtro_de_empleados(self):
        with transaction_context() as db:
            db.add_all([
                self._documento(9909, PROYECTO_ACTOR, RESPONSABLE_A, "signed", AYER),
                self._documento(9910, PROYECTO_ACTOR, RESPONSABLE_B, "signed", AYER),
            ])

        with transaction_context() as db:
            filas = documentos_vencidos_por_responsable_query(
                db, AYER, AYER, {"empleados": [RESPONSABLE_B]}, PROYECTO_ACTOR,
            )

        self.assertEqual([(RESPONSABLE_B, AYER, 1)], [tuple(f) for f in filas])


if __name__ == "__main__":
    unittest.main()
