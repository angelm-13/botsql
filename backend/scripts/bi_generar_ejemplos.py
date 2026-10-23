"""Genera el banco de ejemplos verificados (pregunta -> SQL) del modulo BI.

"Entrenar" al modelo con la base de tyakxa sin ajustar pesos: se arman cientos de
pares pregunta/SQL a partir del esquema REAL, se EJECUTAN contra la base y solo se
conservan los que corren sin error y devuelven datos. En produccion el modulo
recupera los mas parecidos a cada pregunta y se los muestra al modelo como ejemplos
(ver app/bi/ejemplos.py): un 3B imita bien un ejemplo del mismo esquema.

    python scripts/bi_generar_ejemplos.py --salida app/bi/ejemplos/verificados.jsonl

Plantillas por tabla: conteo, ultimos registros, agrupar por una columna categorica,
agrupar por la tabla padre (FK), total por mes y suma de una columna de importe/cantidad.
Cada SQL pasa por el mismo validador de seguridad que el de cualquier consulta.
"""

import argparse
import json
import re
import unicodedata

from sqlalchemy import create_engine, text

from app.bi import security
from app.bi.acceso import SOLO_ADMIN
from app.bi.config import AjustesBI
from app.bi.schema_extractor import extraer_esquema

# Nombre natural (plural, singular) de las tablas de negocio mas preguntadas.
ETIQUETAS = {
    "product": ("productos", "producto"), "material": ("materiales", "material"),
    "incident": ("vales", "vale"), "incident_type": ("tipos de vale", "tipo de vale"),
    "nm_incident_product": ("renglones de vales", "renglon de vale"),
    "proyect": ("proyectos", "proyecto"), "task": ("tareas", "tarea"), "task_type": ("tipos de tarea", "tipo de tarea"),
    "invoice": ("facturas", "factura"), "customer_supplier": ("clientes", "cliente"),
    "customer_contact": ("contactos", "contacto"), "user": ("usuarios", "usuario"),
    "location": ("ubicaciones", "ubicacion"), "inventory_stock": ("existencias", "existencia"),
    "movement": ("movimientos", "movimiento"), "ticket": ("tickets", "ticket"),
    "document": ("documentos", "documento"), "appointment": ("citas", "cita"),
    "payroll_period": ("periodos de nomina", "periodo de nomina"), "payroll_detail": ("recibos de nomina", "recibo de nomina"),
    "pos_sale": ("ventas del punto de venta", "venta del punto de venta"), "pos_sale_item": ("partidas de venta", "partida de venta"),
    "restaurant_order": ("pedidos del restaurante", "pedido del restaurante"), "restaurant_dish": ("platillos", "platillo"),
    "logistics_trip": ("viajes", "viaje"), "logistics_unit": ("unidades de transporte", "unidad de transporte"),
    "logistics_shipment": ("envios", "envio"), "logistics_quotation": ("cotizaciones de logistica", "cotizacion de logistica"),
    "laboratory_service_order": ("ordenes de laboratorio", "orden de laboratorio"),
    "laboratory_equipment": ("equipos de laboratorio", "equipo de laboratorio"),
    "bank_account": ("cuentas bancarias", "cuenta bancaria"), "bank": ("bancos", "banco"),
    "department": ("departamentos", "departamento"), "brand": ("marcas", "marca"), "unit": ("unidades de medida", "unidad de medida"),
    "status": ("estatus", "estatus"), "service": ("servicios", "servicio"), "notification": ("notificaciones", "notificacion"),
    "survey_question": ("preguntas de encuesta", "pregunta de encuesta"), "template": ("plantillas", "plantilla"),
    "kpi_definition": ("indicadores", "indicador"), "team": ("equipos de usuarios", "equipo de usuarios"),
    "pos_product_variant": ("variantes de producto", "variante de producto"),
    "inventory_lot": ("lotes de inventario", "lote de inventario"), "product_family": ("familias de producto", "familia de producto"),
}
# Otros nombres con los que la gente llama a lo mismo (se agregan como variantes de pregunta).
ALIAS = {
    "incident": ["incidencias", "prestamos", "movimientos de almacen"], "product": ["herramientas", "articulos"],
    "customer_supplier": ["proveedores", "clientes y proveedores"], "user": ["empleados", "personas"],
    "proyect": ["ordenes de trabajo", "obras"], "invoice": ["cobros", "comprobantes"], "task": ["actividades"],
    "nm_incident_product": ["herramientas de los vales", "renglones de los vales"], "movement": ["movimientos contables"],
    "location": ["almacenes", "racks"], "restaurant_order": ["comandas"], "pos_sale": ["ventas de mostrador", "tickets de venta"],
}
# Valores de estatus en ingles -> como los dice la gente.
VALOR_ES = {"draft": "borrador", "authorized": "autorizado", "in_progress": "en proceso", "waiting_material": "esperando material",
            "blocked": "bloqueado", "completed": "completado", "delivered": "entregado", "denied": "rechazado",
            "abierta": "abierto", "cerrada": "cerrado", "en_transito": "en transito", "en_espera": "en espera",
            "cancelado": "cancelado", "borrador": "borrador", "pendiente": "pendiente", "terminada": "terminado",
            "en_proceso": "en proceso", "alta": "alta", "media": "media", "baja": "baja"}
# Columnas id_* que apuntan a una tabla pero NO tienen llave foranea declarada.
SEUDO_FK = {"id_marca": "brand", "id_familia": "product_family", "id_unidad": "unit", "id_ubicacion": "location"}
COLUMNAS_ES = {"status": "estatus", "type": "tipo", "direction": "direccion", "currency": "moneda", "city": "ciudad",
               "priority": "prioridad", "category": "categoria", "stage": "etapa"}
ETIQUETA_PADRE = ("name", "full_name", "descripcion", "title", "product_code", "folio")
RUIDO = {"created_by", "creation_date", "last_update_date", "ajustado_por_gestor", "deletion_date"}


def norm(t: str) -> str:
    s = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def humano(nombre: str) -> str:
    return nombre.replace("_", " ")


def etiqueta(tabla: str):
    return ETIQUETAS.get(tabla, (humano(tabla) + "s", humano(tabla)))


def col_es(c: str) -> str:
    base = c.lower()
    for k, v in COLUMNAS_ES.items():
        if base == k or base.endswith("_" + k):
            return v
    return humano(re.sub(r"^id_", "", base))


def es_texto(t: str) -> bool:
    return any(k in t.upper() for k in ("CHAR", "TEXT"))


def es_num(t: str) -> bool:
    return any(k in t.upper() for k in ("INT", "NUM", "DEC", "FLOAT", "DOUBLE", "REAL"))


def es_fecha(t: str) -> bool:
    return any(k in t.upper() for k in ("DATE", "TIMESTAMP"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="app/bi/ejemplos/verificados.jsonl")
    ap.add_argument("--max-por-tabla", type=int, default=8)
    args = ap.parse_args()

    ajustes = AjustesBI.desde_entorno()
    engine = create_engine(ajustes.database_url)
    esquema = extraer_esquema(engine, ajustes)
    rels = {r.nombre.lower(): r for r in esquema.relaciones}
    permitidas = esquema.nombres

    def cuenta(tabla):
        with engine.connect() as c:
            return c.execute(text(f'SELECT COUNT(*) FROM "{tabla}"')).scalar() if tabla != "user" else c.execute(text('SELECT COUNT(*) FROM "user"')).scalar()

    def prueba(sql):
        """(ok, filas): valida con el validador real y ejecuta con tope de tiempo."""
        try:
            v = security.validar_sql(sql, permitidas, motor=esquema.motor, limite_maximo=1000,
                                     columnas_ocultas=ajustes.columnas_ocultas)
            with engine.connect() as c:
                c.execute(text("SET LOCAL statement_timeout = 5000"))
                filas = c.execute(text(v.sql)).fetchall()
            return True, len(filas)
        except Exception:
            return False, 0

    ejemplos = []

    def agregar(tipo, tablas, preguntas, sql, minimo=0):
        ok, n = prueba(sql)
        if ok and n >= minimo:
            ejemplos.append({"tipo": tipo, "tablas": sorted(set(tablas)), "preguntas": preguntas, "sql": sql, "filas": n})

    for nombre, r in sorted(rels.items()):
        if nombre in SOLO_ADMIN or r.es_vista or nombre.startswith(("bi_", "kpi_snapshot")):
            continue
        try:
            total = cuenta(nombre)
        except Exception:
            continue
        pl, sing = etiqueta(nombre)
        q = f'"{nombre}"' if nombre == "user" else nombre
        cols = {c.nombre.lower(): c for c in r.columnas}
        borrado = " WHERE deletion_date IS NULL" if "deletion_date" in cols else ""
        y_borrado = " AND deletion_date IS NULL" if "deletion_date" in cols else ""
        pk = next((c.nombre for c in r.columnas if c.es_pk), None)
        n_antes = len(ejemplos)

        # A. conteo
        agregar("conteo", [nombre], [f"cuantos {pl} hay", f"total de {pl}", f"numero de {pl} registrados"],
                f"SELECT COUNT(*) AS total_{nombre} FROM {q}{borrado}")

        # B. ultimos registros
        mostrar = [c.nombre for c in r.columnas if c.nombre.lower() not in RUIDO][:6]
        orden = next((c for c in ("creation_date", "date", "incident_date", "date_emision") if c in cols), None)
        orden = orden or (pk or mostrar[0])
        if mostrar:
            agregar("ultimos", [nombre], [f"ultimos {pl} registrados", f"muestrame los ultimos 10 {pl}", f"lista de {pl} recientes"],
                    f"SELECT {', '.join(mostrar)} FROM {q}{borrado} ORDER BY {orden} DESC LIMIT 10")

        # C. agrupar por columna categorica (texto con pocos valores)
        for c in r.columnas:
            if not es_texto(c.tipo) or c.es_pk or c.nombre.lower() in RUIDO:
                continue
            if not re.search(r"status|type|direction|currency|city|priority|category|stage|state", c.nombre.lower()):
                continue
            try:
                with engine.connect() as cx:
                    k = cx.execute(text(f'SELECT COUNT(DISTINCT "{c.nombre}") FROM {q}')).scalar()
            except Exception:
                continue
            if 2 <= (k or 0) <= 15:
                ces = col_es(c.nombre)
                agregar("agrupar", [nombre], [f"{pl} por {ces}", f"cuantos {pl} hay por {ces}", f"distribucion de {pl} segun {ces}"],
                        f"SELECT {c.nombre} AS {ces.replace(' ', '_')}, COUNT(*) AS total FROM {q}{borrado} "
                        f"GROUP BY {c.nombre} ORDER BY total DESC LIMIT 20")

        # D. agrupar por la tabla padre (FK)
        for c in r.columnas:
            if not c.fk:
                continue
            padre, _, pcol = str(c.fk).partition(".")
            pr = rels.get(padre.lower())
            if not pr or padre.lower() in SOLO_ADMIN or padre.lower() == nombre:
                continue
            etiq = next((x.nombre for e in ETIQUETA_PADRE for x in pr.columnas if x.nombre.lower() == e),
                        next((x.nombre for x in pr.columnas if es_texto(x.tipo) and not x.es_pk), None))
            if not etiq:
                continue
            ppl, psing = etiqueta(padre.lower())
            qp = f'"{padre}"' if padre.lower() == "user" else padre
            filtro = f" WHERE c.deletion_date IS NULL" if "deletion_date" in cols else ""
            base = (f"SELECT p.{etiq} AS {psing.replace(' ', '_')}, COUNT(*) AS total FROM {q} c "
                    f"JOIN {qp} p ON p.{pcol} = c.{c.nombre}{filtro} GROUP BY p.{etiq} ORDER BY total DESC")
            agregar("padre", [nombre, padre.lower()], [f"{pl} por {psing}", f"cuantos {pl} hay por {psing}", f"{pl} agrupados por {psing}"],
                    base + " LIMIT 200")
            agregar("padre_top", [nombre, padre.lower()], [f"que {psing} tiene mas {pl}", f"top 10 de {ppl} con mas {pl}"],
                    base + " LIMIT 10")

        # D2. columnas id_* sin llave foranea declarada (id_marca, id_familia...)
        for c in r.columnas:
            destino = SEUDO_FK.get(c.nombre.lower())
            if c.fk or not destino or destino not in rels or destino == nombre:
                continue
            pr = rels[destino]
            pk_p = next((x.nombre for x in pr.columnas if x.es_pk), None)
            etiq = next((x.nombre for x in pr.columnas if es_texto(x.tipo) and not x.es_pk and x.nombre.lower() not in RUIDO), None)
            if not pk_p or not etiq:
                continue
            ppl, psing = etiqueta(destino)
            filtro = " WHERE c.deletion_date IS NULL" if "deletion_date" in cols else ""
            base = (f"SELECT p.{etiq} AS {psing.replace(' ', '_')}, COUNT(*) AS total FROM {q} c "
                    f"JOIN {destino} p ON p.{pk_p} = c.{c.nombre}{filtro} GROUP BY p.{etiq} ORDER BY total DESC")
            agregar("padre", [nombre, destino], [f"{pl} por {psing}", f"cuantos {pl} hay por {psing}", f"{pl} agrupados por {psing}"], base + " LIMIT 200")
            agregar("padre_top", [nombre, destino], [f"que {psing} tiene mas {pl}"], base + " LIMIT 10")

        # E. por mes
        fecha = next((c.nombre for c in r.columnas if es_fecha(c.tipo) and c.nombre.lower() not in RUIDO), None) \
            or ("creation_date" if "creation_date" in cols else None)
        if fecha:
            agregar("mensual", [nombre], [f"{pl} por mes", f"cuantos {pl} se registraron cada mes", f"evolucion mensual de {pl}"],
                    f"SELECT date_trunc('month', {fecha})::date AS mes, COUNT(*) AS total FROM {q} "
                    f"WHERE {fecha} IS NOT NULL{y_borrado} GROUP BY 1 ORDER BY 1 LIMIT 36", minimo=2)

        # F. suma de columnas de importe o cantidad
        for c in r.columnas:
            if es_num(c.tipo) and re.search(r"^(total|amount|subtotal|cost|total_cost|quantity|cantidad|gross_price|credit_limit)$", c.nombre.lower()):
                ces = col_es(c.nombre)
                agregar("suma", [nombre], [f"total de {ces} de {pl}", f"suma de {ces} en {pl}"],
                        f"SELECT SUM({c.nombre}) AS suma_{c.nombre} FROM {q}{borrado}")

        # G. conteo por cada valor de una columna categorica ("cuantos proyectos estan entregados")
        for c in r.columnas:
            if not es_texto(c.tipo) or c.es_pk or c.nombre.lower() in RUIDO:
                continue
            if not re.search(r"status|type|direction|priority|category|stage|state", c.nombre.lower()):
                continue
            try:
                with engine.connect() as cx:
                    valores = [v[0] for v in cx.execute(text(
                        f'SELECT "{c.nombre}" FROM {q} WHERE "{c.nombre}" IS NOT NULL GROUP BY "{c.nombre}" '
                        f'ORDER BY COUNT(*) DESC LIMIT 6')).fetchall()]
            except Exception:
                continue
            ces = col_es(c.nombre)
            for v in valores:
                if not v or "'" in str(v) or len(str(v)) > 40:
                    continue
                ves = VALOR_ES.get(str(v), str(v).lower().replace("_", " "))
                agregar("valor", [nombre], [f"cuantos {pl} estan {ves}", f"cuantos {pl} tienen {ces} {ves}", f"numero de {pl} con {ces} {ves}"],
                        f"SELECT COUNT(*) AS total FROM {q} WHERE {c.nombre} = '{v}'{y_borrado}")

        # H. ventanas de tiempo
        if fecha:
            for ventana, cond, etiq_v in (("hoy", f"{fecha} >= date_trunc('day', now())", "hoy"),
                                          ("semana", f"{fecha} >= date_trunc('week', now())", "esta semana"),
                                          ("mes", f"{fecha} >= date_trunc('month', now())", "este mes"),
                                          ("ano", f"{fecha} >= date_trunc('year', now())", "este ano")):
                agregar("ventana", [nombre], [f"cuantos {pl} se registraron {etiq_v}", f"{pl} de {etiq_v}", f"numero de {pl} {etiq_v}"],
                        f"SELECT COUNT(*) AS total FROM {q} WHERE {cond}{y_borrado}")

        # I. promedio / maximo de columnas numericas de importe o cantidad
        for c in r.columnas:
            if es_num(c.tipo) and re.search(r"^(total|amount|subtotal|cost|total_cost|quantity|cantidad|gross_price|credit_limit)$", c.nombre.lower()):
                ces = col_es(c.nombre)
                agregar("promedio", [nombre], [f"promedio de {ces} por {sing}", f"cual es el promedio de {ces} de {pl}"],
                        f"SELECT AVG({c.nombre}) AS promedio_{c.nombre} FROM {q}{borrado}")
                etq = next((x.nombre for e in ETIQUETA_PADRE for x in r.columnas if x.nombre.lower() == e),
                           next((x.nombre for x in r.columnas if es_texto(x.tipo) and not x.es_pk), None))
                if etq:
                    agregar("maximo", [nombre], [f"cual es el {sing} con mas {ces}", f"{sing} con mayor {ces}"],
                            f"SELECT {etq} AS {sing.replace(' ', '_')}, {c.nombre} FROM {q}{borrado} ORDER BY {c.nombre} DESC NULLS LAST LIMIT 1")

        # variantes con los otros nombres de la tabla
        for e in ejemplos[n_antes:]:
            extra = []
            for alias in ALIAS.get(nombre, []):
                extra += [p.replace(pl, alias) for p in e["preguntas"] if pl in p]
            e["preguntas"] = e["preguntas"] + [p for p in extra if p not in e["preguntas"]]

        # tope por tabla
        prioridad = {'padre': 0, 'valor': 1, 'padre_top': 2, 'agrupar': 3, 'conteo': 4, 'maximo': 5, 'promedio': 5,
                     'suma': 6, 'mensual': 6, 'ventana': 7, 'ultimos': 8}
        nuevos = sorted(ejemplos[n_antes:], key=lambda e: (e['filas'] == 0, prioridad.get(e['tipo'], 9)))
        limite = {'ventana': 2, 'padre': 4, 'padre_top': 2, 'valor': 6, 'maximo': 2, 'promedio': 2, 'suma': 2}
        usados, conservados = {}, []
        for e in nuevos:
            usados[e['tipo']] = usados.get(e['tipo'], 0) + 1
            if usados[e['tipo']] <= limite.get(e['tipo'], 99):
                conservados.append(e)
        ejemplos[n_antes:] = conservados[:args.max_por_tabla]

    import os
    os.makedirs(os.path.dirname(args.salida) or ".", exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as fh:
        for i, e in enumerate(ejemplos, 1):
            fh.write(json.dumps({"id": i, **e}, ensure_ascii=False) + "\n")
    por_tipo = {}
    for e in ejemplos:
        por_tipo[e["tipo"]] = por_tipo.get(e["tipo"], 0) + 1
    print(f"{len(ejemplos)} ejemplos verificados en {len({t for e in ejemplos for t in e['tablas']})} tablas -> {args.salida}")
    print(por_tipo)


if __name__ == "__main__":
    main()
