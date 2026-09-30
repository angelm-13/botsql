# Existencia inicial de adser y vales de baja

- **Script:** `backend/scripts/fix_adser_existencia_inicial.py` (`--dry-run`, idempotente).
- **Código:** `backend/app/services/warehouse_voucher_service.py` (`_registrar_baja`,
  `MOVIMIENTO_DE_BAJA`, `SE_CIERRA_AL_REGISTRAR`).
- **Pruebas:** `backend/tests/test_services/test_vale_de_baja_registra_lo_que_paso.py`.

Decisiones tomadas el 2026-09-29 (Alan: "que convenga mejor a los KPIs y al entorno del
negocio"), con lo que se midió para tomarlas.

## 1. La existencia inicial contaba como "en almacén" lo que no estaba

Al migrar adser, `inventory_stock` nació igual a `cantidad` (casi siempre 1), sin mirar
dónde está la pieza. Medido en adser-prod, con el libro de inventario vacío:

| Caso | Productos | Existencia contada |
|---|---|---|
| Préstamo vigente (renglón de salida sin cerrar, vale que no es baja) | 179 | 178 en 1 aunque están fuera |
| Destruidos o extraviados (catálogo `retirado` / `extraviado`) | 151 | 1 cada uno |

Dos consecuencias reales: (1) al devolver una herramienta prestada la existencia sube a 2
—una pieza que nunca estuvo descontada—, que es lo que dejaron los vales de prueba en dev;
y (2) los KPI de existencia (`articulos_bajo_stock`) y cualquier conteo de almacén salen
inflados en unas 330 piezas.

**Decisión:** corregirla con ajustes auditables. El script pone la existencia en lo que hay
de verdad —`retirado`/`extraviado` → 0; el resto → `cantidad` menos lo prestado—, **solo la
baja, nunca la sube**, con un movimiento de ajuste por producto (quién, cuándo y por qué
quedan en el libro, y se revierte con un ajuste inverso). Lo `danado` no se toca: no se sabe
si está en almacén.

Solo actúa sobre productos **sin movimientos en el libro** (la existencia *inicial*): uno que
ya operó la app tiene una existencia que refleja lo que pasó, y `cantidad` cambia con cada
movimiento, así que recalcular sobre ella no sería seguro. Por eso es idempotente.

## 2. Un vale de baja ya no exige que la herramienta esté en el almacén

Antes un vale de destrucción o extravío hacía lo mismo que uno de préstamo: sacar una unidad
del almacén. Con la herramienta que más se pierde —la que ya está en manos de alguien, con
existencia 0— se rechazaba con "existencia insuficiente" (verificado con una prueba).

**Ahora:**

1. Si el producto está **prestado**, ese préstamo se cierra (la herramienta ya no está con
   esa persona) y la existencia **no** se mueve. Se prefiere el préstamo del mismo
   responsable y luego el más antiguo; solo se cierran renglones completos, así que perder 2
   de un préstamo de 5 se rechaza en vez de inventar.
2. Lo que quede —la herramienta sí estaba en almacén— sale con el movimiento de baja del
   libro: `destroy` (destrucción) o `loss` (extravío), con el motivo del vale.
3. **Destrucción:** el renglón nace cerrado (lo destruido no vuelve) y el vale se deriva
   cerrado. **Extravío:** el renglón queda abierto hasta que la pieza aparezca —en el
   sistema anterior, 6 de 72 productos extraviados volvieron—, y entonces se devuelve por
   el camino de siempre (la existencia sube y el estado se limpia).

Sin cambios: **Dañado y Reparación** siguen siendo préstamo (siguen con alguien), y los
productos **serializados** siguen su camino (su estado es de la pieza).

## 3. Lo que se decidió NO hacer

- **Los 6 renglones gemelos que prod dejó abiertos** (vales 9, 19 y 112) se quedan como
  están. Los 2 con el producto en `SALIDA` (vale 112) son el préstamo vigente; los 4 con el
  producto `DAÑADO` (vale 9 y vale 19, que es de tipo Dañado) siguen visibles en "quién
  tiene qué" por la misma razón que Dañado se queda dentro: cuando hay duda, se ve de más
  antes que esconder.
- **Ausencias** (jornada, comida, permiso, vacaciones, maternidad): sin flujo propio. Adser
  tiene 0 registros de esos tipos y ningún KPI depende de ellos; se capturan, si hace falta,
  en la pantalla genérica de Incidencias. Queda como pendiente de producto.

## Pasos

Orden en cada ambiente (después del despliegue, que aplica las migraciones solo):

```bash
kubectl -n <ns> exec deploy/backend -- python scripts/fix_adser_existencia_inicial.py --dry-run
kubectl -n <ns> exec deploy/backend -- python scripts/fix_adser_existencia_inicial.py
kubectl -n <ns> exec deploy/backend -- python scripts/fix_adser_existencia_inicial.py --dry-run   # debe dar 0
```

El script reconoce el estado por el catálogo **y** por el texto histórico, así que no
depende de haber corrido antes la migración `20260929120000`.

Verificación: `SELECT sum(quantity) FROM inventory_stock` debe bajar en las unidades que
reportó el dry-run, y `inventory_ledger` debe tener un ajuste `Existencia inicial…` por
producto corregido.

## Estado

| Ambiente | Existencia inicial | Vales de baja |
|---|---|---|
| `tyakxa-dev` | ver commit | ver commit |
| `adser-prod` | pendiente (requiere OK de Alan) | llega con el despliegue |
