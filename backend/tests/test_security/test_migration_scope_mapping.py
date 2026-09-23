"""La regla de migracion de datos existentes: bit encendido -> Todos (4).

Documenta y fija la unica regla que uso tanto la migracion real
(`20260914110000_equipos_y_alcance_por_accion.sql`) como el registro de
modulos (`app/modules/registry.py`) para convertir el viejo `control_type`
(mascara CREAR=1/LEER=2/ACTUALIZAR=4/BORRAR=8) en las 4 columnas de alcance
nuevas: un bit que ya estaba encendido se convierte en Todos (4); uno apagado,
en Sin acceso (0). Acordada con el usuario para no quitarle a nadie acceso que
ya tenia hoy.

`_alcance_desde_bits` es la MISMA funcion que usa `filas_de_permisos()` para
sembrar el registro -- fijarla aqui evita que alguien la cambie sin darse
cuenta de que tambien describe la migracion de datos ya aplicada.
"""

from __future__ import annotations

import unittest

from app.modules.registry import CREAR, LEER, ACTUALIZAR, BORRAR, TOTAL, CAPTURA, EDITAR, CONSULTA, _alcance_desde_bits


class TestMigrationScopeMapping(unittest.TestCase):
    def test_no_bits_means_no_access_anywhere(self):
        self.assertEqual((0, 0, 0, 0), _alcance_desde_bits(0))

    def test_total_grants_all_four_as_todos(self):
        self.assertEqual((4, 4, 4, 4), _alcance_desde_bits(TOTAL))

    def test_captura_grants_create_read_update_but_not_delete(self):
        self.assertEqual((4, 4, 4, 0), _alcance_desde_bits(CAPTURA))

    def test_editar_grants_read_update_only(self):
        self.assertEqual((0, 4, 4, 0), _alcance_desde_bits(EDITAR))

    def test_consulta_grants_read_only(self):
        self.assertEqual((0, 4, 0, 0), _alcance_desde_bits(CONSULTA))

    def test_each_single_bit_maps_to_its_own_column_only(self):
        self.assertEqual((4, 0, 0, 0), _alcance_desde_bits(CREAR))
        self.assertEqual((0, 4, 0, 0), _alcance_desde_bits(LEER))
        self.assertEqual((0, 0, 4, 0), _alcance_desde_bits(ACTUALIZAR))
        self.assertEqual((0, 0, 0, 4), _alcance_desde_bits(BORRAR))

    def test_the_mapping_never_produces_a_value_outside_0_or_4(self):
        """El esquema admite 0-7, pero esta regla de migracion solo emite 0 o 4."""
        for bits in range(0, 16):
            for scope in _alcance_desde_bits(bits):
                self.assertIn(scope, (0, 4))


if __name__ == "__main__":
    unittest.main()
