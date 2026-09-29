# Reconciliación de vales migrados de adser

- **Scripts:** `backend/scripts/sync_adser_cierre_de_gemelos_20260929.py` y
  `backend/scripts/fix_adser_estado_de_vales.py` (ambos con `--dry-run`, idempotentes).
- **Origen:** comparación de `tyakxa-dev` y `adser-prod` contra el respaldo `Sep2126`
  del sistema anterior, 2026-09-29.

## 1. Renglones cerrados en prod que el sistema anterior tiene abiertos (66)

adser-prod tiene **66 renglones de vale cerrados** (10 vales: 13, 27, 45, 50, 75, 95,
112, 113, 114, 116) que el sistema anterior tiene abiertos. Nadie dejó escrito el
criterio ni el script. Lo que se pudo comprobar:

- Los 66 tienen un renglón **gemelo** (mismo vale, producto y cantidad) que el sistema
  anterior sí cerró, y la fecha aplicada es la del gemelo: **66 de 66**, y es la
  **mínima** cuando hay varios gemelos.
- El sistema anterior, al devolverse una herramienta, cerraba **una** de las copias
  de un bloque guardado varias veces y dejaba las demás "abiertas".
- 57 de los 66 tienen el producto en `ENTRADA` (devuelto).

`sync_adser_cierre_de_gemelos_20260929.py` aplica **exactamente esos 66** (id + fecha
explícitos, como `sync_adser_devoluciones_20260921.py`). En adser-prod es un no-op.
No generaliza la regla, porque prod dejó fuera 6 renglones que también cumplen el
patrón y no se sabe por qué:

| Vale | Producto | Renglón abierto | Estado del producto |
|---|---|---|---|
| 9 | 350 | 536 | DAÑADO |
| 19 | 684, 685, 686 | 1528, 1529, 1530 | DAÑADO |
| 112 | 336 | 2507 | SALIDA |
| 112 | 2349 | 2504 | SALIDA |

En `tyakxa-dev` hay 72 candidatos (los 66 más estos 6). **Decisión pendiente** de
cuáles de los 6 son préstamos reales.

## 2. Estado de los vales

En la app el estado de un vale se **deriva** de sus renglones, no se captura. El sistema
anterior sí lo dejaba capturar y `migrate_adser.py` lo copió.

- **"Abierta" con todo devuelto: 14 vales** (67, 70, 83, 85, 99, 103, 116, 118, 119, 121,
  123, 126, 131, 136), en adser-prod y en dev tras cerrar los gemelos. La app solo
  re-deriva al devolver un renglón, así que nunca se corregirían solos.
  `fix_adser_estado_de_vales.py` los cierra con la fecha del último cierre, que es lo
  que hace la app. Solo cubre este caso.
- **"Cerrada" con renglones abiertos: 10 vales** (3, 7, 19, 48, 60, 64, 69, 73, 78, 90).
  **No se tocan.** 7 son de tipo Destrucción, Dañado o Extraviado: en el sistema
  anterior un vale cerrado con la herramienta "abierta" era la forma de registrar una
  baja.

## 3. "Quién tiene qué" ya no cuenta las bajas como préstamos

**Decisión del 2026-09-29 (Alan): excluir Destrucción y Extraviado; Dañado se queda
dentro.** Solo cambia código, no datos.

Antes, las consultas que cuentan "lo que está con alguien" contaban un renglón si era de
salida y no tenía `close_date`, **sin mirar el tipo del vale**. En adser-prod:

| Tipo del vale | Renglones "abiertos" | Vales |
|---|---|---|
| Préstamo Material | 156 | 112 |
| Destrucción | 80 | 5 |
| Extraviado | 66 | 3 |
| Dañado | 27 | 4 |

Eran 329 renglones "en manos de alguien", de los que 173 eran bajas. La persona con más
herramientas era un marcador (`ESTANCIA EN EL TALLER`, 169 renglones, todos de vales
de baja).

**Qué cambia.** `TIPOS_DE_BAJA` y `_vales_de_baja()` en `warehouse_voucher_service.py` son
la única definición, y las siete consultas siguientes la usan:

| Consulta | Antes | Ahora |
|---|---|---|
| Pantalla "Quién tiene qué" (`quien_tiene_que`) | contaba las bajas | las excluye |
| Vales vencidos (`vales_vencidos`) y el KPI de vencidos por responsable | contaban las bajas | las excluyen |
| Búsqueda de vales con pendientes y su conteo de renglones pendientes | contaban las bajas | las excluyen |
| Reporte de vales pendientes | contaba las bajas | las excluye |
| Quién tiene un producto ahora (trazabilidad de inventario) | contaba las bajas | las excluye |
| KPI "Material prestado actual" | excluía **Destrucción, Dañado y Extraviado** | excluye solo Destrucción y Extraviado; **Dañado ahora cuenta** |

Ese último cambio es deliberado: antes de esta decisión, el KPI escondía lo dañado como
"estado terminal", mientras la pantalla lo mostraba; ahora los dos dicen lo mismo.
Los reportes por estado (`_estado_del_renglon`) siguen etiquetando los tres tipos.

**El vale de baja no se esconde:** sigue abierto y consultable en la lista de vales; solo
deja de contarse como préstamo. El estado del vale sigue derivándose de sus renglones.

**Lo que no cubre.** El seguimiento de material por proyecto
(`project_management_service`) cuenta sus propios renglones abiertos y no se tocó. Y
"Dañado" sigue siendo ambiguo: si más adelante se sabe que un dañado ya no está con
quien lo dañó, basta con agregarlo a `TIPOS_DE_BAJA`.

## Pasos

Orden (en `tyakxa-dev`, tras el despliegue; en prod solo el segundo aplica algo):

```bash
kubectl -n <ns> exec deploy/backend -- python scripts/sync_adser_cierre_de_gemelos_20260929.py --dry-run
kubectl -n <ns> exec deploy/backend -- python scripts/sync_adser_cierre_de_gemelos_20260929.py
kubectl -n <ns> exec deploy/backend -- python scripts/fix_adser_estado_de_vales.py --dry-run
kubectl -n <ns> exec deploy/backend -- python scripts/fix_adser_estado_de_vales.py
```

## Estado

| Ambiente | Gemelos (66) | Estado de vales (14) |
|---|---|---|
| `tyakxa-dev` | aplicado 2026-09-29: 66 renglones cerrados | aplicado 2026-09-29: 14 vales cerrados |
| `adser-prod` | ya estaban (no-op) | pendiente (requiere OK de Alan) |
