# Segunda promoción de adser-prod a `3f0f14d`

**Estado: EJECUTADA el 2026-09-30 a las 18:04–18:06 hora de México (00:04–00:06 UTC del 10-01), con el OK de
Alan. Verificada contra los valores esperados.** Overlay promovido en el commit `e4097cc`.

- **De:** `de1aa56` (la primera promoción, ver `2026-09-30_promocion_adser_prod.md`).
- **A:** `3f0f14d`, la misma versión que corría `tyakxa-dev` al promover. Las imágenes existen (el bot publicó
  «actualizar a 3f0f14d»).

## Qué entra (20 commits desde `de1aa56`: 14 de Ángel, 4 de Alan, 2 de Aurora)

- **Migraciones:** 3 nuevas (`20260929090000` relaja `priority`/`total_cost` de `proyect`; `20260930090000`
  menú de la bitácora diaria; `20260930100000` agrega `requires_maquila`, `id_user_delivered_to` y
  `custody_confirmed_date`) y 2 antiguas corregidas (`'taken'`/`'released'` en los constraints de `proyect_event`,
  que hacían tronar el replay en cualquier base con un evento real).
- **Vales:** entrega de una pieza a un operador y confirmación de recepción (no mueven existencia ni cierran el
  préstamo), y mejoras al PDF (código del renglón, precio, fecha larga, cliente). **No tocan** las bajas, los
  estados ni la existencia.
- **Cotizaciones/facturas:** el IVA por renglón ya no se pierde al convertir y la fecha de emisión es la del
  timbrado. Adser no se ve afectada (2 facturas marcador).
- **Proyectos:** maquila opcional, bitácora diaria, y otras correcciones de Jefe de taller y Almacenista.

## Una corrección propia antes de promover

`20260930090000_bitacora_diaria_entra_al_menu.sql` movía la pantalla al menú con `WHERE menu_location IS
DISTINCT FROM 'sidebar'`; como `db-migrate` corre todo en cada arranque, un administrador que la ocultara desde
el Gestor de roles la veía reaparecer en el siguiente reinicio. Ahora solo actúa sobre la fila que sigue como la dejó
la siembra (oculta, sin grupo ni etiqueta). Comprobado sobre una copia de prod (siembra → menú, idempotente;
oculta/engrane por el administrador → perdura; con la migración anterior se revertía) y con una prueba nueva en
`test_manager_wins.py`. Decisión de Alan: la pantalla **aparece** en el menú de Administrator y Jefe de taller; se
puede ocultar después desde el Gestor y se respeta.

## Ensayo previo (copia fresca de prod tras la primera promoción)

121 migraciones sin fallos ni avisos (110 s); suite completa 1537 pasaron / 103 omitidas / 0 fallidas; pruebas de
Postgres 63 + 39 pasaron (1 omitida documentada por Aurora); humo del código nuevo con vales reales sin errores.

## Registro de la ejecución

| Paso | Resultado |
|---|---|
| Antes de empezar | prod sin cambios desde la primera promoción (139 / 2745 / 2220, existencia 1881, 328 ajustes, 67 permisos dados de baja, 0 notificaciones, sin vales ni movimientos nuevos); dev corría `3f0f14d` con 0 errores |
| Respaldo | `adser_antes_de_3f0f14d_20260930_2359.sql`, 13 008 384 bytes, «dump complete», copia en `C:\Users\TDW2\respaldos_prod\` con el mismo SHA-256 (`9053d2d5…b88d`) |
| Overlay | `kubectl diff` mostró solo 6 líneas de imagen; archivo del VPS idéntico al del repo |
| Apply y rollout | los 4 despliegues en `3f0f14d`; **1 min 27 s** de rollout; `postgres-0` se reinició unos segundos por el cambio de imagen, datos intactos |
| Migraciones | 121 aplicadas, las 3 nuevas, «esquema al dia», **0 avisos** |
| Esquema | 3 columnas nuevas; `priority`/`total_cost` aceptan NULL; `requires_maquila = true` en los 4 proyectos existentes |
| Datos | 139 / 2745 / 2220, existencia 1881, 328 ajustes, 184 préstamos abiertos, estado de piezas 86 / 38 / 65, 21 KPIs: **sin cambios** |
| Salud | 6 pods 1/1, 0 errores en los logs de los 4 componentes, frontend HTTP 200, API 400 / 401 |
| Código nuevo en prod (solo lectura) | `documento_del_vale` sobre 8 vales reales sin errores y con código de renglón; «quién tiene qué» 22 personas / 184 renglones; `buscar_vales` 48 pendientes |

## Permisos

- **Acceso por pantalla** (`entity_permission`, 4 niveles por rol): huella idéntica antes y después
  (`b0355eed…`). La única diferencia es el **menú** de la «Bitácora diaria de taller» para Administrator y Jefe de
  taller (oculta → menú lateral), con el mismo acceso (4/4/4/0).
- **Permisos por campo vigentes:** 0 perdidos y 0 modificados; **10 nuevos** sobre los 3 campos de las columnas
  recién agregadas (ids 1588 a 1590, nivel de lectura), que el sistema deriva solo al arrancar.
- Siguen sin tocarse los 67 permisos dados de baja del Gestor de roles de Adser.

## Pendiente

- **Avisos a `yesgo`** (`2026-09-30_avisos_revision_datos_adser.md`): requieren el OK de Alan.
- **Conciliación de inventario:** `sembrar_existencia_inicial` no escribe renglón de apertura en el libro y
  `reconcile_product_stock` lo exige (hallazgo de Aurora, ya existía); es un endpoint de auditoría a pedido. Decisión
  de diseño pendiente.
- **Ángel:** si su rama `initAngm` tiene una copia de la migración de la bitácora, que traiga antes esta versión.
