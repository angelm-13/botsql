"""El expediente de un vale (su PDF archivado como `document`) sigue el alcance del vale."""
from __future__ import annotations

from app.models import Incident
from app.models.document import Document, DocumentCategory
from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.services.document_service import DocumentManagementService
from tests.conftest import BackendTestCase

SOLICITANTE = 11
OTRO = 12
ROL_SOLICITANTE = 201
ROL_ALMACEN = 401


class TestDocumentoDeVale(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                EntityPermission(id_permission=ROL_SOLICITANTE, entity_name="warehouse_prevoucher",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
                EntityPermission(id_permission=ROL_ALMACEN, entity_name="warehouse_voucher",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
            ])
            vale = DocumentCategory(code="warehouse_voucher", name="Vale", created_by=1)
            otra = DocumentCategory(code="contract", name="Contrato", created_by=1)
            db.add_all([vale, otra])
            suyo = Incident(id_incident_type=1, id_user=SOLICITANTE, created_by=1)
            ajeno = Incident(id_incident_type=1, id_user=OTRO, created_by=1)
            db.add_all([suyo, ajeno])
            db.flush()
            self.id_suyo, self.id_ajeno = suyo.id_incident, ajeno.id_incident
            for titulo, categoria, ref in (
                ("Vale suyo", vale, str(self.id_suyo)),
                ("Vale ajeno", vale, str(self.id_ajeno)),
            ):
                db.add(Document(id_proyect=1, id_document_category=categoria.id_document_category,
                                title=titulo, status="issued", created_by=1,
                                business_reference_type="incident", business_reference_value=ref))
            db.add(Document(id_proyect=1, id_document_category=otra.id_document_category,
                            title="Contrato", status="issued", created_by=1))

    def _titulos(self, **claims):
        actor = {"id_proyect": 1, "user_type": "employee", **claims}
        return {d["title"] for d in DocumentManagementService.list(actor)["items"]}

    def test_a_requester_only_sees_the_voucher_files_that_are_his(self):
        titulos = self._titulos(id_user=SOLICITANTE, id_permission=ROL_SOLICITANTE)
        self.assertIn("Vale suyo", titulos)
        self.assertNotIn("Vale ajeno", titulos)

    def test_other_documents_are_not_affected(self):
        self.assertIn("Contrato", self._titulos(id_user=SOLICITANTE, id_permission=ROL_SOLICITANTE))

    def test_whoever_operates_the_warehouse_sees_every_voucher_file(self):
        titulos = self._titulos(id_user=31, id_permission=ROL_ALMACEN)
        self.assertLessEqual({"Vale suyo", "Vale ajeno", "Contrato"}, titulos)
