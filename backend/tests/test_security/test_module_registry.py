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

    def test_the_seven_business_modules_are_declared(self):
        esperados = {
            "facturacion", "logistica", "restaurante", "rh", "crm",
            "operaciones", "inventario",
        }

        self.assertEqual(esperados, set(registry.MODULOS_DE_NEGOCIO))


class TestAlmacenesSeparados(unittest.TestCase):
    """Inventario, logistica y restaurante tienen almacen propio.

    Cada uno guarda algo distinto: logistica mercancia de terceros con lote y
    numero de serie, inventario material propio de obra en piezas enteras, y el
    restaurante insumos que se consumen por receta. Unificarlos obligaria a que
    los tres pierdan lo que les es propio.
    """

    def test_the_three_modules_declare_their_own_warehouse(self):
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
        self.assertNotIn("logistica", almacenista.modulos)
        self.assertNotIn("restaurante", almacenista.modulos)

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
        """
        for rol in registry.ROLES:
            for clave in rol.capacidades:
                modulo = registry.CAPACIDAD_POR_CLAVE[clave].modulo
                if modulo == "restaurante":
                    continue
                with self.subTest(rol=rol.nombre, capacidad=clave):
                    self.assertIn(modulo, rol.modulos)

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


class TestSqlGenerado(unittest.TestCase):
    def _sql(self):
        import importlib.util

        ruta = RAIZ / "scripts" / "seed_module_permissions.py"
        especificacion = importlib.util.spec_from_file_location("seed_module_permissions", ruta)
        modulo = importlib.util.module_from_spec(especificacion)
        especificacion.loader.exec_module(modulo)
        return modulo.generar()

    def test_it_replaces_the_previous_matrix_instead_of_piling_on(self):
        """Dos criterios conviviendo es como aparecieron los descuadres."""
        sql = self._sql()

        self.assertIn("SET deletion_date = now()", sql)
        self.assertIn("ON CONFLICT (id_permission, entity_name) DO UPDATE", sql)

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
