"""Que ninguna entidad protegida quede sin un perfil que pueda alcanzarla.

El hallazgo que motiva estas pruebas: 48 de las 63 entidades que el backend
protege no tenian ninguna fila en `entity_permission`, y ningun usuario real de
la base es superusuario -`is_superuser` solo lo da la cuenta de arranque-. En
la practica ningun usuario real podia facturar, ver un cliente ni registrar un
movimiento, y el front, que gatea cada pantalla contra la misma tabla, las
dejaba en blanco.

Nada fallaba al respecto. El sistema se habia usado siempre con la cuenta de
arranque, que salta todas las comprobaciones, asi que el hueco era invisible
justo para quien lo habria notado.

Lo que se comprueba aqui es el generador, no la base: si alguien protege una
entidad nueva y no la clasifica, estas pruebas fallan antes de que el sintoma
llegue a ser una pantalla vacia sin explicacion.
"""

from __future__ import annotations

import importlib.util
import pathlib
import unittest


RAIZ = pathlib.Path(__file__).resolve().parents[3]
GENERADOR = RAIZ / "backend" / "scripts" / "seed_entity_permissions.py"


def _cargar_generador():
    especificacion = importlib.util.spec_from_file_location("seed_entity_permissions", GENERADOR)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


class TestCoberturaDePermisos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = _cargar_generador()
        cls.protegidas = cls.seed.entidades_protegidas()
        cls.clasificadas = cls.seed.clasificar()

    def test_every_guarded_entity_belongs_to_a_domain(self):
        """Sin dominio, ningun perfil la recibe y la pantalla queda muerta."""
        huerfanas = sorted(self.protegidas - set(self.clasificadas))

        self.assertEqual(
            [], huerfanas,
            "Estas entidades estan protegidas pero no pertenecen a ningun dominio, "
            "asi que ningun perfil podria alcanzarlas: " + ", ".join(huerfanas),
        )

    def test_no_entity_falls_into_two_domains(self):
        """clasificar() revienta si hay duplicados; aqui se deja constancia."""
        self.assertEqual(len(self.clasificadas), len(set(self.clasificadas)))

    def test_every_guarded_entity_reaches_at_least_one_profile(self):
        alcanzadas = {
            entidad
            for _, concesiones in self.seed.PERFILES.values()
            for dominio, bits in concesiones.items()
            if bits
            for entidad in self.seed.DOMINIOS[dominio]
        }
        inalcanzables = sorted(self.protegidas - alcanzadas)

        self.assertEqual(
            [], inalcanzables,
            "Ningun perfil puede alcanzar: " + ", ".join(inalcanzables),
        )

    def test_the_invoicing_module_is_reachable(self):
        """El hallazgo concreto: nadie podia facturar."""
        facturacion = set(self.seed.DOMINIOS["facturacion"])
        self.assertIn("invoice", facturacion)

        perfiles = [
            nombre for nombre, concesiones in self.seed.PERFILES.values()
            if concesiones.get("facturacion")
        ]
        self.assertTrue(perfiles, "Ningun perfil puede facturar.")

    def test_the_bootstrap_only_entities_are_not_seeded(self):
        """Sembrarlas daria una fila inutil: el codigo las bloquea igual."""
        from app.utils.auth import BOOTSTRAP_ONLY_ENTITIES

        self.assertTrue(BOOTSTRAP_ONLY_ENTITIES <= self.seed.SOLO_ARRANQUE)
        self.assertEqual(set(), self.protegidas & self.seed.SOLO_ARRANQUE)

    def test_no_bit_outside_the_four_the_code_understands(self):
        from app.utils.auth import PERMISSION_BITS

        valido = 0
        for bit in PERMISSION_BITS.values():
            valido |= bit

        for nombre, concesiones in self.seed.PERFILES.values():
            for dominio, bits in concesiones.items():
                with self.subTest(perfil=nombre, dominio=dominio):
                    self.assertEqual(bits, bits & valido)
                    self.assertGreater(bits, 0)

    def test_only_administration_may_delete(self):
        """Un borrado en contabilidad o almacen deja huecos irreconstruibles."""
        borrar = self.seed.BORRAR
        for nombre, concesiones in self.seed.PERFILES.values():
            for dominio, bits in concesiones.items():
                if bits & borrar and nombre != "Administrator":
                    with self.subTest(perfil=nombre, dominio=dominio):
                        self.assertIn(
                            dominio, {"inventario", "logistica"},
                            f"{nombre} puede borrar en {dominio}; solo se acepta "
                            "para los responsables de almacen.",
                        )

    def test_operating_profiles_do_not_administer_security(self):
        for nombre, concesiones in self.seed.PERFILES.values():
            if nombre == "Administrator":
                continue
            with self.subTest(perfil=nombre):
                self.assertFalse(
                    concesiones.get("seguridad"),
                    f"{nombre} administraria usuarios y perfiles.",
                )

    def test_the_generated_sql_does_not_overwrite_earlier_decisions(self):
        """Las filas afinadas a mano no deben pisarse al rellenar huecos."""
        sql = self.seed.generar()

        self.assertIn("ON CONFLICT (id_permission, entity_name) DO NOTHING", sql)
        self.assertNotIn("DO UPDATE", sql)

    def test_the_generated_sql_puts_the_comma_before_the_comment(self):
        """Con la coma despues del `--`, el renglon siguiente deja de contar."""
        for linea in self.seed.generar().splitlines():
            if linea.lstrip().startswith("(") and "--" in linea:
                with self.subTest(linea=linea.strip()[:60]):
                    self.assertNotIn(",", linea.split("--", 1)[1])


if __name__ == "__main__":
    unittest.main()
