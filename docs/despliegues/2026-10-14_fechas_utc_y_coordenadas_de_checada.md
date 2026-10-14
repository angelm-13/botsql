# 2026-10-14 — Fechas en UTC con zona del negocio (-6) y coordenadas de checada

Dos cambios que van juntos en la misma rama. Ninguno requiere correr scripts
sobre datos: no hay backfill.

## 1. Convención de fechas (todos los clientes)

**Síntoma:** en la tabla de incidencias, `Fecha de creación` salía 6 h adelantada
(8:33 p.m. donde eran las 2:33 p.m.). Medido en comala-prod: Postgres corre en
UTC (el StatefulSet no fija `TZ`), `incident_date` se guarda en hora local (la
manda el dispositivo) y el backend corre con `TZ=America/Mexico_City`. La API
entregaba las fechas sin zona y la pantalla las tomaba por hora local.

**Convención (`backend/app/utils/tiempo.py`):**

| Tipo de fecha | Se guarda | La API la entrega | La pantalla |
|---|---|---|---|
| Auditoría: `creation_date`, `last_update_date`, `deletion_date` | UTC | `...Z` | convierte a -6 |
| Negocio: `incident_date`, cierres, vencimientos | hora de pared del cliente | sin zona, tal cual | la muestra tal cual |

- La sesión de la base se fija en UTC (`models/session.py`, `-c timezone=UTC`):
  `now()` es UTC en el clúster y también en el compose local (que traía hora de
  México).
- `a_iso_utc()` reemplaza a `to_json_value`/`.isoformat()` solo para las tres
  columnas de auditoría: 75 modelos y 7 servicios/rutas.
- Pantalla: `frontend/src/utils/fechas.js` (`formatearFechaHora`), usada en las
  45 pantallas genéricas y en seis vistas sueltas. Una sola zona, no la del
  navegador.
- Zona configurable sin tocar datos: `APP_TIMEZONE` (backend) y
  `VITE_APP_TIMEZONE` (frontend); por omisión `America/Mexico_City`.
- `IncidentService`: `incident_date`/cierre con zona (`-06:00`, `Z`) se
  convierten a hora de pared; antes se les quitaba la zona sin convertir. La
  validación de "fecha futura" y el cierre automático usan hora del negocio, no
  UTC (una incidencia podía fecharse hasta 6 h en el futuro sin rechazarse).
- `activity_log` y `notification` marcaban `deletion_date` con la hora local;
  ahora UTC como el resto.

### Qué NO cambia (deuda conocida)

- **Fechas de negocio de otras tablas** (`paid_at`, `delivered_date`,
  `received_confirmed_date`, etc.): cada servicio las escribe con su propio reloj
  (unos `utcnow`, otros hora local). No se tocaron; se unifican módulo por
  módulo cuando se revise cada uno.
- **Filas migradas de adser:** si `creation_date` vino de MySQL en hora local en
  vez de `now()`, se mostrarán 6 h atrasadas. `fix_adser_creation_date.py` las
  rellenó con `now()` (UTC), así que debería cuadrar; confirmarlo con una fila.
- `AppointmentsPage`/`PublicCalendarPage` tienen su propia zona por perfil: no
  se tocaron.
- `warehouse_voucher_service` mezcla `creation_date or incident_date` en un
  mismo campo: no se tocó.
- La zona no es por cliente todavía: si un cliente no está en UTC-6, hay que
  fijar `APP_TIMEZONE`/`VITE_APP_TIMEZONE` en su overlay.

## 2. Latitud, longitud y distancia en incidencias (checador)

Migración `20261014090000_coordenadas_y_distancia_en_incidencia.sql`: columnas
`latitude`, `longitude` (NUMERIC(10,7)) y `distance_m` (NUMERIC(10,2)) en
`incident`, nulas salvo en las checadas. Las llena n8n por `POST /incident/`
(antes viajaban dentro de `note` como JSON). La API valida rangos (latitud
±90, longitud ±180, distancia ≥ 0) y devuelve 400 `errors.invalid_field`.

- n8n debe mandar `incident_date` en hora local sin zona, o con su desfase
  (`-06:00`); también acepta `Z`.
- Los permisos por campo de las tres columnas los deriva el sembrado de
  `nm_field_permission` al reiniciar el backend; un rol que no sea admin debe
  tener lectura de `incident`.
- La tabla de incidencias muestra las tres columnas solo si la página trae al
  menos una checada.

## Verificación

- Backend: 2028 pasan, 0 fallan (SQLite). Contra Postgres local: la sesión
  reporta `UTC`, `creation_date` sale con `Z`, `incident_date` en UTC se guarda
  como hora local.
- Frontend: 164 pruebas de `node --test` (incluye `fechas.test.js`, que corre
  con `TZ=Asia/Tokyo` para probar que no depende del navegador). `npm test`
  falla en Node 24 por pasar directorios a `node --test` (ya fallaba antes).
- **Sin verificar en navegador** con una sesión real ni en un clúster.

## Promoción

1. Código y migración van en la imagen: sin pasos manuales.
2. Tras promover, abrir Incidencias: `creation_date` debe coincidir con
   `incident_date` a los pocos segundos (las checadas de n8n).
3. No hace falta tocar `k8s/base/postgres.yaml`: el UTC lo fija la conexión.
