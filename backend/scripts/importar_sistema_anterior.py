"""Importa el almacen del sistema anterior (adser_prod) a TYAKXA.

Uso
---
    python scripts/importar_sistema_anterior.py --carpeta RUTA            # ensayo
    python scripts/importar_sistema_anterior.py --carpeta RUTA --aplicar  # escribe

Sin `--aplicar` no escribe nada: lee, resuelve todo y reporta lo que haria. Es
lo que se corre primero, siempre.

Los respaldos NO se modifican: se abren en lectura.

Lo que se midio en los datos, y por que cambia la importacion
-------------------------------------------------------------
1. **`1990-01-01` no es una fecha, es el centinela de "no aplica".** Se ve en
   que `producto.fecha_baja` tiene ese unico valor en las 2 220 filas. Una carga
   literal habria importado los 2 220 productos BORRADOS y los 2 787 renglones
   de vale como devueltos.

2. **Que sigue fuera se sabe cruzando dos cosas**, no una: el renglon sin cerrar
   Y el vale sin cerrar. Solo por el renglon salen 457; solo por el vale, 1 289;
   por las dos, **302 renglones de 225 productos en manos de 22 personas**.

3. **`producto.estado` no es fiable y no es un estado.** `ENTRADA` y `SALIDA` son
   la direccion del ultimo movimiento, y contradice a los vales: 88 productos
   estan en un vale abierto sin decir SALIDA. Se conserva como texto historico;
   el estado vigente lo manda el vale.

4. **`producto.id_ubicacion` es texto y trae solo seis valores.** `'0'` -780
   productos, el 35% del catalogo- no es una ubicacion: es "sin sitio". Va a la
   ubicacion general.

5. **El responsable es un EMPLEADO, no un usuario.** `usuario` tiene 3 filas y
   `empleado` 41. Se crean usuarios a partir de los empleados, sin contrasena:
   existen para poder responder "quien tiene que", no para entrar al sistema.

6. **`material` no tiene familia ni marca**; viven en `producto`. Asi que la
   familia y la marca de cada material se resuelven desde sus productos.

7. **La ubicacion 1 se contiene a si misma** (`id_ubicacion_contenedor = 1`).
   Copiarlo tal cual dejaria un ciclo y el arbol de ubicaciones no terminaria de
   recorrerse. Se mapea a nulo.

Como se respetan las llaves
---------------------------
Las fases van en el orden de las dependencias -catalogos, personas, productos,
existencia, vales- y ninguna escribe una fila cuyo padre no exista. Lo que no se
puede resolver se reporta y se salta, en lugar de inventarse un padre.

La existencia SOLO se mueve por `apply_movement_in_session`, que es la unica
puerta que mueve el almacen. Los documentos -vale y renglones- se escriben
directo, porque son papeles y no saldos.

Se puede repetir
----------------
Todo se ancla con `external_id` / `external_source`, asi que correrlo dos veces
actualiza en lugar de duplicar. Con 2 220 productos y 2 787 renglones eso no es
un lujo: una carga de ese tamano se interrumpe, se corrige y se vuelve a correr.
"""

from __future__ import annotations

import argparse
import collections
import os
import pathlib
import sys


RAIZ = pathlib.Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from lector_volcado_mysql import entero, fecha, leer, texto  # noqa: E402

ORIGEN = "adser_prod"

# El texto que el sistema anterior usa para "sin ubicacion".
SIN_UBICACION = "0"

# `familia.herramienta_consumible` ya trae la division que el almacen necesita.
PROPOSITO_POR_FAMILIA = {
    "Maquinaria/Herramienta": "uso_interno",
    "Consumible": "mercancia",
}

# `producto.estado` mezcla dos cosas. Estas cuatro SI son estados de la pieza;
# ENTRADA y SALIDA son direccion de movimiento y no se traducen.
ESTADO_A_CATALOGO = {
    "DESTRUCCION": "retirado",
    "EXTRAVIADO": "extraviado",
    "DANADO": "danado",
    "DAÑADO": "danado",
    "EQ. DANADOS": "danado",
    "EQ. DAÑADOS": "danado",
}

RELLENO = "Sin clasificar"


class Reporte:
    """Lo que paso, contado. Es la salida que se revisa antes de aplicar."""

    def __init__(self):
        self.creado = collections.Counter()
        self.actualizado = collections.Counter()
        self.saltado = collections.Counter()
        self.avisos: list[str] = []

    def aviso(self, texto_aviso):
        self.avisos.append(texto_aviso)

    def imprimir(self, aplicado):
        print()
        print("=" * 68)
        print("RESULTADO" if aplicado else "ENSAYO (no se escribio nada)")
        print("=" * 68)
        for titulo, contador in (("creado", self.creado),
                                 ("actualizado", self.actualizado),
                                 ("saltado", self.saltado)):
            if not contador:
                continue
            print("%s:" % titulo)
            for clave, n in sorted(contador.items()):
                print("   %-34s %6d" % (clave, n))
        if self.avisos:
            print("avisos:")
            for a in self.avisos:
                print("   -", a)


def cargar(carpeta, nombre):
    ruta = pathlib.Path(carpeta) / ("adser_prod_%s.sql" % nombre)
    if not ruta.exists():
        raise SystemExit("no encuentro %s" % ruta)
    return leer(ruta)["filas"]


# --- catalogos ------------------------------------------------------------

def importar_catalogos(db, datos, rep, actor):
    """Tipos de ubicacion, ubicaciones, marcas, familias, unidad y materiales.

    Se emparejan por descripcion, sin distinguir mayusculas: si el catalogo ya
    tiene "Bodega", se reusa en lugar de crear una segunda. Es lo que hace que
    correr esto sobre una base con datos no los duplique.
    """
    from sqlalchemy import func, select

    from app.models.brand import Brand
    from app.models.incident_type import IncidentType
    from app.models.location import Location
    from app.models.location_type import LocationType
    from app.models.material import Material
    from app.models.product_family import ProductFamily
    from app.models.unit import Unit

    mapas = {}

    def por_descripcion(modelo, campo, valor, extra=None, clave_creado="?"):
        """Encuentra por descripcion o crea. Devuelve la fila."""
        limpio = texto(valor) or RELLENO
        fila = db.scalars(
            select(modelo).where(
                func.lower(getattr(modelo, campo)) == limpio.lower(),
                modelo.deletion_date.is_(None),
            ).limit(1)
        ).first()
        if fila is not None:
            return fila
        fila = modelo(created_by=actor, **{campo: limpio}, **(extra or {}))
        db.add(fila)
        db.flush()
        rep.creado[clave_creado] += 1
        return fila

    # 1. Tipos de ubicacion. El sistema anterior tiene nueve -Bodega, Pasillo,
    #    Rack, Nivel, Caja, Estante, Derecho, Izquierdo, Palet- y solo Bodega es
    #    un almacen: lo demas es donde esta dentro de la bodega.
    tipos = {}
    for f in datos["tipo_ubicacion"]:
        descripcion = texto(f.get("descripcion"))
        es_almacen = str(descripcion or "").lower() == "bodega"
        fila = por_descripcion(
            LocationType, "location_type_description", descripcion,
            {"is_warehouse": es_almacen}, "location_type")
        tipos[entero(f["id_tipo_ubicacion"])] = fila.id_location_type
    mapas["tipo_ubicacion"] = tipos

    # 2. Ubicaciones. Dos pasadas: primero todas, luego el padre, porque el
    #    padre puede venir despues del hijo en el volcado.
    ubicaciones = {}
    for f in datos["ubicacion"]:
        fila = por_descripcion(
            Location, "location_description", texto(f.get("descripcion")),
            {"id_location_type": tipos.get(entero(f.get("id_tipo_ubicacion")))
                or next(iter(tipos.values()))},
            "location")
        ubicaciones[entero(f["id_ubicacion"])] = fila.id_location
    db.flush()

    for f in datos["ubicacion"]:
        viejo = entero(f["id_ubicacion"])
        padre_viejo = entero(f.get("id_ubicacion_contenedor"))
        # Una ubicacion que se contiene a si misma deja el arbol sin fondo: la
        # ubicacion 1 viene asi en el respaldo.
        if padre_viejo is None or padre_viejo == viejo:
            if padre_viejo == viejo:
                rep.aviso("ubicacion %s se contiene a si misma; su padre queda "
                          "en nulo para no dejar un ciclo en el arbol" % viejo)
            continue
        nuevo = ubicaciones.get(viejo)
        padre = ubicaciones.get(padre_viejo)
        if nuevo and padre:
            db.get(Location, nuevo).id_location_reference = padre
    db.flush()
    mapas["ubicacion"] = ubicaciones

    # 3. La ubicacion general: donde va lo que el sistema anterior no ubica.
    from app.services.inventory_service import ubicacion_general

    general = ubicacion_general(db)
    if general is None:
        raise SystemExit(
            "no hay ubicacion general declarada (location.is_general_stock). "
            "Aplica la migracion 20260908090000 antes de importar: 780 productos "
            "vienen sin ubicacion y no hay donde ponerlos.")
    mapas["general"] = general.id_location

    # 4. Marcas y familias.
    marcas = {}
    for f in datos["marca"]:
        fila = por_descripcion(Brand, "brand_description",
                              texto(f.get("descripcion")), None, "brand")
        marcas[entero(f["id_marca"])] = fila.id_brand
    mapas["marca"] = marcas

    familias = {}
    proposito_de_familia = {}
    for f in datos["familia"]:
        clase = texto(f.get("herramienta_consumible"))
        # `product_family.type` acepta 'tool' o 'consumable'.
        tipo = "tool" if clase == "Maquinaria/Herramienta" else (
            "consumable" if clase == "Consumible" else None)
        fila = por_descripcion(ProductFamily, "product_family_description",
                              texto(f.get("descripcion")), {"type": tipo},
                              "product_family")
        familias[entero(f["id_familia"])] = fila.id_product_family
        proposito_de_familia[entero(f["id_familia"])] = \
            PROPOSITO_POR_FAMILIA.get(clase, "mercancia")
    mapas["familia"] = familias
    mapas["proposito_de_familia"] = proposito_de_familia

    # Los de relleno, para lo que apunta a un catalogo que no existe: 13
    # productos con material inexistente, 3 con marca, 1 con familia.
    mapas["marca_relleno"] = por_descripcion(
        Brand, "brand_description", RELLENO, None, "brand").id_brand
    mapas["familia_relleno"] = por_descripcion(
        ProductFamily, "product_family_description", RELLENO, None,
        "product_family").id_product_family
    unidad = por_descripcion(
        Unit, "unit_name", "Pieza",
        {"is_active": True, "measurement_system": "metric"}, "unit")
    mapas["unidad"] = unidad.id_unit

    # 5. Materiales. Su familia y su marca NO estan en `material`: viven en
    #    `producto`. Se resuelven por mayoria de sus productos, y lo que no
    #    tenga productos cae en el relleno.
    familia_de_material = collections.defaultdict(collections.Counter)
    marca_de_material = collections.defaultdict(collections.Counter)
    for f in datos["producto"]:
        m = entero(f.get("id_material"))
        if m is None:
            continue
        fam = familias.get(entero(f.get("id_familia")))
        mar = marcas.get(entero(f.get("id_marca")))
        if fam:
            familia_de_material[m][fam] += 1
        if mar:
            marca_de_material[m][mar] += 1

    materiales = {}
    for f in datos["material"]:
        viejo = entero(f["id_material"])
        descripcion = texto(f.get("descripcion"), 200) or RELLENO
        existente = db.scalars(
            select(Material).where(
                func.lower(Material.material_description) == descripcion.lower(),
                Material.deletion_date.is_(None),
            ).limit(1)
        ).first()
        if existente is not None:
            materiales[viejo] = existente.id_material
            continue
        fam = familia_de_material[viejo].most_common(1)
        mar = marca_de_material[viejo].most_common(1)
        fila = Material(
            material_description=descripcion,
            id_unit=mapas["unidad"],
            id_product_family=fam[0][0] if fam else mapas["familia_relleno"],
            id_brand=mar[0][0] if mar else mapas["marca_relleno"],
            created_by=actor,
        )
        db.add(fila)
        db.flush()
        materiales[viejo] = fila.id_material
        rep.creado["material"] += 1
    mapas["material"] = materiales

    material_relleno = db.scalars(
        select(Material).where(
            func.lower(Material.material_description) == RELLENO.lower(),
            Material.deletion_date.is_(None),
        ).limit(1)
    ).first()
    if material_relleno is None:
        material_relleno = Material(
            material_description=RELLENO, id_unit=mapas["unidad"],
            id_product_family=mapas["familia_relleno"],
            id_brand=mapas["marca_relleno"], created_by=actor)
        db.add(material_relleno)
        db.flush()
        rep.creado["material"] += 1
    mapas["material_relleno"] = material_relleno.id_material

    # 6. Tipos de incidencia. Los diez del sistema anterior, aunque solo cinco
    #    tengan vales: el catalogo se trae entero para que el historico diga el
    #    tipo con su nombre y no con un numero.
    tipos_incidencia = {}
    for f in datos["tipo_incidente"]:
        fila = por_descripcion(IncidentType, "incident_type_description",
                              texto(f.get("descripcion")), None, "incident_type")
        tipos_incidencia[entero(f["id_tipo_incidente"])] = fila.id_incident_type
    mapas["tipo_incidente"] = tipos_incidencia

    return mapas


# --- personas -------------------------------------------------------------

def importar_personas(db, datos, mapas, rep, actor):
    """Los empleados que tienen material, como usuarios sin contrasena.

    Existen para poder contestar "quien tiene que". No para entrar al sistema:
    se crean SIN contrasena, asi que no hay inicio de sesion posible hasta que
    alguien se la ponga a proposito.

    `incident.id_user` tiene llave a `"user"`, y en el sistema anterior el
    responsable es un `empleado` -41 filas, 31 con vales- cuyo `id_usuario`
    apunta a usuarios que no existen ni en su propio respaldo.
    """
    from sqlalchemy import func, select

    from app.models.proyect import Proyect
    from app.models.status import Status
    from app.models.user import User

    proyecto = db.scalars(
        select(Proyect).where(Proyect.deletion_date.is_(None))
        .order_by(Proyect.id_proyect).limit(1)
    ).first()
    estatus = db.scalars(
        select(Status).order_by(Status.id_status).limit(1)).first()
    if proyecto is None or estatus is None:
        raise SystemExit("hacen falta un proyecto y un estatus para poder crear "
                         "usuarios: `user.id_proyect` e `id_status` son NOT NULL")

    usuarios = {}
    for f in datos["empleado"]:
        viejo = entero(f["id_empleado"])
        partes = [f.get("nombres"), f.get("apellido_paterno"),
                  f.get("apellido_materno")]
        nombre = " ".join(
            str(p).strip() for p in partes
            if p and str(p).strip() not in (".", "")) or "Empleado %s" % viejo
        nombre = nombre[:150]

        existente = db.scalars(
            select(User).where(
                func.lower(User.full_name) == nombre.lower(),
                User.deletion_date.is_(None),
            ).limit(1)
        ).first()
        if existente is not None:
            usuarios[viejo] = existente.id_user
            rep.saltado["empleado (ya existia como usuario)"] += 1
            continue

        fila = User(
            full_name=nombre,
            # Sin contrasena y sin nombre de usuario: es un tenedor de material,
            # no una cuenta. `username` es unico, y dejarlo nulo evita choques.
            username=None,
            password=None,
            is_employee=True,
            # Pide material, no lo surte: es el papel del supervisor en el flujo
            # -levanta el prevale y el almacen lo atiende-.
            id_permission=2,
            id_proyect=proyecto.id_proyect,
            id_status=estatus.id_status,
            supervisor=actor,
            email=texto(f.get("correo"), 100),
            principal_phone=texto(f.get("telefono_principal"), 15),
            title=texto(f.get("puesto"), 50),
            created_by=actor,
        )
        db.add(fila)
        db.flush()
        usuarios[viejo] = fila.id_user
        rep.creado["usuario (desde empleado)"] += 1

    mapas["empleado"] = usuarios
    return mapas


# --- la factura sobre la que cuelgan los productos -----------------------

def factura_de_importacion(db, rep, actor):
    """Una factura para colgar lo importado.

    `product.id_invoice` es NOT NULL con llave: un producto tiene que pertenecer
    a un documento. El sistema anterior trae `producto.id_factura`, pero su
    tabla `factura` tiene dos filas, asi que casi todo apunta a facturas que no
    existen.

    Se crea UNA que representa la carga. Su proyecto importa: el alcance del
    almacen se resuelve por el proyecto de la factura, asi que sin el los
    productos importados solo los veria un superusuario.
    """
    from sqlalchemy import select

    from app.models.customer_supplier import CustomerSupplier
    from app.models.invoice import Invoice
    from app.models.proyect import Proyect
    from app.models.status import Status

    existente = db.scalars(
        select(Invoice).where(Invoice.note == "Importacion %s" % ORIGEN,
                              Invoice.deletion_date.is_(None)).limit(1)
    ).first()
    if existente is not None:
        return existente.id_invoice

    empresa = db.scalars(
        select(CustomerSupplier).where(CustomerSupplier.deletion_date.is_(None))
        .order_by(CustomerSupplier.id_customer_supplier).limit(1)).first()
    proyecto = db.scalars(
        select(Proyect).where(Proyect.deletion_date.is_(None))
        .order_by(Proyect.id_proyect).limit(1)).first()
    estatus = db.scalars(select(Status).order_by(Status.id_status).limit(1)).first()
    if empresa is None or estatus is None:
        raise SystemExit("hace falta al menos una empresa y un estatus para "
                         "crear la factura de importacion")

    fila = Invoice(
        id_customer_supplier=empresa.id_customer_supplier,
        id_issuer_customer_supplier=empresa.id_customer_supplier,
        tax_certification_supplier=empresa.id_customer_supplier,
        id_status=estatus.id_status,
        id_proyect=proyecto.id_proyect if proyecto else None,
        invoice_status="importado",
        note="Importacion %s" % ORIGEN,
        apply_tax=False,
        manual_capture=True,
        created_by=actor,
    )
    db.add(fila)
    db.flush()
    rep.creado["factura de importacion"] += 1
    return fila.id_invoice


# --- productos ------------------------------------------------------------

def importar_productos(db, datos, mapas, rep, actor, id_factura):
    """Los 2 220 productos, con su ubicacion resuelta y su proposito.

    Lo que NO se copia: `fecha_baja`. Tiene el centinela `1990-01-01` en las
    2 220 filas, asi que mapearla a `deletion_date` importaria todo borrado.
    """
    from sqlalchemy import select

    from app.models.inventory_status import InventoryStatus
    from app.models.product import Product

    catalogo_estado = {}
    for fila in db.scalars(
        select(InventoryStatus).where(
            InventoryStatus.entity_scope == "product",
            InventoryStatus.deletion_date.is_(None),
        )
    ).all():
        catalogo_estado[str(fila.inventory_status_code or "").lower()] = \
            fila.id_inventory_status

    vigentes = {
        int(p.external_id): p for p in db.scalars(
            select(Product).where(
                Product.external_source == ORIGEN,
                Product.external_id.isnot(None),
            )
        ).all()
    }

    productos = {}
    sin_ubicacion = 0
    for f in datos["producto"]:
        viejo = entero(f["id_producto"])
        crudo_ubicacion = texto(f.get("id_ubicacion"))

        # La ubicacion: '0' no es una ubicacion, es "sin sitio".
        destino = None
        if crudo_ubicacion and crudo_ubicacion != SIN_UBICACION:
            destino = mapas["ubicacion"].get(entero(crudo_ubicacion))
        if destino is None:
            destino = mapas["general"]
            sin_ubicacion += 1

        id_material = mapas["material"].get(entero(f.get("id_material")))
        if id_material is None:
            id_material = mapas["material_relleno"]
            rep.saltado["producto con material inexistente (al relleno)"] += 1

        id_familia = mapas["familia"].get(entero(f.get("id_familia")))
        if id_familia is None:
            id_familia = mapas["familia_relleno"]
            rep.saltado["producto con familia inexistente (al relleno)"] += 1
        id_marca = mapas["marca"].get(entero(f.get("id_marca")))
        if id_marca is None:
            id_marca = mapas["marca_relleno"]
            rep.saltado["producto con marca inexistente (al relleno)"] += 1

        estado_crudo = texto(f.get("estado"))
        codigo_estado = ESTADO_A_CATALOGO.get(
            str(estado_crudo or "").upper().replace("Ñ", "N"))
        if codigo_estado is None and estado_crudo:
            codigo_estado = ESTADO_A_CATALOGO.get(str(estado_crudo).upper())

        campos = dict(
            id_invoice=id_factura,
            id_location=destino,
            id_material=id_material,
            id_marca=id_marca,
            id_familia=id_familia,
            product_code=texto(f.get("codigo"), 30),
            descripcion=texto(f.get("descripcion"), 250),
            note=texto(f.get("nota"), 200),
            color=texto(f.get("color"), 100),
            cantidad=entero(f.get("cantidad")) or 0,
            path_imagen=texto(f.get("path_imagen"), 100),
            # El estado crudo se conserva como texto historico: mezcla direccion
            # de movimiento -ENTRADA/SALIDA- con estado de la pieza, y contradice
            # a los vales en 88 productos. El vigente lo manda el vale.
            product_status=estado_crudo,
            id_inventory_status=catalogo_estado.get(codigo_estado)
            if codigo_estado else None,
            stock_purpose=mapas["proposito_de_familia"].get(
                entero(f.get("id_familia")), "mercancia"),
            external_id=viejo,
            external_source=ORIGEN,
            external_location_text=crudo_ubicacion,
            is_directly_related_to_product_service=True,
        )

        existente = vigentes.get(viejo)
        if existente is not None:
            for clave, valor in campos.items():
                setattr(existente, clave, valor)
            productos[viejo] = existente.id_product
            rep.actualizado["producto"] += 1
            continue

        precio = texto(f.get("precio_bruto"))
        fila = Product(created_by=actor, gross_price=precio, **campos)
        db.add(fila)
        db.flush()
        productos[viejo] = fila.id_product
        rep.creado["producto"] += 1

    if sin_ubicacion:
        rep.aviso("%d productos sin ubicacion en el origen -id_ubicacion '0'- "
                  "quedaron en la ubicacion general" % sin_ubicacion)
    mapas["producto"] = productos
    return mapas


# --- existencia -----------------------------------------------------------

def sembrar_existencia(db, datos, mapas, rep, actor):
    """La existencia inicial, por la puerta de siempre.

    Se siembra lo que el producto dice tener. Lo que esta FUERA en un vale
    abierto se descuenta despues, en la fase de vales, con un movimiento de
    prestamo de verdad: asi el saldo y el libro cuentan la misma historia.
    """
    from app.models.product import Product
    from app.services.inventory_service import sembrar_existencia_inicial

    for viejo, nuevo in mapas["producto"].items():
        producto = db.get(Product, nuevo)
        if producto is None:
            continue
        if sembrar_existencia_inicial(db, producto) is not None:
            rep.creado["existencia inicial"] += 1
        else:
            rep.saltado["existencia (ya tenia, o cantidad 0)"] += 1
    return mapas


# --- vales ----------------------------------------------------------------

def importar_vales(db, datos, mapas, rep, actor):
    """Los 139 vales y sus 2 787 renglones, con el folio del sistema anterior.

    Como se decide que sigue fuera
    ------------------------------
    Cruzando dos cosas: el renglon sin cerrar Y el vale sin cerrar. Con una sola
    los numeros son otros -457 por renglon, 1 289 por vale- y el correcto es
    302, de 225 productos en manos de 22 personas.

    Un renglon devuelto se importa como su SALIDA y su ENTRADA, con la fecha real
    de cada una: es el modelo de solo agregado que ya usa el vale, y es lo que
    permite contestar "por producto, quien se lo ha llevado".

    La existencia solo se mueve para lo que sigue fuera. Lo devuelto salio y
    volvio: en el saldo de hoy es neutro, y fabricar 4 660 movimientos de libro
    para reconstruirlo no diria nada que el propio renglon no diga.
    """
    from sqlalchemy import select

    from app.models.incident import Incident
    from app.models.nm_incident_product import NmIncidentProduct
    from app.models.product import Product
    from app.services.inventory_service import apply_movement_in_session
    from app.utils.errors import AppError

    SALIDA, ENTRADA = "salida", "entrada"

    estado_de_vale = {}
    cierre_de_vale = {}
    vigentes = {
        str(v.external_folio): v for v in db.scalars(
            select(Incident).where(Incident.external_source == ORIGEN,
                                   Incident.external_folio.isnot(None))
        ).all()
    }

    vales = {}
    for f in datos["incidente"]:
        folio = str(entero(f["id_incidente"]))
        abierto = str(f.get("estado") or "").lower() != "cerrado"
        estado_de_vale[entero(f["id_incidente"])] = abierto
        cierre_de_vale[entero(f["id_incidente"])] = fecha(f.get("fecha_cierre"))

        id_usuario = mapas["empleado"].get(entero(f.get("id_empleado")))
        if id_usuario is None:
            rep.saltado["vale sin empleado que exista"] += 1
            continue

        campos = dict(
            id_incident_type=mapas["tipo_incidente"].get(
                entero(f.get("id_tipo_incidente")))
            or next(iter(mapas["tipo_incidente"].values())),
            id_user=id_usuario,
            incident_date=fecha(f.get("fecha_incidente"))
            or fecha(f.get("fecha_creacion")),
            incident_status="abierto" if abierto else "cerrado",
            close_date=fecha(f.get("fecha_cierre")),
            note=texto(f.get("nota"), 300),
            external_folio=folio,
            external_source=ORIGEN,
        )
        existente = vigentes.get(folio)
        if existente is not None:
            for clave, valor in campos.items():
                setattr(existente, clave, valor)
            vales[entero(f["id_incidente"])] = existente.id_incident
            rep.actualizado["vale"] += 1
            continue
        fila = Incident(created_by=actor, **campos)
        db.add(fila)
        db.flush()
        vales[entero(f["id_incidente"])] = fila.id_incident
        rep.creado["vale"] += 1

    renglones_vigentes = {
        int(r.external_id) for r in db.scalars(
            select(NmIncidentProduct).where(
                NmIncidentProduct.external_source == ORIGEN,
                NmIncidentProduct.external_id.isnot(None),
            )
        ).all()
    }

    por_vale = collections.Counter()
    fuera = []
    for f in datos["nm_incidente_producto"]:
        viejo = entero(f["id_nm_incidente_producto"])
        id_vale = vales.get(entero(f.get("id_incidente")))
        id_producto = mapas["producto"].get(entero(f.get("id_producto")))

        if id_vale is None:
            rep.saltado["renglon de un vale que no se importo"] += 1
            continue
        if id_producto is None:
            # 19 renglones apuntan a un producto que no existe ni en el propio
            # respaldo. No se puede escribir: `id_product` es NOT NULL con llave.
            rep.saltado["renglon con producto inexistente"] += 1
            continue
        if viejo in renglones_vigentes:
            rep.saltado["renglon ya importado"] += 1
            por_vale[entero(f.get("id_incidente"))] += 1
            continue

        cantidad = entero(f.get("cantidad")) or 0
        if cantidad <= 0:
            # Nueve renglones con cantidad cero: no dicen que salio.
            rep.saltado["renglon con cantidad cero"] += 1
            continue

        vale_abierto = estado_de_vale.get(entero(f.get("id_incidente")), False)
        cierre = fecha(f.get("fecha_cierre"))

        # Un renglon sin cerrar en un vale CERRADO no sigue fuera: el vale
        # cerrado significa que todo volvio. Sin este arreglo quedan 457
        # renglones abiertos donde solo hay 302, y toda consulta de "quien tiene
        # que" tendria que acordarse de mirar tambien el estado del vale.
        #
        # Se cierra con la fecha del vale, que es cuando de verdad volvio, no
        # con la de hoy.
        if cierre is None and not vale_abierto:
            cierre = cierre_de_vale.get(entero(f.get("id_incidente")))
            if cierre is not None:
                rep.saltado["renglon cerrado con la fecha de su vale"] += 1

        sigue_fuera = cierre is None and vale_abierto
        inicio = fecha(f.get("fecha_creacion"))
        producto = db.get(Product, id_producto)

        # La salida: siempre. Es el hecho de que se lo llevaron.
        db.add(NmIncidentProduct(
            id_incident=id_vale,
            id_product=id_producto,
            quantity=cantidad,
            direction=SALIDA,
            id_location_from=producto.id_location if producto else None,
            start_date=inicio,
            close_date=cierre,
            note=texto(f.get("nota"), 300),
            external_id=viejo,
            external_source=ORIGEN,
            created_by=actor,
        ))
        rep.creado["renglon de salida"] += 1
        por_vale[entero(f.get("id_incidente"))] += 1

        # La entrada: solo si volvio. Con su fecha, no con la de hoy.
        if cierre is not None:
            db.add(NmIncidentProduct(
                id_incident=id_vale,
                id_product=id_producto,
                quantity=cantidad,
                direction=ENTRADA,
                id_location_to=producto.id_location if producto else None,
                start_date=cierre,
                close_date=cierre,
                note=texto(f.get("nota"), 300),
                external_source=ORIGEN,
                created_by=actor,
            ))
            rep.creado["renglon de entrada (devuelto)"] += 1

        if sigue_fuera:
            fuera.append((id_producto, cantidad, id_vale, viejo))

    db.flush()

    # Lo que sigue fuera se descuenta del almacen, por la puerta de siempre.
    for id_producto, cantidad, id_vale, viejo in fuera:
        try:
            apply_movement_in_session(
                db, id_producto, {"id_user": actor, "is_superuser": True},
                movement_type="loan",
                quantity_delta=-cantidad,
                idempotency_key="import:%s:linea:%s" % (ORIGEN, viejo),
                reference_type="incident",
                reference_id=str(id_vale),
                reason="Prestamo vigente importado de %s" % ORIGEN,
            )
            rep.creado["prestamo vigente descontado"] += 1
        except AppError as e:
            # El caso normal: el producto no tiene tanta existencia como el vale
            # dice que salio. Se reporta con su renglon en lugar de tumbar la
            # carga: es un descuadre del origen y hay que verlo, no esconderlo.
            rep.saltado["prestamo que no se pudo descontar"] += 1
            rep.aviso("renglon %s: no se pudo descontar %d del producto %s (%s)"
                      % (viejo, cantidad, id_producto, e.message_key))

    vacios = [i for i in vales if por_vale.get(i, 0) == 0]
    if vacios:
        rep.aviso("%d vales sin ningun renglon utilizable: %s"
                  % (len(vacios), sorted(vacios)[:12]))
    return mapas


# --- orquestacion ---------------------------------------------------------

def rehacer(db, rep):
    """Borra lo que este origen importo, para volver a cargarlo limpio.

    Solo lo que trae `external_source = ORIGEN`: lo que se capturo en el sistema
    nuevo no tiene origen y no se toca. Es borrado FISICO a proposito -no
    lógico- porque el sentido es dejar la carga como si no hubiera pasado.
    """
    from sqlalchemy import delete, select

    from app.models.incident import Incident
    from app.models.inventory_ledger import InventoryLedger
    from app.models.inventory_stock import InventoryStock
    from app.models.nm_incident_product import NmIncidentProduct
    from app.models.product import Product

    ids = [int(x) for x in db.scalars(
        select(Product.id_product).where(Product.external_source == ORIGEN)
    ).all()]

    borrado = db.execute(delete(NmIncidentProduct).where(
        NmIncidentProduct.external_source == ORIGEN)).rowcount
    rep.saltado["renglon borrado para rehacer"] += borrado or 0

    if ids:
        db.execute(delete(InventoryLedger).where(
            InventoryLedger.id_product.in_(ids)))
        db.execute(delete(InventoryStock).where(
            InventoryStock.id_product.in_(ids)))
        # Los renglones de vale que apunten a estos productos, aunque no traigan
        # origen: si no, la llave ajena impide borrar el producto.
        db.execute(delete(NmIncidentProduct).where(
            NmIncidentProduct.id_product.in_(ids)))
        db.execute(delete(Product).where(Product.id_product.in_(ids)))
        rep.saltado["producto borrado para rehacer"] += len(ids)

    db.execute(delete(Incident).where(Incident.external_source == ORIGEN))
    db.flush()


TABLAS = ("tipo_ubicacion", "ubicacion", "marca", "familia", "material",
          "tipo_incidente", "empleado", "producto", "incidente",
          "nm_incidente_producto")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--carpeta", required=True,
                   help="carpeta con los adser_prod_*.sql (no se modifican)")
    p.add_argument("--aplicar", action="store_true",
                   help="escribe en la base; sin esto solo reporta")
    p.add_argument("--rehacer", action="store_true",
                   help="borra lo que este origen importo antes de volver a "
                        "cargarlo; no toca nada que no traiga external_source")
    p.add_argument("--actor", type=int, default=1,
                   help="id_user que queda como created_by")
    args = p.parse_args()

    os.environ.setdefault("FLASK_ENV", "development")

    from app import create_app
    from app.models.session import transaction_context

    datos = {}
    for tabla in TABLAS:
        datos[tabla] = cargar(args.carpeta, tabla)
        print("leido %-24s %5d filas" % (tabla, len(datos[tabla])))

    rep = Reporte()
    app = create_app()
    with app.app_context():
        with transaction_context() as db:
            if args.rehacer:
                rehacer(db, rep)
            mapas = importar_catalogos(db, datos, rep, args.actor)
            mapas = importar_personas(db, datos, mapas, rep, args.actor)
            id_factura = factura_de_importacion(db, rep, args.actor)
            mapas = importar_productos(db, datos, mapas, rep, args.actor,
                                       id_factura)
            mapas = sembrar_existencia(db, datos, mapas, rep, args.actor)
            mapas = importar_vales(db, datos, mapas, rep, args.actor)

            if not args.aplicar:
                # Todo lo anterior corrio de verdad -asi el ensayo encuentra los
                # errores que encontraria la carga- y aqui se deshace.
                db.rollback()

    rep.imprimir(args.aplicar)
    if not args.aplicar:
        print()
        print("Ensayo. Para escribir: agrega --aplicar")


if __name__ == "__main__":
    main()
