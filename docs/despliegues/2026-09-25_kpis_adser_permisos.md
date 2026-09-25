# Adser: asignar KPIs a Administrator (`nm_permission_kpi`)

- **Script:** `backend/scripts/seed_kpi_permissions.py`, con el perfil `adser`.
- **Qué hace:** da a **Administrator** (en Adser, `taroj`) dos KPIs:
  - `articulos_bajo_stock`
  - `incidentes_resueltos_por_empleado`

  `vales_vencidos_por_responsable` queda fuera a propósito: en Adser
  `due_date` viene vacío y el KPI saldría siempre en cero. Almacenista no
  cambia.
- **No toca `ROLES` ni `entity_permission`:** Administrator ya tiene el
  módulo `kpis` (la capa 1). El script solo agrega la capa 2, `puede_ver`
  por KPI.
- **Sobrevive a reinicios:** ninguna migración toca `nm_permission_kpi`. Se
  verificó en local que las filas siguen después de `db-migrate` y de
  reiniciar el backend.

## Por qué hace falta

`taroj` **no es superusuario**: solo lo es el usuario de
`BOOTSTRAP_ADMIN_USERNAME` (`backend/app/routes/auth.py:99-105`). Sin filas
en `nm_permission_kpi`, el Dashboard le dice "No tienes KPIs asignados",
aunque su rol tenga el módulo.

## Requisitos previos

1. **`adser-prod` debe correr una imagen que traiga el script y la regla de
   agregación** (`4c36348` o posterior). Hoy el overlay está en `0bf9d69`,
   que no tiene ninguno de los dos. Hay que promoverlo según §7.1 de
   `ARQUITECTURA_TYAKXA_TNY.md` a una imagen construida después de subir este
   cambio.
2. **Backfill de snapshots** después de promover, según
   `2026-09-25_kpi_agregacion.md` (paso 3). Sin él,
   `incidentes_resueltos_por_empleado` sale vacío para todo lo anterior al
   despliegue.

Comprobación rápida de que la imagen trae el script:

```bash
kubectl -n adser-prod exec deployment/backend -- ls scripts/seed_kpi_permissions.py
```

## Pasos

### 1. Dry-run (no escribe nada)

```bash
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_permissions --perfil adser --dry-run
```

Salida esperada en una base sin asignaciones previas:

```
Perfil 'adser' (dry-run: no se escribe nada):
  Administrator        articulos_bajo_stock                          INSERTAR
  Administrator        incidentes_resueltos_por_empleado             INSERTAR
Se insertarian: 2 fila(s) en nm_permission_kpi.
```

Si aparece `ROL INEXISTENTE` o un `AVISO`, parar y revisar antes de seguir.
Un `AVISO ... no tiene lectura de kpi_definition` significa que falta la
capa 1 en esa base.

### 2. Aplicar

```bash
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_permissions --perfil adser
```

Esperado: las mismas líneas, con `Insertadas: 2 fila(s) en nm_permission_kpi.`

Es idempotente. Una segunda corrida dice `ya existe, sin cambios` e
`Insertadas: 0`. Nunca quita nada.

**Cuidado al volver a correrlo:** desmarcar un KPI en `/kpi_permissions`
**borra** la fila (no la da de baja). Si después se corre el script otra
vez, ese KPI se vuelve a asignar. Para quitar un KPI de forma permanente,
hay que sacarlo también de `ASIGNACIONES` en el script.

**Códigos de salida:**

- `0`: bien.
- `1`: error de validación, no se escribió nada. Por ejemplo, un KPI con
  `alcance_proyecto=False` asignado a un rol acotado a proyecto.
- `2`: algún rol no existe; se reporta y no se crea.

### 3. Verificar

**En la base:**

```bash
kubectl -n adser-prod exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT p.permission_description AS rol, d.clave, n.puede_ver
FROM nm_permission_kpi n
JOIN permission p USING (id_permission)
JOIN kpi_definition d USING (id_kpi_definition)
WHERE n.deletion_date IS NULL
ORDER BY 1, 2;
SQL
```

Esperado: `Administrator` con los dos KPIs y `puede_ver = t`.

**En la aplicación:** `taroj` cierra sesión y vuelve a entrar. En el
Dashboard, el selector de KPIs muestra exactamente "Artículos bajo stock" e
"Incidentes resueltos por empleado", con datos si el backfill ya corrió.

## Resultado de la prueba local (2026-09-25)

Usuario de prueba con rol Administrator, sin ser superusuario, como `taroj`:

| | KPIs en `GET /kpi_definition/` | Valores |
|---|---|---|
| Antes del script | 0 | — |
| Después del script | 2 | `incidentes_resueltos_por_empleado` 50.0 % (4 incidentes: resuelta, cerrada, cancelada, abierta); `articulos_bajo_stock` 1 pieza |
| Después de `db-migrate` y reinicio del backend | 2 | Los mismos |

## Deshacer

Desde `/kpi_permissions`, como administrador: seleccionar el rol y desmarcar
los KPIs. Eso borra las filas, así que **no se debe volver a correr el
script** con esos KPIs en `ASIGNACIONES`, porque los reasignaría.
