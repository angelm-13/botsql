# Ensayo general de la promoción a adser-prod (2026-09-30)

Se restauró un `pg_dump` de `adser-prod` tomado el 2026-09-30 (solo lectura) en un Postgres
local, se copió a una base desechable y sobre esa copia se corrió **la misma secuencia** que
propone `2026-09-25_kpis_adser_permisos.md`: las 118 migraciones como las aplica `db-migrate`
(`psql -v ON_ERROR_STOP=1`, en orden) y luego los scripts de datos. Nada se tocó en el clúster.

## Resultado

| Paso | Esperado (guía) | Medido en la copia de prod |
|---|---|---|
| 118 migraciones, en orden | sin error | 0 fallos, 0 avisos, 114 s |
| `20260929100000` índice de material | se crea (0 duplicados) | creado |
| `20260929110000` `DEFAULT now()` | en `incident` y `nm_incident_product` | ambos |
| `20260929120000` estado de pieza | 86 retirado, 38 danado, 65 extraviado | 86, 38 (27+11), 65 |
| `fix_adser_creation_date.py` | 139 incidencias, renglones | 139 / 2745, 2.ª corrida 0 |
| `fix_adser_start_date.py` | rellena lo vacío | 2745, sin NULL |
| `sync_adser_cierre_de_gemelos_20260929.py` | no hace nada (66 ya cerrados) | 0 cerrados, 66 ya cerrados |
| `fix_adser_estado_de_vales.py` | 14 vales (67, 70, 83, 85, 99, 103, 116, 118, 119, 121, 123, 126, 131, 136) | exactamente esos 14; 2.ª corrida 0 |
| `fix_adser_existencia_inicial.py` | 327 ajustes | 327 (178 prestados + 149 destruidos/extraviados), 2.ª corrida 0 |
| Backfill de snapshots (364 días) | `ok: True` | `ok: True`, 3015 filas, **5.5 s** |
| Préstamos abiertos que no son baja | ~183 | 183 |

Invariantes después de todo: existencia total 2209 → 1883 (−326: −327 de los ajustes y +1 de una
devolución de prueba), ninguna existencia negativa, ningún retirado/extraviado con existencia,
`cantidad` igual a `inventory_stock` en los 2220 productos, 0 incidencias y 0 renglones sin
`creation_date`/`start_date`.

## Lo que el ensayo encontró (y la guía no decía)

### 1. Lo que bloquea los pasos 6 a 8 (se omiten por decisión de Alan): al rol Administrator le faltan permisos en prod

`seed_kpi_permissions.py --dry-run` avisa «El rol 'Administrator' no tiene lectura de
kpi_definition». La guía manda **parar** ante un AVISO, y con razón: en adser-prod hay **38
filas de `entity_permission` del rol Administrator dadas de baja** (59 en total, contando las que
tienen reemplazo vivo) que en dev están vivas. Incluyen `kpi_definition`, `kpi_dashboard`,
`kpi_dashboard_widget`, `nm_permission_kpi`, `nm_incident_product`, `status`, `field`, `service`,
`theme`, `inventory_adjustment`, `incident_supervision`, `warehouse_voucher_confirm`,
`project_authorization`, `project_execution` y los módulos que Adser no usa (restaurante, POS,
laboratorio, documentos, citas, encuestas…).

- **No es un defecto del sembrado:** la bitácora (`event_log`) muestra, el 2026-09-14 entre las
  22:52 y las 23:58, 334 actualizaciones y 60 bajas de `created_by = 1` (`admin1`): alguien
  usando el Gestor de roles con la cuenta bootstrap.
- **Por qué no se arregla solo:** el sembrado inserta `WHERE NOT EXISTS` / `ON CONFLICT DO
  NOTHING`, que respeta la baja. Promover no las revive. Mismo patrón que el episodio del
  2026-09-07 (ver memoria `project_tyakxa_tny_permisos_id_fijo_bug`).
- **A quién afecta:** el guardia solo tiene bypass para `admin1`. `taroj` es Administrator sin
  bypass: sin esas filas no ve el tablero de KPI ni (para algunas) otras pantallas.
- **Verificado en la copia:** restaurar solo las 4 del tablero
  (`UPDATE entity_permission SET deletion_date = NULL WHERE id_permission = 1 AND entity_name IN
  ('kpi_definition','kpi_dashboard','kpi_dashboard_widget','nm_permission_kpi')`) deja el dry-run
  de permisos sin avisos (6 filas por insertar, 2.ª corrida 0) y la plantilla del tablero lista.
- **Decisión de Alan (2026-09-30): no se mueve nada del Gestor de roles de adser-prod.** Se
  dejan las 38 bajas como están. Se omiten los pasos 6, 7 y 8 de
  `2026-09-25_kpis_adser_permisos.md` (permisos de KPI y plantilla del tablero); `taroj` no
  verá el tablero hasta que Adser lo pida. Si hace falta activar algo en el Gestor de roles,
  Adser avisa a Alan y él decide.
- **La promoción por sí sola no mueve permisos de nadie** (medido en la copia, antes y después
  de aplicar las 118 migraciones): `entity_permission` 0 filas cambiadas; permisos por campo
  (`nm_field_permission`) 0 perdidos, 0 ganados y 0 con otro `control_type` (1578 filas
  vivas antes y después). Las +981 filas que crecen son registros ya dados de baja que el
  sembrado agrega en cada arranque.
- Se sigue corriendo el backfill de snapshots (paso 5): no depende de permisos.

### 2. Préstamos abiertos que se contradicen con el estado de la pieza

29 renglones abiertos (13 responsables, desde 2025-05-05 hasta 2026-06-30) cuyo producto dice
`ENTRADA` (en el almacén). El sistema anterior ya los traía así. `fix_adser_existencia_inicial.py`
**los resta** como a los demás, a propósito: si se excluyeran, el día que alguien devuelva el
renglón la existencia subiría a 2 (se probó en la copia: devolver uno pasa de 0 a 1, no a 2).
Si Adser confirma que siguen en el almacén, basta devolver el renglón en el vale.

### 2b. Estados de las piezas contra sus vales (medido 2026-09-30 en la copia de prod)

El texto de estado es idéntico al del sistema anterior en las 2220 piezas y solo hay seis
valores (sin erratas): `ENTRADA` 1901, `SALIDA` 130, `DESTRUCCION` 86, `EXTRAVIADO` 65, `DAÑADO` 27,
`EQ. DAÑADOS` 11. Contra lo que dicen los vales:

| Estado | Piezas | Respaldado por sus vales | Excepciones |
|---|---|---|---|
| `EXTRAVIADO` | 65 | 65 con renglón de Extraviado abierto | ninguna |
| `DAÑADO` | 27 | 27 con renglón de Dañado abierto | 1 además tiene un préstamo abierto |
| `EQ. DAÑADOS` | 11 | sin vales (estado puesto a nivel de pieza) | propio del sistema anterior |
| `DESTRUCCION` | 86 | 80 con renglón de Destrucción abierto | 6 sin ningún vale |
| `SALIDA` | 130 | 123 con préstamo abierto | 7 sin préstamo abierto (ver abajo) |
| `ENTRADA` | 1901 | 1872 sin préstamo abierto | 29 con préstamo abierto (ya avisados) |

- **7 piezas en `SALIDA` sin préstamo abierto:** 6 tienen todos sus préstamos ya devueltos y el
  estado quedó sin actualizar (el sistema anterior no lo reponía): 72, 169, 283, 1304, 1416 y
  2277. La 7.ª es la **736 (CRUZETA)**, ver el siguiente punto.
- **Un préstamo abierto del legado que se perdió en prod: CRUZETA (pieza 736), vale 75, a nombre de
  Mario.** El legado tenía 2 renglones abiertos (1489 y 1495, una captura doble del mismo
  préstamo). En prod el 1489 no existe y el 1495 está dado de baja (2026-09-22), así que la pieza
  quedó en `SALIDA` **sin ningún renglón vivo**. Es el único caso: de los 443 préstamos abiertos
  del legado, 395 conservan su renglón, 41 conservan un gemelo vivo de la misma pieza en el vale,
  5 eran de productos inexistentes y 2 son este. La limpieza de gemelos quitó los dos en lugar de
  dejar uno.
- **Pieza 249 (BROCA PARA CONCRETO 5/8):** tiene abiertos a la vez un préstamo (vale 128) y un
  extravío (vale 64): apareció y se volvió a prestar sin cerrar el extravío.

### 3. Otros puntos para Adser (no bloquean)

- **5 préstamos abiertos de productos que no existen en el legado** (vales 1 ×2, 3, 36 y 96,
  renglones 85, 117, 145, 743, 1998): el script de migración los excluyó por diseño (producto
  inexistente en origen). Son herramientas posiblemente fuera sin registro visible.
- **6 vales «abierta» sin ningún renglón** (44, 120, 133, 134, 138, 139; tampoco tenían en el
  legado): cuentan como pendientes sin nada que devolver.
- **Incidencia 90:** era de Fernanda Contreras; la cuenta 2 se renombró a «Oscar Javier».
- **Duplicados de renglones:** 28 grupos / 62 sobrantes idénticos, todos **ya cerrados**: solo
  ensucian el historial, no afectan «quién tiene qué». Se dejan.
- **`incident_date` es confiable:** coincide con `fecha_incidente` del legado en las 139
  incidencias (0 diferencias), lo que cierra la duda que frenaba la tabla «Material prestado
  ahora» de la plantilla del tablero.
