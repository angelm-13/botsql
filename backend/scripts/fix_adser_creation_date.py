#!/usr/bin/env python3
"""Rellena `creation_date` de las incidencias (vales) y de sus renglones
migrados de adser, que `migrate_adser.py` dejo en NULL.

De donde sale cada fecha
------------------------
* INCIDENCIA: la `fecha_creacion` que el sistema anterior guardaba en
  `incidente`, incrustada abajo (los ids se preservaron en la migracion, asi
  que 139 pares id -> fecha valen igual en cualquier ambiente). Verificado
  contra el respaldo Sep2126: en 123 de 139 cae el mismo dia que la fecha del
  vale y en 127 dentro de 3 dias, o sea que es una hora de captura real.
* RENGLON: la `creation_date` de SU VALE. Un renglon se guarda junto con su
  vale, asi que es la mejor aproximacion honesta. NO se usa la
  `fecha_creacion` propia del renglon del sistema anterior: solo tiene 16
  valores distintos en 2 787 filas (397 renglones de 27 vales distintos con la
  misma hora) y en 2 105 va ANTES de la fecha del vale -- son sellos de carga
  masiva, no horas de captura.
* Incidencia sin par en el sistema anterior (capturada ya en el sistema
  nuevo): `incident_date`, la unica fecha que tiene. Es una aproximacion (la
  hora sera medianoche), y se cuenta aparte para que se vea cuantas son.

Solo toca filas con `creation_date IS NULL`: no pisa nada capturado con fecha.
Es idempotente. Complementa la migracion 20260929110000, que pone el DEFAULT
para las altas futuras.
"""
from __future__ import annotations

import argparse
import os

import psycopg2

# id_incident -> fecha_creacion del sistema anterior (respaldo Sep2126).
FECHAS_DE_CAPTURA = [
    (1, "2025-08-15 15:52:22"),
    (2, "2025-08-15 16:40:58"),
    (3, "2025-08-20 10:50:03"),
    (4, "2025-08-20 10:57:27"),
    (5, "2025-08-20 15:05:36"),
    (6, "2025-08-21 09:23:08"),
    (7, "2025-09-01 10:11:42"),
    (8, "2025-09-02 08:28:41"),
    (9, "2025-09-02 12:25:41"),
    (10, "2025-09-03 10:25:03"),
    (11, "2025-09-04 08:47:30"),
    (12, "2025-09-05 08:23:34"),
    (13, "2025-09-08 10:12:59"),
    (14, "2025-09-08 17:07:26"),
    (15, "2025-09-10 10:14:16"),
    (16, "2025-09-16 09:43:51"),
    (17, "2025-09-17 11:16:49"),
    (18, "2025-09-18 09:56:40"),
    (19, "2025-09-22 12:50:23"),
    (20, "2025-09-22 16:41:57"),
    (21, "2025-09-26 08:34:37"),
    (22, "2025-09-29 09:11:54"),
    (23, "2025-09-30 11:52:44"),
    (24, "2025-10-03 09:52:33"),
    (25, "2025-10-06 15:16:14"),
    (26, "2025-10-07 09:49:04"),
    (27, "2025-10-09 09:51:49"),
    (28, "2025-10-09 12:46:03"),
    (29, "2025-10-10 08:55:12"),
    (30, "2025-10-15 10:24:08"),
    (31, "2025-10-15 10:24:08"),
    (32, "2025-10-15 10:24:08"),
    (33, "2025-10-15 12:13:44"),
    (34, "2025-10-15 15:23:57"),
    (35, "2025-10-15 16:54:53"),
    (36, "2025-10-21 10:53:18"),
    (37, "2025-10-24 08:49:17"),
    (38, "2025-11-06 09:35:55"),
    (39, "2025-11-11 17:06:51"),
    (40, "2025-11-12 15:54:16"),
    (41, "2025-11-18 09:41:18"),
    (42, "2025-11-18 10:51:42"),
    (43, "2025-11-19 09:07:41"),
    (44, "2025-11-20 10:53:14"),
    (45, "2025-11-25 10:13:53"),
    (46, "2025-11-29 13:14:34"),
    (47, "2025-12-01 09:34:24"),
    (48, "2025-12-01 12:16:42"),
    (49, "2025-12-02 11:13:33"),
    (50, "2025-12-03 17:32:48"),
    (51, "2025-12-03 17:32:48"),
    (52, "2025-12-04 08:23:28"),
    (53, "2025-12-04 14:23:28"),
    (54, "2025-12-20 08:52:26"),
    (55, "2025-12-23 15:13:40"),
    (56, "2025-12-26 14:29:59"),
    (57, "2025-12-29 09:30:08"),
    (58, "2026-01-05 16:41:04"),
    (59, "2026-01-06 17:09:33"),
    (60, "2026-01-07 12:29:14"),
    (61, "2026-01-08 17:53:04"),
    (62, "2026-01-15 16:51:28"),
    (63, "2026-01-20 08:35:48"),
    (64, "2026-01-20 14:50:40"),
    (65, "2026-01-20 16:06:44"),
    (66, "2026-01-21 09:26:36"),
    (67, "2026-01-22 08:40:45"),
    (68, "2026-01-22 08:59:14"),
    (69, "2026-01-22 16:52:03"),
    (70, "2026-01-22 18:10:52"),
    (71, "2026-01-23 10:36:54"),
    (72, "2026-01-24 10:52:32"),
    (73, "2026-01-26 15:09:14"),
    (74, "2026-01-28 10:27:20"),
    (75, "2026-02-03 10:19:23"),
    (76, "2026-02-09 09:14:23"),
    (77, "2026-02-09 09:14:23"),
    (78, "2026-02-11 11:07:42"),
    (79, "2026-02-17 09:32:32"),
    (80, "2026-02-17 11:27:01"),
    (81, "2026-02-17 17:15:42"),
    (82, "2026-02-19 09:54:12"),
    (83, "2026-02-21 09:13:50"),
    (84, "2026-02-23 09:35:54"),
    (85, "2026-02-26 15:49:56"),
    (86, "2026-03-03 16:40:38"),
    (87, "2026-03-05 10:20:13"),
    (88, "2026-03-06 10:57:48"),
    (89, "2026-03-10 16:26:47"),
    (90, "2026-03-10 17:52:21"),
    (91, "2026-03-11 12:11:41"),
    (92, "2026-03-12 09:16:32"),
    (93, "2026-03-13 10:22:56"),
    (94, "2026-03-18 08:38:28"),
    (95, "2026-03-18 09:56:07"),
    (96, "2026-03-25 11:48:45"),
    (97, "2026-03-31 08:40:04"),
    (98, "2026-04-08 09:19:52"),
    (99, "2026-04-13 15:54:37"),
    (100, "2026-04-21 16:08:40"),
    (101, "2026-04-22 08:35:54"),
    (102, "2026-04-23 14:38:15"),
    (103, "2026-04-23 15:08:15"),
    (104, "2026-04-23 17:08:54"),
    (105, "2026-05-05 15:36:58"),
    (106, "2026-05-07 10:52:24"),
    (107, "2026-05-07 15:58:07"),
    (108, "2026-05-13 09:46:40"),
    (109, "2026-05-14 09:44:35"),
    (110, "2026-05-15 09:05:53"),
    (111, "2026-05-20 12:06:38"),
    (112, "2026-06-01 11:02:02"),
    (113, "2026-06-24 09:06:21"),
    (114, "2026-06-24 09:12:51"),
    (115, "2026-06-26 14:30:38"),
    (116, "2026-06-30 09:36:52"),
    (117, "2026-06-30 09:55:54"),
    (118, "2026-06-30 12:42:51"),
    (119, "2026-07-07 09:27:49"),
    (120, "2026-07-09 11:43:33"),
    (121, "2026-07-15 12:39:48"),
    (122, "2026-07-22 09:12:38"),
    (123, "2026-07-22 09:13:41"),
    (124, "2026-07-23 09:39:31"),
    (125, "2026-07-29 16:07:45"),
    (126, "2026-08-03 08:37:15"),
    (127, "2026-08-04 08:28:50"),
    (128, "2026-08-04 09:20:19"),
    (129, "2026-08-04 16:24:09"),
    (130, "2026-08-05 08:49:05"),
    (131, "2026-08-06 16:50:56"),
    (132, "2026-08-08 09:52:48"),
    (133, "2026-08-14 08:34:54"),
    (134, "2026-08-14 10:28:00"),
    (135, "2026-08-16 12:04:36"),
    (136, "2026-08-16 13:00:20"),
    (137, "2026-08-16 20:54:11"),
    (138, "2026-08-16 20:56:41"),
    (139, "2026-08-16 21:18:59"),
]


def conectar():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    conn = conectar()
    try:
        cur = conn.cursor()

        cur.execute("SELECT count(*) FROM incident WHERE creation_date IS NULL")
        (incidencias_null,) = cur.fetchone()
        cur.execute("SELECT count(*) FROM nm_incident_product WHERE creation_date IS NULL")
        (renglones_null,) = cur.fetchone()
        print(f"antes: incidencias sin creation_date={incidencias_null}, renglones sin creation_date={renglones_null}")

        # 1. Incidencias con par en el sistema anterior.
        cur.execute(
            "UPDATE incident i SET creation_date = v.fecha::timestamp "
            "FROM (SELECT * FROM unnest(%s::int[], %s::text[]) AS t(id, fecha)) v "
            "WHERE i.id_incident = v.id AND i.creation_date IS NULL AND v.fecha::timestamp <= now()",
            ([i for i, _ in FECHAS_DE_CAPTURA], [f for _, f in FECHAS_DE_CAPTURA]),
        )
        del_sistema_anterior = cur.rowcount

        # 2. Las demas (capturadas en el sistema nuevo): la fecha del vale.
        cur.execute(
            "UPDATE incident SET creation_date = incident_date "
            "WHERE creation_date IS NULL AND incident_date IS NOT NULL"
        )
        con_fecha_del_vale = cur.rowcount

        # 3. Renglones: la creation_date de su vale.
        cur.execute(
            "UPDATE nm_incident_product n SET creation_date = i.creation_date "
            "FROM incident i WHERE n.id_incident = i.id_incident "
            "AND n.creation_date IS NULL AND i.creation_date IS NOT NULL"
        )
        renglones = cur.rowcount

        cur.execute("SELECT count(*) FROM incident WHERE creation_date IS NULL")
        (incidencias_quedan,) = cur.fetchone()
        cur.execute("SELECT count(*) FROM nm_incident_product WHERE creation_date IS NULL")
        (renglones_quedan,) = cur.fetchone()

        if args.dry_run:
            conn.rollback()
            print("\n--dry-run: todo revertido, no se escribio nada permanente.")
        else:
            conn.commit()
            print("\nRelleno confirmado.")

        prefijo = '[dry-run] ' if args.dry_run else ''
        print(f"{prefijo}incidencias con la fecha de captura del sistema anterior: {del_sistema_anterior}")
        print(f"{prefijo}incidencias sin par, con la fecha del vale (aproximacion): {con_fecha_del_vale}")
        print(f"{prefijo}renglones con la creation_date de su vale: {renglones}")
        print(f"{prefijo}quedan sin creation_date -> incidencias={incidencias_quedan}, renglones={renglones_quedan}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
