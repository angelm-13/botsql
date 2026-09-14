-- incident_status en catalogo real es femenino ("abierta"/"cerrada"), no
-- masculino ("abierto"/"cerrado").
--
-- Que paso
-- --------
-- Los incidentes de prueba sembrados en el ambiente "sistema-test" quedaron
-- con incident_status = 'abierto' / 'cerrado' (masculino). El codigo que
-- calcula KPIs de incidentes (backend/app/kpis/registry.py,
-- INCIDENT_RESOLVED_STATUSES = {"resuelta", "cerrada"}) solo reconoce el
-- catalogo real en femenino ("abierta", "en_proceso", "resuelta", "cerrada",
-- "cancelada"). Con el valor masculino, esos incidentes no calzan en ningun
-- bucket esperado: no cuentan como resueltos ni se distinguen de un estado
-- desconocido, lo que rompe el KPI de tasa de resolucion para ese rango de
-- fechas.
--
-- Que hace esta migracion
-- ------------------------
-- Corrige unicamente los dos valores masculinos detectados
-- ("abierto" -> "abierta", "cerrado" -> "cerrada"). incident_status es
-- VARCHAR(20) libre (sin CHECK constraint en el esquema), asi que esto es
-- una limpieza de dato mal capturado, no un cambio de catalogo.
--
-- Reaplicable: el WHERE solo alcanza filas que sigan en masculino. Una fila
-- ya corregida -o insertada despues ya en femenino- no se vuelve a tocar en
-- la siguiente corrida.

BEGIN;

UPDATE incident
   SET incident_status = 'abierta',
       last_update_date = now()
 WHERE deletion_date IS NULL
   AND incident_status = 'abierto';

UPDATE incident
   SET incident_status = 'cerrada',
       last_update_date = now()
 WHERE deletion_date IS NULL
   AND incident_status = 'cerrado';

COMMIT;
