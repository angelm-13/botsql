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

## 3. Problema abierto: "quién tiene qué" cuenta bajas como préstamos

`quien_tiene_que` y el KPI de material prestado cuentan un renglón como "alguien lo
tiene" si es de salida y no tiene `close_date`, **sin mirar el tipo del vale**. En
adser-prod:

| Tipo del vale | Renglones "abiertos" | Vales |
|---|---|---|
| Préstamo Material | 156 | 112 |
| Destrucción | 80 | 5 |
| Extraviado | 66 | 3 |
| Dañado | 27 | 4 |

De 329 renglones que hoy cuentan como en manos de alguien, **173 son de vales de baja**
(destruido, perdido o dañado). Solo 156 son préstamos reales. **Decisión pendiente** de
cómo contar: excluir los tipos de baja de "quién tiene qué", cerrar esos renglones al
registrar la baja, o distinguir "dañado, todavía lo tiene" de "destruido/extraviado".

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
