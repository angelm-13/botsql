"""Pruebas de la busqueda del catalogo c_ClaveProdServ.

Todo corre en local contra la base de pruebas: no se timbra nada ni se llama
a ningun PAC. Las filas del fixture son entradas reales del catalogo del SAT,
recortadas a las que hacen falta para fijar el comportamiento del ranking.

La tabla `RANKING_CASES` es el contrato de calidad de la busqueda: si un
cambio en los pesos o en los sinonimos degrada un caso, estas pruebas lo
detienen. Los casos que el catalogo no puede resolver bien estan documentados
en `TestKnownLimitations`, para que la limitacion sea explicita y no parezca
un descuido.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.models.sat_product_key import SatProductKey, normalize_search_text
from app.models.session import transaction_context
from app.services.sat_catalog_service import (
    _is_service,
    _starts_word,
    _tokenize,
    _token_score,
    catalog_status,
    import_product_keys,
    search_product_keys,
)
from tests.conftest import BackendTestCase


# (clave, descripcion, palabras clave) tomadas del catalogo oficial.
CATALOG_ROWS = [
    ("01010101", "No existe en el catálogo", "Público en general"),
    ("10122103", "Comida para monos", ""),
    ("14111828", "Papelería comercial membreteada", ""),
    ("30111601", "Cemento", ""),
    # Estas dos existen para fijar una regresion real: sus palabras clave
    # contienen la frase "servicio de vigilancia" completa, y con un bono de
    # frase demasiado alto le ganaban a "Servicios de vigilancia", que es la
    # clave correcta y la unica cuya descripcion cubre los dos terminos.
    ("70101600", "Vigilancia pesquera", "Servicio de vigilancia pesquera"),
    (
        "77121701",
        "Servicio de monitoreo o control de la contaminación de las aguas de superficie",
        "Servicio de vigilancia o control de la contaminación de las aguas",
    ),
    ("43202222", "Cables de computador", "Cables de computadora"),
    ("43211500", "Computadores", "Computadoras"),
    ("43211503", "Computadores notebook", "Computadoras notebook"),
    ("43211508", "Computadores personales", "Computadoras personales o laptop, Equipo de cómputo"),
    ("43212105", "Impresoras láser", ""),
    ("43232610", "Software médico", ""),
    ("43233005", "Firmware de computador", "Firmware de computadora"),
    ("71151007", "Servicios de programas de capacitación de simulación basados en computador", ""),
    ("72101508", "Servicio de limpieza de pisos", ""),
    ("78101500", "Transporte de carga aérea", ""),
    ("78102200", "Servicios postales de paqueteo y courrier", ""),
    ("78121603", "Tarifa de los fletes", "Servicio de fletes de carga"),
    ("78141501", "Servicios de expedidores de fletes", "Servicios de agentes de carga"),
    ("80121600", "Servicios de derecho comercial", "Asesoría jurídica"),
    ("80131502", "Arrendamiento de instalaciones comerciales o industriales", "Renta de local comercial"),
    ("80151605", "Servicios de consultoría aduanera", "Servicios de asesoría aduanera"),
    ("81112300", "Mantenimiento y soporte de hardware de computador", "Mantenimiento y soporte de programas"),
    ("81112307", "Mantenimiento de pc o puestos de trabajo o cuadernos", "Mantenimiento de PC o portátiles"),
    ("82101500", "Publicidad impresa", "Servicios de publicidad impresa"),
    ("84111500", "Servicios contables", "Honorarios contables"),
    ("84111600", "Servicios de auditoría", "Honorarios contables"),
    ("86111600", "Educación de adultos", ""),
    ("90101500", "Establecimientos para comer y beber", "Consumo de alimentos y bebidas"),
    ("92101501", "Servicios de vigilancia", ""),
    ("93161500", "Impuesto de renta", ""),
    ("94101606", "Colegios de abogados", ""),
]

# consulta -> clave que debe salir en el primer lugar.
RANKING_CASES = [
    # La clave generica gana a un accesorio que menciona la misma palabra.
    ("equipo de computo", "43211508"),
    ("computadora", "43211500"),
    # El singular de la consulta alcanza al plural del catalogo.
    ("computador", "43211500"),
    ("laptop", "43211508"),
    ("notebook", "43211503"),
    # Servicio de mantenimiento, no el bien.
    ("reparacion de pc", "81112307"),
    ("mantenimiento de computadoras", "81112300"),
    # Coincidencia por palabras clave, no por descripcion.
    ("honorarios contables", "84111500"),
    ("renta de local", "80131502"),
    # La intencion de servicio manda sobre el bien homonimo.
    ("servicio de limpieza", "72101508"),
    ("servicio de vigilancia", "92101501"),
    ("flete", "78121603"),
    ("transporte de carga", "78101500"),
    # Bienes.
    ("cemento", "30111601"),
    ("impresora", "43212105"),
    ("papeleria", "14111828"),
    ("software", "43232610"),
    ("publicidad", "82101500"),
    ("consultoria", "80151605"),
]


def seed_catalog():
    with transaction_context() as db:
        db.add_all([
            SatProductKey(
                clave=clave,
                description=description,
                keywords=keywords,
                description_norm=normalize_search_text(description),
                keywords_norm=normalize_search_text(keywords),
            )
            for clave, description, keywords in CATALOG_ROWS
        ])


class TestSearchRanking(BackendTestCase):
    def setUp(self):
        super().setUp()
        seed_catalog()

    def test_expected_key_ranks_first(self):
        for query, expected in RANKING_CASES:
            with self.subTest(query=query):
                results = search_product_keys(query, limit=5)
                self.assertTrue(results, f"'{query}' no devolvio resultados")
                claves = [row["clave"] for row in results]
                self.assertEqual(
                    expected, claves[0],
                    f"'{query}' esperaba {expected} primero, obtuvo {claves}",
                )

    def test_digits_search_by_key_prefix(self):
        claves = [row["clave"] for row in search_product_keys("432115", limit=10)]

        self.assertEqual(["43211500", "43211503", "43211508"], claves)

    def test_digit_search_does_not_fall_back_to_text(self):
        """Una clave inexistente no debe devolver coincidencias de texto."""
        self.assertEqual([], search_product_keys("99999999"))

    def test_query_shorter_than_two_characters_is_ignored(self):
        for query in ("", " ", "a", None):
            with self.subTest(query=query):
                self.assertEqual([], search_product_keys(query))

    def test_accents_and_case_do_not_matter(self):
        plain = search_product_keys("publicidad impresa", limit=3)
        fancy = search_product_keys("PUBLICIDAD IMPRESÁ", limit=3)

        self.assertEqual([row["clave"] for row in plain], [row["clave"] for row in fancy])

    def test_description_coverage_beats_a_phrase_hit_in_keywords(self):
        """Cubrir todos los terminos en la descripcion es la mejor senal.

        'Vigilancia pesquera' y el servicio de aguas traen la frase completa en
        sus palabras clave, pero solo 'Servicios de vigilancia' cubre los dos
        terminos en su descripcion. Un bono de frase demasiado alto invertia
        este orden.
        """
        claves = [row["clave"] for row in search_product_keys("servicio de vigilancia", limit=3)]

        self.assertEqual("92101501", claves[0])

    def test_stopwords_do_not_drag_unrelated_rows(self):
        """Sin descartar 'de'/'la', cualquier fila que las contenga entraria."""
        claves = [row["clave"] for row in search_product_keys("servicios de la vigilancia", limit=3)]

        self.assertEqual("92101501", claves[0])

    def test_limit_is_honored_and_bounded(self):
        self.assertEqual(2, len(search_product_keys("computador", limit=2)))
        # Un limite absurdo se acota al maximo, no revienta ni pagina infinito.
        self.assertLessEqual(len(search_product_keys("servicios", limit=10_000)), 50)

    def test_invalid_limit_falls_back_to_default(self):
        self.assertTrue(search_product_keys("cemento", limit="muchos"))

    def test_unknown_words_return_nothing_instead_of_guessing(self):
        self.assertEqual([], search_product_keys("zxqwv floopy"))

    def test_results_carry_the_fields_the_capture_form_needs(self):
        row = search_product_keys("cemento", limit=1)[0]

        self.assertEqual("30111601", row["clave"])
        self.assertEqual("Cemento", row["description"])
        self.assertIn("keywords", row)


class TestKnownLimitations(BackendTestCase):
    """Casos que el catalogo no resuelve bien, documentados a proposito."""

    def setUp(self):
        super().setUp()
        seed_catalog()

    def test_ambiguous_noun_returns_the_literal_match(self):
        """'comida' sin mas contexto cae en el bien, no en el restaurante.

        El catalogo tiene 'Comida para monos' y 'Establecimientos para comer y
        beber'; la palabra literal solo esta en el primero. Se deja asi en vez
        de codificar una excepcion por sustantivo, que es como una busqueda se
        vuelve imposible de mantener. La solucion real es el autocompletado,
        donde el usuario ve las opciones y elige.
        """
        claves = [row["clave"] for row in search_product_keys("comida", limit=3)]

        self.assertIn("10122103", claves)

    def test_profession_matches_the_guild_before_the_service(self):
        """'abogado' encuentra 'Colegios de abogados' antes que el servicio.

        La clave de servicios legales no contiene la palabra 'abogado', asi que
        no hay señal textual que la favorezca.
        """
        claves = [row["clave"] for row in search_product_keys("abogado", limit=5)]

        self.assertEqual("94101606", claves[0])


class TestScoringHelpers(unittest.TestCase):
    def test_word_start_match_reaches_plurals(self):
        self.assertTrue(_starts_word("computador", "computadores"))
        self.assertTrue(_starts_word("computador", "cables de computador"))
        # No debe coincidir a media palabra.
        self.assertFalse(_starts_word("putador", "computadores"))

    def test_literal_token_outweighs_its_synonym(self):
        literal = _token_score("computador", "computadores", "")
        synonym = _token_score("pc", "computadores", "")

        self.assertGreater(literal, synonym)

    def test_description_outweighs_keywords(self):
        in_description = _token_score("cemento", "cemento", "")
        in_keywords = _token_score("cemento", "otra cosa", "cemento")

        self.assertGreater(in_description, in_keywords)

    def test_earlier_synonym_outweighs_later_one(self):
        """El orden de la lista de sinonimos es significativo."""
        first = _token_score("laptop", "computador portatil", "")
        later = _token_score("laptop", "computadores", "")

        self.assertGreater(first, later)

    def test_unmatched_token_scores_zero(self):
        self.assertEqual(0, _token_score("cemento", "computadores", ""))

    def test_service_segments_are_recognized(self):
        for clave in ("70171600", "78101500", "94101606"):
            with self.subTest(clave=clave):
                self.assertTrue(_is_service(clave))
        for clave in ("10122103", "43211500", "60101000"):
            with self.subTest(clave=clave):
                self.assertFalse(_is_service(clave))
        self.assertFalse(_is_service(""))

    def test_tokenize_drops_stopwords_and_expands_phrases(self):
        self.assertEqual(["computador"], _tokenize("equipo de computo"))
        self.assertEqual(["limpieza"], _tokenize("servicio de limpieza"))

    def test_tokenize_keeps_stopwords_when_nothing_else_remains(self):
        """Si todo era palabra vacia, se conservan: mejor eso que no buscar."""
        self.assertEqual(["de", "la"], _tokenize("de la"))

    def test_misleading_literal_is_replaced(self):
        """'renta' se sustituye para no caer en 'Impuesto de renta'."""
        self.assertEqual(["arrendamiento"], _tokenize("renta"))


class CatalogImportTestCase(BackendTestCase):
    """El CSV de prueba, para los casos que importan el catalogo."""

    HEADER = "c_ClaveProdServ,Descripción,Palabras similares\n"

    def _write_csv(self, body, preamble=""):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "catalogo.csv"
        path.write_text(preamble + self.HEADER + body, encoding="utf-8")
        return path


class TestCatalogImport(CatalogImportTestCase):

    def test_imports_rows_and_reports_counts(self):
        result = import_product_keys(self._write_csv(
            "43211500,Computadores,Computadoras\n30111601,Cemento,\n"
        ))

        self.assertEqual(
            {"created": 2, "updated": 0, "unchanged": 0, "skipped": 0}, result)
        self.assertEqual({"loaded": True, "total": 2}, catalog_status())

    def test_skips_the_sat_preamble_before_the_headers(self):
        """El archivo oficial trae titulo, version y fecha antes de la tabla."""
        result = import_product_keys(self._write_csv(
            "30111601,Cemento,\n",
            preamble="Catálogo c_ClaveProdServ\nVersión 1.0\nFecha 01/01/2026\n",
        ))

        self.assertEqual(1, result["created"])

    def test_reimport_updates_instead_of_duplicating(self):
        path = self._write_csv("30111601,Cemento,\n")
        import_product_keys(path)
        path.write_text(self.HEADER + "30111601,Cemento gris,cal\n", encoding="utf-8")

        result = import_product_keys(path)

        self.assertEqual(
            {"created": 0, "updated": 1, "unchanged": 0, "skipped": 0}, result)
        self.assertEqual(1, catalog_status()["total"])
        self.assertEqual("Cemento gris", search_product_keys("cemento", limit=1)[0]["description"])

    def test_rows_without_an_eight_digit_key_are_skipped(self):
        result = import_product_keys(self._write_csv(
            "30111601,Cemento,\n"
            "301116,Clave corta,\n"
            "3011160X,Clave con letra,\n"
            ",Sin clave,\n"
        ))

        self.assertEqual(1, result["created"])
        self.assertEqual(3, result["skipped"])

    def test_missing_file_is_reported(self):
        with self.assertRaises(FileNotFoundError):
            import_product_keys("no/existe/catalogo.csv")

    def test_csv_without_recognizable_headers_is_reported(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "malo.csv"
        path.write_text("uno,dos,tres\n1,2,3\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            import_product_keys(path)

    def test_empty_catalog_reports_not_loaded(self):
        self.assertEqual({"loaded": False, "total": 0}, catalog_status())


if __name__ == "__main__":
    unittest.main()


class TestLaReimportacionNoReescribeLoIgual(CatalogImportTestCase):
    """Reimportar el mismo archivo no puede tocar la tabla.

    Medido antes: reimportar `c_ClaveProdServ.csv` sin cambios mandaba 52,514
    UPDATE a la base -18 segundos y la tabla entera reescrita para dejarla
    igual-. El catalogo se carga en cada despliegue, asi que ese coste se paga
    en cada arranque y se multiplica por cada replica.

    Lo que se fija es la cuenta que lo delata: las filas identicas se informan
    como `unchanged` y no como `updated`.
    """

    def test_reimporting_the_same_file_changes_nothing(self):
        path = self._write_csv("30111601,Cemento,cal\n43211500,Computadores,\n")
        import_product_keys(path)

        result = import_product_keys(path)

        self.assertEqual(
            {"created": 0, "updated": 0, "unchanged": 2, "skipped": 0}, result)
        self.assertEqual(2, catalog_status()["total"])

    def test_only_the_row_that_changed_is_updated(self):
        path = self._write_csv("30111601,Cemento,cal\n43211500,Computadores,\n")
        import_product_keys(path)
        path.write_text(
            self.HEADER + "30111601,Cemento gris,cal\n43211500,Computadores,\n",
            encoding="utf-8")

        result = import_product_keys(path)

        self.assertEqual(
            {"created": 0, "updated": 1, "unchanged": 1, "skipped": 0}, result)
        self.assertEqual("Cemento gris",
                         search_product_keys("cemento", limit=1)[0]["description"])

    def test_a_row_that_only_changes_its_keywords_is_updated(self):
        """Las palabras similares alimentan la busqueda: si cambian, se escriben."""
        path = self._write_csv("30111601,Cemento,\n")
        import_product_keys(path)
        path.write_text(self.HEADER + "30111601,Cemento,mortero cal\n",
                        encoding="utf-8")

        self.assertEqual(1, import_product_keys(path)["updated"])
        self.assertTrue(search_product_keys("mortero", limit=1))
