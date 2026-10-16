# Propuesta: quién puede gestionar a quién, sin `user_type`

Para acordar con Alan, Tanya y Ángel (regla 5 de `CLAUDE.md`). **Nada de lo que sigue
está implementado.** Borrador del 2026-10-15. Origen: Tanya autorizó quitar `user_type`
de las decisiones de permisos si choca con el Gestor de roles y permisos, y la
alta/baja de personal por un Gerente (pendiente del 2026-10-07) hoy no puede
resolverse desde el Gestor.

**Cómo leer este documento.** Cada afirmación sobre el sistema está verificada en el
repo o en los ambientes (solo lectura, 2026-10-15) salvo donde dice *(sin verificar)*.

## 1. Qué ya está hecho y qué falta

Hecho hoy, sin commitear (ver el cambio anterior de esta misma jornada): `user_type`
dejó de dar acceso a campos, al catálogo del gestor de roles, a la config de timbrado, al
reinicio de MFA y a las pantallas del Gestor. Esas decisiones ahora salen del Gestor
(más el superusuario).

**Falta un solo lugar donde `user_type` todavía manda sobre personas: la jerarquía de
usuarios.** Está copiada en dos archivos:

- [routes/user.py](../../backend/app/routes/user.py): `_can_create_user_payload`,
  `_can_manage_user_row`, `_payload_elevates_beyond_actor` (alta, edición, borrado).
- [routes/auth.py](../../backend/app/routes/auth.py): `_request_can_manage_target_user`
  (reinicio de MFA ajeno).

Cómo funciona hoy:

| Quién actúa | Sobre quién | Resultado |
|---|---|---|
| `user_type = 'admin'` ("company admin") | cualquiera salvo el bootstrap | permitido, sin pasar por el Gestor |
| cualquier otro tipo | solo rango **estrictamente menor** (admin 80 > client/supplier 50 > employee 40 > user 20 > vacío 10) | un Gerente (`employee`, 40) no puede gestionar a otro `employee` (40) |

Consecuencia: aunque el Gestor le dé a un Gerente `user` (C/R/U/D), recibe 403. Es el
caso real de Adser: sus 2 Gerentes son `employee`, igual que el resto del personal.
Las variables `COMPANY_ADMIN_USER_TYPES` y `USER_HIERARCHY_RANKS` que ajustan esto **no
están puestas en ningún ambiente** (verificado en el `app-secrets` de los cuatro).

## 2. Qué se probó y se descartó

**"Un rol solo gestiona roles cuyos permisos son un subconjunto de los suyos."** Es la
regla más elegante, pero **se descarta con datos**. Medí, por ambiente, a qué roles
podría gestionar cada rol que hoy tiene permisos de escritura sobre `user`:

| Ambiente | Rol que gestiona | Roles que podría gestionar con esa regla |
|---|---|---|
| adser-prod | Administrator | **solo Vendedor** (de 7 roles) |
| tyakxa-dev | Administrator | **solo Compras y Jefe de taller** |
| torredigital-prod | Administrator | 7 de 10 |
| comala-prod | Administrator | operador |

El Administrator **no es superconjunto** de los roles operativos: las capacidades
`project_authorization`, `project_execution`, `warehouse_voucher*` y varias más viven
solo en los roles que las usan. Con esa regla, el Administrador de Adser no podría dar
de alta a un Gerente, un Supervisor ni un Almacenista. Rompería lo que hoy funciona.

**"Usar `permission.id_level` como rango."** Se descarta: la tabla `level` tiene una
sola fila ("General") y todos los roles de adser y torredigital la usan (verificado).
No hay orden. Habría que agregar una columna de rango y capturarla por cliente.

**"Agregar un tipo `manager` con rango 60"** (la idea de la nota del 2026-10-07). Se
descarta: le daría más autoridad a `user_type`, justo lo contrario de lo acordado.

## 3. Propuesta

**El Gestor decide *si* se puede gestionar usuarios; el código solo protege a quien
nadie debe poder tocar desde abajo.** Una sola función compartida por `user.py` y
`auth.py` (hoy duplicadas) que aplica estas reglas, todas por rol o identidad, ninguna
por `user_type`:

1. **¿Puede?** Lo decide el Gestor: `scope_create` / `scope_update` / `scope_delete`
   de `user` (ya lo exige la ruta). Sin esa casilla, nada de lo que sigue importa.
2. **El superusuario** (bootstrap) puede todo y nadie más lo ve ni lo toca. Igual que
   hoy.
3. **Quien tenga el rol Administrator (id 1)** solo lo asigna el superusuario
   (`_payload_assigns_protected_role`, que ya existe) y **solo lo gestiona otro
   Administrator o el superusuario**. Sustituye al "company admin" por tipo: protege
   a los administradores del cliente de que un rol operativo los edite, borre o les
   reinicie el MFA. Paridad con hoy: un Administrator sigue gestionando a todos menos
   al bootstrap.
4. **Sin autoescalada:** nadie cambia su propio rol (salvo el superusuario) y nadie se
   borra a sí mismo (esto último ya existe).
5. **Todo lo demás lo permite el Gestor:** un Gerente con `user` puede dar de alta,
   editar y borrar a Supervisor, Jefe de taller, Almacenista y a otro Gerente.

Lo que desaparece: `_company_admin_types`, `_user_hierarchy_rank_from_type`, las dos
variables de entorno y el candado de `user_type` en `_payload_elevates_beyond_actor`.

**Lo que NO cambia:** `user_type` sigue existiendo como dato descriptivo (la columna,
el formulario, el token) y como discriminador de las cuentas del portal público
(`web_shopper`) y de la restricción de documentos para `client` y `supplier`. Tampoco
se toca cómo se reconoce al bootstrap en el login: [auth.py:99](../../backend/app/routes/auth.py)
exige usuario `admin1` **y** tipo `admin`; es una amarra de identidad, no un permiso, y
aflojarla ensancharía la superficie del superusuario sin ganar nada.

### Opción opcional, solo si un cliente la pide: "roles asignables"

Una lista por rol ("este rol solo puede dar de alta a estos roles"), editable en el
Gestor. Cubre el caso "el Gerente puede crear operadores pero no otro Gerente". **No la
recomiendo ahora**: agrega una tabla y una pantalla, y tiene una trampa (si la lista
nace vacía, "le di permiso y no funciona" otra vez). Si se hace, que una lista vacía
signifique "todos", no "ninguno". Se puede añadir después sin tocar lo de arriba.

## 4. Efecto por ambiente (medido)

Usuarios activos por tipo y rol; "permisos sobre `user`" son los roles con escritura:

| Ambiente | Roles con escritura sobre `user` | Efecto de la propuesta |
|---|---|---|
| adser-prod | Administrator | Ninguno. Los 2 Gerentes no ganan nada hasta que Alan les dé `user` en el Gestor. |
| tyakxa-dev | Administrator | Ninguno. |
| comala-prod | Administrator, `adm_asistencias` | Ninguno visible: su único `admin` restringido (`cormur`, `adm_asistencias`) gestionaba a todos salvo el bootstrap, y el único usuario con rol Administrator es el bootstrap. |
| torredigital-prod | Administrator, **Calidad** | **Amplía poder:** el usuario con rol Calidad (1, tipo vacío) tiene `user` C/R/U/D en el Gestor pero hoy cae en rango 10 y no puede gestionar a nadie. Pasaría a poder gestionar a todos menos a los Administrator. **Alan debe confirmar que eso es lo que se quiso al darle ese permiso.** |

## 5. Pruebas

- Gerente con `user` en el Gestor da de alta, edita y borra a un Supervisor y a otro
  Gerente (hoy 403).
- Gerente **sin** `user`: 403 aunque su `user_type` sea `admin`.
- Un rol operativo no puede editar, borrar ni reiniciar el MFA de un usuario con rol
  Administrator; otro Administrator sí.
- Nadie, salvo el superusuario, asigna el rol Administrator ni cambia su propio rol.
- El bootstrap sigue invisible y protegido.
- Prueba estructural (como la de campos): ningún archivo de `routes/` ni `services/`
  decide por `user_type == 'admin'` ni por rangos de tipo.
- Suite completa en verde antes del push (regla 6).

## 6. Despliegue y reversa

Sin migración y sin cambio de datos: es solo código en `user.py`, `auth.py` y una
función compartida, más un ajuste menor al formulario de usuarios. Orden: tyakxa-dev,
verificarlo con un Gerente de prueba, y luego adser, torredigital y comala. La reversa
es revertir el commit.

## 7. Decisiones que necesito de ustedes

1. ¿Se aprueba la regla del §3 (el Gestor decide, el código protege al Administrator)
   en lugar de una lista de "roles asignables"?
2. **Torredigital, rol Calidad:** ¿es correcto que gane la gestión de usuarios que el
   Gestor ya le concede?
3. ¿Se deja la amarra `admin1` + tipo `admin` para reconocer al bootstrap (recomendado)
   o se cambia por otra marca de identidad?
4. En el formulario de usuarios, ¿se oculta la opción `admin` del tipo, ya que dejó de
   significar algo? Los registros existentes la conservan.
5. **Baja de personal:** esta propuesta permite que un Gerente *borre* usuarios, pero
   el borrado real da 409 si tienen historial (según la nota del 2026-10-07, 31 de 43
   usuarios de Adser tenían vales; *sin reverificar hoy*) y **el login no revisa `deletion_date`**: quien ya no trabaja podría seguir
   entrando. Antes de darle baja al Gerente, ¿construimos la baja lógica (desactivar sin
   borrar, bloquear login y token, conservar historial)? Es un trabajo aparte que
   recomiendo hacer primero.
