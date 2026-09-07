---
name: migrar-cliente-legado
description: Guía el análisis y la escritura de un script para migrar la base legada (MySQL/MariaDB) de un cliente nuevo hacia tyakxa_tny (Postgres), reusando backend/scripts/migration_toolkit.py. Úsala cuando haya que traer los datos reales de un cliente nuevo a tyakxa_tny, o cuando el usuario pida "migrar a <cliente>", "traer la base de <cliente>", o pregunte cómo hacer una migración de datos legados.
---

# Migrar la base legada de un cliente nuevo

Esta guía **no reemplaza el criterio de negocio** — lo estructura. La parte
difícil de una migración de este tipo nunca es correr el script; es decidir
qué hacer con cada hueco, colisión o dato sucio de la base vieja de ESE
cliente. Cada punto marcado abajo con **"preguntar al usuario"** es un
punto real de decisión: usa `AskUserQuestion` con quien esté corriendo esta
migración en la sesión actual — no asumas ni inventes un default, y no
asumas tampoco que se trata de Alan; puede ser cualquiera del equipo
encargado del despliegue de ese cliente.

Referencia de ejemplo completo, ya hecho de punta a punta: `backend/scripts/migrate_adser.py`
(usa las piezas de `backend/scripts/migration_toolkit.py`) y el artefacto
"Guía — Migración de adser" (comandos operativos exactos: cargar dumps en
un pod/contenedor desechable, correr dry-run, verificar el bootstrap).

## Paso 1 — Cargar los dumps del cliente en algo desechable

Nunca cuentes o leas un `.sql` a mano — ni para contar filas ni para
entender columnas. Carga los dumps reales en una base MySQL/MariaDB de
usar-y-tirar y verifica todo con SQL real:

- Si se trabaja localmente: un contenedor Docker (`docker run mariadb:10.11 ...`)
  con los dumps montados o copiados adentro.
- Si se trabaja dentro del clúster (como con adser): un pod temporal vía
  `kubectl run`, cargar con `kubectl cp` + `mariadb -u... < archivo.sql`. Ver
  los comandos exactos, ya probados, en el artefacto "Guía — Migración de
  adser".

## Paso 2 — Mapear tabla por tabla contra el esquema de Postgres

Para cada tabla del origen: ¿existe su equivalente en tyakxa_tny? ¿qué
columna corresponde a cuál? ¿qué tipo de dato, qué NOT NULL, qué CHECK
constraints tiene el destino que el origen no garantiza? Documentar esto en
un artefacto de mapeo (mismo formato que el de adser: hallazgos, diagrama
ER, orden de migración por dependencias, mapeo columna-por-columna,
decisiones resueltas, verificación de integridad referencial).

No avanzar al paso 3 sin haber revisado, con consultas SQL reales:
- Conteos de filas de cada tabla origen.
- Llaves foráneas huérfanas (referencian un ID que no existe).
- Valores sentinela (fechas tipo "nunca pasó", IDs tipo "sin asignar").
- Columnas NOT NULL en destino que el origen no tiene o deja NULL.

## Paso 3 — Verificar el estado REAL del destino antes de asumir nada

Antes de decidir si hay colisiones de ID, contar con una consulta SQL
directa (nunca asumir) las tablas del bootstrap circular de
`database/init.sql`: `status`, `customer_supplier`, `permission`, `proyect`,
`user`, `department`, `subdepartment`, `level`.

```sql
SELECT
  (SELECT count(*) FROM department) AS department,
  (SELECT count(*) FROM subdepartment) AS subdepartment,
  (SELECT count(*) FROM level) AS level,
  (SELECT count(*) FROM status) AS status,
  (SELECT count(*) FROM permission) AS permission,
  (SELECT count(*) FROM customer_supplier) AS customer_supplier,
  (SELECT count(*) FROM proyect) AS proyect,
  (SELECT count(*) FROM "user") AS "user";
```

Esto no es opcional ni un formalismo: un ambiente "instalación fresca" NO
garantiza traer el bootstrap completo — `init.sql` solo corre la primera
vez que se crea el volumen de Postgres, así que un ambiente viejo (armado
con el tiempo, no desde cero) puede tener huecos reales ahí. Así se
encontró, en la migración de adser, que a `tyakxa-dev` le faltaban 2 filas
(`status`, `customer_supplier`) — no era un bug del script, era un hueco
real del ambiente que había que corregir primero.

## Paso 4 — Detectar colisiones de ID reales y decidirlas con el usuario

Solo cuentan como colisión real las tablas donde el destino YA tiene una
fila con ese mismo ID (verificado en el paso 3), no un ID cualquiera.
Para cada colisión real: **preguntar al usuario** cómo resolverla (nuevo ID,
fusionar con la fila existente, etc.) — no decidir a solas. Ejemplo real de
adser (decidido en su momento con Alan, el encargado de ese despliegue):
`user` y `customer_supplier` ya traían su fila `id=1` del bootstrap,
así que "taroj" y "Adser SA de CV" se movieron a un ID nuevo; las otras 17
tablas se migraron con su ID original exacto porque se confirmó que estaban
vacías en el destino.

## Paso 5 — Para cada hueco o dato sucio, preguntar — nunca inventar

Patrones típicos que van a aparecer (los mismos que en adser):
- Una categoría/familia/marca faltante o inconsistente → **preguntar al
  usuario** si se crea un valor genérico tipo "Sin categoría" y con qué
  criterio se usa.
- Una FK que apunta a un sentinela (`id_ubicacion=0` significando "sin
  asignar", no un ID real) → **preguntar al usuario** qué debe representar
  el destino de ese sentinela.
- Un campo NOT NULL en destino sin equivalente real en origen → revisar
  primero qué hace la propia app cuando ese campo no se especifica (ej.
  `manual_invoice_service.py` usa `SELECT * FROM status ORDER BY id_status
  ASC LIMIT 1` como default) y usar esa misma regla, no un valor inventado.

## Paso 6 — Escribir `backend/scripts/migrate_<cliente>.py`

Reusar `backend/scripts/migration_toolkit.py` en vez de reimplementar el
esqueleto:

- `parser_base(__doc__)` + `parser.set_defaults(source_db='...')` si el
  cliente siempre migra la misma base.
- `conectar_origen(host, port, user, password, db)` para la conexión MySQL.
- `sesion_migracion(dry_run)` como context manager: envuelve toda la
  migración en una sola transacción, revierte en `--dry-run` o si algo
  truena, confirma solo si todo salió bien.
- `resolver_ids_por_nombre(session, tabla, columna_id, columna_nombre)`
  para CUALQUIER tabla con una columna autogenerada (`GENERATED BY DEFAULT
  AS IDENTITY`/`SERIAL`) cuyo ID real dependa del orden de migraciones ya
  corridas — nunca hardcodear ese número a mano.
- `normalizar_fecha(valor, sentinela)` para limpiar sentinelas de fecha.
- `ajustar_secuencias(session, tablas)` y `reporte_conteos(session, tablas)`
  al final, con la lista de `(tabla, columna_id)` de este cliente.

Seguir el mismo patrón de una función `migrar_<tabla>()` por tabla, llamadas
en `main()` en el orden real de dependencias (sin FK a una tabla que aún no
se migró).

## Paso 7 — Autorrevisión antes de correr nada real

Buscar específicamente estos dos patrones — los 2 bugs reales que salieron
en la migración de adser antes de tocar datos reales:
1. Un ID autogenerado hardcodeado a mano en vez de resuelto por
   `resolver_ids_por_nombre`.
2. Un `join`/diccionario armado sin filtrar contra el conjunto real de IDs
   válidos del destino (riesgo de que un huérfano del origen choque por
   casualidad con un ID real y desplace datos buenos).

## Paso 8 — Probar `--dry-run` en un ambiente desechable

Correr el script recién escrito contra una base Postgres de prueba (local o
disponible), revisar los conteos reportados, corregir lo que salga mal.
Repetir hasta que salga limpio.

## Paso 9 — Probar dry-run + real contra tyakxa-dev

Mismo gate de siempre: nunca tocar la base real del cliente sin antes
probar de punta a punta contra `tyakxa-dev` (ambiente de bajo riesgo). Ver
los comandos operativos exactos (pod temporal, `kubectl cp`, dry-run, y qué
hacer si aparece un `ForeignKeyViolation` de bootstrap) en el artefacto
"Guía — Migración de adser".

## Paso 10 — Correr contra la base real del cliente

Solo con una confirmación explícita y nueva de quien esté a cargo de ese
despliegue — nunca asumir que un "sí" anterior (para otro cliente, para
otra persona, o para la prueba en dev) aplica aquí también.
