#!/usr/bin/env python3
"""Avisa, por la campana del sistema, de los datos migrados de adser que solo Adser puede
confirmar.

Por que existe
--------------
La comparacion de adser-prod contra el respaldo del sistema anterior (2026-09-30) dejo
cuatro temas que ningun script puede resolver, porque dependen de saber donde esta una
herramienta o quien es una persona. En lugar de decidirlos por ellos, se les avisan:

1. Prestamos abiertos de herramientas cuyo estado dice ENTRADA (en el almacen): uno de los
   dos datos es falso. Si ya volvieron, basta "Marcar devuelto" en el vale.
2. Prestamos abiertos del sistema anterior cuya herramienta ya no existe en el catalogo
   (el script de migracion los excluyo por diseno): no aparecen en "quien tiene que".
   Esos renglones NO estan en la base, asi que sus datos vienen del respaldo (`HUERFANOS`).
3. La incidencia 90 era de Fernanda Contreras; la cuenta 2 se renombro despues.
4. Vales abiertos sin ningun renglon: cuentan como pendientes sin nada que devolver.

Es solo un aviso: no cambia ningun dato ni permiso. Cada tema es una notificacion aparte;
el destinatario la quita con "Enterado" (es la unica forma de quitarla de la lista).

Uso
---
    python scripts/notify_adser_revision_datos.py --dry-run          # muestra los textos
    python scripts/notify_adser_revision_datos.py                    # crea los avisos
    python scripts/notify_adser_revision_datos.py --destinatario admin1   # p. ej. en dev

Idempotente: un tema que ya se aviso (aunque este leido) no se vuelve a crear, y un tema
sin casos (ya se resolvio) no se avisa. El resumen solo se crea si hay al menos un tema.
"""
from __future__ import annotations

import argparse
import os
import sys

import psycopg2
from psycopg2.extras import Json

DESTINATARIO_POR_OMISION = "yesgo"
ID_REMITENTE = 1  # admin1: la campana pide un autor, no se muestra
# `notification_type` tiene una restriccion CHECK con una lista cerrada (project_status_change,
# project_modified, activity_log_created, task_assigned, material_confirmed, custom); `custom` es
# el de uso general. Estos avisos se distinguen por `metadata->>'clave'`, no por el tipo.
TIPO = "custom"
CONTACTO = "Alan Pérez"

# Renglones del sistema anterior que la migracion excluyo porque su producto no existe en
# origen y que seguian ABIERTOS. No estan en la base, por eso se listan aqui (medido el
# 2026-09-30 contra el respaldo Sep2126): (renglon, vale, fecha del vale, nota).
HUERFANOS = (
    (85, 1, "27/04/2025", None),
    (117, 1, "27/04/2025", None),
    (145, 3, "30/06/2025", "VALES ANTERIORES FOLIO0117"),
    (743, 36, "21/10/2025", "Valeo termico1-actualizacion de vales"),
    (1998, 96, "25/03/2026", None),
)

# La incidencia 90 era de esta persona en el sistema anterior.
INCIDENCIA_90 = (90, "Fernanda Contreras")

SQL_CONTRADICCIONES = """
SELECT u.full_name, r.id_incident,
       coalesce(nullif(btrim(p.descripcion), ''), m.material_description, 'producto ' || p.id_product) AS herramienta
FROM nm_incident_product r
JOIN incident i ON i.id_incident = r.id_incident
JOIN incident_type t ON t.id_incident_type = i.id_incident_type
JOIN "user" u ON u.id_user = i.id_user
JOIN product p ON p.id_product = r.id_product
LEFT JOIN material m ON m.id_material = p.id_material
WHERE r.deletion_date IS NULL AND i.deletion_date IS NULL AND p.deletion_date IS NULL
  AND lower(r.direction) = 'salida'
  AND (r.close_date IS NULL OR r.close_date < '2000-01-01')
  AND upper(btrim(p.product_status)) = 'ENTRADA'
  AND lower(btrim(t.incident_type_description)) NOT IN ('destruccion', 'destrucción', 'extraviado')
ORDER BY u.full_name, r.id_incident, r.id_nm_incident_product
"""

SQL_VALES_VACIOS = """
SELECT i.id_incident
FROM incident i
WHERE i.deletion_date IS NULL AND lower(i.incident_status) LIKE 'abiert%'
  AND NOT EXISTS (SELECT 1 FROM nm_incident_product r
                  WHERE r.id_incident = i.id_incident AND r.deletion_date IS NULL)
ORDER BY i.id_incident
"""


def conectar():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
    )


def nombre(texto: str) -> str:
    """'MAXIMINO  CANO' -> 'Maximino Cano'."""
    return " ".join(str(texto or "").split()).title()


def recortar(texto: str, largo: int = 30) -> str:
    texto = " ".join(str(texto or "").split())
    return texto if len(texto) <= largo else texto[: largo - 1].rstrip() + "…"


def plural(n: int, uno: str, varios: str) -> str:
    return uno if n == 1 else varios


# --- textos: funciones puras, sin base de datos -------------------------------------------

def aviso_contradicciones(filas):
    """filas: (responsable, vale, herramienta). None si no hay casos."""
    if not filas:
        return None
    # persona -> vale -> herramientas, para no repetir el numero de vale en cada renglon.
    por_persona: dict[str, dict[int, list[str]]] = {}
    for responsable, vale, herramienta in filas:
        por_persona.setdefault(nombre(responsable), {}).setdefault(vale, []).append(recortar(herramienta))
    lineas = []
    for persona, vales in sorted(por_persona.items(),
                                 key=lambda par: (-sum(len(h) for h in par[1].values()), par[0])):
        total = sum(len(herramientas) for herramientas in vales.values())
        detalle = "; ".join(f"vale {vale} — " + ", ".join(herramientas)
                            for vale, herramientas in sorted(vales.items()))
        lineas.append(f"• {persona} ({total}): {detalle}")
    n = len(filas)
    titulo = (f"{n} {plural(n, 'préstamo abierto', 'préstamos abiertos')} de herramientas "
              f"que figuran en el almacén")
    mensaje = (
        "Estos préstamos siguen abiertos, pero la herramienta está marcada como «en almacén»: "
        "uno de los dos datos no es cierto. Confirmen dónde está. Si ya volvió, en Vales de "
        "almacén abran el vale y pulsen «Marcar devuelto» en ese renglón (así vuelve a contar en "
        "existencia). Si sigue con la persona, no hagan nada.\n\n" + "\n".join(lineas)
    )
    return "contradicciones_entrada_abierto", titulo, mensaje


def aviso_huerfanos(huerfanos, responsables):
    """huerfanos: (renglon, vale, fecha, nota); responsables: {vale: nombre actual}."""
    if not huerfanos:
        return None
    por_vale: dict[int, list] = {}
    for renglon, vale, fecha, nota in huerfanos:
        por_vale.setdefault(vale, []).append((fecha, nota))
    lineas = []
    for vale in sorted(por_vale):
        casos = por_vale[vale]
        fecha = casos[0][0]
        notas = sorted({nota for _, nota in casos if nota})
        detalle = f"Vale {vale} — {nombre(responsables.get(vale, ''))}, {fecha}"
        if len(casos) > 1:
            detalle += f" ({len(casos)} renglones)"
        if notas:
            detalle += ", nota «" + "; ".join(notas) + "»"
        lineas.append("• " + detalle)
    n = len(huerfanos)
    titulo = (f"{n} {plural(n, 'préstamo', 'préstamos')} del sistema anterior sin herramienta en el catálogo")
    mensaje = (
        "En el sistema anterior estos préstamos seguían abiertos, pero su herramienta ya no existe "
        "en el catálogo, por eso no aparecen en «quién tiene qué». Si alguna sigue fuera, "
        "regístrenla en un vale nuevo con la herramienta correcta.\n\n" + "\n".join(lineas)
    )
    return "prestamos_sin_herramienta", titulo, mensaje


def aviso_incidencia(id_incidencia, nombre_anterior, nombre_actual):
    """None si el responsable actual es el mismo del sistema anterior."""
    if nombre_actual is None or " ".join(nombre_actual.upper().split()) == " ".join(nombre_anterior.upper().split()):
        return None
    titulo = f"Incidencia {id_incidencia}: el responsable cambió de nombre"
    mensaje = (
        f"En el sistema anterior la incidencia {id_incidencia} era de {nombre_anterior}; hoy aparece "
        f"a nombre de {nombre(nombre_actual)} (esa cuenta cambió de nombre). Si no es la misma "
        "persona, corrijan el responsable de la incidencia."
    )
    return f"incidencia_{id_incidencia}_responsable", titulo, mensaje


def aviso_vales_vacios(ids):
    if not ids:
        return None
    n = len(ids)
    lista = ", ".join(str(i) for i in ids)
    titulo = f"{n} {plural(n, 'vale abierto', 'vales abiertos')} sin ningún material"
    mensaje = (
        f"{plural(n, 'El vale', 'Los vales')} {lista} {plural(n, 'está abierto', 'están abiertos')} "
        f"pero {plural(n, 'no tiene', 'no tienen')} ningún renglón: cuentan como pendientes sin nada "
        "que devolver. Si no se van a usar, ciérrenlos o cancélenlos."
    )
    return "vales_abiertos_vacios", titulo, mensaje


def aviso_resumen(n_temas):
    titulo = "Revisión de datos tras la actualización"
    mensaje = (
        f"Con la actualización del sistema quedaron {n_temas} {plural(n_temas, 'tema', 'temas')} que "
        "solo ustedes pueden confirmar. Son solo avisos: no se cambió nada por ustedes. Cada uno llega "
        "como una notificación aparte; pulsen «Enterado» cuando lo hayan revisado. Si necesitan acceso "
        f"a alguna pantalla o permiso, avisen a {CONTACTO}."
    )
    return "revision_datos_resumen", titulo, mensaje


# --- base de datos ------------------------------------------------------------------------

def reunir_avisos(cur):
    """Los avisos que hoy corresponden, sin el resumen: [(clave, titulo, mensaje)]."""
    cur.execute(SQL_CONTRADICCIONES)
    contradicciones = cur.fetchall()

    vales = [vale for _, vale, _, _ in HUERFANOS]
    cur.execute('SELECT i.id_incident, u.full_name FROM incident i JOIN "user" u ON u.id_user = i.id_user '
                'WHERE i.deletion_date IS NULL AND i.id_incident = ANY(%s)', (vales,))
    responsables = dict(cur.fetchall())
    # Solo los que siguen teniendo su vale en esta base (en una base sin los datos de adser no aplica).
    huerfanos = [h for h in HUERFANOS if h[1] in responsables]

    id_incidencia, anterior = INCIDENCIA_90
    cur.execute('SELECT u.full_name FROM incident i JOIN "user" u ON u.id_user = i.id_user '
                'WHERE i.id_incident = %s AND i.deletion_date IS NULL', (id_incidencia,))
    fila = cur.fetchone()

    cur.execute(SQL_VALES_VACIOS)
    vacios = [f[0] for f in cur.fetchall()]

    candidatos = (
        aviso_contradicciones(contradicciones),
        aviso_huerfanos(huerfanos, responsables),
        aviso_incidencia(id_incidencia, anterior, fila[0] if fila else None),
        aviso_vales_vacios(vacios),
    )
    return [c for c in candidatos if c]


def ya_avisado(cur, id_usuario, clave):
    cur.execute("SELECT 1 FROM notification WHERE id_user_recipient = %s AND deletion_date IS NULL "
                "AND metadata->>'clave' = %s LIMIT 1", (id_usuario, clave))
    return cur.fetchone() is not None


def crear(cur, id_usuario, clave, titulo, mensaje):
    # clock_timestamp(): `now()` es la hora de la transaccion y daria la misma a todos los
    # avisos; la campana ordena por fecha, asi que el orden de creacion se respeta.
    cur.execute(
        "INSERT INTO notification (id_user_recipient, id_user_sender, notification_type, title, message, "
        "metadata, created_by, creation_date) VALUES (%s, %s, %s, %s, %s, %s, %s, clock_timestamp())",
        (id_usuario, ID_REMITENTE, TIPO, titulo, mensaje, Json({"clave": clave}), ID_REMITENTE))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true', help="muestra los textos y no crea nada")
    parser.add_argument('--destinatario', default=DESTINATARIO_POR_OMISION,
                        help=f"username que verá los avisos (por omisión {DESTINATARIO_POR_OMISION})")
    args = parser.parse_args()

    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute('SELECT id_user, full_name FROM "user" WHERE username = %s AND deletion_date IS NULL',
                    (args.destinatario,))
        destino = cur.fetchone()
        if destino is None:
            print(f"ERROR: no existe el usuario '{args.destinatario}'.")
            return 1
        id_usuario, nombre_completo = destino
        print(f"destinatario: {args.destinatario} ({nombre(nombre_completo)}, id {id_usuario})")

        avisos = reunir_avisos(cur)
        pendientes = [a for a in avisos if not ya_avisado(cur, id_usuario, a[0])]
        omitidos = len(avisos) - len(pendientes)
        print(f"temas con casos: {len(avisos)}; ya avisados: {omitidos}; por avisar: {len(pendientes)}")

        # El resumen va al final para que, al ordenar por fecha descendente, quede arriba.
        if pendientes:
            resumen = aviso_resumen(len(avisos))
            if not ya_avisado(cur, id_usuario, resumen[0]):
                pendientes.append(resumen)

        for clave, titulo, mensaje in pendientes:
            print(f"\n--- [{clave}]\n{titulo}\n{mensaje}")
            if not args.dry_run:
                crear(cur, id_usuario, clave, titulo, mensaje)

        if args.dry_run:
            conn.rollback()
            print("\n--dry-run: no se creó ningún aviso.")
        else:
            conn.commit()
            print(f"\navisos creados: {len(pendientes)}")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
