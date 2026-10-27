#!/usr/bin/env python3
"""Datos de demo LOCAL de catalogo: clientes, proveedores, productos y su entrada.

Por que existe
--------------
Una base recien levantada trae un solo producto y un solo cliente de bootstrap,
y los otros sembrados de demo (`init_test_data.py`, `seed_kpi_*_demo.py`,
`seed_fiscal_demo.py`) llenan vales, facturas y tareas pero no el catalogo. Sin
productos ni clientes no hay con que probar Localizar, el vale o la cotizacion.

Como lo hace
------------
Por la API REST, con el usuario bootstrap, igual que lo capturaria una persona
en pantalla: pasa por permisos, por la regla de descripcion en formato de
oracion (`app/utils/product_description.py`) y por el libro de inventario. La
existencia NO se escribe en `product.cantidad`: el producto nace en 0 y su
existencia llega con un movimiento `receive` (entrada), con llave de
idempotencia, como cualquier entrada real.

Todo es inventado: nombres, RFC genericos (XAXX010101000 / XEXX010101000) y
marcas que no existen.

Guarda de seguridad
-------------------
Se niega a correr contra una URL que no sea localhost/127.0.0.1.

Idempotente: cada registro se busca antes de crearse (por nombre, descripcion o
`product_code`) y las entradas usan una llave fija por producto, asi que volver
a correrlo no duplica nada.

Uso (desde la raiz del repo, con el stack de docker compose arriba):
    python backend/scripts/seed_demo_catalogo_api.py --dry-run
    python backend/scripts/seed_demo_catalogo_api.py
    python backend/scripts/seed_demo_catalogo_api.py --api http://localhost:5001 --env .env
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1"}
ID_UBICACION_GENERAL = 2  # "Almacen general", sembrado por seed.sql

MARCAS = ["Herramex", "Acero Norte", "Voltix", "Tornillería del Bajío", "Protekta"]

FAMILIAS = [
    ("Herramienta manual", "tool"),
    ("Herramienta eléctrica", "tool"),
    ("Tornillería", "consumable"),
    ("Material eléctrico", "consumable"),
    ("Equipo de protección", "consumable"),
]

UNIDADES = [
    # unit_code, unit_name, symbol, unit_category
    ("H87", "Pieza", "pza", "cantidad"),
    ("XBX", "Caja", "cja", "cantidad"),
    ("MTR", "Metro", "m", "longitud"),
    ("PR", "Par", "par", "cantidad"),
]

# codigo, descripcion (formato de oracion), familia, marca, unidad, precio, entrada
PRODUCTOS = [
    ("DEMO-001", "Martillo de uña 16 oz", "Herramienta manual", "Herramex", "H87", 189.0, 25),
    ("DEMO-002", "Desarmador plano 1/4", "Herramienta manual", "Herramex", "H87", 54.5, 60),
    ("DEMO-003", "Desarmador de cruz 1/4", "Herramienta manual", "Herramex", "H87", 54.5, 60),
    ("DEMO-004", "Pinza de electricista 8 pulgadas", "Herramienta manual", "Acero Norte", "H87", 215.0, 30),
    ("DEMO-005", "Llave perica 10 pulgadas", "Herramienta manual", "Acero Norte", "H87", 260.0, 20),
    ("DEMO-006", "Juego de llaves allen 9 piezas", "Herramienta manual", "Acero Norte", "XBX", 145.0, 15),
    ("DEMO-007", "Flexómetro 5 m", "Herramienta manual", "Herramex", "H87", 98.0, 40),
    ("DEMO-008", "Taladro percutor 1/2 650 W", "Herramienta eléctrica", "Voltix", "H87", 1450.0, 8),
    ("DEMO-009", "Esmeriladora angular 4 1/2", "Herramienta eléctrica", "Voltix", "H87", 1120.0, 6),
    ("DEMO-010", "Sierra circular 7 1/4", "Herramienta eléctrica", "Voltix", "H87", 2380.0, 4),
    ("DEMO-011", "Rotomartillo SDS plus", "Herramienta eléctrica", "Voltix", "H87", 3150.0, 3),
    ("DEMO-012", "Tornillo para madera 1 1/2 caja con 100", "Tornillería", "Tornillería del Bajío", "XBX", 85.0, 50),
    ("DEMO-013", "Taquete de plastico 1/4 caja con 100", "Tornillería", "Tornillería del Bajío", "XBX", 42.0, 80),
    ("DEMO-014", "Pija para lamina 1 pulgada caja con 100", "Tornillería", "Tornillería del Bajío", "XBX", 96.0, 45),
    ("DEMO-015", "Cable THW calibre 12", "Material eléctrico", "Voltix", "MTR", 14.5, 500),
    ("DEMO-016", "Contacto doble polarizado", "Material eléctrico", "Voltix", "H87", 38.0, 120),
    ("DEMO-017", "Cinta de aislar negra", "Material eléctrico", "Voltix", "H87", 19.0, 200),
    ("DEMO-018", "Foco LED 9 W luz fría", "Material eléctrico", "Voltix", "H87", 32.0, 150),
    ("DEMO-019", "Casco de seguridad blanco", "Equipo de protección", "Protekta", "H87", 120.0, 35),
    ("DEMO-020", "Guantes de carnaza", "Equipo de protección", "Protekta", "PR", 65.0, 90),
    ("DEMO-021", "Lentes de seguridad claros", "Equipo de protección", "Protekta", "H87", 45.0, 70),
    ("DEMO-022", "Chaleco reflejante naranja", "Equipo de protección", "Protekta", "H87", 88.0, 40),
]

# nombre, tipo, ciudad, estado, contacto, correo, telefono, limite de credito
CLIENTES = [
    ("Constructora Puerta Alta", "client", "León", "Guanajuato", "Ricardo Salas", "compras@puertaalta.example", "4770000101", 50000),
    ("Grupo Industrial Mirador", "client", "Silao", "Guanajuato", "Laura Pineda", "almacen@mirador.example", "4720000102", 120000),
    ("Mantenimiento Integral del Centro", "client", "Irapuato", "Guanajuato", "Héctor Ruiz", "hruiz@mic.example", "4620000103", 30000),
    ("Hotel Jardín Real", "client", "Guanajuato", "Guanajuato", "Sofia Mendez", "mantenimiento@jardinreal.example", "4730000104", 25000),
    ("Agroindustrias San Miguel", "client", "Celaya", "Guanajuato", "Jorge Ávila", "jorge@agrosm.example", "4610000105", 80000),
    ("Plásticos y Moldes del Bajío", "client", "León", "Guanajuato", "Patricia Luna", "pluna@pymb.example", "4770000106", 60000),
    ("Escuela Técnica Horizonte", "client", "Salamanca", "Guanajuato", "Miguel Ortega", "admin@horizonte.example", "4640000107", 15000),
    ("Distribuidora Ferretera Atlas", "supplier", "Guadalajara", "Jalisco", "Andrea Cruz", "ventas@atlas.example", "3300000108", 0),
    ("Electro Suministros Delta", "supplier", "Querétaro", "Querétaro", "Fernando Gil", "pedidos@delta.example", "4420000109", 0),
    ("Seguridad Industrial Escudo", "supplier", "Aguascalientes", "Aguascalientes", "Carmen Vega", "contacto@escudo.example", "4490000110", 0),
]


class Api:
    def __init__(self, base: str, token: str | None = None, dry_run: bool = False):
        self.base = base.rstrip("/")
        self.token = token
        self.dry_run = dry_run

    def _call(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as err:
            detalle = err.read().decode(errors="replace")[:600]
            raise SystemExit(f"{method} {path} -> {err.code}: {detalle}") from None

    def get(self, path, **params):
        query = ("?" + urllib.parse.urlencode(params)) if params else ""
        return self._call("GET", path + query)

    def post(self, path, body, escribe: bool = True):
        if escribe and self.dry_run:
            print(f"[dry-run] POST {path} {json.dumps(body, ensure_ascii=False)}")
            return None
        return self._call("POST", path, body)

    def buscar(self, path, campo, valor):
        """Primer registro vivo con `campo == valor`, recorriendo todas las paginas."""
        pagina = 1
        while True:
            datos = self.get(path, page=pagina, per_page=100)
            for item in datos.get("items", []):
                if item.get(campo) == valor and not item.get("deletion_date"):
                    return item
            if pagina >= int(datos.get("pages") or 1):
                return None
            pagina += 1


def leer_env(ruta: pathlib.Path) -> dict:
    valores = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.lstrip().startswith("#"):
            clave, valor = linea.split("=", 1)
            valores[clave.strip()] = valor.strip()
    return valores


def asegurar(api: Api, path: str, campo: str, valor, cuerpo: dict, id_campo: str, conteo: dict, nombre: str) -> int:
    existente = api.buscar(path, campo, valor)
    if existente:
        conteo[nombre + "_existentes"] = conteo.get(nombre + "_existentes", 0) + 1
        return existente[id_campo]
    creado = api.post(path, cuerpo)
    conteo[nombre + "_creados"] = conteo.get(nombre + "_creados", 0) + 1
    return creado[id_campo] if creado else -1


def main() -> None:
    raiz = pathlib.Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Siembra catalogo de demo por la API local.")
    parser.add_argument("--api", default="http://localhost:5001")
    parser.add_argument("--env", default=str(raiz / ".env"))
    parser.add_argument("--dry-run", action="store_true", help="muestra lo que crearia sin escribir nada")
    args = parser.parse_args()

    host = urllib.parse.urlparse(args.api).hostname
    if host not in HOSTS_LOCALES:
        raise SystemExit(f"Solo corre contra el stack local; {host!r} no es localhost.")

    env = leer_env(pathlib.Path(args.env))
    api = Api(args.api, dry_run=args.dry_run)
    sesion = api.post("/auth/login", escribe=False, body={
        "username": env.get("BOOTSTRAP_ADMIN_USERNAME", "admin1"),
        "password": env["BOOTSTRAP_ADMIN_PASSWORD"],
    })
    api.token = sesion["token"]
    conteo: dict = {}

    marcas = {
        m: asegurar(api, "/brand/", "brand_description", m, {"brand_description": m}, "id_brand", conteo, "marcas")
        for m in MARCAS
    }
    familias = {
        f: asegurar(api, "/product_family/", "product_family_description", f,
                    {"product_family_description": f, "type": t}, "id_product_family", conteo, "familias")
        for f, t in FAMILIAS
    }
    unidades = {
        code: asegurar(api, "/unit/", "unit_code", code, {
            "unit_code": code, "unit_name": nombre, "symbol": simbolo, "unit_category": categoria,
            "measurement_system": "metric", "is_active": True,
        }, "id_unit", conteo, "unidades")
        for code, nombre, simbolo, categoria in UNIDADES
    }

    for nombre, tipo, ciudad, estado, contacto, correo, tel, credito in CLIENTES:
        asegurar(api, "/customer_supplier/", "name", nombre, {
            "name": nombre, "type": tipo, "city": ciudad,
            "geographic_state": estado, "contact_name": contacto, "email": correo, "phone": tel,
            "credit_limit": credito, "sla_level": "standard",
            "tax_id": "XAXX010101000" if tipo == "client" else "XEXX010101000",
        }, "id_customer_supplier", conteo, "clientes_proveedores")

    for codigo, descripcion, familia, marca, unidad, precio, entrada in PRODUCTOS:
        id_material = asegurar(api, "/material/", "material_description", descripcion, {
            "material_description": descripcion, "id_unit": unidades[unidad],
            "id_brand": marcas[marca], "id_product_family": familias[familia],
        }, "id_material", conteo, "materiales")
        id_producto = asegurar(api, "/product/", "product_code", codigo, {
            "product_code": codigo, "descripcion": descripcion, "id_material": id_material,
            "id_familia": familias[familia], "id_marca": marcas[marca],
            "id_location": ID_UBICACION_GENERAL, "gross_price": precio, "cantidad": 0,
            "is_directly_related_to_product_service": True,
            "tracking_mode": "fungible", "stock_purpose": "mercancia",
        }, "id_product", conteo, "productos")
        if id_producto == -1:
            conteo["entradas_por_registrar"] = conteo.get("entradas_por_registrar", 0) + 1
            continue
        resultado = api.post(f"/product/{id_producto}/inventory-movements", {
            "movement_type": "receive", "quantity": entrada, "id_location": ID_UBICACION_GENERAL,
            "reason": "Entrada inicial de demo", "idempotency_key": f"demo-entrada-{codigo}",
        })
        clave = "entradas_repetidas" if resultado.get("idempotent_replay") else "entradas_registradas"
        conteo[clave] = conteo.get(clave, 0) + 1

    print(json.dumps(conteo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
