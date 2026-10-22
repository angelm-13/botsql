# Partida libre y material confirmado por Compras (2026-10-16)

Origen: observaciones de Adser sobre proyectos (2026-10-16). Dos bloques
independientes en el mismo despliegue; el segundo cambia **quién ve qué** en
todos los ambientes, así que tiene un paso previo en el Gestor.

## Qué cambia

**Partida (`proyect.folio`) = referencia libre.** Opcional, puede repetirse y no
se inventa nada (vacía se queda vacía).
- Se retira el índice único `uq_proyect_folio` y el relleno `OT-AAAA-NNNNN`
  (migraciones `20260911180000` y `20260918130000` editadas a propósito: se
  reaplican en cada arranque y, con partidas repetidas, el `CREATE UNIQUE INDEX`
  viejo habría tumbado el backend).
- Migración nueva `20261016090000_la_partida_es_una_referencia_libre.sql`: borra
  el índice único donde exista y deja uno normal para buscar.
- Pantalla: sin el respaldo `PRJ-…` (se muestra "—"); la lista busca también por
  partida; al editar, vaciar la partida la quita.

**Material de un proyecto autorizado.** `authorized → waiting_material` y
`waiting_material → in_progress` ya no son solo de Gerente:
- Capacidad nueva `project_supply` ("Confirmar material de proyectos"), catálogo
  en `registry.py`, migración `20261016100000_resembrar_project_supply.sql`
  (generada; solo agrega la fila de Administrator). **No se concede a ningún rol
  por omisión**: se asigna en el Gestor (hoy: Compras).
- Gerente conserva los dos pasos de respaldo con `project_authorization`.
- Tener una tarea capturada **ya no es obligatorio** para pasar a en proceso
  (se retiró `errors.project_requires_task`). El candado suave de material
  (`project_material_pending`, pide motivo) sigue igual.
- Avisos: al autorizar un proyecto se avisa a quien tenga `project_supply`; al
  pasar a en proceso, al responsable y al Jefe de taller que lo tomó.
- **Quien tiene `project_supply` (y no autoriza ni ejecuta) solo ve proyectos de
  autorizado en adelante** (autorizado, en espera, en proceso, detenido,
  completado, entregado), más los que él mismo creó o lidera. Es una regla de
  etapa del flujo, no una celda del Gestor: se suma a `proyect.scope_read`.

**Material parcial (2026-10-19).** Se puede arrancar con lo que ya llegó y se
completa solo con todo el material:
- `waiting_material → in_progress` con material incompleto: si ya llegó algo, pasa
  sin motivo y queda asentado "Arranca con material parcial: X de Y recibido"; si no
  ha llegado nada, pide motivo (candado suave de siempre).
- **Completar** con necesidades de material abiertas sin recibir da 409
  `errors.project_material_incomplete`. Una necesidad que ya no aplica se cancela en
  la lista de necesidades.
- Al recibir una orden, si el proyecto (en espera, en proceso o detenido) ya no
  tiene material pendiente, se avisa "Material completo" a responsable, supervisor y
  Compras, una sola vez. La lista de proyectos muestra "Material X/Y" mientras falte.
- Es una regla para todos los proyectos, sin columna nueva. **Medido antes de
  promover (solo lectura, 2026-10-19): adser-prod no tiene ningún proyecto en
  proceso con necesidades abiertas** (solo 2 autorizados, aún sin arrancar), así que
  ninguno queda trabado para completarse. Repetir la medición antes de promover.

**Proyectos sin maquila: ya no saltan a completado** (retira el atajo del
2026-09-30). Recorren los mismos estatus: autorizado → en espera de material
(Compras) → en proceso (Compras) → completado y entregado, estos dos por el
supervisor que lo lidera. El Jefe de taller no lo ve ni participa. La pantalla le
ofrece al supervisor, en esos proyectos, detener, reanudar y completar.

**Lo que se ve y lo que se edita lo manda el Gestor** (para un rol sin
`project_authorization` ni `project_execution`):
- `proyect.scope_read`: Todos = sin filtro (antes se ignoraba), Mis grupos = su
  equipo, Propios = lo propio.
- `update_project` filtra por dueño con `proyect.scope_update`, como ya hacía
  `delete_project`.

## Pasos, en orden

1. **Medir antes de promover** (solo lectura), en cada ambiente:
   ```
   kubectl -n <ns> exec deploy/backend -- python scripts/medir_alcance_de_proyectos.py
   ```
   Marca los roles que pasarían a ver todos los proyectos. En adser-prod,
   **Supervisor** está en Todos (lectura y actualización): con el código nuevo
   sus 4 usuarios verían (y podrían editar borradores de) todos los proyectos.
   Compras también aparece como "CAMBIA": ahí es lo que se busca.
2. En el Gestor de roles y permisos, de cada rol que **no** deba ver lo ajeno
   (Supervisor, en adser): `proyect` → Leer y Actualizar en **Propios**. Hacerlo
   antes o justo al promover; el código nuevo se apoya en esas celdas.
3. Promover el código (imágenes y overlay como siempre, ver
   `ARQUITECTURA_TYAKXA_TNY.md` §7.1). `db-migrate` aplica las migraciones; deben
   correr limpias dos veces seguidas (se probó con partidas repetidas guardadas).
4. Limpiar las partidas `OT-…` que puso el sistema (adser-prod: el proyecto 7).
   Primero en seco, luego real, con el respaldo en un volumen que persista:
   ```
   python scripts/limpiar_folios_autogenerados.py --dry-run
   python scripts/limpiar_folios_autogenerados.py --respaldo /uploads/folios_ot_2026-10-16.csv
   ```
   Solo toca partidas exactamente `OT-AAAA-NNNNN`; otra forma (`1`, `10130`,
   `OT-2026-0042`) no se toca. Idempotente.
5. En el Gestor, para quien confirma el material (Compras): capacidad
   `project_supply`, y `proyect` con Leer en Todos y Actualizar en Propios (el
   guardia de la ruta pide Actualizar; Propios no le deja editar lo ajeno).
   Después, cambiar de rol a Govanny (Jefe de taller → Compras).

## Cómo verificar

- Partida repetida: crear dos proyectos con la misma partida → ambos guardan (201).
- Compras: no ve borradores ajenos; ve los autorizados en adelante; puede pasar
  uno (con o sin maquila) a "en espera" y de ahí a "en proceso"; no puede
  autorizar, completar ni editar un proyecto ajeno.
- Sin maquila: tras "en proceso", el supervisor que lo creó lo completa y lo
  entrega; el Jefe de taller no lo ve en su lista.
- Supervisor (ya en Propios): solo ve los suyos.
- `SELECT indexname FROM pg_indexes WHERE tablename='proyect' AND indexname LIKE '%folio%'`
  → solo `idx_proyect_folio`.

## Si algo sale mal

- Un rol ve más proyectos de los debidos: es la celda `proyect.scope_read` del
  Gestor; pasarla a Propios. No hace falta revertir código.
- La partida: no hay nada que revertir; el índice único no se vuelve a crear.
- Respaldo de las partidas limpiadas: el CSV del paso 4 (id, partida anterior,
  título, quién lo creó).
