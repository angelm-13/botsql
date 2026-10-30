"""Datos de PRUEBA para ver las checadas en el Dashboard (pestana «Asistencias»). Corre DENTRO del contenedor del backend.

    python receta_datos_demo.py sembrar      # 12 personas, 3 equipos y una semana de jornadas (idempotente)
    python receta_datos_demo.py snapshots    # corre el job frecuente y el nocturno para poblar kpi_snapshot
    python receta_datos_demo.py verificar    # compara lo sembrado contra las consultas reales y la API (no escribe)
    python receta_datos_demo.py limpiar      # borra lo marcado PRUEBA y deja los snapshots como si nunca hubiera existido

Lee docs/verificaciones/README.md: la variante recomendada es probar primero sobre una COPIA (`tyakxa_verif`).

Guardia. Cada subcomando imprime en que base va a trabajar y se NIEGA a seguir salvo que TODO esto sea cierto:
  * la base es `tyakxa_erp` o `tyakxa_verif` (la copia de prueba; ninguna otra);
  * el host es `db`, el servicio del docker-compose local (un `kubectl port-forward` llegaria como `localhost`: no pasa);
  * el proceso no corre dentro de un pod (`KUBERNETES_SERVICE_HOST` no esta definida);
  * si `RECETA_BASE_ESPERADA` esta definida, la base real coincide con ella.

Marca. TODO lo que crea lleva el prefijo «PRUEBA »: personas (`full_name` «PRUEBA ...», `username` `prueba.NN`), equipos, el rol «PRUEBA sin permisos»,
el tipo de incidencia «PRUEBA checador» y cada checada (`incident.note` «PRUEBA jornada ...»). La unica tabla sin texto, `nm_team_user`, se reconoce por
pertenecer a una persona o a un equipo PRUEBA. `limpiar` borra solo eso.

Lo que se siembra es la forma que entienden HOY los siete KPIs de `app/kpis/modulos/checadas.py`: una checada es una fila de `incident` con `latitude`,
`incident_date` = entrada y `close_date` = salida en hora de pared GMT-6 (sin zona), `creation_date`/`last_update_date` y las fechas de membresia en UTC. Sin pausas.
Las coordenadas son ficticias (un punto redondo), no un lugar real. Todo se ancla a `ahora_negocio()`: «hoy» es el dia del negocio, no el del contenedor.

Una checada abierta cambia de categoria con el tiempo (en turno -> sin salida a las 12 h). Para volver a anclar todo a «ahora», corre `sembrar` otra vez.

Importarlo no hace nada: no abre conexiones ni escribe; todo ocurre dentro de `main()`.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

import jwt
from sqlalchemy import text

from app.kpis.dimensiones import SIN_ASIGNAR
from app.models.session import engine, transaction_context
from app.utils.tiempo import ahora_negocio, hoy_negocio, pared_a_utc

PREFIJO = "PRUEBA "
BASES_PERMITIDAS = ("tyakxa_erp", "tyakxa_verif")
HOST_COMPOSE = "db"
ROL = "PRUEBA sin permisos"
TIPO = "PRUEBA checador"
NOTA = "PRUEBA jornada "
LATITUD, LONGITUD = Decimal("19.0000000"), Decimal("-99.0000000")    # ficticias: un punto redondo, no un sitio real
UMBRAL_SIN_SALIDA = timedelta(hours=12)                              # los mismos valores de checadas.py; aqui se repiten a proposito: lo esperado
TOPE_DURACION = timedelta(hours=16)                                  # sale del diseno, no de la implementacion que se esta verificando
DIAS = 7                                                             # una semana: hace 6 dias ... hoy

KPIS = (
    "checadas_en_turno_por_equipo", "checadas_sin_salida_por_equipo", "checadas_entradas_por_equipo", "checadas_salidas_por_equipo",
    "horas_trabajadas_por_empleado", "checadas_en_turno_por_empleado", "checadas_con_duracion_anomala",
)

EQUIPOS = {"T1": "PRUEBA Manzanillo 1", "T2": "PRUEBA Culiacán prueba", "T3": "PRUEBA Parque 3"}

# clave: (nombre, (hora, minuto) de entrada, minutos de jornada, dias de descanso entre «hace 6 dias» y «hace 1 dia»).
# Los dias de descanso son distintos entre personas para que las barras de cada dia no sean iguales.
PERSONAS = {
    "U01": ("PRUEBA Persona 01", (7, 0), 480, (5,)),
    "U02": ("PRUEBA Persona 02", (7, 10), 480, (4,)),
    "U03": ("PRUEBA Persona 03", (7, 20), 495, (3,)),
    "U04": ("PRUEBA Persona 04", (8, 0), 480, (2,)),
    "U05": ("PRUEBA Persona 05", (8, 0), 510, (1,)),
    "U06": ("PRUEBA Persona 06", (8, 15), 480, (6,)),
    "U07": ("PRUEBA Persona 07", (9, 0), 480, (5, 1)),
    "U08": ("PRUEBA Persona 08", (9, 10), 540, (4, 2)),
    "U09": ("PRUEBA Persona 09", (9, 20), 480, (6, 3)),
    "U10": ("PRUEBA Persona 10 (cambia de equipo)", (7, 45), 480, (5,)),
    "U11": ("PRUEBA Persona 11 (sin equipo)", (8, 30), 480, (1,)),
    "U12": ("PRUEBA Persona 12 (dos equipos)", (8, 45), 480, (2,)),
}

# (persona, equipo, alta, baja): alta/baja = (dias_antes_de_hoy, hora, minuto) en hora de pared, o None = sigue vigente.
# La persona 10 pasa de T1 a T2 a las 09:00 de «hace 3 dias» (baja logica con fecha en el pasado + membresia NUEVA); la 11 no tiene equipo;
# la 12 esta en dos equipos a la vez.
MEMBRESIAS = (
    ("U01", "T1", (8, 0, 0), None), ("U02", "T1", (8, 0, 0), None), ("U03", "T1", (8, 0, 0), None),
    ("U04", "T2", (8, 0, 0), None), ("U05", "T2", (8, 0, 0), None), ("U06", "T2", (8, 0, 0), None),
    ("U07", "T3", (8, 0, 0), None), ("U08", "T3", (8, 0, 0), None), ("U09", "T3", (8, 0, 0), None),
    ("U10", "T1", (8, 0, 0), (3, 9, 0)), ("U10", "T2", (3, 9, 0), None),
    ("U12", "T1", (8, 0, 0), None), ("U12", "T3", (8, 0, 0), None),
)
CREACION_DE_EQUIPOS = (9, 0, 0)

# Lo de HOY, relativo a ahora (minutos atras): persona -> (clave, entrada hace N min, salida hace N min o None = abierta).
HOY = {
    "U01": ("hoy-en-turno", 180, None),         # 3 h abierta: en turno
    "U02": ("hoy-sin-salida", 780, None),       # 13 h abierta: sin salida
    "U03": ("hoy-en-turno", 360, None),
    "U04": ("hoy-en-turno", 300, None),
    "U06": ("hoy-ya-salio", 540, 60),           # 8 h trabajadas, ya salio
    "U08": ("hoy-sin-salida", 780, None),
    "U09": ("hoy-ya-salio", 480, 30),           # 7 h 30 min trabajadas
    "U10": ("hoy-en-turno", 240, None),
    "U11": ("hoy-en-turno", 120, None),
    "U12": ("hoy-en-turno", 60, None),
}                                               # U05 y U07 descansan hoy

# Jornadas con horas fijas: (persona, clave, entrada, salida), cada una (dias_antes, hora, minuto).
ESPECIALES = (
    ("U05", "anomala", (3, 8, 0), (2, 10, 30)),            # 26 h 30 min: salida olvidada y capturada despues (> 16 h)
    ("U10", "dia-del-cambio", (3, 8, 20), (3, 17, 0)),     # entra a las 08:20 (T1, antes de las 09:00) y sale a las 17:00 (T2)
)


# --- el diseno, en hora de pared ------------------------------------------------------------------

def momento(ahora: datetime, dias_antes: int, hora: int, minuto: int) -> datetime:
    return datetime.combine(ahora.date() - timedelta(days=dias_antes), time(hora, minuto))


def _se_traslapa(entrada, salida, otras, ahora) -> bool:
    return any(entrada < (fin or ahora) and salida > ini for ini, fin in otras)


def jornadas(ahora: datetime) -> list[tuple[str, str, datetime, datetime | None]]:
    """`[(persona, clave, entrada, salida o None)]`: lo de hoy, las dos jornadas especiales y los dias normales sin traslapes."""
    filas = []
    for persona, (clave, hace_entrada, hace_salida) in HOY.items():
        filas.append((persona, clave, ahora - timedelta(minutes=hace_entrada),
                      None if hace_salida is None else ahora - timedelta(minutes=hace_salida)))
    for persona, clave, (d1, h1, m1), (d2, h2, m2) in ESPECIALES:
        filas.append((persona, clave, momento(ahora, d1, h1, m1), momento(ahora, d2, h2, m2)))
    for persona, (_, (hora, minuto), duracion, descansa) in PERSONAS.items():
        for dias_antes in range(DIAS - 1, 0, -1):
            if dias_antes in descansa:
                continue
            entrada = momento(ahora, dias_antes, hora, minuto)
            salida = entrada + timedelta(minutes=duracion)
            propias = [(e, s) for p, _, e, s in filas if p == persona]
            if not _se_traslapa(entrada, salida, propias, ahora):
                filas.append((persona, f"D-{dias_antes}", entrada, salida))
    return sorted(filas, key=lambda f: (f[0], f[2]))


# --- guardia y utilerias --------------------------------------------------------------------------

def confirmar_base():
    base, host = engine.url.database, engine.url.host
    print(f"base de datos: {base} (host {host})")
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        sys.exit("ABORTADO: esto corre dentro de un pod. Esta receta es solo para el docker-compose local. No se hizo nada.")
    if host != HOST_COMPOSE:
        sys.exit(f"ABORTADO: el host debe ser '{HOST_COMPOSE}' (el del compose local) y es '{host}'. No se hizo nada.")
    if base not in BASES_PERMITIDAS:
        sys.exit(f"ABORTADO: la base debe ser una de {BASES_PERMITIDAS} y es '{base}'. No se hizo nada.")
    esperada = os.environ.get("RECETA_BASE_ESPERADA")
    if esperada and esperada != base:
        sys.exit(f"ABORTADO: se esperaba la base '{esperada}' y la conexion apunta a '{base}'. No se hizo nada.")


class Api:
    """El cliente de Flask de la aplicacion real, con un token de superusuario (igual que `receta_equipos.py`)."""

    def __init__(self):
        from app import create_app
        from app.utils.auth import SECRET_KEY
        self.cliente = create_app().test_client()
        self.cabecera = {"Authorization": "Bearer " + jwt.encode({"id_user": 1, "is_superuser": True}, SECRET_KEY, algorithm="HS256")}

    def __call__(self, metodo, ruta):
        respuesta = getattr(self.cliente, metodo.lower())(ruta, headers=self.cabecera)
        return respuesta.status_code, (respuesta.get_json(silent=True) if respuesta.data else None)


def _marcados(db):
    """`(usuarios {id: clave «U01»}, nombres {id: full_name}, equipos {id: descripcion})` de lo marcado PRUEBA."""
    filas = db.execute(text('select id_user, username, full_name from "user" where username like :u and full_name like :n order by id_user'),
                       {"u": "prueba.%", "n": PREFIJO + "%"}).all()
    equipos = {i: d for i, d in db.execute(text("select id_team, team_description from team where team_description like :n order by id_team"),
                                           {"n": PREFIJO + "%"})}
    return {i: "U" + u.split(".")[1] for i, u, _ in filas}, {i: n for i, _, n in filas}, equipos


def resumen(db) -> dict:
    usuarios, _, equipos = _marcados(db)
    ids_u, ids_t = list(usuarios) or [-1], list(equipos) or [-1]
    uno = lambda sql, **p: db.execute(text(sql), p).scalar()    # noqa: E731
    return {
        "permission (rol «PRUEBA sin permisos»)": uno("select count(*) from permission where permission_description = :d", d=ROL),
        "incident_type («PRUEBA checador»)": uno("select count(*) from incident_type where incident_type_description = :d", d=TIPO),
        "user": len(usuarios),
        "team": len(equipos),
        "nm_team_user vigentes": uno("select count(*) from nm_team_user where (id_user = any(:u) or id_team = any(:t)) and deletion_date is null", u=ids_u, t=ids_t),
        "nm_team_user de baja": uno("select count(*) from nm_team_user where (id_user = any(:u) or id_team = any(:t)) and deletion_date is not null", u=ids_u, t=ids_t),
        "incident abiertas": uno("select count(*) from incident where note like :n and close_date is null", n=NOTA + "%"),
        "incident cerradas": uno("select count(*) from incident where note like :n and close_date is not null", n=NOTA + "%"),
        "kpi_snapshot de personas/equipos PRUEBA": uno(
            "select count(*) from kpi_snapshot where (dimension_key->>'id_user') = any(:u) or (dimension_key->>'id_team') = any(:t)",
            u=[str(i) for i in ids_u], t=[str(i) for i in ids_t]),
    }


def imprimir_resumen(titulo, db):
    print(f"\n{titulo}")
    for tabla, n in resumen(db).items():
        print(f"  {tabla:46s} {n}")


# --- sembrar --------------------------------------------------------------------------------------

def _asegurar(db, tabla, columna_id, columna_texto, texto):
    """Id de la fila de `tabla` cuya `columna_texto` es `texto`; la crea (con los defaults de la tabla) si no existe. Solo crea filas PRUEBA."""
    if not texto.startswith(PREFIJO):
        raise AssertionError(f"no se crea nada sin el prefijo PRUEBA: {texto!r}")
    existe = db.execute(text(f"select {columna_id} from {tabla} where {columna_texto} = :t"), {"t": texto}).scalar()
    if existe is not None:
        return existe
    return db.execute(text(f"insert into {tabla} ({columna_texto}) values (:t) returning {columna_id}"), {"t": texto}).scalar()


def sembrar():
    confirmar_base()
    ahora = ahora_negocio().replace(microsecond=0)
    print(f"ahora (hora de pared GMT-6): {ahora}  |  semana: {(ahora - timedelta(days=DIAS - 1)).date()} ... {ahora.date()}")
    with transaction_context() as db:
        id_rol = _asegurar(db, "permission", "id_permission", "permission_description", ROL)
        id_tipo = _asegurar(db, "incident_type", "id_incident_type", "incident_type_description", TIPO)

        id_equipo = {}
        for clave, descripcion in EQUIPOS.items():
            id_equipo[clave] = _asegurar(db, "team", "id_team", "team_description", descripcion)
            # Se reancla en cada corrida y se revive si alguien lo dio de baja: sembrar deja SIEMPRE el mismo estado.
            db.execute(text("update team set creation_date = :c, last_update_date = :c, deletion_date = null where id_team = :i"),
                       {"c": pared_a_utc(momento(ahora, CREACION_DE_EQUIPOS[0], *CREACION_DE_EQUIPOS[1:])), "i": id_equipo[clave]})

        id_persona = {}
        for clave, (nombre, *_) in PERSONAS.items():
            username = "prueba." + clave[1:]
            id_existente = db.execute(text('select id_user, full_name from "user" where username = :u'), {"u": username}).first()
            if id_existente is not None and not id_existente[1].startswith(PREFIJO):
                sys.exit(f"ABORTADO: ya existe un usuario '{username}' que NO es de PRUEBA. No se toca.")
            creacion = pared_a_utc(momento(ahora, CREACION_DE_EQUIPOS[0], 0, 0))
            if id_existente is None:
                id_persona[clave] = db.execute(text(
                    'insert into "user" (full_name, username, is_employee, user_type, id_permission, creation_date) '
                    "values (:n, :u, true, 'employee', :r, :c) returning id_user"),
                    {"n": nombre, "u": username, "r": id_rol, "c": creacion}).scalar()
            else:
                id_persona[clave] = id_existente[0]
                db.execute(text('update "user" set full_name = :n, id_permission = :r, creation_date = :c, deletion_date = null where id_user = :i'),
                           {"n": nombre, "r": id_rol, "c": creacion, "i": id_existente[0]})

        # Membresias y checadas se rehacen enteras (no tienen nada que las referencie): asi no quedan filas viejas si cambia el diseno.
        ids_u = list(id_persona.values())
        db.execute(text("delete from nm_team_user where id_user = any(:u)"), {"u": ids_u})
        db.execute(text("delete from incident where note like :n and id_user = any(:u)"), {"n": NOTA + "%", "u": ids_u})
        for persona, equipo, alta, baja in MEMBRESIAS:
            alta_utc = pared_a_utc(momento(ahora, *alta))
            db.execute(text("insert into nm_team_user (id_team, id_user, creation_date, last_update_date, deletion_date) values (:t, :u, :a, :a, :b)"),
                       {"t": id_equipo[equipo], "u": id_persona[persona], "a": alta_utc,
                        "b": None if baja is None else pared_a_utc(momento(ahora, *baja))})
        todas = jornadas(ahora)
        for i, (persona, clave, entrada, salida) in enumerate(todas):
            db.execute(text(
                "insert into incident (incident_date, close_date, id_incident_type, note, id_user, incident_status, created_by, creation_date, last_update_date, "
                "latitude, longitude, distance_m) values (:e, :s, :tipo, :n, :u, :st, :u, :c, :m, :lat, :lon, :d)"),
                {"e": entrada, "s": salida, "tipo": id_tipo, "n": f"{NOTA}{persona} {clave}", "u": id_persona[persona],
                 "st": "abierta" if salida is None else "resuelta", "c": pared_a_utc(entrada), "m": pared_a_utc(salida or entrada),
                 "lat": LATITUD, "lon": LONGITUD, "d": Decimal(3 + (i * 7) % 40)})
        imprimir_resumen("Sembrado (filas marcadas PRUEBA por tabla):", db)
    print("\nListo. Siguiente: `snapshots` (poblar kpi_snapshot) y `verificar`.")


# --- snapshots ------------------------------------------------------------------------------------

def snapshots():
    confirmar_base()
    from app.jobs.tasks_kpis import _recalcular_kpi_snapshots_en_sesion, recalculate_kpi_snapshots, recalculate_kpi_snapshots_frecuentes
    print("job frecuente (hoy; fotos y entradas/salidas):", recalculate_kpi_snapshots_frecuentes())
    print("job nocturno (ventana de 7 dias, todos los KPIs):", recalculate_kpi_snapshots())
    hoy = hoy_negocio()
    desde = hoy - timedelta(days=DIAS - 1)
    # La ventana del nocturno es `date.today() - 6 ... date.today()`: si el contenedor y el negocio no estan en el mismo dia (UTC cerca de las 18:00 de
    # Mexico) pierde el primer dia de la semana. Se completa solo con los siete KPIs de checadas, sobre el rango de la semana.
    with transaction_context() as db:
        filas = _recalcular_kpi_snapshots_en_sesion(db, desde, hoy, claves=list(KPIS))
    print(f"relleno de la semana completa ({desde} ... {hoy}) solo para los siete KPIs de checadas: {filas} filas (idempotente)")
    with transaction_context() as db:
        imprimir_resumen("Despues de los jobs:", db)


# --- verificar ------------------------------------------------------------------------------------

def _leer(db):
    usuarios, nombres, equipos = _marcados(db)
    membresias = [(u, t, a, b) for u, t, a, b in db.execute(text(
        "select id_user, id_team, creation_date, deletion_date from nm_team_user where id_user = any(:u) or id_team = any(:t)"),
        {"u": list(usuarios) or [-1], "t": list(equipos) or [-1]})]
    checadas = [(u, e, s) for u, e, s in db.execute(text(
        "select id_user, incident_date, close_date from incident where note like :n and deletion_date is null and latitude is not null order by id_incident"),
        {"n": NOTA + "%"})]
    return usuarios, nombres, equipos, membresias, checadas


def esperado(equipos, membresias, checadas, ahora):
    """Lo que DEBEN dar los siete KPIs, calculado con Python puro a partir de lo sembrado y de las reglas del diseno."""
    hoy = ahora.date()
    dias = [hoy - timedelta(days=i) for i in range(DIAS - 1, -1, -1)]

    def equipos_en(persona, instante):
        t = pared_a_utc(instante)
        return sorted(eq for p, eq, alta, baja in membresias if p == persona and alta <= t and (baja is None or t < baja)) or [None]

    def equipos_hoy(persona):
        return sorted(eq for p, eq, _, baja in membresias if p == persona and baja is None) or [None]

    entradas = {(eq, d): 0 for eq in list(equipos) + [None] for d in dias}
    salidas = {(eq, d): 0 for eq in list(equipos) + [None] for d in dias}
    horas, anomalas = defaultdict(Decimal), defaultdict(int)
    en_turno, sin_salida = {eq: set() for eq in list(equipos) + [None]}, {eq: set() for eq in list(equipos) + [None]}
    turno_empleado = {}
    for persona, entrada, salida in checadas:
        if entrada.date() in dias:
            for eq in equipos_en(persona, entrada):
                entradas[(eq, entrada.date())] += 1
        if salida is not None:
            if salida.date() in dias:
                for eq in equipos_en(persona, salida):
                    salidas[(eq, salida.date())] += 1
            if salida >= entrada:
                if salida - entrada > TOPE_DURACION:
                    if salida.date() in dias:
                        anomalas[(persona, salida.date())] += 1
                elif entrada.date() in dias:
                    horas[(persona, entrada.date())] += Decimal((salida - entrada).total_seconds()) / 60
        else:
            abierta_menos_de_12h = entrada > ahora - UMBRAL_SIN_SALIDA
            for eq in equipos_hoy(persona):
                (en_turno if abierta_menos_de_12h else sin_salida)[eq].add(persona)
            if abierta_menos_de_12h:
                minutos = Decimal((ahora - entrada).total_seconds()) / 60
                turno_empleado[persona] = min(turno_empleado.get(persona, minutos), minutos)    # la entrada mas reciente = los menos minutos
    return {
        "dias": dias,
        "entradas": entradas, "salidas": salidas,
        "horas": {k: v.quantize(Decimal("0.01")) for k, v in horas.items()}, "anomalas": dict(anomalas),
        "en_turno_equipo": {eq: len(p) for eq, p in en_turno.items()}, "sin_salida_equipo": {eq: len(p) for eq, p in sin_salida.items()},
        "turno_empleado": turno_empleado,
    }


def verificar():
    confirmar_base()
    ahora = ahora_negocio()
    hoy, desde = ahora.date(), ahora.date() - timedelta(days=DIAS - 1)
    resultados = []

    def comprobar(nombre, ok, detalle=""):
        resultados.append(ok)
        print(f"  {'OK ' if ok else 'MAL'} {nombre}" + ("" if ok else f"\n      {detalle}"))

    with transaction_context() as db:
        usuarios, nombres, equipos, membresias, checadas = _leer(db)
        ids_kpi = {clave: i for clave, i in db.execute(text("select clave, id_kpi_definition from kpi_definition where clave = any(:c)"), {"c": list(KPIS)})}
    if len(usuarios) != len(PERSONAS) or len(equipos) != len(EQUIPOS) or not checadas:
        sys.exit(f"Se esperaban {len(PERSONAS)} personas, {len(EQUIPOS)} equipos y checadas PRUEBA y hay {len(usuarios)}, {len(equipos)} y {len(checadas)}: corre `sembrar`.")
    clave_de = usuarios
    esp = esperado(equipos, membresias, checadas, ahora)
    nombre_equipo = {**equipos, None: "Sin equipo"}

    print("\n1) Lo que DEBE mostrar cada KPI (calculado de lo sembrado, con Python puro)")
    por_equipo = lambda d: " | ".join(f"{nombre_equipo[eq]} = {n}" for eq, n in sorted(d.items(), key=lambda kv: (kv[0] is None, kv[0])))    # noqa: E731
    print(f"  Personas en turno por equipo (foto de ahora)    {por_equipo(esp['en_turno_equipo'])}")
    print(f"  Personas sin salida por equipo (foto de ahora)  {por_equipo(esp['sin_salida_equipo'])}")
    for titulo, clave in (("Entradas por equipo, semana completa", "entradas"), ("Salidas por equipo, semana completa", "salidas")):
        total = defaultdict(int)
        for (eq, _), n in esp[clave].items():
            total[eq] += n
        print(f"  {titulo:48s}{por_equipo(total)}")
    por_persona = defaultdict(Decimal)
    for (u, _), m in esp["horas"].items():
        por_persona[u] += m
    print("  Tiempo trabajado por empleado, semana (minutos)  " + " | ".join(f"{clave_de[u]} = {por_persona[u]:.0f}" for u in sorted(usuarios) if por_persona.get(u)))
    print("  Tiempo en turno por empleado (minutos, ahora)    " + " | ".join(f"{clave_de[u]} = {m:.0f}" for u, m in sorted(esp["turno_empleado"].items())))
    print("  Checadas con duracion anomala (por dia de salida) " + (" | ".join(f"{clave_de[u]} el {d} = {n}" for (u, d), n in sorted(esp["anomalas"].items())) or "ninguna"))

    print("\n2) Las consultas REALES de checadas.py dan lo mismo")
    from app.kpis.modulos import checadas as K
    with transaction_context() as db:
        real_entradas = {(t, d): n for t, d, n in K.checadas_entradas_por_equipo_query(db, desde, hoy, {}, None)}
        real_salidas = {(t, d): n for t, d, n in K.checadas_salidas_por_equipo_query(db, desde, hoy, {}, None)}
        real_horas = {(u, d): m for u, d, m in K.horas_trabajadas_por_empleado_query(db, desde, hoy, {}, None) if u in usuarios}
        real_anomalas = {(u, d): n for u, d, n in K.checadas_con_duracion_anomala_query(db, desde, hoy, {}, None) if u in usuarios}
        real_turno_eq = {t: n for t, _, n in K.checadas_en_turno_por_equipo_query(db, desde, hoy, {}, None)}
        real_sin_eq = {t: n for t, _, n in K.checadas_sin_salida_por_equipo_query(db, desde, hoy, {}, None)}
        real_turno_emp = {u: m for u, _, m in K.checadas_en_turno_por_empleado_query(db, desde, hoy, {}, None) if u in usuarios}

    # «Sin equipo» se compara con >= (la base puede tener otras checadas de gente sin equipo); lo de cada equipo PRUEBA, exacto.
    def aparte(d):
        return {k: v for k, v in d.items() if k[0] in equipos}, {k: v for k, v in d.items() if k[0] is None}
    for nombre, esp_d, real_d in (("entradas por equipo y dia", esp["entradas"], real_entradas), ("salidas por equipo y dia", esp["salidas"], real_salidas)):
        e_eq, e_sin = aparte(esp_d)
        r_eq, r_sin = aparte(real_d)
        comprobar(f"{nombre} ({len(e_eq)} celdas de equipo, exactas)", {k: v for k, v in r_eq.items()} == e_eq,
                  f"diferencias: {({k: (e_eq.get(k), r_eq.get(k)) for k in set(e_eq) | set(r_eq) if e_eq.get(k) != r_eq.get(k)})}")
        comprobar(f"{nombre}, «Sin equipo» (>= lo sembrado)", all(r_sin.get(k, 0) >= v for k, v in e_sin.items()),
                  f"esperado >= {e_sin}, obtenido {r_sin}")
    comprobar("tiempo trabajado por empleado y dia (minutos, exacto)", real_horas == esp["horas"],
              f"diferencias: {({k: (esp['horas'].get(k), real_horas.get(k)) for k in set(esp['horas']) | set(real_horas) if esp['horas'].get(k) != real_horas.get(k)})}")
    comprobar("duracion anomala por empleado y dia", real_anomalas == esp["anomalas"], f"esperado {esp['anomalas']}, obtenido {real_anomalas}")
    for nombre, esp_d, real_d in (("personas en turno por equipo", esp["en_turno_equipo"], real_turno_eq), ("personas sin salida por equipo", esp["sin_salida_equipo"], real_sin_eq)):
        comprobar(f"{nombre} (equipos PRUEBA, exacto)", {t: real_d.get(t) for t in equipos} == {t: esp_d[t] for t in equipos},
                  f"esperado {({t: esp_d[t] for t in equipos})}, obtenido {({t: real_d.get(t) for t in equipos})}")
        comprobar(f"{nombre}, «Sin equipo» (>= lo sembrado)", real_d.get(None, 0) >= esp_d[None], f"esperado >= {esp_d[None]}, obtenido {real_d.get(None)}")
    minutos_ok = all(abs(float(real_turno_emp.get(u, 0)) - float(esp["turno_empleado"].get(u, 0))) < 2 for u in usuarios)
    comprobar("tiempo en turno por empleado (minutos, +-2 min por los segundos entre las dos lecturas)", minutos_ok,
              f"esperado {esp['turno_empleado']}, obtenido {real_turno_emp}")

    print("\n3) La API real (kpi_snapshot/query), como la lee el Dashboard")
    api = Api()
    estado, cuerpo = api("GET", f"/kpi_snapshot/query?id_kpi_definition={ids_kpi['checadas_en_turno_por_equipo']}&fecha_inicio={desde}&fecha_fin={hoy}")
    if estado != 200 or not cuerpo["rango_a"]["por_empleado"]:
        print("  (sin snapshots de hoy: corre `snapshots` y vuelve a verificar; el resto de esta seccion se omite)")
    else:
        def consulta(clave):
            e, c = api("GET", f"/kpi_snapshot/query?id_kpi_definition={ids_kpi[clave]}&fecha_inicio={desde}&fecha_fin={hoy}")
            assert e == 200, (clave, e, c)
            return c["rango_a"]
        def por_equipo_api(rango):
            return {t: rango["por_empleado"].get(str(t)) for t in equipos}, rango["por_empleado"].get(SIN_ASIGNAR, 0)
        for clave, esp_d in (("checadas_en_turno_por_equipo", esp["en_turno_equipo"]), ("checadas_sin_salida_por_equipo", esp["sin_salida_equipo"])):
            eq, sin = por_equipo_api(consulta(clave))
            comprobar(f"{clave}: equipos PRUEBA exactos y «Sin equipo» >=", eq == {t: float(esp_d[t]) for t in equipos} and sin >= esp_d[None], f"obtenido {eq}, sin equipo {sin}")
        for clave, esp_d in (("checadas_entradas_por_equipo", esp["entradas"]), ("checadas_salidas_por_equipo", esp["salidas"])):
            rango = consulta(clave)
            eq, sin = por_equipo_api(rango)
            suma = {t: float(sum(n for (e, _), n in esp_d.items() if e == t)) for t in equipos}
            comprobar(f"{clave}: total de la semana por equipo", eq == suma and sin >= sum(n for (e, _), n in esp_d.items() if e is None), f"esperado {suma}, obtenido {eq}")
            comprobar(f"{clave}: las etiquetas son los nombres PRUEBA", all(rango["etiquetas"].get(str(t)) == equipos[t] for t in equipos), f"{rango.get('etiquetas')}")
        rango = consulta("horas_trabajadas_por_empleado")
        suma = {u: float(sum(m for (p, _), m in esp["horas"].items() if p == u)) for u in usuarios}
        comprobar("horas_trabajadas_por_empleado: minutos de la semana por persona", {u: rango["por_empleado"].get(str(u), 0.0) for u in usuarios if suma[u]} == {u: v for u, v in suma.items() if v},
                  f"esperado {({clave_de[u]: v for u, v in suma.items() if v})}, obtenido {rango['por_empleado']}")
        rango = consulta("checadas_con_duracion_anomala")
        suma = {u: float(sum(n for (p, _), n in esp["anomalas"].items() if p == u)) for u in usuarios}
        comprobar("checadas_con_duracion_anomala: por persona", {u: rango["por_empleado"].get(str(u), 0.0) for u in usuarios} == suma, f"esperado {suma}, obtenido {rango['por_empleado']}")
        rango = consulta("checadas_en_turno_por_empleado")
        obtenido = {u: rango["por_empleado"].get(str(u), 0.0) for u in usuarios}
        comprobar("checadas_en_turno_por_empleado: minutos por persona (+-10 min: es la foto del ultimo job)",
                  all(abs(obtenido[u] - float(esp["turno_empleado"].get(u, 0))) < 10 for u in usuarios), f"esperado {esp['turno_empleado']}, obtenido {obtenido}")
        print("  (el detalle por dia de entradas/salidas y de horas se compara en la seccion 2; aqui, el total que dibuja cada barra)")

    print(f"\nRESULTADO: {sum(resultados)}/{len(resultados)} OK" + ("" if all(resultados) else "   <-- hay MAL: revisa antes de confiar"))


# --- limpiar --------------------------------------------------------------------------------------

def limpiar():
    confirmar_base()
    with transaction_context() as db:
        usuarios, _, equipos = _marcados(db)
        ids_u, ids_t = list(usuarios) or [-1], list(equipos) or [-1]
        ajenas = db.execute(text("select count(*) from incident where id_user = any(:u) and (note is null or note not like :n)"),
                            {"u": ids_u, "n": NOTA + "%"}).scalar()
        if ajenas:
            sys.exit(f"ABORTADO: hay {ajenas} incidencias que NO son de PRUEBA a nombre de personas PRUEBA. No se borra nada: revisa o reasigna esas filas.")
        desde, hasta = db.execute(text("select min(date(incident_date)), max(date(coalesce(close_date, incident_date))) from incident where note like :n"),
                                  {"n": NOTA + "%"}).one()
        borrados = {}
        # Los snapshots de PRUEBA (de CUALQUIER KPI: las incidencias de siempre tambien cuentan estas filas por responsable).
        borrados["kpi_snapshot"] = db.execute(text(
            "delete from kpi_snapshot where (dimension_key->>'id_user') = any(:u) or (dimension_key->>'id_team') = any(:t)"),
            {"u": [str(i) for i in ids_u], "t": [str(i) for i in ids_t]}).rowcount
        # Los de flujo por dia SIN desglose por persona ni equipo (p. ej. incidencias abiertas vs cerradas) tampoco traen el id de nadie, y el
        # upsert del job solo reescribe lo que la consulta devuelve: sin incidencias en esos dias, la fila vieja se quedaria pegada. Esos si se pueden
        # regenerar exactos desde los datos vivos (las fotos de «ahora» no), asi que se borran en el rango que ocuparon y se recalculan abajo.
        if desde is not None:
            from app.kpis.registry import KPI_REGISTRY
            flujos = [k.clave for k in KPI_REGISTRY if k.modulo == "operaciones" and k.modo == "snapshot"
                      and k.agregacion in ("suma", "promedio_ponderado") and k.dimensiones[0] not in ("empleado", "equipo")]
            borrados["kpi_snapshot (flujos globales)"] = db.execute(text(
                "delete from kpi_snapshot where periodo between :d and :h and id_kpi_definition in "
                "(select id_kpi_definition from kpi_definition where clave = any(:c))"), {"d": desde, "h": hasta, "c": flujos}).rowcount
        borrados["incident"] = db.execute(text("delete from incident where note like :n and id_user = any(:u)"), {"n": NOTA + "%", "u": ids_u}).rowcount
        borrados["nm_team_user"] = db.execute(text("delete from nm_team_user where id_user = any(:u) or id_team = any(:t)"), {"u": ids_u, "t": ids_t}).rowcount
        borrados["team"] = db.execute(text("delete from team where id_team = any(:t)"), {"t": ids_t}).rowcount
        borrados["user"] = db.execute(text('delete from "user" where id_user = any(:u)'), {"u": ids_u}).rowcount
        borrados["incident_type"] = db.execute(text(
            "delete from incident_type where incident_type_description = :d and not exists (select 1 from incident i where i.id_incident_type = incident_type.id_incident_type)"),
            {"d": TIPO}).rowcount
        con_permisos = db.execute(text(
            "select (select count(*) from entity_permission e join permission p using (id_permission) where p.permission_description = :d) "
            "+ (select count(*) from nm_field_permission f join permission p using (id_permission) where p.permission_description = :d)"), {"d": ROL}).scalar()
        if con_permisos:
            print(f"AVISO: el rol «{ROL}» tiene {con_permisos} permisos asignados (alguien los dio en el Gestor): no se borra el rol.")
            borrados["permission"] = 0
        else:
            borrados["permission"] = db.execute(text(
                'delete from permission where permission_description = :d and not exists (select 1 from "user" u where u.id_permission = permission.id_permission)'),
                {"d": ROL}).rowcount
    print("Filas borradas por tabla:", borrados)
    if desde is not None:
        # Las incidencias de siempre (y el «Sin equipo» de los KPIs de checadas) contaron estas filas: se vuelven a calcular los snapshots del modulo
        # `operaciones` en el rango que ocuparon, para que no quede ningun numero pegado. Es lo mismo que hace el job nocturno cada noche.
        from app.jobs.tasks_kpis import _recalcular_kpi_snapshots_en_sesion
        with transaction_context() as db:
            filas = _recalcular_kpi_snapshots_en_sesion(db, desde, max(hasta, hoy_negocio()), modulos=("operaciones",))
        print(f"snapshots de `operaciones` recalculados de {desde} a {max(hasta, hoy_negocio())} ({filas} filas): «Sin equipo» y las incidencias vuelven a lo real")
    with transaction_context() as db:
        quedan = resumen(db)
    print("Despues de limpiar:", quedan, "-> OK" if not any(quedan.values()) else "-> QUEDAN FILAS")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    accion = {"sembrar": sembrar, "snapshots": snapshots, "verificar": verificar, "limpiar": limpiar}.get(argv[0] if argv else "")
    if accion is None:
        sys.exit(__doc__)
    accion()


if __name__ == "__main__":
    main()
