# Roles de la plataforma de entrega (propuesta)

Redactado 2026-11-05. **Propuesta, sin aplicar.** Complementa
`2026-10-29_flujo_de_ramas_y_despliegue.md` (ramas, candados y workflow `promover`).
Un cambio de proceso se acuerda con el equipo antes de aplicarse (CLAUDE.md, regla 5).

## 1. Alcance

Estos son los roles de la **plataforma de entrega**: quien puede cambiar el codigo, proponer
una promocion a un cliente, aprobarla o administrar la plataforma. **No** son los roles del ERP
(Gestor de roles y permisos, `entity_permission`), que son una funcion del producto y se
gestionan aparte.

El documento no lleva nombres de persona: la asignacion de cada rol a cada persona se lleva
fuera del repositorio.

## 2. Principios

- **Minimo privilegio, acumulativo.** Cada rol incluye lo del anterior. Se da el rol mas bajo
  que alcance para el trabajo que la persona ya hace.
- **Quien propone no aprueba.** Quien lanza o propone una promocion no es quien la aprueba.
- **Lo que protege es una regla comprobable**, no la memoria de alguien: CI bloqueante,
  `CODEOWNERS` y proteccion de rama.
- **Acceso a la plataforma y acceso al cluster son cosas distintas.** Estos roles describen lo
  primero. Los accesos al VPS y al cluster se revisan por separado (seccion 6).

## 3. Roles

| Rol | Incluye | Puede | No puede |
|---|---|---|---|
| **Desarrollador** | — | Abrir PR a `initAlan`; mergear cuando el CI esta verde y el cambio queda **fuera de las zonas sensibles**; ver `tyakxa-dev` | Tocar zonas sensibles sin revision; proponer promociones a clientes |
| **Desplegador** | Desarrollador | **Proponer** una promocion a un cliente (PR que cambia el tag del overlay) | Aprobar su propia promocion; aprobar promociones |
| **Aprobador** | Desplegador | Revisar y aprobar PR en zonas sensibles; **aprobar promociones** a clientes | Cambiar reglas de rama o secretos del repositorio |
| **Administrador** | Aprobador | Reglas de rama y del repositorio, secretos de Actions, control del cluster | — |

### Zonas sensibles (revision obligatoria de un Aprobador)

`database/migrations/`, `backend/scripts/seed_module_permissions.py` y resiembras de permisos,
`k8s/` (incluidos los overlays por cliente), `.github/`, `infra/docker/`.

### Niveles de autonomia

| Nivel | Quien | Que puede |
|---|---|---|
| 1 | Desarrollador | PR y merge con CI verde fuera de zonas sensibles |
| 2 | Desplegador | Lo anterior, mas proponer promociones; aprueba un Aprobador, siempre |
| 3 (a decidir) | Desplegador con N promociones limpias | Aprobar promociones **sin migraciones nuevas** cuando no haya Aprobador disponible. Con migraciones sigue la aprobacion. Fuera de alcance hasta definir N y el criterio. |

Fuera de alcance en todos los niveles que no sean Administrador: `sudo` en el nodo de entrada,
Secrets del cluster, mover volumenes, cambios a `k8s/base/` sin revision.

## 4. Como se hace cumplir

| Regla | Mecanismo | Estado |
|---|---|---|
| El codigo no entra con secretos ni hallazgos de alta severidad | Workflow `ci-seguridad` (Semgrep y gitleaks bloqueantes) | **Implementado** y probado con un secreto falso |
| Las migraciones y las pruebas pasan antes de integrar | Workflow `ci-pruebas` (migraciones en dos pasadas y pytest) | **Implementado** |
| Que el CI verde sea obligatorio para mergear | Ruleset de rama sobre `initAlan` (check requerido) | Pendiente |
| Revision obligatoria en zonas sensibles | `CODEOWNERS` y ruleset (PR y revision de un code owner) | Pendiente |
| Promocion con aprobacion, `pg_dump` previo y bitacora | Workflow `promover` | Pendiente |

## 5. Limitaciones conocidas

- **No hay revisores obligatorios en environments de GitHub**: el plan del repositorio no los
  ofrece. La aprobacion de una promocion se apoya en el **PR protegido por `CODEOWNERS`**
  (la promocion es el cambio del tag del overlay) y no dentro del propio workflow.
- **El bloqueo hoy es del escaneo, no de la fusion.** Un check en rojo no impide pulsar
  *Merge* hasta que exista el ruleset de rama con el check requerido.
- Los administradores pueden saltarse las reglas de rama si el ruleset se lo permite. Conviene
  que la lista de excepciones quede vacia, salvo el bot de CD.
- `pip-audit` y `npm audit` siguen informativos: quedan avisos que piden un salto de version mayor.

## 6. Pendientes fuera de este documento

- **Cuentas del VPS y del cluster:** hoy existen usuarios con carpeta de despliegue y, al menos
  uno, con permisos de administrador del cluster. Eso es mas de lo que pide el rol Desplegador.
  Revisarlo y recortarlo es una decision de infraestructura con quien administra el cluster; no
  se toca desde esta propuesta.
- **`admin1` con contrasena por defecto:** el hash de arranque esta documentado como excepcion
  de Semgrep, pero falta comprobar en cada ambiente que ya no se usa.
- **Credenciales de vida corta** para el CD y boveda de secretos: Fases C y D de la ruta de cierre.
