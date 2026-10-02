"""`material_prestado_actual`: filtro por responsable, busqueda, orden y agregados en el SERVIDOR.

El bug que motiva estas pruebas: el Dashboard pedia las 50 filas mas antiguas y filtraba/buscaba en el
navegador sobre esas 50, asi que un vale nuevo (los mas recientes van al final) nunca aparecia al filtrar
por su responsable ni al buscar su articulo, y los conteos por responsable mentian. Aqui hay mas de 50
renglones, varios responsables, y lo "nuevo" queda mas alla de la fila 50.

Corre solo contra PostgreSQL. La base real puede traer renglones prestados propios: las pruebas
acotan por `id_user` / busqueda o comparan contra su propia fixture.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from sqlalchemy import delete, event

from app.kpis.registry import (
    KPI_POR_CLAVE, PRESTADO_ORDENES, material_prestado_actual_query, material_prestado_actual_resumen_query,
)
from app.models import (
    Brand, Incident, IncidentType, Invoice, Location, LocationType,
    Material, NmIncidentProduct, Product, ProductFamily, Unit, User,
)
from app.models.session import engine, transaction_context

ADMIN_ID = 1
# IDs propios (970+) para no chocar con los demas archivos de KPI.
OMAR, ANA, TALLER_1, TALLER_2 = 970, 971, 972, 973
USUARIOS = {OMAR: "OMAR GONZALEZ", ANA: "ANA LOPEZ", TALLER_1: "ESTANCIA EN EL TALLER", TALLER_2: "ESTANCIA EN EL TALLER"}
TIPO_NORMAL, TIPO_DESTRUCCION = 970, 971
TIPOS = [TIPO_NORMAL, TIPO_DESTRUCCION]
LOCATION_TYPE = LOCATION = BRAND = FAMILIA = UNIT = MATERIAL = INVOICE = 970
P_COMUN, P_ESCALERA, P_MALETIN, P_TANQUE = 970, 971, 972, 973
PRODUCTOS = [P_COMUN, P_ESCALERA, P_MALETIN, P_TANQUE]
PRIMER_VALE, PRIMER_RENGLON = 97000, 970000

HOY = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
VIEJOS_DE_OMAR = 60   # mas de 50: lo nuevo de Omar cae mas alla de la fila 50
RENGLONES_DE_ANA = 40


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class MaterialPrestadoActualServidorTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        self._vale = PRIMER_VALE
        self._renglon = PRIMER_RENGLON
        with transaction_context() as db:
            for id_user, nombre in USUARIOS.items():
                db.add(User(id_user=id_user, created_by=ADMIN_ID, full_name=nombre, id_permission=1, id_proyect=1,
                            id_status=1, supervisor=ADMIN_ID, user_type="employee", is_employee=True,
                            username=f"kpi-prestado-servidor-{id_user}"))
            db.add_all([
                IncidentType(id_incident_type=TIPO_NORMAL, incident_type_description="Vale normal", created_by=ADMIN_ID),
                IncidentType(id_incident_type=TIPO_DESTRUCCION, incident_type_description="Destruccion", created_by=ADMIN_ID),
                LocationType(id_location_type=LOCATION_TYPE, location_type_description="KPI test", is_warehouse=True, created_by=ADMIN_ID),
                Brand(id_brand=BRAND, brand_description="KPI test", created_by=ADMIN_ID),
                ProductFamily(id_product_family=FAMILIA, product_family_description="KPI test", created_by=ADMIN_ID),
                Unit(id_unit=UNIT, unit_name="Pieza", is_active=True, measurement_system="metric", created_by=ADMIN_ID),
            ])
            db.flush()
            db.add(Location(id_location=LOCATION, id_location_type=LOCATION_TYPE, location_description="KPI test", created_by=ADMIN_ID))
            db.add(Material(id_material=MATERIAL, material_description="KPI test", id_unit=UNIT, id_brand=BRAND,
                            id_product_family=FAMILIA, created_by=ADMIN_ID))
            db.add(Invoice(id_invoice=INVOICE, id_customer_supplier=1, id_issuer_customer_supplier=1, id_proyect=1,
                           id_status=1, tax_certification_supplier=1, apply_tax=False, invoice_status="pendiente",
                           created_by=ADMIN_ID))
            db.flush()
            for id_product, descripcion in (
                (P_COMUN, "Taladro ZZ"), (P_ESCALERA, "ESCALERA DE TIJERA ZZ"),
                (P_MALETIN, "Maletín de herramientas ZZ"), (P_TANQUE, "Tanque de CO2 ZZ"),
            ):
                db.add(Product(id_product=id_product, id_invoice=INVOICE, id_location=LOCATION, id_material=MATERIAL,
                               is_directly_related_to_product_service=False, cantidad=5, created_by=ADMIN_ID,
                               descripcion=descripcion, product_code=f"ZZ-{id_product}"))
        # Omar: 60 renglones viejos (oct-2025 en el caso real) y UN vale nuevo con 3 renglones.
        for i in range(VIEJOS_DE_OMAR):
            self._prestar(OMAR, P_COMUN, 400 - i // 20)          # 3 vales viejos (400, 399, 398 dias)
        self._prestar(OMAR, P_ESCALERA, 30)
        self._prestar(OMAR, P_MALETIN, 30)
        self._prestar(OMAR, P_TANQUE, 30)
        for i in range(RENGLONES_DE_ANA):
            self._prestar(ANA, P_COMUN, 200 - i)
        for _ in range(5):
            self._prestar(TALLER_1, P_COMUN, 100)
            self._prestar(TALLER_2, P_COMUN, 90)

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(NmIncidentProduct).where(NmIncidentProduct.id_nm_incident_product >= PRIMER_RENGLON))
            db.execute(delete(Incident).where(Incident.id_incident_type.in_(TIPOS)))
            db.execute(delete(Product).where(Product.id_product.in_(PRODUCTOS)))
            db.execute(delete(Invoice).where(Invoice.id_invoice == INVOICE))
            db.execute(delete(Material).where(Material.id_material == MATERIAL))
            db.execute(delete(Location).where(Location.id_location == LOCATION))
            db.execute(delete(Unit).where(Unit.id_unit == UNIT))
            db.execute(delete(ProductFamily).where(ProductFamily.id_product_family == FAMILIA))
            db.execute(delete(Brand).where(Brand.id_brand == BRAND))
            db.execute(delete(LocationType).where(LocationType.id_location_type == LOCATION_TYPE))
            db.execute(delete(IncidentType).where(IncidentType.id_incident_type.in_(TIPOS)))
            db.execute(delete(User).where(User.id_user.in_(list(USUARIOS))))

    def _prestar(self, id_user, id_product, dias_atras, *, tipo=TIPO_NORMAL):
        id_vale, id_renglon = self._vale, self._renglon
        self._vale += 1
        self._renglon += 1
        with transaction_context() as db:
            db.add(Incident(id_incident=id_vale, id_incident_type=tipo, id_user=id_user, incident_status="abierta",
                            incident_date=HOY - timedelta(days=dias_atras), created_by=ADMIN_ID))
            db.flush()
            db.add(NmIncidentProduct(id_nm_incident_product=id_renglon, id_incident=id_vale, id_product=id_product,
                                     quantity=1, direction="salida", created_by=ADMIN_ID))

    # --- ayudas -----------------------------------------------------------------------------
    def _pagina(self, **filtros):
        limit = filtros.pop("limit", 50)
        offset = filtros.pop("offset", 0)
        with transaction_context() as db:
            return material_prestado_actual_query(db, limit=limit, offset=offset, **filtros)

    def _todo(self, **filtros):
        """Recorre TODAS las paginas de 50, como el scroll infinito, y las junta."""
        items, offset = [], 0
        while True:
            pagina, total = self._pagina(limit=50, offset=offset, **filtros)
            items.extend(pagina)
            offset += 50
            if offset >= total or not pagina:
                return items, total

    def _resumen(self, total, **filtros):
        with transaction_context() as db:
            return material_prestado_actual_resumen_query(db, total=total, **filtros)

    # --- el bug: lo nuevo no aparece ---------------------------------------------------------
    def test_las_primeras_50_no_incluyen_lo_nuevo_pero_el_total_si_lo_cuenta(self):
        items, total = self._pagina(limit=50, offset=0)
        self.assertEqual(50, len(items))
        self.assertGreaterEqual(total, 63 + RENGLONES_DE_ANA + 10)
        self.assertFalse([i for i in items if "ZZ" in i["articulo"] and "ESCALERA" in i["articulo"]])

    def test_filtrar_por_un_responsable_trae_todos_sus_renglones_los_viejos_y_los_nuevos(self):
        items, total = self._todo(id_user=OMAR)
        self.assertEqual(VIEJOS_DE_OMAR + 3, total)
        self.assertEqual(total, len(items))
        self.assertEqual({OMAR}, {i["id_user"] for i in items})
        articulos = {i["articulo"] for i in items}
        self.assertTrue({"ESCALERA DE TIJERA ZZ", "Maletín de herramientas ZZ", "Tanque de CO2 ZZ"} <= articulos)
        self.assertEqual({400, 399, 398, 30}, {i["dias_prestado"] for i in items})

    def test_buscar_un_articulo_mas_alla_de_la_fila_50_lo_encuentra(self):
        items, total = self._pagina(q="escalera")
        self.assertEqual(1, total)
        self.assertEqual("ESCALERA DE TIJERA ZZ", items[0]["articulo"])
        self.assertEqual(OMAR, items[0]["id_user"])

    def test_la_busqueda_ignora_mayusculas_y_acentos_y_pide_todas_las_palabras(self):
        self.assertEqual(1, self._pagina(q="MALETIN")[1])            # el articulo trae "Maletín"
        self.assertEqual(1, self._pagina(q="maletín herramientas zz")[1])
        self.assertEqual(1, self._pagina(q="tanque co2")[1])
        self.assertEqual(0, self._pagina(q="escalera maletin")[1])   # ninguna fila trae las dos
        self.assertEqual(0, self._pagina(q="zzz-no-existe")[1])

    def test_la_busqueda_tambien_mira_responsable_fecha_y_dias(self):
        fecha_nueva = (HOY - timedelta(days=30)).date().isoformat()
        self.assertEqual(3, self._pagina(q=f"omar {fecha_nueva}")[1])
        self.assertEqual(3, self._pagina(q=f"omar gonzalez {fecha_nueva}")[1])
        self.assertGreaterEqual(self._pagina(id_user=OMAR, q="398")[1], 1)   # dias prestado

    def test_busqueda_y_responsable_se_combinan(self):
        self.assertEqual(1, self._pagina(id_user=OMAR, q="escalera")[1])
        self.assertEqual(0, self._pagina(id_user=ANA, q="escalera")[1])
        self.assertEqual(RENGLONES_DE_ANA, self._pagina(id_user=ANA, q="taladro")[1])

    def test_el_porcentaje_y_el_guion_bajo_no_son_comodines(self):
        self.assertEqual(0, self._pagina(q="%")[1])
        self.assertEqual(0, self._pagina(q="_")[1])
        self.assertEqual(0, self._pagina(q="tal_dro")[1])

    # --- paginar sin perder ni repetir -------------------------------------------------------
    def test_recorrer_todas_las_paginas_no_pierde_ni_repite_renglones(self):
        for orden in PRESTADO_ORDENES:
            for direccion in ("asc", "desc"):
                with self.subTest(orden=orden, direccion=direccion):
                    items, total = self._todo(orden=orden, direccion=direccion)
                    ids = [i["id_nm_incident_product"] for i in items]
                    self.assertEqual(total, len(ids))
                    self.assertEqual(len(ids), len(set(ids)))

    # --- orden -------------------------------------------------------------------------------
    def test_el_orden_por_omision_es_mas_dias_primero(self):
        items, _ = self._todo(id_user=OMAR)
        dias = [i["dias_prestado"] for i in items]
        self.assertEqual(sorted(dias, reverse=True), dias)
        invertido, _ = self._todo(id_user=OMAR, direccion="asc")
        self.assertEqual(sorted(dias), [i["dias_prestado"] for i in invertido])

    def test_ordenar_por_dias_da_los_extremos_del_TOTAL_no_los_de_la_pagina(self):
        """El servidor ordena sobre todos los renglones: lo primero de la pagina 1 es el extremo de TODO, y
        lo ultimo de la ultima pagina es el otro extremo (no solo el mejor de las 50 que se alcanzaron a ver)."""
        todos, total = self._todo()
        dias = [i["dias_prestado"] for i in todos]
        self.assertGreaterEqual(total, 63 + RENGLONES_DE_ANA + 10)
        for direccion, primero, ultimo in (("desc", max(dias), min(dias)), ("asc", min(dias), max(dias))):
            with self.subTest(direccion=direccion):
                pagina_1, _ = self._pagina(orden="dias_prestado", direccion=direccion, limit=50, offset=0)
                recorrido, _ = self._todo(orden="dias_prestado", direccion=direccion)
                self.assertEqual(primero, pagina_1[0]["dias_prestado"])
                self.assertEqual(ultimo, recorrido[-1]["dias_prestado"])
                ordenados = [i["dias_prestado"] for i in recorrido]
                self.assertEqual(sorted(dias, reverse=direccion == "desc"), ordenados)

    def test_ordenar_por_fecha_del_vale_da_los_extremos_del_total(self):
        todos, _ = self._todo()
        fechas = [i["fecha_prestamo"] for i in todos]
        for direccion, primero, ultimo in (("desc", max(fechas), min(fechas)), ("asc", min(fechas), max(fechas))):
            with self.subTest(direccion=direccion):
                pagina_1, _ = self._pagina(orden="fecha_prestamo", direccion=direccion, limit=50, offset=0)
                recorrido, _ = self._todo(orden="fecha_prestamo", direccion=direccion)
                self.assertEqual(primero, pagina_1[0]["fecha_prestamo"])
                self.assertEqual(ultimo, recorrido[-1]["fecha_prestamo"])
                self.assertEqual(sorted(fechas, reverse=direccion == "desc"), [i["fecha_prestamo"] for i in recorrido])

    def test_mas_dias_primero_es_lo_mismo_que_fecha_mas_antigua_primero(self):
        por_dias, _ = self._todo(orden="dias_prestado", direccion="desc")
        por_fecha, _ = self._todo(orden="fecha_prestamo", direccion="asc")
        self.assertEqual([i["fecha_prestamo"] for i in por_dias], [i["fecha_prestamo"] for i in por_fecha])

    def test_cambiar_de_orden_entre_paginas_no_pierde_ni_repite_renglones(self):
        """El usuario pide la pagina 1 en un orden y luego cambia: la pagina 1 del orden nuevo es otra consulta
        completa. Cada orden por separado recorre TODOS los renglones una sola vez (el desempate por id hace que
        un empate -aqui 20 renglones con los mismos dias- no baraje las paginas)."""
        referencia = {i["id_nm_incident_product"] for i in self._todo()[0]}
        for orden, direccion in (("dias_prestado", "desc"), ("dias_prestado", "asc"), ("fecha_prestamo", "desc"), ("fecha_prestamo", "asc")):
            with self.subTest(orden=orden, direccion=direccion):
                self._pagina(orden="dias_prestado", direccion="desc", limit=50, offset=0)      # lo que se veia antes
                items, total = self._todo(orden=orden, direccion=direccion)
                ids = [i["id_nm_incident_product"] for i in items]
                self.assertEqual(total, len(ids))
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual(referencia, set(ids))
                # pedir la misma pagina dos veces da lo mismo: el orden es estable
                una, _ = self._pagina(orden=orden, direccion=direccion, limit=50, offset=50)
                otra, _ = self._pagina(orden=orden, direccion=direccion, limit=50, offset=50)
                self.assertEqual([i["id_nm_incident_product"] for i in una], [i["id_nm_incident_product"] for i in otra])

    def test_el_orden_se_conserva_al_filtrar_y_al_buscar(self):
        items, _ = self._todo(id_user=OMAR, orden="dias_prestado", direccion="asc")
        dias = [i["dias_prestado"] for i in items]
        self.assertEqual(sorted(dias), dias)
        self.assertEqual(30, dias[0])                                         # lo nuevo de Omar, primero
        items, _ = self._todo(q="zz", orden="fecha_prestamo", direccion="desc")
        fechas = [i["fecha_prestamo"] for i in items]
        self.assertEqual(sorted(fechas, reverse=True), fechas)

    def test_ordenar_por_articulo_y_por_responsable_lo_hace_el_servidor(self):
        items, _ = self._todo(id_user=OMAR, orden="articulo", direccion="asc")
        nombres = [i["articulo"].lower() for i in items]
        self.assertEqual(sorted(nombres), nombres)
        items, _ = self._todo(id_user=OMAR, orden="articulo", direccion="desc")
        self.assertEqual(sorted(nombres, reverse=True), [i["articulo"].lower() for i in items])
        items, _ = self._todo(q="zz", orden="responsable", direccion="asc")
        responsables = [(i["responsable"] or "").lower() for i in items]
        self.assertEqual(sorted(responsables), responsables)

    def test_agrupar_deja_a_cada_responsable_en_un_solo_tramo_aun_paginando(self):
        items, _ = self._todo(q="zz", agrupar=True)
        secuencia = [i["id_user"] for i in items]
        tramos = [u for n, u in enumerate(secuencia) if n == 0 or u != secuencia[n - 1]]
        self.assertEqual(len(tramos), len(set(tramos)))
        # y el responsable con el prestamo mas viejo va primero (Omar: 400 dias)
        self.assertEqual(OMAR, secuencia[0])

    # --- responsables con el mismo nombre ----------------------------------------------------
    def test_dos_responsables_con_el_mismo_nombre_no_mezclan_renglones(self):
        """Se filtra por id_user, no por nombre. Ojo: esto NO limpia el dato: los dos siguen llamandose
        "ESTANCIA EN EL TALLER" hasta que se corrija en origen; solo dejan de confundirse."""
        uno, total_uno = self._todo(id_user=TALLER_1)
        otro, total_otro = self._todo(id_user=TALLER_2)
        self.assertEqual((5, 5), (total_uno, total_otro))
        self.assertEqual({TALLER_1}, {i["id_user"] for i in uno})
        self.assertEqual({TALLER_2}, {i["id_user"] for i in otro})
        self.assertEqual({"ESTANCIA EN EL TALLER"}, {i["responsable"] for i in uno + otro})
        listado = [r for r in self._resumen(10)["responsables"] if r["id_user"] in (TALLER_1, TALLER_2)]
        self.assertEqual([(TALLER_1, 5), (TALLER_2, 5)], [(r["id_user"], r["renglones"]) for r in listado])

    # --- agregados ---------------------------------------------------------------------------
    def test_el_conteo_por_responsable_es_el_real_y_no_cambia_con_la_busqueda_ni_el_filtro(self):
        def cuenta(**filtros):
            lista = self._resumen(1, **filtros)["responsables"]
            return {r["id_user"]: r["renglones"] for r in lista if r["id_user"] in USUARIOS}
        esperado = {OMAR: VIEJOS_DE_OMAR + 3, ANA: RENGLONES_DE_ANA, TALLER_1: 5, TALLER_2: 5}
        self.assertEqual(esperado, cuenta())
        self.assertEqual(esperado, cuenta(q="escalera"))
        self.assertEqual(esperado, cuenta(id_user=ANA))
        self.assertEqual(esperado, cuenta(id_user=OMAR, q="maletin"))

    def test_los_dias_del_mas_antiguo_por_responsable(self):
        lista = {r["id_user"]: r for r in self._resumen(1)["responsables"]}
        self.assertEqual(400, lista[OMAR]["mas_antiguo_dias"])
        self.assertEqual(200, lista[ANA]["mas_antiguo_dias"])
        self.assertEqual("OMAR GONZALEZ", lista[OMAR]["responsable"])

    def test_el_resumen_describe_lo_que_cumple_los_filtros(self):
        _, total = self._pagina(id_user=OMAR)
        resumen = self._resumen(total, id_user=OMAR)["resumen"]
        self.assertEqual(
            {"renglones": VIEJOS_DE_OMAR + 3, "responsables": 1}, {k: resumen[k] for k in ("renglones", "responsables")})
        self.assertEqual(400, resumen["mas_antiguo"]["dias"])
        self.assertEqual("OMAR GONZALEZ", resumen["mas_antiguo"]["responsable"])
        # buscando algo reciente, el mas antiguo es ese
        _, total = self._pagina(q="escalera")
        resumen = self._resumen(total, q="escalera")["resumen"]
        self.assertEqual((1, 1, 30), (resumen["renglones"], resumen["responsables"], resumen["mas_antiguo"]["dias"]))
        self.assertEqual("ESCALERA DE TIJERA ZZ", resumen["mas_antiguo"]["articulo"])

    def test_el_resumen_de_una_busqueda_sin_resultados_no_inventa_un_mas_antiguo(self):
        resumen = self._resumen(0, q="zzz-no-existe")["resumen"]
        self.assertEqual((0, 0, None), (resumen["renglones"], resumen["responsables"], resumen["mas_antiguo"]))

    def test_el_filtro_de_otra_tarjeta_acota_filas_y_conteos(self):
        items, total = self._todo(id_user_ambito=ANA)
        self.assertEqual((RENGLONES_DE_ANA, {ANA}), (total, {i["id_user"] for i in items}))
        lista = self._resumen(total, id_user_ambito=ANA)["responsables"]
        self.assertEqual([(ANA, RENGLONES_DE_ANA)], [(r["id_user"], r["renglones"]) for r in lista])
        # el desplegable no puede salirse del ambito: otro responsable da vacio
        self.assertEqual(0, self._pagina(id_user_ambito=ANA, id_user=OMAR)[1])

    def test_una_baja_no_se_cuenta_como_prestado(self):
        self._prestar(OMAR, P_COMUN, 5, tipo=TIPO_DESTRUCCION)
        self.assertEqual(VIEJOS_DE_OMAR + 3, self._pagina(id_user=OMAR)[1])

    # --- eficiencia ---------------------------------------------------------------------------
    def test_los_agregados_son_consultas_constantes_no_una_por_renglon_ni_por_responsable(self):
        sentencias = []

        def contar(conn, cursor, statement, parameters, context, executemany):
            sentencias.append(statement)

        def con_conteo():
            sentencias.clear()
            event.listen(engine, "before_cursor_execute", contar)
            try:
                with transaction_context() as db:
                    _, total = material_prestado_actual_query(db, limit=50, offset=0, q="zz")
                    material_prestado_actual_resumen_query(db, total=total, q="zz")
            finally:
                event.remove(engine, "before_cursor_execute", contar)
            return len(sentencias)

        antes = con_conteo()
        for _ in range(40):
            self._prestar(ANA, P_COMUN, 10)         # mas renglones y mas vales, mismo responsable
        despues = con_conteo()
        self.assertEqual(antes, despues)
        self.assertEqual(3, despues)                 # pagina con su total, por responsable, distintos + mas antiguo

    # --- registro ----------------------------------------------------------------------------
    def test_solo_el_kpi_vivo_declara_un_resumen(self):
        con_resumen = [k.clave for k in KPI_POR_CLAVE.values() if k.resumen_builder is not None]
        self.assertEqual(["material_prestado_actual"], con_resumen)
        self.assertEqual("vivo", KPI_POR_CLAVE["material_prestado_actual"].modo)


if __name__ == "__main__":
    unittest.main()
