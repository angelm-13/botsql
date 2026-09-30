# Promoción de adser-prod a `de1aa56`

**Estado: EJECUTADA el 2026-09-30, 23:22–23:27 UTC (17:22–17:27 hora de México), con el OK de
Alan. Pasos 0 a 5 hechos y verificados; el paso 6 (avisos a `yesgo`) queda pendiente de su OK
aparte.** Overlay promovido en el commit `fb674ae`.

## Registro de la ejecución

| Paso | Resultado |
|---|---|
| Antes de empezar | prod idéntico al ensayo (139 / 2745 / 2220, 67 permisos dados de baja, 0 notificaciones, mismas fechas de última modificación) |
| 0 Respaldo | `adser_antes_de_de1aa56_20260930_2320.sql`, 12 574 047 bytes, termina en «dump complete»; copia local en `C:\Users\TDW2\respaldos_prod\` con el mismo SHA-256 (`d0b68a9c…822f`) |
| 1 Overlay | `kubectl diff` mostró **solo** 6 líneas de imagen; archivo del VPS idéntico al del repo |
| 2 Apply y rollout | backend, celery-worker, celery-beat y frontend en `de1aa56`; **1 min 44 s** de rollout (el backend estuvo sin servicio ~1.5 min); `postgres-0` se reinició unos segundos por el cambio de imagen, con los datos intactos; 118 migraciones, las 3 nuevas, «esquema al dia», **0 avisos** |
| 2 Verificación | índice `uq_material_identidad` creado, `DEFAULT now()` en ambas tablas, 21 KPIs, estado de piezas 86 retirado / 27+11 dañado / 65 extraviado |
| 3a `creation_date` | 139 incidencias, 2745 renglones; 2.ª corrida 0 |
| 3b `start_date` | 2745 renglones |
| 3-bis renglón 1495 | `UPDATE 1` (CRUZETA, vale 75) |
| 3c gemelos | en seco: 0 cerrados, 66 ya cerrados (no se corrió sin `--dry-run`) |
| 3d estado de vales | exactamente los 14 vales esperados; 2.ª corrida 0 |
| 3e existencia | **328** ajustes (179 prestados + 149), 0 fallidos; 2.ª corrida 0 |
| 4 Backfill de KPI | `ok: True`, 3014 filas, 8.9 s |
| 5 Verificación | existencia 1881, ajustes 328 / −328, sin negativos, `cantidad` = existencia, 0 sin fechas, **184** préstamos abiertos, 6 vales vacíos (44, 120, 133, 134, 138, 139), CRUZETA 0 / 1, permisos dados de baja **67 (sin cambios)**, frontend HTTP 200, 0 errores en los logs de los 4 componentes, API 400 / 401 como debe |

**No incluido en esta promoción:** desde `de1aa56` entraron al repo más cambios (Ángel y otros:
5 migraciones, cambios al servicio de vales y a modelos). Van en una promoción aparte, con su propio
ensayo sobre una copia de prod.

*(Lo que sigue es el runbook tal como se preparó, para consulta.)*

- **De:** `b21a793` (lo que corre hoy, verificado en el clúster).
- **A:** `de1aa56`, **la misma versión que probó `tyakxa-dev`**. Las 4 imágenes existen: el bot
  solo publica «actualizar a de1aa56» cuando terminaron todas las del build, incluido el
  frontend de adser (`needs: [backend-and-worker, frontend-por-cliente]`).
- **Qué cambia en el rango (80 commits):** tres migraciones, ningún modelo y ningún cambio en
  `k8s/base`. Por eso basta copiar el `kustomization.yaml` del overlay al VPS.
- **Permisos:** no se mueven (decisión de Alan). Se **omiten** los pasos 6, 7 y 8 de
  `2026-09-25_kpis_adser_permisos.md`. Medido en una copia de prod: la promoción no cambia
  ninguna fila de `entity_permission` ni ningún permiso por campo efectivo.

## Verificado hoy antes de empezar (solo lectura)

| Comprobación | Resultado |
|---|---|
| Versión en adser-prod | `b21a793`, 6 pods 1/1 |
| Datos de prod vs. la copia usada en el ensayo | idénticos: 139 incidencias, 2745 renglones, 2220 productos, 12 usuarios con login, 67 permisos dados de baja, 0 notificaciones, 0 movimientos de inventario; misma última modificación en incidencias, productos y usuarios |
| Espacio en el VPS | 8.8 GB libres; el respaldo pesa ~13 MB |
| Ensayo general en copia de prod | 118 migraciones sin fallos y todos los scripts con el resultado esperado (`2026-09-30_ensayo_general_adser.md`) |

**Antes de ejecutar, repetir la comprobación de deriva** (los conteos de arriba): si alguien
capturó datos entre hoy y la ventana, los números esperados de abajo cambian.

## Ventana y aviso a Adser

- **Habrá una ventana sin servicio**: el backend usa estrategia `Recreate` (por el volumen de
  `/uploads`), y mientras corren las 118 migraciones (~2 min en el ensayo) y arranca el pod
  nuevo no hay API. Contar ~5–10 min, más los scripts de datos (segundos).
- **Elegir un horario de poco uso** (el último vale migrado es del 15-ago, así que el uso
  real es bajo) y **avisar a Adser antes**. Borrador para que Alan lo envíe:

  > Hola, el [día] a las [hora] actualizaremos el sistema de Adser. Estará fuera de servicio
  > unos 10 minutos. Después verán: los 14 vales que ya estaban todos devueltos pasan a
  > cerrados (bajan los «pendientes»); «Material prestado» ya cuenta lo dañado y deja fuera lo
  > destruido y lo extraviado; la existencia baja en 328 unidades que figuraban en el
  > almacén estando prestadas, destruidas o extraviadas; los vales y renglones migrados ganan
  > su fecha de captura; y Yessica González recibirá en la campana cuatro avisos de datos que
  > solo ustedes pueden confirmar. No se cambia ningún permiso.

## Pasos (en este orden; cada script con `--dry-run` antes)

### 0. Respaldo — obligatorio, no pasar al paso 1 sin esto

```bash
kubectl -n adser-prod exec statefulset/postgres -- sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > ~/adser_antes_de_de1aa56_$(date +%Y%m%d_%H%M).sql
ls -l ~/adser_antes_de_de1aa56_*.sql          # megabytes, no 0 bytes
tail -n 3 ~/adser_antes_de_de1aa56_*.sql      # debe terminar en "PostgreSQL database dump complete"
```

Copiarlo **fuera del clúster y fuera de OneDrive**: contiene datos personales (RFC, CURP, NSS)
y hashes de contraseña, y la carpeta Escritorio de esta máquina se sincroniza.

```powershell
scp 168.231.67.33:~/adser_antes_de_de1aa56_*.sql C:\Users\TDW2\respaldos_prod\
```

### 1. Promover la imagen (en el repo)

El diff ya está preparado en `k8s/overlays/adser-prod/kustomization.yaml` (los 4 `newTag`:
`b21a793` → `de1aa56`, y `b21a793-adser-prod` → `de1aa56-adser-prod`).

```bash
git add k8s/overlays/adser-prod/kustomization.yaml
git commit -m "deploy(adser-prod): promover a de1aa56 (misma version que probo tyakxa-dev)"
git fetch && git pull --rebase origin initAlan && git push origin initAlan
scp k8s/overlays/adser-prod/kustomization.yaml 168.231.67.33:/home/alanp/tyakxa_tny/k8s/overlays/adser-prod/kustomization.yaml
```

### 2. Aplicar y esperar el rollout

```bash
cd /home/alanp/tyakxa_tny
kubectl apply -k k8s/overlays/adser-prod
kubectl -n adser-prod rollout status deployment/backend --timeout=600s
kubectl -n adser-prod rollout status deployment/celery-worker
kubectl -n adser-prod rollout status deployment/celery-beat
kubectl -n adser-prod rollout status deployment/frontend
kubectl -n adser-prod logs deployment/backend -c db-migrate | grep -E "20260929100000|20260929110000|20260929120000|esquema al dia|WARNING"
```

Esperado: las tres migraciones, `db-migrate: esquema al dia` y **ningún** `WARNING` (un aviso de
duplicados en `material` significaría que el índice no se creó; en la copia dio 0 duplicados).
Si un pod se queda en `Pending`/`ImagePullBackOff`, ver «Contingencias».

Verificar el estado de las piezas (esperado: `DESTRUCCION`→`retirado` 86, `DAÑADO` y
`EQ. DAÑADOS`→`danado` 27+11, `EXTRAVIADO`→`extraviado` 65):

```bash
kubectl -n adser-prod exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT p.product_status, s.inventory_status_code, count(*)
FROM product p LEFT JOIN inventory_status s USING (id_inventory_status)
WHERE p.deletion_date IS NULL GROUP BY 1, 2 ORDER BY 1;
SQL
```

### 3. Scripts de datos

Siempre `--dry-run` primero, comparar con lo esperado, y solo entonces sin `--dry-run`. Si el
dry-run no da lo esperado, **parar**.

| # | Script | Dry-run esperado | Después |
|---|---|---|---|
| 3a | `fix_adser_creation_date.py` | 139 incidencias, 2745 renglones, 0 sin par | 2.ª corrida en seco: 0 |
| 3b | `fix_adser_start_date.py` | 2745 renglones | sin NULL |
| 3-bis | restaurar el renglón 1495 (CRUZETA, vale 75), **antes de 3e** (OK de Alan 2026-09-30) | `UPDATE 1`: el renglón está dado de baja desde 2026-09-22 y es el único préstamo abierto del legado que se perdió; ver `2026-09-30_ensayo_general_adser.md` §2b | la pieza 736 vuelve a figurar prestada y 3e le resta su unidad |
| 3c | `sync_adser_cierre_de_gemelos_20260929.py` | 0 cerrados (66 ya cerrados) | no hace falta correrlo sin `--dry-run` |
| 3d | `fix_adser_estado_de_vales.py` | exactamente 14 vales: 67, 70, 83, 85, 99, 103, 116, 118, 119, 121, 123, 126, 131, 136 | 2.ª corrida: 0 |
| 3e | `fix_adser_existencia_inicial.py` | **328** ajustes con el 3-bis hecho (179 prestados + 149 destruidos/extraviados), 0 omitidos | 2.ª corrida: 0 |

```bash
kubectl -n adser-prod exec deploy/backend -- python scripts/<script>.py --dry-run
kubectl -n adser-prod exec deploy/backend -- python scripts/<script>.py
kubectl -n adser-prod exec deploy/backend -- python scripts/<script>.py --dry-run   # debe dar 0
```

El paso 3-bis es un `UPDATE` de una fila (probado en la copia: la pieza 736 vuelve a figurar
prestada y 3e le resta su unidad). Con él hecho, los números de 3e y del paso 5 ya lo incluyen:
**328** ajustes (179 prestados + 149), existencia total **1881**, ajustes **328 / -328** y
**184** préstamos abiertos. Sin 3-bis serían 327, 1882, 327 / -327 y 183.

```bash
kubectl -n adser-prod exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
UPDATE nm_incident_product SET deletion_date = NULL WHERE id_nm_incident_product = 1495 AND deletion_date IS NOT NULL;
SQL
# reversa: UPDATE nm_incident_product SET deletion_date = '2026-09-22' WHERE id_nm_incident_product = 1495;
```

### 4. Backfill de snapshots de KPI (después del 3d)

```bash
kubectl -n adser-prod exec deployment/backend -- python -c "
from datetime import date, timedelta
from app.jobs.tasks_kpis import recalcular_kpi_snapshots_rango
hoy = date.today()
print(recalcular_kpi_snapshots_rango(hoy - timedelta(days=364), hoy))
"
```

Esperado: `ok: True`, ~3015 filas, unos 6 segundos.

### 5. Verificación (solo lectura)

```bash
kubectl -n adser-prod exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' <<'SQL'
select 'existencia total (esperado 1881 = 2209 - 328): ' || sum(quantity) from inventory_stock;
select 'ajustes Existencia inicial / suma (328 / -328): ' || count(*) || ' / ' || sum(quantity_delta) from inventory_ledger where reason like 'Existencia inicial%';
select 'existencia negativa (0): ' || count(*) from inventory_stock where quantity < 0;
select 'cantidad distinta de existencia (0): ' || count(*) from product p join (select id_product, sum(quantity) q from inventory_stock group by 1) s using (id_product) where p.cantidad is distinct from s.q and p.deletion_date is null;
select 'incidencias sin creation_date (0): ' || count(*) from incident where creation_date is null;
select 'renglones vivos sin creation_date / start_date (0 / 0): ' || count(*) filter (where creation_date is null) || ' / ' || count(*) filter (where start_date is null) from nm_incident_product where deletion_date is null;
select 'prestamos abiertos que no son baja (184 con el 3-bis): ' || count(*) from nm_incident_product r join incident i using (id_incident) join incident_type t on t.id_incident_type = i.id_incident_type where r.deletion_date is null and i.deletion_date is null and lower(r.direction) = 'salida' and (r.close_date is null or r.close_date < timestamp '2000-01-01') and lower(btrim(t.incident_type_description)) not in ('destruccion', 'destrucción', 'extraviado');
select 'vales abiertos sin renglones (6: 44,120,133,134,138,139): ' || count(*) from incident i where i.deletion_date is null and lower(i.incident_status) like 'abiert%' and not exists (select 1 from nm_incident_product r where r.id_incident = i.id_incident and r.deletion_date is null);
SQL
curl -s -o /dev/null -w "frontend https://adser.torredigital.mx -> HTTP %{http_code}\n" https://adser.torredigital.mx/
```

### 6. Avisos a Yessica González (solo con el OK de Alan)

Detalle en `2026-09-30_avisos_revision_datos_adser.md`.

```bash
kubectl -n adser-prod exec deploy/backend -- python scripts/notify_adser_revision_datos.py --dry-run
kubectl -n adser-prod exec deploy/backend -- python scripts/notify_adser_revision_datos.py
kubectl -n adser-prod exec deploy/backend -- python scripts/notify_adser_revision_datos.py   # debe crear 0
```

Esperado: 4 temas + resumen (29 préstamos, divididos en 28 «probablemente ya volvieron» y 1
«parece vigente»; 5 sin herramienta; incidencia 90; 6 vales vacíos).

## Lo que NO se hace

- No se mueven permisos del Gestor de roles. `taroj` no verá el tablero de KPI hasta que Adser
  lo pida.
- No se corre `seed_kpi_permissions` ni `seed_kpi_dashboard_template`.
- No se borran los 62 renglones duplicados (todos ya cerrados; solo ensucian el historial).
- No se tocan los 29 préstamos que se contradicen con el estado: se avisan.

## Reversa

Los scripts de datos y la migración `20260929120000` **no se deshacen al volver a la imagen
anterior**; el respaldo es la única marcha atrás completa y **pierde todo lo capturado desde
que se tomó**. Solo con decisión de Alan en el momento:

```bash
kubectl -n adser-prod scale deployment/backend deployment/celery-worker deployment/celery-beat --replicas=0
kubectl -n adser-prod exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"'
kubectl -n adser-prod exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < ~/adser_antes_de_de1aa56_<fecha>.sql
# volver el overlay a b21a793 (4 newTag), scp y kubectl apply -k; luego escalar de nuevo a 1
```

Para deshacer **solo** la existencia inicial, sin restaurar: cada ajuste queda en el libro y
se revierte con un ajuste inverso (`inventory_ledger`, motivo «Existencia inicial…»).

## Contingencias

- **Pod en `Pending` (CPU):** patrón conocido del clúster al desplegar. Buscar el nodo del PV de
  `postgres-0` y borrar ahí el primer pod sin PVC que compita (casi siempre `celery-worker`);
  puede repetirse. Ver memoria `project_tyakxa_tny_cpu_scheduling_cluster`.
- **`ImagePullBackOff`:** la imagen no existe o falta el `ghcr-pull-secret`. Confirmar el tag.
- **`db-migrate` falla:** el backend no arranca y no se corrió ningún script de datos. Leer
  `kubectl -n adser-prod logs deployment/backend -c db-migrate`; no avanzar al paso 3.
