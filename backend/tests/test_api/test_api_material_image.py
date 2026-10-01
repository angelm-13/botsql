from __future__ import annotations

import os
import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from app.models import Product
from app.models.session import transaction_context
from app.services.material_service import MaterialService
from app.services.product_service import ProductService
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload

PNG_BYTES = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
             b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff"
             b"\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\x9f\x00\x00\x00\x00IEND\xaeB`\x82")


class TestMaterialImageApi(BackendTestCase):
    def setUp(self):
        super().setUp()
        self.actor = {"id_user": 1, "is_superuser": True}
        self._upload_dir = tempfile.mkdtemp()
        self._env = patch.dict(os.environ, {"UPLOAD_ROOT": self._upload_dir})
        self._env.start()
        self.app.config["UPLOAD_ROOT"] = self._upload_dir

    def tearDown(self):
        self._env.stop()
        shutil.rmtree(self._upload_dir, ignore_errors=True)
        super().tearDown()

    def _request(self, method, path, **kwargs):
        with patch("app.utils.auth.jwt.decode", return_value=self.actor):
            return self.client.open(
                path, method=method,
                headers={"Authorization": "Bearer material-image-test"}, **kwargs)

    def _material(self):
        return MaterialService.create(build_payload(
            MaterialService, {"material_description": "material con foto", "created_by": 1}
        ))["id_material"]

    def test_uploading_a_material_photo_stores_it_and_serves_it(self):
        id_material = self._material()

        response = self._request(
            "POST", f"/material/{id_material}/image",
            data={"file": (BytesIO(PNG_BYTES), "desarmador.png")},
            content_type="multipart/form-data")

        self.assertEqual(200, response.status_code)
        self.assertEqual(f"uploads/products/m_{id_material}.png", self.json(response)["path_imagen"])
        self.assertTrue(os.path.isfile(os.path.join(self._upload_dir, "products", f"m_{id_material}.png")))
        servida = self.client.get(f"/uploads/products/m_{id_material}.png")
        self.assertEqual(200, servida.status_code)

    def test_a_non_image_is_rejected(self):
        id_material = self._material()
        response = self._request(
            "POST", f"/material/{id_material}/image",
            data={"file": (BytesIO(b"hola"), "notas.txt")},
            content_type="multipart/form-data")
        self.assertEqual(400, response.status_code)

    def test_a_product_list_shows_the_material_photo_when_it_has_none(self):
        id_material = self._material()
        self._request(
            "POST", f"/material/{id_material}/image",
            data={"file": (BytesIO(PNG_BYTES), "desarmador.png")},
            content_type="multipart/form-data")
        creado = ProductService.create(build_payload(
            ProductService, {"created_by": 1, "descripcion": "sin foto propia", "cantidad": 0,
                             "id_material": id_material}))
        with transaction_context() as db:
            db.get(Product, creado["id_product"]).path_imagen = None

        lista = self._request("GET", f"/product/?id_material={id_material}")

        self.assertEqual(200, lista.status_code)
        fotos = {i["id_product"]: i["path_imagen"] for i in self.json(lista)["items"]}
        self.assertEqual(f"uploads/products/m_{id_material}.png", fotos[creado["id_product"]])
        # Es solo de lectura: la ficha del producto sigue sin foto propia.
        with transaction_context() as db:
            self.assertIsNone(db.get(Product, creado["id_product"]).path_imagen)

    def test_editing_a_product_with_the_whole_record_saves(self):
        """Lo que manda el formulario de edicion: el registro completo, `lot_control` incluido."""
        creado = ProductService.create(build_payload(
            ProductService, {"created_by": 1, "descripcion": "herramienta", "cantidad": 0}))
        completo = dict(self._request("GET", f"/product/{creado['id_product']}").get_json())
        completo["note"] = "editada"

        response = self._request("PUT", f"/product/{creado['id_product']}", json=completo)

        self.assertEqual(200, response.status_code, response.get_data(as_text=True))
        self.assertEqual("editada", self.json(response)["note"])
