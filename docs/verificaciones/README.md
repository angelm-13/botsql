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

## Cómo leer el resultado

- Cada línea es `OK` o `MAL` con lo esperado y lo obtenido; el final dice `RESULTADO: n/n OK`.
- «Sin equipo» se compara con `>=`: si la base ya tenía otras checadas de gente sin equipo, saldrá mayor.
- Quien ya no está en turno sale en `0` en la consulta (la API lo omite con `ocultar_ceros`); también es válido que no tenga fila.

## Qué depende de la hora

Todo se calcula con `ahora_negocio()` (hora de pared GMT-6, la que usa el código), **no** con la hora del sistema, así que la zona de tu máquina no importa; sí importa que su reloj esté en hora.
Entre las 00:00 y las 01:00 de México, «hoy» puede cambiar entre `sembrar` y `verificar`, y una entrada de 13 h puede caer en el día anterior: el script compara contra fechas calculadas, no contra números fijos,
pero si ves un `MAL` en esa franja, repite la prueba pasada la 01:00. Si pasan más de ~10 horas entre `sembrar` y `verificar`, las checadas abiertas cambian de categoría (en turno → sin salida).
