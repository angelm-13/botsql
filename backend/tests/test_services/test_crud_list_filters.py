from tests.conftest import BackendTestCase


class TestElFiltroDeListado(BackendTestCase):
    def test_filtering_by_an_integer_column_is_an_exact_match_not_an_ilike(self):
        from app.models.session import transaction_context
        from app.models.brand import Brand
        from app.services.brand_service import BrandService

        with transaction_context() as db:
            db.add_all([Brand(id_brand=10, brand_description="Uno", created_by=1),
                        Brand(id_brand=101, brand_description="Dos", created_by=1)])

        encontrado = BrandService.list(filters={"id_brand": "10"})

        self.assertEqual([10], [b["id_brand"] for b in encontrado["items"]])

    def test_a_non_column_attribute_is_ignored_as_filter_and_sort(self):
        from app.services.brand_service import BrandService

        BrandService.list(filters={"metadata": "x"}, sort="metadata")
