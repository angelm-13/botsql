# Avisos de revisión de datos para Adser (campana del sistema)

- **Script:** `backend/scripts/notify_adser_revision_datos.py` (`--dry-run`, `--destinatario`, idempotente).
- **Pruebas:** `backend/tests/test_services/test_avisos_revision_datos_adser.py`.
- **Frontend:** `NotificationBell.css` (`white-space: pre-line`) para que las listas se lean.

Decisión de Alan (2026-09-30): los avisos los ve **solo `yesgo`** (Yessica González, rol
Gerente). No cambian ningún dato ni permiso: solo dicen qué revisar.

## Qué avisa (una notificación por tema, más un resumen)

| Aviso | Casos en adser-prod (medido 2026-09-30) | Qué se le pide |
|---|---|---|
| Préstamos abiertos de herramientas que figuran en el almacén | 29 renglones, 13 responsables: **28 «probablemente ya volvieron»** y **1 «parece vigente»** (pieza 320, PRENSA C 8", vale 100) | Confirmar dónde está; si ya volvió, «Marcar devuelto» en el vale. La lista va dividida para empezar por lo que casi seguro es solo un renglón sin cerrar |
| Préstamos del sistema anterior sin herramienta en el catálogo | 5 (vales 1 ×2, 3, 36, 96) | Si alguna sigue fuera, registrarla en un vale nuevo |
| Incidencia 90: el responsable cambió de nombre | 1 | Corregir el responsable si no es la misma persona |
| Vales abiertos sin ningún material | 6 (44, 120, 133, 134, 138, 139) | Cerrarlos o cancelarlos |
| Resumen | — | Explica lo anterior y dice que, si necesitan acceso o permiso, avisen a Alan Pérez |

Cada aviso se quita de la lista solo con el botón **«Enterado»**: sirve de recordatorio
hasta que lo confirman. El resumen se crea último para que, con el orden de la campana
(más reciente primero), quede arriba. Un tema sin casos no se avisa, y uno ya avisado (aunque
esté leído) no se repite.

## Pasos

Después de promover y de correr los scripts de datos (los avisos se calculan sobre los datos
ya corregidos):

```bash
kubectl -n <ns> exec deploy/backend -- python scripts/notify_adser_revision_datos.py --dry-run
kubectl -n <ns> exec deploy/backend -- python scripts/notify_adser_revision_datos.py
kubectl -n <ns> exec deploy/backend -- python scripts/notify_adser_revision_datos.py   # debe dar 0 creados
```

**No correr en `adser-prod` sin el OK de Alan:** son mensajes para personal de Adser. En dev,
para verlos tú mismo en la campana: `--destinatario admin1`.

## Estado

| Ambiente | Estado |
|---|---|
| Copia local de `adser-prod` (dump 2026-09-30) | ✅ corrido como `yesgo`: 4 temas + resumen; 2.ª corrida 0 |
| `tyakxa-dev` (imagen `de1aa56`) | ✅ 2026-09-30, para `admin1`: 3 temas + resumen (29 préstamos, divididos en 28 «probablemente ya volvieron» y 1 «parece vigente»; 5 sin herramienta; 6 vales vacíos; el de la incidencia 90 no aplica porque en dev la cuenta de Fernanda Contreras nunca se renombró); 2.ª corrida 0 |
| `adser-prod` (imagen `3f0f14d`) | ✅ 2026-10-01, para `yesgo` (id 34): dry-run sin escribir; corrida real 5 avisos creados (4 temas + resumen); 2.ª corrida 0. Confirmado por Alan: `yesgo` los ve en la campana. Conteos reales: **31** préstamos (28 «probablemente ya volvieron», 1 «parece vigente», **2 «sin evidencia»**: vale 140, MARRO y ESCALERA, de Victor Gonzalez), 5 sin herramienta, incidencia 90, 6 vales vacíos |

**Diferencia contra lo medido el 2026-09-30:** en adser-prod salieron 31 préstamos, no 29. Los 2 de
más (vale 140, MARRO y ESCALERA) son un **falso positivo del aviso, no un hueco del flujo**
(revisado el 2026-10-01 con `SELECT` en adser-prod): el vale 140 es el único creado en el sistema
nuevo (2026-09-30 21:13 hora local), sus dos renglones son de productos *fungibles* y son un préstamo
legítimo y vigente. El aviso detecta «préstamo abierto + `product.product_status = 'ENTRADA'`», pero
el sistema nuevo no cambia ese texto histórico al prestar (ver `warehouse_voucher_service.py`: solo se
escribe en vales de reparación/destrucción/dañado/extraviado), así que todo producto prestado en el
sistema nuevo cumple la condición. La consulta solo tiene sentido para préstamos **migrados**.
**Corregido (2026-10-01):**
- `SQL_CONTRADICCIONES` y `SQL_VALES_VACIOS` se acotan a los vales migrados con
  `ULTIMO_VALE_MIGRADO = 139` (un vale nuevo todavía sin renglones también habría salido como «vacío»).
  Tres pruebas nuevas lo vigilan, incluido el `%%` del `LIKE`, que con parámetros ya no admite un `%` suelto.
  21 pruebas del archivo en verde; las dos consultas ejecutan bien con parámetros en Postgres local.
- El aviso ya enviado a `yesgo` (sin leer) se corrigió en adser-prod con un `UPDATE` de título y mensaje
  (1 fila, mismo texto que genera el script corregido): ahora dice **29** préstamos (28 + 1), sin el vale 140.
  Los otros 4 avisos no se tocaron (ya estaban en 29/5/1/6 vales ≤ 139).
- Existencia del vale 140 verificada: MARRO y ESCALERA tienen un movimiento `loan −1` en el libro y
  existencia 0. `fix_adser_existencia_inicial.py` no los pisó porque solo toca productos sin movimientos.
- El script corregido **no está desplegado** en adser-prod (el pod tiene la versión de `3f0f14d`); no hace
  falta correrlo otra vez ahí. Llega con la siguiente promoción.

En dev los ve quien entre como `admin1` (campana de la barra superior); se quitan con «Enterado».

## Lo que se aprendió al probarlo

- La tabla `notification` tiene una restricción CHECK con una lista **cerrada** de tipos
  (`project_status_change`, `project_modified`, `activity_log_created`, `task_assigned`,
  `material_confirmed`, `custom`). Un primer intento con un tipo propio habría fallado al
  crear el primer aviso; se usa `custom` y los avisos se distinguen por `metadata->>'clave'`.
  Una prueba vigila que el tipo sea uno admitido.
- La campana pintaba el mensaje sin respetar saltos de línea; una lista se veía como un
  párrafo corrido. Con `white-space: pre-line` se lee en viñetas (verificado en el navegador
  con la app local).
- La división de los 29 préstamos sale de comparar, en el respaldo del sistema anterior, la fecha
  de última actualización de la pieza con la del préstamo: si el estado «en almacén» se marcó
  **después** del préstamo, alguien la regresó y solo faltó cerrar el renglón (28); si es
  **anterior**, el préstamo parece vigente (1). Esa fecha **no se puede calcular al correr el
  script**: `fix_adser_existencia_inicial.py` mueve la existencia y cambia `product.last_update_date`
  de 341 piezas, así que la clasificación queda fija en el script (`PROBABLEMENTE_YA_VOLVIO`,
  `PARECE_VIGENTE`). Una pieza que no esté en ninguna de las dos listas sale como «sin evidencia».
  Es una pista, no una certeza: por eso solo se avisa y no se cierra ningún renglón.
- Los 5 préstamos sin herramienta **no están en la base** (la migración los excluyó porque su
  producto no existe en el origen): sus datos están en el script, tomados del respaldo.
  Las otras tres consultas se calculan en vivo.
- Con el rol Gerente, `yesgo` recibe la campana sin más permisos: las rutas solo piden sesión
  (`@token_required`), no una fila de `entity_permission`.
