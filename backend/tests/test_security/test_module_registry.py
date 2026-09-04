"""El registro de modulos y la matriz de permisos que sale de el.

Lo que estas pruebas sostienen:

* cada entidad protegida pertenece a exactamente un modulo, para que conceder un
  modulo diga con precision que arrastra;
* los tres almacenes -inventario, logistica y restaurante- no comparten ni una
  tabla, asi que dar acceso a uno no da acceso a los otros;
* la matriz no concede capacidades que el acceso al modulo no puede ejercer, ni
  borrado fuera de administracion.

El registro ya valida buena parte de esto al importarse. Estas pruebas cubren lo
que el registro no puede ver por si mismo -que la lista de entidades protegidas
del codigo coincida con la declarada- y dejan por escrito los criterios, para
que cambiarlos sea una decision y no un descuido.
"""

from __future__ import annotations

import pathlib
import re
import unittest

from app.modules import registry


RAIZ = pathlib.Path(__file__).resolve().parents[2]
RUTAS = RAIZ / "app" / "routes"
APP_JSX = RAIZ.parent / "frontend" / "src" / "App.jsx"


def entidades_protegidas() -> set[str]:
    """Lo que el backend protege y lo que el front sabe mostrar."""
    encontradas: set[str] = set()
    patron = re.compile(r"require_entity_permission\(\s*'([a-z_]+)'")
    for archivo in RUTAS.glob("*.py"):
        encontradas.update(patron.findall(archivo.read_text(encoding="utf-8", errors="ignore")))
    if APP_JSX.exists():
        encontradas.update(re.findall(
            r'entityName="([a-z_]+)"', APP_JSX.read_text(encoding="utf-8", errors="ignore")))
    return encontradas


class TestCobertura(unittest.TestCase):
    def test_every_guarded_entity_belongs_to_a_module(self):
        """Sin modulo, ningun rol la recibe y la pantalla queda muerta."""
        declaradas = set(registry.ENTIDAD_A_MODULO) | set(registry.CAPACIDAD_POR_CLAVE)
        huerfanas = sorted(entidades_protegidas() - declaradas)

        self.assertEqual(
            [], huerfanas,
            "Estas entidades estan protegidas pero no pertenecen a ningun modulo, "
            "asi que ningun rol podria alcanzarlas: " + ", ".join(huerfanas),
        )

    def test_no_entity_belongs_to_two_modules(self):
        """El registro revienta al importarse; aqui queda constancia."""
        vistas = []
        for modulo in registry.MODULOS:
            vistas.extend(modulo.entidades)

        self.assertEqual(len(vistas), len(set(vistas)))

    def test_nothing_is_both_an_entity_and_a_capability(self):
        self.assertEqual(
            set(),
            set(registry.ENTIDAD_A_MODULO) & set(registry.CAPACIDAD_POR_CLAVE),
        )

    def test_the_business_modules_are_declared(self):
        """Lo que se puede vender por separado.

        La lista es exacta a proposito y hay que tocarla al agregar un modulo.
        Eso es la mitad del valor de esta prueba: un modulo que se declara sin
        pasar por aqui es un modulo que nadie decidio vender, y el plan lo
        vendera igual. Documentos y Laboratorio llegaron asi -con tablas,
        rutas y sembrado, sin declararse en el registro- y la prueba de
        cobertura los encontro.
        """
        esperados = {
            # Los siete que se pidieron al principio.
            "facturacion", "logistica", "restaurante", "rh", "crm",
            "operaciones", "inventario",
            # El punto de venta, integrado despues como submodulo grande.
            "pos",
            # Llegados con tny_docs.
            "documentos", "laboratorio",
        }

        self.assertEqual(esperados, set(registry.MODULOS_DE_NEGOCIO))


class TestAlmacenesSeparados(unittest.TestCase):
    """Inventario, logistica y restaurante tienen almacen propio.

    Cada uno guarda algo distinto: logistica mercancia de terceros con lote y
    numero de serie, inventario material propio de obra en piezas enteras, y el
    restaurante insumos que se consumen por receta. Unificarlos obligaria a que
    los tres pierdan lo que les es propio.
    """

    def test_the_modules_with_a_warehouse_in_the_core_database(self):
        """El punto de venta no aparece aqui porque lleva el suyo en su base."""
        almacenes = registry.almacenes()

        self.assertEqual({"inventario", "logistica", "restaurante"}, set(almacenes))
        for modulo, cadena in almacenes.items():
            with self.subTest(modulo=modulo):
                self.assertGreaterEqual(len(cadena), 2, "un almacen necesita saldo y libro")

    def test_no_table_is_shared_between_two_warehouses(self):
        """Una tabla compartida seria una fuga silenciosa entre modulos."""
        almacenes = registry.almacenes()
        for izquierda, cadena_izq in almacenes.items():
            for derecha, cadena_der in almacenes.items():
                if izquierda >= derecha:
                    continue
                with self.subTest(par=(izquierda, derecha)):
                    self.assertEqual(
                        set(), set(cadena_izq) & set(cadena_der),
                        f"{izquierda} y {derecha} comparten tabla de almacen",
                    )

    def test_operating_one_warehouse_never_grants_operating_another(self):
        """La separacion que se pidio, dicha con precision.

        No es que un gerente no pueda mirar logistica -eso es deliberado y va en
        solo lectura-, es que nadie opere un almacen ajeno por arrastre. Quien
        puede escribir en dos almacenes tiene que estar declarado, y hoy solo lo
        esta el jefe de almacen.
        """
        ESCRITURA = registry.CREAR | registry.ACTUALIZAR | registry.BORRAR
        con_almacen = set(registry.almacenes())

        for rol in registry.ROLES:
            if rol.nombre == "Administrator":
                continue
            opera = {
                clave for clave, bits in rol.modulos.items()
                if clave in con_almacen and bits & ESCRITURA
            }
            with self.subTest(rol=rol.nombre, opera=sorted(opera)):
                if len(opera) > 1:
                    self.assertEqual(
                        "Jefe de almacen", rol.nombre,
                        f"{rol.nombre} opera {sorted(opera)}; solo el jefe de almacen "
                        "tiene dos almacenes declarados.",
                    )

    def test_the_warehouse_clerk_reaches_only_its_own_warehouse(self):
        """El caso concreto que se pidio separar."""
        almacenista = next(r for r in registry.ROLES if r.nombre == "Almacenista")

        self.assertEqual({"inventario", "configuracion"}, set(almacenista.modulos))
        for ajeno in ("logistica", "restaurante", "pos"):
            with self.subTest(modulo=ajeno):
                self.assertNotIn(ajeno, almacenista.modulos)

    def test_a_module_with_its_own_database_declares_it(self):
        """Separacion por base: no se cruza ni por una consulta mal escrita."""
        pos = registry.MODULO_POR_CLAVE["pos"]

        self.assertEqual("pos_enterprise", pos.base_de_datos)
        self.assertEqual((), pos.entidades, "no tiene tablas en la base del nucleo")
        self.assertEqual((), pos.almacen, "su almacen vive en su propia base")

    def test_the_warehouse_chains_exist_as_models(self):
        """Que las tablas declaradas sean las que el codigo usa de verdad."""
        from app.models.base import Base

        tablas = set(Base.metadata.tables)
        for modulo, cadena in registry.almacenes().items():
            for tabla in cadena:
                with self.subTest(modulo=modulo, tabla=tabla):
                    self.assertIn(tabla, tablas)


class TestMatrizDePermisos(unittest.TestCase):
    def test_only_administration_may_delete(self):
        """Un borrado con contabilidad y almacen de por medio no se reconstruye."""
        for rol in registry.ROLES:
            if rol.nombre == "Administrator":
                continue
            for clave, bits in rol.modulos.items():
                if bits & registry.BORRAR:
                    with self.subTest(rol=rol.nombre, modulo=clave):
                        self.assertIn(
                            clave, {"inventario", "logistica"},
                            f"{rol.nombre} puede borrar en {clave}; solo se acepta para "
                            "los responsables de almacen.",
                        )

    def test_no_operating_role_administers_security(self):
        for rol in registry.ROLES:
            if rol.nombre == "Administrator":
                continue
            with self.subTest(rol=rol.nombre):
                self.assertNotIn(
                    "seguridad", rol.modulos,
                    f"{rol.nombre} administraria usuarios y perfiles.",
                )

    def test_every_role_can_read_the_shared_catalogs(self):
        """Sin leer `status` los desplegables de cualquier pantalla van vacios."""
        for rol in registry.ROLES:
            with self.subTest(rol=rol.nombre):
                self.assertIn("configuracion", rol.modulos)
                self.assertTrue(rol.modulos["configuracion"] & registry.LEER)

    def test_a_capability_is_never_granted_without_its_module(self):
        """El registro lo valida al importarse; aqui se explica por que.

        Una capacidad que el acceso al modulo no puede ejercer es una fila que
        no sirve y que hace creer que el rol puede hacer algo que no puede.

        La excepcion son los modulos que se operan solo por capacidad, porque no
        tienen entidades en la base del nucleo y por tanto no hay acceso de
        tabla que conceder. Se reconoce por eso -no tener entidades- y no por
        nombre: al integrar el punto de venta esta prueba fallo porque eximia al
        restaurante a mano, y el criterio real no era el nombre sino la
        naturaleza del modulo.
        """
        for rol in registry.ROLES:
            for clave in rol.capacidades:
                modulo = registry.MODULO_POR_CLAVE[registry.CAPACIDAD_POR_CLAVE[clave].modulo]
                if not modulo.entidades:
                    continue
                with self.subTest(rol=rol.nombre, capacidad=clave):
                    self.assertIn(modulo.clave, rol.modulos)

    def test_a_capability_only_module_has_no_core_entities(self):
        """Lo que hace valida la excepcion de arriba."""
        for modulo in registry.MODULOS:
            capacidades = [c for c in registry.CAPACIDADES if c.modulo == modulo.clave]
            if modulo.entidades or not capacidades:
                continue
            with self.subTest(modulo=modulo.clave):
                self.assertEqual(
                    (), modulo.entidades,
                    "un modulo que se opera por capacidad no declara entidades del nucleo",
                )

    def test_the_warehouse_clerk_cannot_adjust(self):
        """Quien mueve la mercancia no tapa su propio faltante."""
        almacenista = next(r for r in registry.ROLES if r.nombre == "Almacenista")

        self.assertNotIn("inventory_adjustment", almacenista.capacidades)
        self.assertIn("inventario", almacenista.modulos)

    def test_the_project_leader_executes_but_does_not_authorize(self):
        jefe = next(r for r in registry.ROLES if r.nombre == "Jefe de taller")
        gerente = next(r for r in registry.ROLES if r.nombre == "Gerente")

        self.assertIn("project_execution", jefe.capacidades)
        self.assertNotIn("project_authorization", jefe.capacidades)
        self.assertIn("project_authorization", gerente.capacidades)

    def test_restaurant_roles_only_reach_the_restaurant(self):
        for nombre in ("Mesero", "Cocina", "Caja Restaurante"):
            rol = next(r for r in registry.ROLES if r.nombre == nombre)
            with self.subTest(rol=nombre):
                self.assertEqual({"configuracion"}, set(rol.modulos))
                self.assertTrue(rol.capacidades)

    def test_every_generated_row_uses_bits_the_code_understands(self):
        from app.utils.auth import PERMISSION_BITS

        validos = 0
        for bit in PERMISSION_BITS.values():
            validos |= bit

        for fila in registry.filas_de_permisos():
            bits = fila[2]
            with self.subTest(entidad=fila[1], rol=fila[0]):
                self.assertEqual(bits, bits & validos)
                self.assertGreater(bits, 0)

    def test_the_bootstrap_only_entities_are_not_seeded(self):
        """Sembrarlas daria una fila inutil: el codigo las bloquea igual."""
        from app.utils.auth import BOOTSTRAP_ONLY_ENTITIES

        self.assertTrue(BOOTSTRAP_ONLY_ENTITIES <= registry.SOLO_ARRANQUE)
        sembradas = {fila[1] for fila in registry.filas_de_permisos()}
        self.assertEqual(set(), sembradas & registry.SOLO_ARRANQUE)


class TestLicenciaPorModulo(unittest.TestCase):
    """LICENSED_MODULES: que un cliente que no pago un modulo no reciba sus filas."""

    def test_core_modules_are_exactly_the_ones_excluded_from_business(self):
        self.assertEqual(
            set(registry.MODULOS_CORE),
            {m.clave for m in registry.MODULOS} - set(registry.MODULOS_DE_NEGOCIO),
        )
        self.assertEqual({"configuracion", "seguridad"}, set(registry.MODULOS_CORE))

    def test_capacidad_defaults_to_bundled_with_its_module(self):
        capacidad = registry.Capacidad("test_cap", "Prueba", "inventario")

        self.assertFalse(capacidad.licencia_independiente)

    def test_entity_rows_carry_their_own_module_as_the_license_key(self):
        for fila in registry.filas_de_permisos():
            entidad = fila[1]
            modulo_licencia = fila[-1]
            modulo_dueno = registry.ENTIDAD_A_MODULO.get(entidad)
            if modulo_dueno is None:
                continue  # es una capacidad, no una entidad
            with self.subTest(entidad=entidad):
                self.assertEqual(modulo_dueno, modulo_licencia)

    def test_a_bundled_capability_uses_its_parent_module_as_the_license_key(self):
        # inventory_adjustment no esta marcada licencia_independiente: viaja
        # con la licencia de inventario, no con una clave propia.
        capacidad = registry.CAPACIDAD_POR_CLAVE["inventory_adjustment"]
        self.assertFalse(capacidad.licencia_independiente)

        filas = [f for f in registry.filas_de_permisos() if f[1] == "inventory_adjustment"]
        self.assertTrue(filas)
        for fila in filas:
            with self.subTest(rol=fila[0]):
                self.assertEqual("inventario", fila[-1])

    def test_an_independently_licensed_capability_uses_its_own_key(self):
        """Una capacidad marcada aparte no debe viajar con la de su modulo padre."""
        capacidades_originales = registry.CAPACIDADES
        roles_originales = registry.ROLES
        try:
            capacidad_prueba = registry.Capacidad(
                "prueba_addon", "Addon de prueba", "facturacion", licencia_independiente=True,
            )
            registry.CAPACIDADES = capacidades_originales + (capacidad_prueba,)
            registry.CAPACIDAD_POR_CLAVE["prueba_addon"] = capacidad_prueba
            rol_admin = next(r for r in roles_originales if r.nombre == "Administrator")
            registry.ROLES = tuple(
                registry.Rol(
                    r.id_permission, r.nombre, r.modulos,
                    r.capacidades + ("prueba_addon",) if r is rol_admin else r.capacidades,
                )
                for r in roles_originales
            )

            filas = [f for f in registry.filas_de_permisos() if f[1] == "prueba_addon"]

            self.assertTrue(filas)
            for fila in filas:
                self.assertEqual("prueba_addon", fila[-1])
        finally:
            registry.CAPACIDADES = capacidades_originales
            registry.ROLES = roles_originales
            del registry.CAPACIDAD_POR_CLAVE["prueba_addon"]


class TestSqlGenerado(unittest.TestCase):
    def _sql(self):
        import importlib.util

        ruta = RAIZ / "scripts" / "seed_module_permissions.py"
        especificacion = importlib.util.spec_from_file_location("seed_module_permissions", ruta)
        modulo = importlib.util.module_from_spec(especificacion)
        especificacion.loader.exec_module(modulo)
        return modulo.generar()

    def test_it_seeds_only_what_is_missing(self):
        """El gestor manda; el registro da el valor por omision y nada mas.

        Esta prueba decia lo contrario: exigia que el sembrado diera de baja
        todo lo vigente y pisara con `DO UPDATE`, para que no convivieran dos
        criterios. El razonamiento era bueno y la consecuencia no se habia
        medido: corriendo en cada arranque del pod, eso revertia cualquier
        ajuste hecho desde el gestor de roles en el siguiente despliegue -un
        permiso subido de 2 a 15 volvia a 2-.

        La decision fue que el gestor sea la autoridad. El sembrado inserta el
        par (perfil, entidad) que no existe y no toca el resto: ni sus bits, ni
        su navegacion, ni su baja.
        """
        sql = self._sql()

        self.assertIn("ON CONFLICT (id_permission, entity_name) DO NOTHING", sql)
        self.assertNotIn("DO UPDATE", sql)
        # El borrado general es lo que hacia que nada del gestor durase. Lo que
        # si queda es el DELETE acotado por fecha que limpia los residuos de
        # aquel mecanismo, y ese no lleva `SET`.
        compacto = " ".join(sql.split())
        self.assertNotIn(
            "UPDATE entity_permission SET deletion_date = now() WHERE deletion_date IS NULL",
            compacto,
        )

    def test_it_rebuilds_the_field_permissions_too(self):
        """Un modulo que cambio de alcance arrastra sus campos.

        Sin esto la pantalla queda en blanco aunque el permiso de entidad este:
        ya paso una vez con facturacion.
        """
        sql = self._sql()

        self.assertIn("nm_field_permission", sql)

    def test_the_comma_goes_before_the_comment(self):
        """Con la coma despues del `--`, el renglon siguiente deja de contar."""
        for linea in self._sql().splitlines():
            if linea.lstrip().startswith("(") and "--" in linea:
                with self.subTest(linea=linea.strip()[:60]):
                    self.assertNotIn(",", linea.split("--", 1)[1])


if __name__ == "__main__":
    unittest.main()
