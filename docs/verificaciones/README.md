# Verificaciones manuales

Scripts que se corren a mano contra una base real para comprobar un comportamiento que las pruebas automáticas solo cubren con fixtures.
No forman parte de la suite ni de CI.

## `receta_checadas.py`: KPIs de checadas

Siembra 4 personas, 2 equipos y 4 checadas (todo marcado con `incident.note = 'VERIF-CHECADAS'`, personas `990001`–`990004`, equipos `990001`–`990002`),
llama a las consultas **reales** de `app/kpis/modulos/checadas.py` y compara con lo esperado. Lo esperado se calcula con Python puro a partir de lo sembrado,
así que no depende de la hora a la que lo corras.

| Persona | Equipos | Checada sembrada |
|---|---|---|
| uno | Norte | abierta de 2 h |
| dos | Norte y Sur | abierta de 13 h |
| sin equipo | ninguno | abierta de 2 h |
| cuatro | Sur | cerrada de 17 h (más de 16 h: horas no la cuentan, anomalía sí) |

Tres subcomandos: `sembrar`, `verificar` (solo lectura) y `limpiar`. Corre **dentro del contenedor del backend**, que ya tiene `app` y la conexión a la base.
Desde la raíz del repo, con el stack arriba (`docker compose up -d db backend`):

### Variante recomendada: sobre una copia de la base

No toca tu base. La copia se crea con `pg_dump`, se prueba y se borra.

```bash
# 1. Copia (tyakxa_erp no se modifica; solo se lee)
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE tyakxa_verif" \
  && pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | psql -U "$POSTGRES_USER" -d tyakxa_verif -q'

# 2. Sembrar y verificar, apuntando a la copia.
#    RECETA_BASE_ESPERADA hace que el script se niegue si la conexion no cae en tyakxa_verif.
for paso in sembrar verificar; do
  docker compose run --rm --no-deps -T \
    -e DB_NAME=tyakxa_verif -e RECETA_BASE_ESPERADA=tyakxa_verif -e PYTHONPATH=/app \
    -v "$PWD/docs/verificaciones/receta_checadas.py:/receta_checadas.py:ro" \
    --entrypoint python backend /receta_checadas.py "$paso"
done

# 3. Borrar la copia
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE tyakxa_verif"'
```

En la copia no hace falta `limpiar`: se borra la base completa.

### Variante directa: sobre la base del stack

Escribe en tu base (4 personas, 2 equipos y 4 checadas marcadas) y las borra al final. Úsala solo si no quieres copiar la base.

```bash
for paso in sembrar verificar limpiar; do
  docker compose run --rm --no-deps -T -e PYTHONPATH=/app \
    -v "$PWD/docs/verificaciones/receta_checadas.py:/receta_checadas.py:ro" \
    --entrypoint python backend /receta_checadas.py "$paso"
done
```

`limpiar` borra lo marcado y confirma con un conteo que quedó en cero. Si algo falla a medias, vuelve a correr `limpiar`.

## `receta_equipos.py`: equipos con baja lógica, historia, filtro y título propio

Comprueba, **por la API real** (cliente de Flask con un token de superusuario) y con las consultas reales, lo del lote 6. Siembra dos equipos, **«Manzanillo 1» y «Culiacán prueba»** (así, con acento), y una persona (`990101`) que
**pasa del uno al otro**: la API la da de alta en Manzanillo, la da de baja de ahí (baja lógica) y la agrega a Culiacán (membresía **nueva**). Como eso acaba de pasar hoy, lo único que se escribe a mano (SQL) es la
fecha de las membresías, para que el cambio haya sido a las 09:00 de «hace 2 días». Siembra 5 checadas en los 4 días previos a hoy (todas de días completos, así que no depende de la hora a la que corras) y recalcula los snapshots.

| Día | Checada | Equipo que se espera |
|---|---|---|
| hace 4 días | 10:00–18:00 | Manzanillo 1 |
| hace 3 días | 10:00–18:00 | Manzanillo 1 |
| hace 2 días (día del cambio) | 08:00–08:30, antes de las 09:00 | Manzanillo 1 |
| hace 2 días (día del cambio) | 10:00–17:00, después de las 09:00 | Culiacán prueba |
| hace 1 día | 10:00–18:00 | Culiacán prueba |

Subcomandos: `sembrar`, `verificar` (no escribe), `dar_de_baja_equipo` (da de baja «Culiacán prueba» **por la API** y comprueba que la historia sigue en pie) y `limpiar`. Verifica, en este orden: la baja es lógica
(la membresía vieja sigue, la nueva es otra fila, los listados solo traen lo vigente); cada marca cuenta en el equipo de **ese momento** (con los bordes: un minuto antes del cambio y el instante exacto); lo mismo por la API
`/kpi_snapshot/query`, con la etiqueta de cada equipo; el filtro `id_teams` en un KPI por persona (minutos de los días de A, de B, la unión sin contar dos veces y sin filtro); y el título propio (recortado al guardar,
rechazado con 400 si pasa de 80 caracteres o trae HTML, y lo guardado no cambia).

**Corre solo sobre una copia.** `sembrar` recalcula los snapshots de varios KPIs (también los de «Sin equipo» y de otra gente) y `limpiar` no los puede deshacer. Desde la raíz del repo, con el stack arriba:

```bash
# 1. Copia (tyakxa_erp no se modifica; solo se lee) y migraciones al dia sobre la copia
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE tyakxa_verif" \
  && pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | psql -U "$POSTGRES_USER" -d tyakxa_verif -q'
docker compose run --rm --no-deps -T -e PGDATABASE=tyakxa_verif db-migrate

# 2. Sembrar, verificar y dar de baja un equipo, apuntando a la copia
for paso in sembrar verificar dar_de_baja_equipo; do
  docker compose run --rm --no-deps -T \
    -e DB_NAME=tyakxa_verif -e RECETA_BASE_ESPERADA=tyakxa_verif -e PYTHONPATH=/app \
    -v "$PWD/docs/verificaciones/receta_equipos.py:/receta_equipos.py:ro" \
    --entrypoint python backend /receta_equipos.py "$paso"
done

# 3. Borrar la copia
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE tyakxa_verif"'
```

Resultado esperado (corrida del 2026-10-22 sobre una copia de `tyakxa_erp`): `verificar` termina en `RESULTADO: 23/23 OK` y `dar_de_baja_equipo` en `RESULTADO: 9/9 OK`. El paso `db-migrate` deja la copia con el esquema que se va a desplegar (incluido el índice parcial de `nm_team_user`); esta receta no vuelve a agregar a nadie al mismo equipo, así que también corre sin él, pero entonces
no prueba el esquema nuevo (con el índice viejo, esa alta repetida falla: lo cubren las pruebas automáticas, no esta receta). Cada línea es `OK` o `MAL` con lo esperado y lo obtenido; el esperado sale del diseño de la tabla de arriba, no de la implementación.

## Cómo leer el resultado

- Cada línea es `OK` o `MAL` con lo esperado y lo obtenido; el final dice `RESULTADO: n/n OK`.
- «Sin equipo» se compara con `>=`: si la base ya tenía otras checadas de gente sin equipo, saldrá mayor.
- Quien ya no está en turno sale en `0` en la consulta (la API lo omite con `ocultar_ceros`); también es válido que no tenga fila.

## Qué depende de la hora

Todo se calcula con `ahora_negocio()` (hora de pared GMT-6, la que usa el código), **no** con la hora del sistema, así que la zona de tu máquina no importa; sí importa que su reloj esté en hora.
Entre las 00:00 y las 01:00 de México, «hoy» puede cambiar entre `sembrar` y `verificar`, y una entrada de 13 h puede caer en el día anterior: el script compara contra fechas calculadas, no contra números fijos,
pero si ves un `MAL` en esa franja, repite la prueba pasada la 01:00. Si pasan más de ~10 horas entre `sembrar` y `verificar`, las checadas abiertas cambian de categoría (en turno → sin salida).

## Pestaña «Asistencias» del selector de KPI

Cómo ver la pestaña como superusuario y como un rol limitado (`adm_asistencias`). **Ninguna de las dos partes escribe en tu base** (`tyakxa_erp`).
Qué es la pestaña y por qué el módulo real de los siete KPIs sigue siendo `operaciones`: `docs/arquitectura-kpis.md`, §2.7.

### 1. Como superusuario, en el navegador

No hace falta preparar nada: el superusuario es el administrador de arranque (`admin1`) y las filas de `kpi_definition` de los siete KPIs ya existen (el backend las
siembra en cada arranque). `grupo` no es una columna: lo entrega el registry, así que **hay que reiniciar el backend** para que cargue el código nuevo (no toca datos).

1. `docker compose restart backend` (el frontend, Vite, toma los cambios solo).
2. Abre http://localhost:3010, entra como `admin1` y ve al Dashboard.
3. Abre el panel «Agregar gráfico», paso «Qué medir». En la fila de pestañas debe aparecer **Operaciones 12** y, justo a su derecha, **Asistencias 7**.
   - **Asistencias** trae los siete KPIs de checadas y ninguna sección «Combinables» (los siete tienen desglose). **Operaciones** ya no trae ninguno de ellos.
   - Elige un KPI de Asistencias: el botón Asistencias marca «1 elegido» y Operaciones no.
   - Escribe «turno» en el buscador: salen 2 KPIs, bajo Asistencias.
   - Combinar con unidades distintas sigue igual: con «Tiempo trabajado por empleado» (minutos) elegido, «Personas en turno por equipo» (cantidad) sale atenuado.
   - Con un KPI de Asistencias elegido y un rango sin datos (lo normal si tu base no tiene checadas), aparece «Ver ejemplo».
   - El nombre de la pestaña cambia con el idioma de la interfaz: Asistencias, Attendance, Presenças, Anwesenheit.

Los demás conteos (Inventario, Facturación…) son los de tu base; los de Operaciones y Asistencias son los del registry completo, que un superusuario ve entero.

### 2. Como `adm_asistencias`, sobre una copia

Tu base no tiene el rol `adm_asistencias` (en Comala se crea a mano en el Gestor de roles), así que hay que crearlo en algún lado: aquí, en una **copia** desechable.
`receta_pestana_asistencias.py` prepara el rol (lectura de `kpi_definition` con alcance Todos) y un usuario de prueba; los siete KPIs se asignan con la herramienta real
(`scripts.seed_kpi_permissions --perfil comala`), y `verificar` pide `GET /kpi_definition/` con la aplicación real como el superusuario y como ese rol. Comprueba lo que el
selector **recibiría**; cómo lo dibuja lo cubren las pruebas de node. Corre dentro del contenedor del backend, desde la raíz del repo, con el stack arriba:

```bash
# 1. Copia (tyakxa_erp no se modifica; solo se lee)
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE tyakxa_verif" \
  && pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | psql -U "$POSTGRES_USER" -d tyakxa_verif -q'

# 2. Preparar, asignar los siete KPIs (primero en seco) y verificar, apuntando a la copia.
#    RECETA_BASE_ESPERADA hace que el script se niegue a escribir si la conexion no cae en tyakxa_verif.
correr() {
  docker compose run --rm --no-deps -T -e DB_NAME=tyakxa_verif -e RECETA_BASE_ESPERADA=tyakxa_verif -e PYTHONPATH=/app \
    -v "$PWD/docs/verificaciones/receta_pestana_asistencias.py:/receta_pestana_asistencias.py:ro" --entrypoint python backend "$@"
}
correr /receta_pestana_asistencias.py preparar
correr -m scripts.seed_kpi_permissions --perfil comala --dry-run
correr -m scripts.seed_kpi_permissions --perfil comala
correr /receta_pestana_asistencias.py verificar

# 3. Borrar la copia
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE tyakxa_verif"'
```

El paso 1 imprime decenas de bloques `setval`: es el volcado restaurándose, no un error. `verificar` debe terminar en `TODO EN ORDEN`: el superusuario ve los 45 KPIs (Asistencias 7, Operaciones 12) y `adm_asistencias` ve **solo** los siete de checadas, todos con `grupo=asistencias`
y `modulo=operaciones` (una sola pestaña, Asistencias 7: sin Operaciones ni Variables). La copia queda con el usuario `asist.prueba` (clave `Prueba2026!`), pero el stack no la sirve: el proxy del
Vite apunta fijo a `backend:5001`, que usa tu base. Para ver esa pestaña **en el navegador** como `adm_asistencias` el rol tendría que existir en la base que sirve el stack, y eso sí es escribir en ella.
