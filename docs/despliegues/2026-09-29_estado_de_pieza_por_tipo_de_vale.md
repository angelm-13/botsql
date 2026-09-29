# Estado de la pieza: catálogo para lo migrado y efecto del tipo de vale

- **Migración:** `database/migrations/20260929120000_estado_de_pieza_al_catalogo.sql`
  (solo `UPDATE` de `product.id_inventory_status`; idempotente, no toca
  `product_status`).
- **Código:** `backend/app/services/warehouse_voucher_service.py`
  (`ESTADO_POR_TIPO`, `_marcar_estado_de_producto`, `_limpiar_estado_de_producto`).
- **Pruebas:** `backend/tests/test_services/test_vale_estado_del_producto.py`.

## Qué arregla

El sistema anterior mezclaba en `producto.estado` dos cosas: dirección de
movimiento (`ENTRADA`, `SALIDA`) y estado de la pieza (`DESTRUCCION`, `DAÑADO`,
`EQ. DAÑADOS`, `EXTRAVIADO`). Y fijaba ese estado según el **tipo de la
incidencia**: en adser, el último vale de 80 de 83 productos de tipo
"Destrucción" los dejó en `DESTRUCCION`, 27 de 37 de "Dañado" en `DAÑADO` y 65 de
72 de "Extraviado" en `EXTRAVIADO`.

El sistema nuevo perdió las dos cosas:

1. **Lo migrado:** `migrate_adser.py` dejó las piezas solo con el texto. Los 65
   `EXTRAVIADO` ya los llevó al catálogo `20260909100000`; los otros **124**
   (86 `DESTRUCCION`, 27 `DAÑADO`, 11 `EQ. DAÑADOS`) tenían `id_inventory_status`
   NULL y cualquier reporte por estado los contaba de menos.
2. **Lo nuevo:** un vale de "Extraviado" dejaba el producto como si nada: el tipo
   solo etiquetaba reportes.

## Qué hace ahora

**Migración** (`DESTRUCCION` → `retirado`, `DAÑADO`/`EQ. DAÑADOS` → `danado`): solo
piezas sin estado de catálogo, no pisa nada puesto a mano, no toca
`ENTRADA`/`SALIDA` (son dirección, no estado) y no hace nada si el catálogo no
tiene el código. Es el mismo patrón de `20260909100000`.

**Vales nuevos**, al abrirse (no un borrador; sí al autorizarlo):

| Tipo del vale | Estado de catálogo | Texto histórico |
|---|---|---|
| Reparacion | `en_reparacion` | `EN REPARACION` |
| Destruccion | `retirado` | `DESTRUCCION` |
| Dañado | `danado` | `DAÑADO` |
| Extraviado | `extraviado` | `EXTRAVIADO` |

Al **devolverse** un renglón: reparación y extraviado se limpian (lo reparado ya no
está en reparación; lo extraviado que aparece ya no está perdido), y el texto pasa a
`ENTRADA`. Dañado y destruido no cambian. Si alguien cambió el estado a mano entre
tanto, no se pisa.

## Lo que NO cubre (decisiones abiertas)

- **Productos serializados:** no se tocan. Su estado es de cada pieza
  (`inventory_asset.status`), y marcar el producto entero porque se perdió *un*
  desarmador dejaría perdidos a todos. adser no tiene piezas serializadas, así que
  hoy no se nota, pero un cliente que sí las use necesita ese camino aparte.
- **Existencias:** un vale de destrucción, daño o extravío sigue registrándose como
  préstamo (`loan`) en el libro de inventario, no como `destroy`/`damage`/`loss`,
  que el libro sí soporta. Cambiarlo altera cómo se cuentan las existencias y
  necesita la decisión del almacén.
- **Ausencias** (jornada, comida, permiso, vacaciones, maternidad): no tienen flujo
  propio; solo el CRUD genérico de Incidencias.

## Pasos

Igual que el resto (`ARQUITECTURA_TYAKXA_TNY.md` §7.1): `tyakxa-dev` se despliega
solo al hacer push a `initAlan`; la migración se aplica sola en el arranque. No hay
script que correr.

Verificación tras el despliegue:

```sql
SELECT p.product_status, s.inventory_status_code, count(*)
FROM product p LEFT JOIN inventory_status s USING (id_inventory_status)
WHERE p.deletion_date IS NULL GROUP BY 1, 2 ORDER BY 1;
```

Esperado en adser: `DESTRUCCION` → `retirado` (86), `DAÑADO` y `EQ. DAÑADOS` →
`danado` (38), `EXTRAVIADO` → `extraviado` (65), `ENTRADA`/`SALIDA` sin catálogo.

## Estado

| Ambiente | Migración |
|---|---|
| `tyakxa-dev` | ver commit |
| `adser-prod` | pendiente |
| resto | pendiente (no aplica: sin esos textos) |
