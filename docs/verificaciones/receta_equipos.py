"""Verificacion MANUAL de los equipos con baja logica, la atribucion historica, el filtro por equipos y el titulo propio. Corre DENTRO del contenedor del backend.

    python receta_equipos.py sembrar              # 2 equipos, 1 persona que se mueve del uno al otro, 5 checadas, 1 tablero con 1 grafico
    python receta_equipos.py verificar            # API real + consultas reales, y compara con lo esperado (no escribe)
    python receta_equipos.py dar_de_baja_equipo   # da de baja «Culiacán prueba» POR LA API y comprueba que la historia sigue en pie
    python receta_equipos.py limpiar              # borra todo lo sembrado y confirma que quedo en cero

Lee docs/verificaciones/README.md antes de correrlo: la variante recomendada es sobre una COPIA de la base, no sobre `tyakxa_erp`.

Lo que hace `sembrar`, todo por la API real (cliente de Flask con un token de superusuario) salvo lo que la API no puede hacer:
  1. Crea los equipos «Manzanillo 1» y «Culiacán prueba».
  2. La persona 990101 entra a Manzanillo; se le da de baja de ahi (baja logica) y se le agrega a Culiacan (membresia NUEVA).
  3. Como todo eso acaba de pasar HOY, las fechas de las membresias se reescriben en SQL para que el cambio haya ocurrido a las 09:00 del dia
     "hace 2 dias" (la API no sabe viajar al pasado). Es lo unico que se escribe a mano.
  4. Siembra 5 checadas cerradas de esa persona en los 4 dias previos a hoy y recalcula los snapshots de los KPIs de checadas.
  5. Crea un tablero con un grafico de titulo propio.

Marca de lo que siembra: incident.note = 'VERIF-EQUIPOS', persona 990101, tablero 'VERIF-EQUIPOS'; los equipos se reconocen por nombre.
Los dias se calculan con `hoy_negocio()` (hora de pared GMT-6, la que usa el codigo), no con la hora del sistema; todas las marcas son de dias completos
del pasado, asi que no importa a que hora lo corras. Lo esperado sale del DISENO de abajo (lo que una persona esperaria), no de la implementacion.

Seguridad: cada subcomando imprime en que base va a trabajar. Si `RECETA_BASE_ESPERADA` esta definida y la base real es otra, el script se niega a seguir.

Importarlo no hace nada: no abre conexiones ni escribe; todo ocurre dentro de `main()`.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

import jwt
from sqlalchemy import text

from app.models.session import engine, transaction_context
from app.utils.tiempo import ahora_negocio, hoy_negocio, pared_a_utc

MARCA = "VERIF-EQUIPOS"
PERSONA = 990101
A, B = "Manzanillo 1", "Culiacán prueba"
TITULO = "Entradas de Manzanillo"

# El DISENO: (dias_antes_de_hoy, entrada, salida, equipo que se espera). La persona pasa de A a B a las 09:00 de "hace 2 dias".
HORA_DEL_CAMBIO = (9, 0)
DIA_DEL_CAMBIO = 2
DISENO = [
    (4, (10, 0), (18, 0), A),     # antes del cambio
    (3, (10, 0), (18, 0), A),
    (2, (8, 0), (8, 30), A),      # el dia del cambio, ANTES de las 09:00: sigue en A
    (2, (10, 0), (17, 0), B),     # el dia del cambio, DESPUES de las 09:00: ya es de B
    (1, (10, 0), (18, 0), B),
]


def dia(dias_antes: int):
    return hoy_negocio() - timedelta(days=dias_antes)


def local(dias_antes: int, hora_minuto) -> datetime:
    """Una hora de pared (sin zona) de hace `dias_antes` dias."""
    return datetime.combine(dia(dias_antes), datetime.min.time()).replace(hour=hora_minuto[0], minute=hora_minuto[1])


def minutos(entrada, salida) -> int:
    return (salida[0] * 60 + salida[1]) - (entrada[0] * 60 + entrada[1])


def confirmar_base():
    base, host = engine.url.database, engine.url.host
    print(f"base de datos: {base} (host {host})")
    esperada = os.environ.get("RECETA_BASE_ESPERADA")
    if esperada and esperada != base:
        sys.exit(f"ABORTADO: se esperaba la base '{esperada}' y la conexion apunta a '{base}'. No se hizo nada.")


class Api:
    """El cliente de Flask de la aplicacion real, con un token de superusuario."""

    def __init__(self):
        from app import create_app
        from app.utils.auth import SECRET_KEY
        self.cliente = create_app().test_client()
        self.cabecera = {"Authorization": "Bearer " + jwt.encode({"id_user": 1, "is_superuser": True}, SECRET_KEY, algorithm="HS256")}

    def __call__(self, metodo, ruta, json=None):
        respuesta = getattr(self.cliente, metodo.lower())(ruta, json=json, headers=self.cabecera)
        return respuesta.status_code, (respuesta.get_json(silent=True) if respuesta.data else None)


def _ids_de_equipos(db):
    return {nombre: id_team for id_team, nombre in db.execute(
        text("select id_team, team_description from team where team_description in (:a, :b) order by id_team"), {"a": A, "b": B})}


def _kpi(db, clave):
    return db.execute(text("select id_kpi_definition from kpi_definition where clave = :c"), {"c": clave}).scalar()


def sembrar():
    confirmar_base()
    api = Api()
    with transaction_context() as db:
        if db.execute(text("select count(*) from incident where note = :m"), {"m": MARCA}).scalar() or db.execute(
                text("select count(*) from team where team_description in (:a, :b) and deletion_date is null"), {"a": A, "b": B}).scalar():
            sys.exit("Ya hay checadas marcadas o equipos con esos nombres: corre `limpiar` primero (o usa otra copia).")
        db.execute(text('insert into "user" (id_user, full_name, username, is_employee) values (:i, :n, :u, true)'),
                   {"i": PERSONA, "n": "VERIF persona que cambia de equipo", "u": f"verif-equipos-{PERSONA}"})

    estado, a = api("POST", "/team/", {"team_description": A})
    estado_b, b = api("POST", "/team/", {"team_description": B})
    assert (estado, estado_b) == (201, 201), (estado, a, estado_b, b)
    print(f"equipos creados por la API: {A} = {a['id_team']}, {B} = {b['id_team']}")

    estado, en_a = api("POST", "/nm_team_user/", {"id_team": a["id_team"], "id_user": PERSONA})
    assert estado == 201, (estado, en_a)
    estado, _ = api("DELETE", f"/nm_team_user/{en_a['id_nm_team_user']}")
    assert estado == 200, estado
    estado, en_b = api("POST", "/nm_team_user/", {"id_team": b["id_team"], "id_user": PERSONA})
    assert estado == 201, (estado, en_b)
    print(f"la persona {PERSONA} pasa de {A} a {B}: membresia vieja {en_a['id_nm_team_user']} (de baja) y NUEVA {en_b['id_nm_team_user']}")

    cambio = pared_a_utc(local(DIA_DEL_CAMBIO, HORA_DEL_CAMBIO))
    with transaction_context() as db:
        # Lo unico que la API no puede: que todo esto haya pasado hace dias. Se reescriben las fechas de la membresia.
        db.execute(text("update nm_team_user set creation_date = :c, deletion_date = :d where id_nm_team_user = :i"),
                   {"c": pared_a_utc(local(4, (0, 0))), "d": cambio, "i": en_a["id_nm_team_user"]})
        db.execute(text("update nm_team_user set creation_date = :c where id_nm_team_user = :i"), {"c": cambio, "i": en_b["id_nm_team_user"]})
        db.execute(text("update team set creation_date = :c where id_team in (:a, :b)"), {"c": pared_a_utc(local(5, (0, 0))), "a": a["id_team"], "b": b["id_team"]})
        for dias_antes, entrada, salida, _ in DISENO:
            db.execute(text(
                "insert into incident (incident_date, close_date, id_user, created_by, incident_status, latitude, longitude, distance_m, note) "
                "values (:e, :s, :u, :u, 'resuelta', 21.1161741, -101.6625754, 9, :m)"),
                {"e": local(dias_antes, entrada), "s": local(dias_antes, salida), "u": PERSONA, "m": MARCA})
    print(f"cambio reescrito a las {HORA_DEL_CAMBIO[0]:02d}:{HORA_DEL_CAMBIO[1]:02d} del {dia(DIA_DEL_CAMBIO)}; {len(DISENO)} checadas sembradas")

    from app.jobs.tasks_kpis import _recalcular_kpi_snapshots_en_sesion
    with transaction_context() as db:
        filas = _recalcular_kpi_snapshots_en_sesion(
            db, dia(5), hoy_negocio(),
            claves=["checadas_entradas_por_equipo", "checadas_salidas_por_equipo", "horas_trabajadas_por_empleado"])
    print(f"snapshots recalculados ({filas} filas)")

    with transaction_context() as db:
        id_kpi = _kpi(db, "checadas_entradas_por_equipo")
    estado, tablero = api("POST", "/kpi_dashboard/", {"nombre": MARCA, "orden": 1})
    assert estado == 201, (estado, tablero)
    estado, widget = api("POST", f"/kpi_dashboard/{tablero['id_kpi_dashboard']}/widgets/", {
        "ids_kpi_definition": [id_kpi], "tipo_grafica": "barras",
        "parametros": {"fecha_inicio": str(dia(5)), "fecha_fin": str(hoy_negocio()), "titulo": f"  {TITULO}  "},
    })
    assert estado == 201, (estado, widget)
    print(f"tablero {tablero['id_kpi_dashboard']} con un grafico (titulo mandado con espacios de los lados)")
    print("Sembrado. Ahora corre `verificar`.")


def verificar():
    confirmar_base()
    api = Api()
    resultados = []

    def comprobar(nombre, esperado, obtenido):
        bien = esperado == obtenido
        resultados.append(bien)
        print(f"  {'OK ' if bien else 'MAL'} {nombre:66s} esperado {esperado!s:28} obtenido {obtenido!s}")

    with transaction_context() as db:
        equipos = _ids_de_equipos(db)
        marcas = db.execute(text("select count(*) from incident where note = :m"), {"m": MARCA}).scalar()
    if len(equipos) != 2 or marcas != len(DISENO):
        sys.exit(f"Se esperaban 2 equipos y {len(DISENO)} checadas marcadas y hay {len(equipos)} y {marcas}: corre `sembrar`.")
    id_equipo = {A: equipos[A], B: equipos[B]}
    nombre_de = {v: k for k, v in id_equipo.items()}
    desde, hasta = dia(5), hoy_negocio()

    print("\n1) La baja es logica: la membresia vieja sigue ahi, la nueva es otra fila")
    with transaction_context() as db:
        filas = db.execute(text(
            "select id_team, deletion_date is null from nm_team_user where id_user = :u order by creation_date"), {"u": PERSONA}).all()
    comprobar("dos membresias (el periodo viejo no se borro)", 2, len(filas))
    comprobar("la primera es de A y esta de baja; la segunda es de B y sigue vigente", [(id_equipo[A], False), (id_equipo[B], True)], [(t, v) for t, v in filas])
    estado, vigentes = api("GET", "/nm_team_user/?per_page=500")
    comprobar("GET /nm_team_user/ solo trae la membresia vigente de la persona", [id_equipo[B]], [f["id_team"] for f in vigentes["items"] if f["id_user"] == PERSONA])
    estado, opciones = api("GET", "/team/options")
    comprobar("GET /team/options ofrece los dos equipos vigentes", sorted([A, B]), sorted(o["team_description"] for o in opciones if o["id_team"] in nombre_de))

    print("\n2) Cada marca cuenta en el equipo que la persona tenia ENTONCES (consultas reales)")
    from app.kpis.modulos import checadas as K
    with transaction_context() as db:
        entradas = {(nombre_de.get(t), d): n for t, d, n in K.checadas_entradas_por_equipo_query(db, desde, hasta, {}, None) if t in nombre_de and n}
        salidas = {(nombre_de.get(t), d): n for t, d, n in K.checadas_salidas_por_equipo_query(db, desde, hasta, {}, None) if t in nombre_de and n}
        esperado = {}
        for dias_antes, _, _, equipo in DISENO:
            esperado[(equipo, dia(dias_antes))] = esperado.get((equipo, dia(dias_antes)), 0) + 1
        comprobar("entradas por equipo y dia", esperado, entradas)
        comprobar("salidas por equipo y dia", esperado, salidas)
        instante = lambda dias_antes, hm: K.equipos_de_la_persona_en(db, PERSONA, local(dias_antes, hm))    # noqa: E731
        comprobar("equipos de la persona antes del cambio (hace 3 dias, 12:00)", (id_equipo[A],), instante(3, (12, 0)))
        comprobar("equipos de la persona un minuto antes del cambio", (id_equipo[A],), K.equipos_de_la_persona_en(db, PERSONA, local(DIA_DEL_CAMBIO, HORA_DEL_CAMBIO) - timedelta(minutes=1)))
        comprobar("equipos de la persona en el instante exacto del cambio", (id_equipo[B],), instante(DIA_DEL_CAMBIO, HORA_DEL_CAMBIO))
        comprobar("equipos de la persona hoy", (id_equipo[B],), K.equipos_de_la_persona_en(db, PERSONA, datetime.combine(hasta, datetime.min.time()).replace(hour=12)))
        comprobar("equipos de la persona antes de entrar a ninguno (hace 6 dias)", (), instante(6, (12, 0)))

    print("\n3) Por la API (kpi_snapshot/query), con la etiqueta de cada equipo")
    with transaction_context() as db:
        id_entradas, id_horas = _kpi(db, "checadas_entradas_por_equipo"), _kpi(db, "horas_trabajadas_por_empleado")
    estado, cuerpo = api("GET", f"/kpi_snapshot/query?id_kpi_definition={id_entradas}&fecha_inicio={desde}&fecha_fin={hasta}")
    rango = cuerpo["rango_a"]
    comprobar("entradas de A en el rango (3 dias)", 3.0, rango["por_empleado"].get(str(id_equipo[A])))
    comprobar("entradas de B en el rango (2 dias)", 2.0, rango["por_empleado"].get(str(id_equipo[B])))
    comprobar("etiquetas", {A, B}, {rango["etiquetas"].get(str(id_equipo[A])), rango["etiquetas"].get(str(id_equipo[B]))})
    estado, cuerpo = api("GET", f"/kpi_snapshot/query?id_kpi_definition={id_entradas}&fecha_inicio={desde}&fecha_fin={hasta}&id_teams={id_equipo[A]}")
    comprobar("filtro id_teams=A en un KPI por equipo deja solo a A", [str(id_equipo[A])], sorted(cuerpo["rango_a"]["por_empleado"]))

    print("\n4) El filtro id_teams en un KPI por persona atribuye cada DIA al equipo que la persona tenia ese dia")
    por_dia = {}
    for dias_antes, entrada, salida, equipo in DISENO:
        por_dia[(equipo, dia(dias_antes))] = por_dia.get((equipo, dia(dias_antes)), 0) + minutos(entrada, salida)
    # Un dia cuenta para el equipo que la persona tenia AL TERMINARLO: el dia del cambio entero cuenta para B.
    equipo_del_dia = {d: (B if d >= dia(DIA_DEL_CAMBIO) else A) for d in {d for (_, d) in por_dia}}
    minutos_por_dia = {}
    for (_, d), m in por_dia.items():
        minutos_por_dia[d] = minutos_por_dia.get(d, 0) + m
    total = {A: sum(m for d, m in minutos_por_dia.items() if equipo_del_dia[d] == A), B: sum(m for d, m in minutos_por_dia.items() if equipo_del_dia[d] == B)}

    def horas(**filtros):
        consulta = f"/kpi_snapshot/query?id_kpi_definition={id_horas}&fecha_inicio={desde}&fecha_fin={hasta}" + "".join(f"&{k}={v}" for k, v in filtros.items())
        return (api("GET", consulta)[1]["rango_a"]["por_empleado"] or {}).get(str(PERSONA))
    comprobar("minutos con id_teams=A (los dias previos al del cambio)", float(total[A]), horas(id_teams=id_equipo[A]))
    comprobar("minutos con id_teams=B (el dia del cambio y despues)", float(total[B]), horas(id_teams=id_equipo[B]))
    comprobar("minutos con los dos equipos (la union, sin contar dos veces)", float(total[A] + total[B]), horas(id_teams=f"{id_equipo[A]},{id_equipo[B]}"))
    comprobar("minutos sin filtro", float(total[A] + total[B]), horas())

    print("\n5) Titulo propio del grafico")
    estado, tableros = api("GET", "/kpi_dashboard/")
    tablero = next((t for t in tableros["items"] if t["nombre"] == MARCA), None)
    if tablero is None:
        sys.exit("No encuentro el tablero sembrado: corre `sembrar`.")
    estado, widgets = api("GET", f"/kpi_dashboard/{tablero['id_kpi_dashboard']}/widgets/")
    guardado = widgets["items"][0]
    comprobar("el titulo se guardo recortado de los espacios de los lados", TITULO, guardado["parametros"].get("titulo"))
    for nombre, valor in (("mas de 80 caracteres", "x" * 81), ("con HTML", "<b>Hola</b>")):
        estado, cuerpo = api("PUT", f"/kpi_dashboard_widget/{guardado['id_kpi_dashboard_widget']}", {"parametros": {"titulo": valor}})
        comprobar(f"un titulo {nombre} se rechaza con 400", 400, estado)
    estado, widgets = api("GET", f"/kpi_dashboard/{tablero['id_kpi_dashboard']}/widgets/")
    comprobar("y lo guardado no cambio", TITULO, widgets["items"][0]["parametros"].get("titulo"))

    print(f"\nRESULTADO: {sum(resultados)}/{len(resultados)} OK" + ("" if all(resultados) else "   <-- hay MAL: revisa antes de confiar"))


def dar_de_baja_equipo():
    confirmar_base()
    api = Api()
    resultados = []

    def comprobar(nombre, esperado, obtenido):
        bien = esperado == obtenido
        resultados.append(bien)
        print(f"  {'OK ' if bien else 'MAL'} {nombre:66s} esperado {esperado!s:28} obtenido {obtenido!s}")

    with transaction_context() as db:
        equipos = _ids_de_equipos(db)
        id_b = equipos.get(B)
    if id_b is None:
        sys.exit("No encuentro el equipo sembrado: corre `sembrar`.")
    desde, hasta = dia(5), hoy_negocio()
    from app.kpis.modulos import checadas as K
    from app.jobs.tasks_kpis import _recalcular_kpi_snapshots_en_sesion

    estado, _ = api("DELETE", f"/team/{id_b}")
    comprobar("DELETE /team/<B> responde 200", 200, estado)
    print("\n1) El equipo y su membresia quedaron de baja, no borrados")
    with transaction_context() as db:
        equipo = db.execute(text("select deletion_date is not null from team where id_team = :t"), {"t": id_b}).scalar()
        membresia = db.execute(text("select deletion_date is not null from nm_team_user where id_team = :t and id_user = :u"), {"t": id_b, "u": PERSONA}).scalar()
    comprobar("la fila del equipo sigue y tiene deletion_date", True, equipo)
    comprobar("la membresia vigente cayo con el equipo", True, membresia)
    estado, opciones = api("GET", "/team/options")
    comprobar("el equipo ya no se ofrece en /team/options", False, any(o["id_team"] == id_b for o in opciones))
    comprobar("GET /team/<B> da 404", 404, api("GET", f"/team/{id_b}")[0])

    print("\n2) La persona hoy no tiene equipo, pero la historia sigue contando")
    with transaction_context() as db:
        comprobar("equipos de la persona ahora", (), K.equipos_de_la_persona_en(db, PERSONA, ahora_negocio()))
        comprobar("equipos de la persona hace 1 dia (B existia)", (id_b,), K.equipos_de_la_persona_en(db, PERSONA, local(1, (12, 0))))
    with transaction_context() as db:
        _recalcular_kpi_snapshots_en_sesion(db, desde, hasta, claves=["checadas_entradas_por_equipo", "checadas_salidas_por_equipo"])
        id_entradas = _kpi(db, "checadas_entradas_por_equipo")
    estado, cuerpo = api("GET", f"/kpi_snapshot/query?id_kpi_definition={id_entradas}&fecha_inicio={desde}&fecha_fin={hasta}")
    rango = cuerpo["rango_a"]
    comprobar("las 2 entradas que ya eran de B siguen siendo de B tras recalcular", 2.0, rango["por_empleado"].get(str(id_b)))
    comprobar("y B conserva su nombre en la etiqueta", B, rango["etiquetas"].get(str(id_b)))
    print(f"\nRESULTADO: {sum(resultados)}/{len(resultados)} OK" + ("" if all(resultados) else "   <-- hay MAL: revisa antes de confiar"))


def limpiar():
    confirmar_base()
    with transaction_context() as db:
        ids_t = [t for (t,) in db.execute(text("select id_team from team where team_description in (:a, :b)"), {"a": A, "b": B})]
        ids_t = ids_t or [-1]
        db.execute(text("delete from incident where note = :m"), {"m": MARCA})
        db.execute(text("delete from kpi_snapshot where dimension_key->>'id_user' = :u or dimension_key->>'id_team' = any(:t)"),
                   {"u": str(PERSONA), "t": [str(t) for t in ids_t]})
        db.execute(text("delete from nm_team_user where id_team = any(:t) or id_user = :u"), {"t": ids_t, "u": PERSONA})
        db.execute(text("delete from team where id_team = any(:t)"), {"t": ids_t})
        db.execute(text('delete from "user" where id_user = :u'), {"u": PERSONA})
        db.execute(text("delete from kpi_dashboard_widget_kpi where id_kpi_dashboard_widget in (select w.id_kpi_dashboard_widget from kpi_dashboard_widget w join kpi_dashboard d on d.id_kpi_dashboard = w.id_kpi_dashboard where d.nombre = :m)"), {"m": MARCA})
        db.execute(text("delete from kpi_dashboard_widget where id_kpi_dashboard in (select id_kpi_dashboard from kpi_dashboard where nombre = :m)"), {"m": MARCA})
        db.execute(text("delete from kpi_dashboard where nombre = :m"), {"m": MARCA})
    with transaction_context() as db:
        quedan = {
            "checadas marcadas": db.execute(text("select count(*) from incident where note = :m"), {"m": MARCA}).scalar(),
            "persona": db.execute(text('select count(*) from "user" where id_user = :u'), {"u": PERSONA}).scalar(),
            "equipos": db.execute(text("select count(*) from team where team_description in (:a, :b)"), {"a": A, "b": B}).scalar(),
            "tableros": db.execute(text("select count(*) from kpi_dashboard where nombre = :m"), {"m": MARCA}).scalar(),
        }
    print("Despues de limpiar:", quedan, "-> OK" if not any(quedan.values()) else "-> QUEDAN FILAS")
    print("Nota: los snapshots 'Sin equipo' y los de otras personas que `sembrar` recalculo NO se deshacen; por eso la receta es para una COPIA.")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    accion = {"sembrar": sembrar, "verificar": verificar, "dar_de_baja_equipo": dar_de_baja_equipo, "limpiar": limpiar}.get(argv[0] if argv else "")
    if accion is None:
        sys.exit(__doc__)
    accion()


if __name__ == "__main__":
    main()
