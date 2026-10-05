# El Gestor de roles ya no se revierte al promover (trigger en la base)

- **Migración:** `database/migrations/20260816000000_el_gestor_manda_sobre_las_migraciones.sql`
  (la primera del directorio, a propósito; una prueba lo vigila).
- **Código:** columna `ajustado_por_gestor` en `EntityPermission` y `NmFieldPermission`;
  `NmFieldPermissionService.delete` ahora da de baja en vez de borrar.
- **Pruebas:** `backend/tests/test_security/test_gestor_manda_en_la_base.py` (solo Postgres,
  `backend/ci/run_postgres_tests.sh`) y los casos nuevos de `test_manager_wins.py`.

## Qué pasaba (medido en adser-prod el 2026-10-02)

`db-migrate` reaplica **todas** las migraciones en cada arranque del backend. Unas 25 hacen
`UPDATE entity_permission` sobre el menú (ubicación, grupo, etiqueta, orden, icono) o los
alcances, y otras tocan `nm_field_permission`. La pasada de las 19:44 de ese día reescribió
5 grupos de filas de `entity_permission` (Configuración, catálogos de Inventario,
Operaciones/Proyectos, Familias, Logística) y 176 de `nm_field_permission`. Es decir: cada
promoción deshacía lo que se hubiera ajustado en el Gestor.

Parchar migración por migración no alcanzaba: ya había una lista de «deuda conocida» en
`test_manager_wins.py` que una regex no podía seguir, y cada migración nueva reabría el hueco.

## Qué hace ahora

- `ajustado_por_gestor` guarda **cuándo tocó la fila el Gestor**. La fija el ORM (al crear y
  al editar), así que cualquier cambio hecho desde la aplicación la cambia.
- Un trigger descarta cualquier `UPDATE` que **no** cambie esa columna sobre una fila ya
  ajustada (es de una migración o de un `psql` a mano), y cualquier `DELETE` físico.
- Las filas que el Gestor **nunca tocó** se comportan como antes: las migraciones las siembran
  y las corrigen, así que una instalación nueva sale con el menú y los alcances del registro.
- Quitar un permiso de **campo** ahora es baja lógica (como ya lo era el de entidad); un
  segundo trigger evita que el `INSERT` de reposición de las migraciones lo devuelva.
- **Congelado inicial:** la primera vez que la columna se crea en una base que ya estaba en uso
  (tiene `scope_*`), **todo lo que existe en ese momento queda marcado**: lo vigente es la
  verdad. En una instalación nueva no se congela nada.

## Qué esperar al promover

1. La primera pasada con esta migración **no cambia ningún permiso**: congela antes de que
   corran las migraciones viejas (verificado: base ya en uso con ediciones sin marca → intactas).
2. **Lo que esté hoy en el Gestor es lo que se queda.** Si la promoción anterior movió algo
   (en adser-prod, la pasada del 2026-10-02 reescribió filas de Administrator, Almacenista y
   Supervisor en Configuración, Inventario, Operaciones, Familias y Logística) hay que
   **revisarlo y corregirlo una vez** en el Gestor *antes* de promover esta versión; después
   ya no se mueve.
3. Un permiso o menú **nuevo** del registro (rol/entidad que no existía) sigue entrando solo,
   porque es un `INSERT` de una fila nueva.
4. Una migración futura que *deba* reescribir una fila ya ajustada tiene que fijar también
   `ajustado_por_gestor` (el trigger deja pasar un `UPDATE` que la cambia).

## Cosas a tener presentes

- Un `UPDATE`/`DELETE` a mano con `psql` sobre `entity_permission`/`nm_field_permission` **no hace
  nada** (0 filas, sin error) si la fila ya está ajustada. Para forzarlo:
  `UPDATE ... SET ..., ajustado_por_gestor = now()` (en `UPDATE`), o
  `ALTER TABLE <tabla> DISABLE TRIGGER trg_gestor_manda;` … `ENABLE TRIGGER` (en `DELETE`).
- Un `INSERT` de una fila nueva con el ORM (también desde pruebas) nace ajustada.
- **Lo que esto no cubre:** `permission` (los roles en sí) y las asignaciones de usuario a rol.
  Las migraciones que tocan roles ya estaban acotadas por valor (`roles_redundantes_retirados`,
  `fusionar_jefe_de_almacen`) y no se detectó que pisen nada.
- `torredigital-prod` y `vidrioyaluminios-prod` (semanas sin promover): al recibir esta versión
  también se congelan tal como estén, así que las migraciones de reparación que lleguen después
  no tocarán filas existentes de esos ambientes.

## Verificación hecha (base desechable con `init.sql` + 124 migraciones, Docker local)

| Caso | Resultado |
|---|---|
| Instalación limpia, 2 pasadas | sin errores; nada congelado; triggers creados |
| Ediciones **con** marca (menú, etiqueta, orden, alcance, ocultar, permiso de campo cambiado y retirado) + reaplicar todo | todas intactas; sin duplicado activo del permiso de campo retirado |
| Misma edición **sin** marca (control) + reaplicar | se revierte (la prueba sí discrimina) |
| Base «ya en uso» sin la columna, con ediciones previas, 1.ª pasada | congela 276/276 y 4976/4976; ediciones intactas |
| 3.ª pasada | idempotente |
| Suite SQLite | 1583 passed, 179 skipped |
