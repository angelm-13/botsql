from app.models.session import transaction_context
from app.services.customer_contact_service import CustomerContactService
from app.services.customer_supplier_service import CustomerSupplierService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


def _cliente(nombre, rfc, **extra):
    return CustomerSupplierService.create(
        {"name": nombre, "tax_id": rfc, "type": "client", "email": "a@b.com", "id_user": 1, **extra}, user_id=1)


class TestClientesYContactos(BackendTestCase):
    def test_the_same_rfc_cannot_be_registered_twice_even_with_other_case_or_spaces(self):
        _cliente("Uno", "AAA010101AAA")

        for rfc in ("AAA010101AAA", " aaa010101aaa "):
            with self.subTest(rfc=rfc), self.assertRaises(AppError) as caja:
                _cliente("Otro", rfc)
            self.assertEqual(409, caja.exception.status_code)

    def test_generic_rfcs_may_repeat(self):
        _cliente("Publico 1", "XAXX010101000")
        _cliente("Publico 2", "XAXX010101000")

    def test_the_rfc_is_stored_normalised(self):
        creado = _cliente("Uno", " aaa010101aaa ")

        self.assertEqual("AAA010101AAA", creado["tax_id"])

    def test_a_customer_needs_a_type(self):
        with self.assertRaises(AppError) as caja:
            CustomerSupplierService.create({"name": "Sin tipo"}, user_id=1)

        self.assertEqual(400, caja.exception.status_code)

    def test_a_contact_needs_a_valid_unique_email(self):
        cliente = _cliente("Uno", "AAA010101AAA")
        base = {"id_customer_supplier": cliente["id_customer_supplier"], "full_name": "Ana"}

        with self.assertRaises(AppError) as caja:
            CustomerContactService.create({**base, "email": "zzz"}, user_id=1)
        self.assertEqual(400, caja.exception.status_code)

        CustomerContactService.create({**base, "email": "ana@empresa.com"}, user_id=1)
        with self.assertRaises(AppError) as caja:
            CustomerContactService.create({**base, "email": "ANA@empresa.com"}, user_id=1)
        self.assertEqual(409, caja.exception.status_code)


class TestElTotalDeUnaFacturaConDescuento(BackendTestCase):
    def test_total_is_subtotal_minus_discount_plus_tax(self):
        from app.validations.validator import validate_payload

        validate_payload("invoice", {"subtotal": 3000, "descuento": 100, "tax": 464, "total": 3364},
                         partial=True)

        with self.assertRaises(AppError):
            validate_payload("invoice", {"subtotal": 3000, "descuento": 100, "tax": 464, "total": 3464},
                             partial=True)

    def test_without_discount_it_is_still_subtotal_plus_tax(self):
        from app.validations.validator import validate_payload

        validate_payload("invoice", {"subtotal": 100, "tax": 16, "total": 116}, partial=True)
        with self.assertRaises(AppError):
            validate_payload("invoice", {"subtotal": 100, "tax": 16, "total": 120}, partial=True)


class TestHorariosYaAgendados(BackendTestCase):
    def test_an_instant_with_a_zone_is_converted_not_relabelled(self):
        from datetime import datetime, timedelta, timezone
        from app.services.appointment_service import _a_utc

        mexico = timezone(timedelta(hours=-6))
        con_zona = datetime(2026, 10, 20, 10, 0, tzinfo=mexico)

        self.assertEqual(datetime(2026, 10, 20, 16, 0, tzinfo=timezone.utc), _a_utc(con_zona))
        self.assertEqual(datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc),
                         _a_utc(datetime(2026, 10, 20, 10, 0)))
