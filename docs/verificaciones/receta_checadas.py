"""Verificacion MANUAL de los KPIs de checadas contra una base real. Corre DENTRO del contenedor del backend.

    python receta_checadas.py sembrar      # 4 personas, 2 equipos y 4 checadas marcadas
    python receta_checadas.py verificar    # llama a las consultas REALES y compara con lo esperado (solo lectura)
    python receta_checadas.py limpiar      # borra todo lo marcado y confirma que quedo en cero

Lee docs/verificaciones/README.md antes de correrlo: la variante recomendada es sobre una COPIA de la base.

Marca de todo lo que siembra: incident.note = 'VERIF-CHECADAS'; personas 990001-990004; equipos 990001-990002.
Las horas se calculan con `ahora_negocio()` (la hora de pared de GMT-6 que usa el codigo), no con la del sistema.
Lo esperado se calcula con Python puro a partir de lo sembrado, asi que no depende de a que hora lo corras.

Seguridad: cada subcomando imprime en que base va a trabajar. Si la variable `RECETA_BASE_ESPERADA` esta definida y la base real es otra, el script se
niega a seguir (asi, si un `-e DB_NAME=...` no surte efecto, no escribe en la base equivocada).

Importarlo no hace nada: no abre conexiones ni escribe; todo ocurre dentro de `main()`.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.kpis.modulos import checadas as K
from app.models.session import engine, transaction_context
from app.utils.tiempo import ahora_negocio

MARCA = "VERIF-CHECADAS"
UNO, DOS, SIN, LARGA = 990001, 990002, 990003, 990004      # personas
NORTE, SUR = 990001, 990002                                 # equipos
PERSONAS = {UNO: "VERIF en un equipo", DOS: "VERIF en dos equipos", SIN: "VERIF sin equipo", LARGA: "VERIF cerrada de 17 h"}
EQUIPOS = {NORTE: "VERIF Parque Norte", SUR: "VERIF Parque Sur"}
MEMBRESIAS = [(NORTE, UNO), (NORTE, DOS), (SUR, DOS), (SUR, LARGA)]    # SIN no esta en ninguno


def checadas_sembradas(ahora):
    """(persona, entrada, salida|None, descripcion): el diseno de la prueba, relativo a `ahora`."""
    return [
        (UNO, ahora - timedelta(hours=2), None, "abierta de 2 h"),
        (DOS, ahora - timedelta(hours=13), None, "abierta de 13 h"),
        (SIN, ahora - timedelta(hours=2), None, "abierta de 2 h (sin equipo)"),
        (LARGA, ahora - timedelta(hours=18), ahora - timedelta(hours=1), "cerrada de 17 h"),
    ]


def confirmar_base():
    """Imprime la base en la que va a trabajar y se niega si no es la que `RECETA_BASE_ESPERADA` dice."""
    base, host = engine.url.database, engine.url.host
    print(f"base de datos: {base} (host {host})")
    esperada = os.environ.get("RECETA_BASE_ESPERADA")
    if esperada and esperada != base:
        sys.exit(f"ABORTADO: se esperaba la base '{esperada}' y la conexion apunta a '{base}'. No se hizo nada.")


def sembrar():
    confirmar_base()
    ahora = ahora_negocio()
    print(f"hora de pared GMT-6 (ahora_negocio): {ahora}   |   UTC real: {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}")
    with transaction_context() as db:
        ya = db.execute(text("select count(*) from incident where note = :m"), {"m": MARCA}).scalar()
        if ya:
            sys.exit(f"Ya hay {ya} checadas marcadas: corre `limpiar` primero.")
        for id_user, nombre in PERSONAS.items():
            db.execute(text('insert into "user" (id_user, full_name, username, is_employee) values (:i, :n, :u, true)'),
                       {"i": id_user, "n": nombre, "u": f"verif-checadas-{id_user}"})
        for id_team, nombre in EQUIPOS.items():
            db.execute(text("insert into team (id_team, team_description) values (:i, :n)"), {"i": id_team, "n": nombre})
        for id_team, id_user in MEMBRESIAS:
            db.execute(text("insert into nm_team_user (id_team, id_user) values (:t, :u)"), {"t": id_team, "u": id_user})
        for id_user, entrada, salida, _ in checadas_sembradas(ahora):
            db.execute(text(
                "insert into incident (incident_date, close_date, id_user, created_by, incident_status, latitude, longitude, distance_m, note) "
                "values (:e, :s, :u, :u, :st, 21.1161741, -101.6625754, 9, :m)"),
                {"e": entrada, "s": salida, "u": id_user, "st": "abierta" if salida is None else "resuelta", "m": MARCA})
    print("Sembrado: 4 personas, 2 equipos, 4 checadas. Ahora corre `verificar`.")


def _consulta(fn, inicio, fin):
    with transaction_context() as db:
        return fn(db, inicio, fin, {}, None)


def verificar():
    confirmar_base()
    ahora = ahora_negocio()
    hoy = ahora.date()
    with transaction_context() as db:
        filas = db.execute(text("select id_user, incident_date, close_date from incident where note = :m order by id_incident"), {"m": MARCA}).all()
    if len(filas) != 4:
        sys.exit(f"Se esperaban 4 checadas marcadas y hay {len(filas)}: corre `sembrar`.")
    reales = {id_user: (e, s) for id_user, e, s in filas}            # lo que quedo guardado, no lo que se pidio
    equipos_de = {UNO: [NORTE], DOS: [NORTE, SUR], SIN: [], LARGA: [SUR]}
    resultados = []

    def comprobar(nombre, esperado, obtenido, mayor_o_igual=False):
        bien = isinstance(obtenido, (int, float)) and (obtenido >= esperado if mayor_o_igual else obtenido == esperado)
        resultados.append(bien)
        print(f"  {'OK ' if bien else 'MAL'} {nombre:58s} esperado {'>=' if mayor_o_igual else '  '}{esperado!s:8} obtenido {obtenido!s}")

    def por_equipo(filas_kpi):
        return {e: v for e, f, v in filas_kpi if f == hoy}

    print(f"\nahora_negocio() = {ahora}  (hoy = {hoy}); tope de duracion = {K.TOPE_DURACION_CHECADA_HORAS} h; umbral sin salida = {K.UMBRAL_SIN_SALIDA_HORAS} h")

    abierta = {u: e for u, (e, s) in reales.items() if s is None}
    edad_h = lambda u: (ahora - abierta[u]).total_seconds() / 3600
    en_turno = {u for u in abierta if edad_h(u) < K.UMBRAL_SIN_SALIDA_HORAS}
    sin_salida = {u for u in abierta if edad_h(u) >= K.UMBRAL_SIN_SALIDA_HORAS}

    print("\n1) Fotos por equipo (checadas_en_turno_por_equipo / checadas_sin_salida_por_equipo)")
    for nombre, fn, quienes in (("en turno", K.checadas_en_turno_por_equipo_query, en_turno), ("sin salida", K.checadas_sin_salida_por_equipo_query, sin_salida)):
        foto = por_equipo(_consulta(fn, hoy, hoy))
        for id_team, etiqueta in ((NORTE, "Norte"), (SUR, "Sur")):
            comprobar(f"{nombre}: {etiqueta}", len([u for u in quienes if id_team in equipos_de[u]]), foto.get(id_team, 0))
        # Sin equipo: la fila existe siempre (entidad None); si la base ya tenia otras checadas de gente sin equipo, sera mayor.
        comprobar(f"{nombre}: «Sin equipo»", len([u for u in quienes if not equipos_de[u]]), foto.get(None, "NO HAY FILA"), mayor_o_igual=True)

    print("\n2) Entradas y salidas del dia (checadas_entradas_por_equipo / checadas_salidas_por_equipo) para hoy")
    entradas = por_equipo(_consulta(K.checadas_entradas_por_equipo_query, hoy, hoy))
    salidas = por_equipo(_consulta(K.checadas_salidas_por_equipo_query, hoy, hoy))
    for id_team, etiqueta in ((NORTE, "Norte"), (SUR, "Sur")):
        comprobar(f"entradas de hoy: {etiqueta}", sum(1 for u, (e, s) in reales.items() if e.date() == hoy and id_team in equipos_de[u]), entradas.get(id_team, 0))
        comprobar(f"salidas de hoy: {etiqueta}", sum(1 for u, (e, s) in reales.items() if s and s.date() == hoy and id_team in equipos_de[u]), salidas.get(id_team, 0))
    comprobar("entradas de hoy: «Sin equipo»", sum(1 for u, (e, s) in reales.items() if e.date() == hoy and not equipos_de[u]), entradas.get(None, "NO HAY FILA"), mayor_o_igual=True)
    comprobar("salidas de hoy: «Sin equipo»", sum(1 for u, (e, s) in reales.items() if s and s.date() == hoy and not equipos_de[u]), salidas.get(None, "NO HAY FILA"), mayor_o_igual=True)

    print("\n3) Tiempo en turno por empleado (checadas_en_turno_por_empleado), en minutos")
    por_persona = {u: float(v) for u, f, v in _consulta(K.checadas_en_turno_por_empleado_query, hoy, hoy)}
    for u in (UNO, DOS, SIN, LARGA):
        if u in en_turno:
            esperado = (ahora - abierta[u]).total_seconds() / 60
            obtenido = por_persona.get(u, "NO HAY FILA")
            bien = isinstance(obtenido, float) and abs(obtenido - esperado) <= 2      # unos segundos entre sembrar y verificar
        else:
            # Fuera de turno: fila en 0 o sin fila (solo salen en 0 quienes tuvieron una checada desde 12 h antes de que empezara hoy).
            esperado = 0.0
            obtenido = por_persona.get(u, "sin fila")
            bien = obtenido in (0.0, "sin fila")
        resultados.append(bien)
        print(f"  {'OK ' if bien else 'MAL'} {PERSONAS[u]:58s} esperado ~{esperado:7.1f}   obtenido {obtenido}")
    print("     (quien ya no esta en turno sale en 0: la API lo omite por `ocultar_ceros`, la consulta no)")

    print("\n4) Cerrada de mas de 16 h: horas (excluye) y anomalia (cuenta, por el dia de la SALIDA)")
    entrada, salida = reales[LARGA]
    desde = min(entrada.date(), hoy) - timedelta(days=1)
    horas = {(u, f): float(v) for u, f, v in _consulta(K.horas_trabajadas_por_empleado_query, desde, hoy)}
    anomalas = {(u, f): v for u, f, v in _consulta(K.checadas_con_duracion_anomala_query, desde, hoy)}
    comprobar("horas trabajadas de la persona de 17 h (no debe sumar)", 0, sum(v for (u, _), v in horas.items() if u == LARGA))
    comprobar(f"anomalias de la persona de 17 h el dia de la salida ({salida.date()})", 1, anomalas.get((LARGA, salida.date()), 0))
    comprobar(f"anomalias de la persona de 17 h el dia de la ENTRADA ({entrada.date()})", 0 if entrada.date() != salida.date() else 1,
              anomalas.get((LARGA, entrada.date()), 0))

    print(f"\nRESULTADO: {sum(resultados)}/{len(resultados)} OK" + ("" if all(resultados) else "   <-- hay MAL: revisa antes de confiar"))


def limpiar():
    confirmar_base()
    ids_u, ids_t = tuple(PERSONAS), tuple(EQUIPOS)
    with transaction_context() as db:
        db.execute(text("delete from incident where note = :m"), {"m": MARCA})
        db.execute(text("delete from nm_team_user where id_team = any(:t)"), {"t": list(ids_t)})
        db.execute(text("delete from team where id_team = any(:t)"), {"t": list(ids_t)})
        db.execute(text('delete from "user" where id_user = any(:u)'), {"u": list(ids_u)})
    with transaction_context() as db:
        quedan = {
            "checadas marcadas": db.execute(text("select count(*) from incident where note = :m"), {"m": MARCA}).scalar(),
            "personas 99000x": db.execute(text('select count(*) from "user" where id_user = any(:u)'), {"u": list(ids_u)}).scalar(),
            "equipos 99000x": db.execute(text("select count(*) from team where id_team = any(:t)"), {"t": list(ids_t)}).scalar(),
            "membresias": db.execute(text("select count(*) from nm_team_user where id_team = any(:t)"), {"t": list(ids_t)}).scalar(),
        }
    print("Despues de limpiar:", quedan, "-> OK" if not any(quedan.values()) else "-> QUEDAN FILAS")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    accion = {"sembrar": sembrar, "verificar": verificar, "limpiar": limpiar}.get(argv[0] if argv else "")
    if accion is None:
        sys.exit(__doc__)
    accion()


if __name__ == "__main__":
    main()
