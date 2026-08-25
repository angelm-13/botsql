from sqlalchemy import func, select

from app.models import Invoice, User
from app.models.session import transaction_context
from scripts.seed_fiscal_demo import MANUAL_REFERENCE, QUOTATION_REFERENCE, seed_fiscal_demo
from tests.conftest import BackendTestCase


class TestFiscalDemoSeed(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(User(
                id_user=1, created_by=1, email="admin@demo.local", id_permission=1,
                full_name="Admin Demo", id_proyect=1, password="test", supervisor=1,
                id_status=1, user_type="admin", username="admin-demo",
            ))

    def test_seed_is_idempotent_and_creates_both_fiscal_flows(self):
        first = seed_fiscal_demo(actor_id=1)
        second = seed_fiscal_demo(actor_id=1)

        self.assertEqual(first, second)
        with transaction_context() as db:
            rows = db.scalars(select(Invoice).where(Invoice.fiscal_reference.in_([QUOTATION_REFERENCE, MANUAL_REFERENCE]))).all()
            self.assertEqual(len(rows), 2)
            self.assertEqual(db.scalar(select(func.count()).select_from(Invoice)), 2)
            self.assertEqual({row.invoice_status for row in rows}, {"Cotizacion", "pendiente"})
            self.assertEqual({row.manual_capture for row in rows}, {False, True})