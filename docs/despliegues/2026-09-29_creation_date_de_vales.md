# `creation_date` de incidencias y renglones de vale: DEFAULT y rellenado

- **Migración:** `database/migrations/20260929110000_creation_date_por_defecto_en_vales.sql`
  (`ALTER COLUMN creation_date SET DEFAULT now()` en `incident` y
  `nm_incident_product`; idempotente, no toca filas).
- **Script de rellenado:** `backend/scripts/fix_adser_creation_date.py`
  (`--dry-run`, idempotente, solo llena `creation_date IS NULL`).
- **Contexto y decisión:** `docs/2026-09-28_creation_date_sin_default_en_incident.md`.

## Qué arregla

`init.sql` crea `creation_date` sin DEFAULT y el servicio de vales inserta por
su cuenta, así que **ningún vale de almacén guardaba cuándo se capturó** —ni
los migrados de adser ni los nuevos—. La migración cubre las altas futuras; el
script rellena lo que ya existe.

## De dónde sale cada fecha

| Fila | Fecha | Por qué |
|---|---|---|
| Incidencia migrada (139) | `fecha_creacion` del sistema anterior, incrustada en el script | En 123 de 139 cae el mismo día que la fecha del vale; es una hora de captura real |
| Renglón | `creation_date` de su vale | Un renglón se guarda junto con su vale |
| Incidencia sin par (capturada ya en el sistema nuevo) | `incident_date` | Es la única fecha que tiene; aproximación (medianoche) |

**No** se usa la `fecha_creacion` propia del renglón del sistema anterior: solo
tiene 16 valores distintos en 2 787 filas y en 2 105 va antes de la fecha del
vale; son sellos de carga masiva.

## Pasos

Aplica a cada ambiente (`tyakxa-dev` se despliega solo al hacer push a
`initAlan`; los clientes se promueven a mano, ver §7.1 de
`ARQUITECTURA_TYAKXA_TNY.md`). `<ns>` = `tyakxa-dev`, `adser-prod`, etc.

1. Desplegar la imagen. El initContainer `db-migrate` aplica la migración solo.
2. Dry-run y corrida real (el script solo tiene sentido en ambientes con datos
   migrados de adser; en otro cliente no hay pares que aplicar y solo usaría la
   fecha del vale):

   ```bash
   kubectl -n <ns> exec deploy/backend -- python scripts/fix_adser_creation_date.py --dry-run
   kubectl -n <ns> exec deploy/backend -- python scripts/fix_adser_creation_date.py
   ```

3. Verificar: `SELECT count(*) FROM incident WHERE creation_date IS NULL` y lo
   mismo en `nm_incident_product` deben dar 0. Una segunda corrida en
   `--dry-run` no debe encontrar nada.
4. Confirmar que el DEFAULT funciona con un alta nueva: levantar un vale desde
   la app y comprobar que trae `creation_date`.

## Estado

| Ambiente | Migración | Rellenado |
|---|---|---|
| `tyakxa-dev` | ver commit | ver commit |
| `adser-prod` | pendiente | pendiente (requiere OK de Alan) |
| `torredigital-prod`, `vidrioyaluminios-prod` | pendiente | no aplica (sin datos migrados de adser) |
