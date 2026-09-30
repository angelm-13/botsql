"""Los avisos de revision de datos de adser dicen lo que deben y se pueden guardar.

`scripts/notify_adser_revision_datos.py` crea notificaciones de la campana. Lo que se fija aqui:

* el tipo de notificacion es uno que la tabla admite -la restriccion CHECK tiene una lista
  cerrada y `revision_datos` la violaba: el script habria fallado al crear el primer aviso-;
* un tema sin casos no genera aviso;
* los textos agrupan por persona y por vale, y usan singular y plural correctos;
* los prestamos que se contradicen con el estado se dividen en lo que probablemente ya volvio,
  lo que parece vigente y lo que no tiene evidencia;
* la incidencia solo se avisa si el responsable de verdad cambio.

La parte que consulta la base se probo contra una copia de adser-prod (ver
docs/despliegues/2026-09-30_ensayo_general_adser.md); aqui solo la que no la necesita.
"""

from __future__ import annotations

import unittest

from scripts import notify_adser_revision_datos as avisos

# Los valores que admite notification.notification_type (modelo y migracion).
TIPOS_ADMITIDOS = {"project_status_change", "project_modified", "activity_log_created",
                   "task_assigned", "material_confirmed", "custom"}

# Dos piezas de la clasificacion fija y una que no esta en ella.
VOLVIO, VIGENTE, NUEVA = 307, 320, 999999


class TestElTipoSePuedeGuardar(unittest.TestCase):

    def test_el_tipo_es_uno_que_la_tabla_admite(self):
        self.assertIn(avisos.TIPO, TIPOS_ADMITIDOS)


class TestLaClasificacionFija(unittest.TestCase):
    """Sale del respaldo del sistema anterior (2026-09-30); no se calcula al correr el script."""

    def test_son_28_y_1_y_no_se_cruzan(self):
        self.assertEqual(len(avisos.PROBABLEMENTE_YA_VOLVIO), 28)
        self.assertEqual(avisos.PARECE_VIGENTE, frozenset({320}))
        self.assertFalse(avisos.PROBABLEMENTE_YA_VOLVIO & avisos.PARECE_VIGENTE)


class TestPrestamosQueSeContradicen(unittest.TestCase):

    def test_sin_casos_no_hay_aviso(self):
        self.assertIsNone(avisos.aviso_contradicciones([]))

    def test_agrupa_por_persona_y_por_vale_y_ordena_por_cantidad(self):
        filas = [
            ("ANA  LOPEZ", 7, "PERICA 12", 65),
            ("MAXIMINO  CANO", 95, "ESCUADRA", 263),
            ("MAXIMINO  CANO", 95, "TORQUIMETRO", 298),
            ("MAXIMINO  CANO", 113, "DADO 22MM", 316),
        ]
        clave, titulo, mensaje = avisos.aviso_contradicciones(filas)
        self.assertEqual(clave, "contradicciones_entrada_abierto")
        self.assertTrue(titulo.startswith("4 préstamos abiertos"))
        self.assertIn("• Maximino Cano (3): vale 95 — ESCUADRA, TORQUIMETRO; vale 113 — DADO 22MM", mensaje)
        self.assertIn("• Ana Lopez (1): vale 7 — PERICA 12", mensaje)
        # El que mas tiene va primero.
        self.assertLess(mensaje.index("Maximino Cano"), mensaje.index("Ana Lopez"))

    def test_divide_en_lo_que_volvio_lo_vigente_y_lo_que_no_tiene_evidencia(self):
        filas = [
            ("ANA LOPEZ", 7, "PERICA", VOLVIO),
            ("LUIS RUIZ", 100, "PRENSA C", VIGENTE),
            ("OMAR GONZALEZ", 45, "TALADRO", NUEVA),
        ]
        mensaje = avisos.aviso_contradicciones(filas)[2]
        volvio = mensaje.index("PROBABLEMENTE YA VOLVIERON (1)")
        vigente = mensaje.index("PARECEN VIGENTES (1)")
        sin = mensaje.index("SIN EVIDENCIA (1)")
        self.assertLess(volvio, vigente)
        self.assertLess(vigente, sin)
        # Cada persona cae en su seccion.
        self.assertLess(volvio, mensaje.index("Ana Lopez"))
        self.assertLess(mensaje.index("Ana Lopez"), vigente)
        self.assertLess(vigente, mensaje.index("Luis Ruiz"))
        self.assertLess(mensaje.index("Luis Ruiz"), sin)
        self.assertGreater(mensaje.index("Omar Gonzalez"), sin)

    def test_una_seccion_sin_casos_no_aparece(self):
        mensaje = avisos.aviso_contradicciones([("ANA LOPEZ", 7, "PERICA", VOLVIO)])[2]
        self.assertIn("PROBABLEMENTE YA VOLVIERON (1)", mensaje)
        self.assertNotIn("PARECEN VIGENTES", mensaje)
        self.assertNotIn("SIN EVIDENCIA", mensaje)

    def test_dice_que_hacer_con_la_pantalla_real(self):
        mensaje = avisos.aviso_contradicciones([("ANA LOPEZ", 7, "PERICA", VOLVIO)])[2]
        self.assertIn("Vales de almacén", mensaje)
        self.assertIn("Marcar devuelto", mensaje)

    def test_singular(self):
        titulo = avisos.aviso_contradicciones([("ANA LOPEZ", 7, "PERICA", VOLVIO)])[1]
        self.assertTrue(titulo.startswith("1 préstamo abierto de herramientas"))

    def test_recorta_un_nombre_de_herramienta_muy_largo(self):
        largo = "X" * 80
        mensaje = avisos.aviso_contradicciones([("ANA LOPEZ", 7, largo, VOLVIO)])[2]
        self.assertNotIn(largo, mensaje)
        self.assertIn("…", mensaje)


class TestPrestamosSinHerramienta(unittest.TestCase):

    def test_sin_casos_no_hay_aviso(self):
        self.assertIsNone(avisos.aviso_huerfanos([], {}))

    def test_un_renglon_por_vale_con_nota_y_responsable_actual(self):
        huerfanos = ((85, 1, "27/04/2025", None), (117, 1, "27/04/2025", None),
                     (145, 3, "30/06/2025", "VALES ANTERIORES FOLIO0117"))
        clave, titulo, mensaje = avisos.aviso_huerfanos(huerfanos, {1: "OMAR GONZALEZ", 3: "MAXIMINO CANO"})
        self.assertEqual(clave, "prestamos_sin_herramienta")
        self.assertTrue(titulo.startswith("3 préstamos"))
        self.assertIn("• Vale 1 — Omar Gonzalez, 27/04/2025 (2 renglones)", mensaje)
        self.assertIn("• Vale 3 — Maximino Cano, 30/06/2025, nota «VALES ANTERIORES FOLIO0117»", mensaje)

    def test_los_datos_de_respaldo_son_los_medidos(self):
        """Son renglones que no estan en la base: si alguien los cambia, que sea a proposito."""
        self.assertEqual([h[0] for h in avisos.HUERFANOS], [85, 117, 145, 743, 1998])
        self.assertEqual(sorted({h[1] for h in avisos.HUERFANOS}), [1, 3, 36, 96])


class TestIncidenciaConOtroResponsable(unittest.TestCase):

    def test_mismo_nombre_no_avisa_aunque_cambien_mayusculas_y_espacios(self):
        self.assertIsNone(avisos.aviso_incidencia(90, "Fernanda Contreras", "FERNANDA   CONTRERAS"))

    def test_sin_responsable_no_avisa(self):
        self.assertIsNone(avisos.aviso_incidencia(90, "Fernanda Contreras", None))

    def test_otro_nombre_avisa_con_los_dos(self):
        clave, titulo, mensaje = avisos.aviso_incidencia(90, "Fernanda Contreras", "Oscar Javier")
        self.assertEqual(clave, "incidencia_90_responsable")
        self.assertIn("Fernanda Contreras", mensaje)
        self.assertIn("Oscar Javier", mensaje)


class TestValesVacios(unittest.TestCase):

    def test_sin_casos_no_hay_aviso(self):
        self.assertIsNone(avisos.aviso_vales_vacios([]))

    def test_plural_y_singular(self):
        self.assertTrue(avisos.aviso_vales_vacios([44, 120])[1].startswith("2 vales abiertos"))
        self.assertIn("Los vales 44, 120", avisos.aviso_vales_vacios([44, 120])[2])
        self.assertTrue(avisos.aviso_vales_vacios([44])[1].startswith("1 vale abierto"))
        self.assertIn("El vale 44 está abierto", avisos.aviso_vales_vacios([44])[2])


class TestResumen(unittest.TestCase):

    def test_dice_cuantos_temas_y_a_quien_avisar_para_un_permiso(self):
        clave, titulo, mensaje = avisos.aviso_resumen(4)
        self.assertEqual(clave, "revision_datos_resumen")
        self.assertIn("4 temas", mensaje)
        self.assertIn("Alan Pérez", mensaje)
        self.assertIn("Enterado", mensaje)


if __name__ == "__main__":
    unittest.main()
