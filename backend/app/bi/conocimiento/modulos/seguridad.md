---
modulo: seguridad
entidades_clave: [permission, entity_permission, nm_field_permission, team]
---
# Seguridad

## Que es Seguridad y para que sirve
Seguridad decide quien entra al sistema y que puede ver y hacer cada persona. Se compone de: roles o perfiles, el Gestor de roles y permisos (que da a cada rol un alcance por accion y campos visibles), los equipos de usuarios, los permisos por KPI, el segundo factor de autenticacion (MFA), el cambio de contrasena, las llaves API del catalogo web y la bitacora de eventos. Es un modulo de administracion: por omision solo el rol Administrator lo administra. Cada usuario tiene un solo rol y el rol define todo lo que ve.

## Pantallas y donde encontrarlas en Seguridad
Todo esta en el engrane de la barra superior: **Gestor de roles y permisos**, **Permisos de KPIs** (ambos solo para usuarios de tipo administrador), **Perfiles** (lista de roles), **Equipos**, **Configurar MFA** y **Cambiar contrasena** (estas dos las ve cualquier persona). **Registro de eventos** y **MFA de usuario** son tecnicas: solo las ve la cuenta de arranque (soporte interno). Las llaves API se administran en **Catalogo Web**, pestana API Keys. Usuarios se explica en el manual de Configuracion.

## Que significa cada alcance: Sin acceso, Propios, Mis grupos y Todos
En el Gestor de roles y permisos, cada modulo tiene cuatro acciones: **Crear**, **Leer**, **Actualizar** y **Eliminar**, y cada una se fija con un alcance: **Sin acceso** (la accion esta prohibida), **Propios** (lo suyo: lo que creo o le pertenece), **Mis grupos** (lo de los equipos a los que pertenece) y **Todos** (sin limite). Un modulo con las cuatro acciones en Sin acceso queda oculto para ese rol: no aparece en el menu.

## Alcance por accion: lo que hoy funciona de verdad
IMPORTANTE: hoy el control es de si o no. Sin acceso niega la accion; Propios, Mis grupos y Todos la permiten por igual, y de momento no limitan que registros se ven. El filtrado real por Propios y Mis grupos esta planeado para una segunda fase (Fase 2) y todavia no esta conectado de forma general; en pantallas puntuales ya se usa (por ejemplo la bitacora de actividades del supervisor: con Todos se ve la de todo el equipo, y con Propios solo la propia). Hoy, para restringir de verdad conviene usar Sin acceso o los permisos por campo.

## Como crear un rol (perfil)
1. Engrane, **Gestor de roles y permisos**, boton **Nuevo rol** (o la pantalla **Perfiles**).
2. Captura el nombre o descripcion del rol, **Autorizado por** (un usuario), **Departamento**, **Subdepartamento** y **Nivel**; todos son obligatorios.
3. Presiona **Guardar rol**.
El rol nace sin permisos: no ve ningun modulo hasta que se los des. Para cambiarle el nombre usa **Editar rol**. **Eliminar rol** pide confirmacion y borra tambien todos sus permisos configurados; el rol base del sistema (el de la cuenta de arranque) esta protegido y oculto: no se puede ver ni borrar.

## Como dar o quitar acceso a un modulo a un rol
1. En el Gestor de roles y permisos, elige el rol en **Seleccionar rol/perfil**.
2. Busca el modulo con el filtro o el grupo, y en la fila elige el alcance de **Crear**, **Leer**, **Actualizar** y **Eliminar**.
3. Marca en el panel derecho los campos que podra ver (ver permisos por campo).
4. Presiona **Guardar permisos**.
Para que el rol pueda ver una pantalla hace falta Leer. Hay acciones masivas (todo CRUD, solo Leer, quitar todo) que se aplican a todos los modulos. Para dar acceso solo de consulta, deja Leer y el resto en Sin acceso. Algunos permisos son capacidades (por ejemplo Autorizar proyectos o Ajustar existencias) y se conceden aparte, con el mismo alcance.

## Como controlar donde aparece cada pantalla en el menu
En la misma tabla del Gestor, cada modulo con acceso tiene: **Ubicacion** (Menu vertical, Engrane o No mostrar), **Grupo** (el titulo del menu donde aparece), **Etiqueta** (el nombre que se ve) y **Orden** (numero menor = mas arriba). La seccion **Grupos del menu** permite renombrar un grupo y cambiar su icono. Todo esto es por rol: dos roles pueden ver la misma pantalla con nombres o lugares distintos. Guarda con **Guardar permisos**.

## Como dejar a un rol sin ver importes (permisos por campo)
1. Elige el rol y haz clic en la fila del modulo, por ejemplo Facturas.
2. En el panel de campos, desmarca **Ver** de los campos de importe (subtotal, impuesto, total, precios...).
3. Guarda.
Esos campos dejan de mostrarse a ese rol en las pantallas y en el asistente BI. Cada modulo con acceso debe conservar al menos un campo visible; si no, el Gestor no deja guardar. Los botones **Seleccionar todos los campos** y **Quitar campos** ayudan a marcar rapido. Otra opcion, mas fuerte: poner **Leer** en Sin acceso para ocultar la tabla completa.

## Como ver que puede leer un rol
Como administrador: en el Gestor de roles y permisos elige el rol; la tabla muestra el alcance de cada modulo y, al hacer clic en una fila, los campos visibles. Como cualquier usuario: pregunta al asistente BI "mis permisos" o "a que tengo acceso" y responde con lo que tu propio rol puede leer, crear, editar y eliminar. Los cambios de permisos se aplican al siguiente movimiento de la persona; si cambias el rol que tiene asignado, debe cerrar sesion y volver a entrar.

## Que ve cada rol por omision
En una instalacion nueva: Administrator administra todo. Supervisor captura Operaciones (tareas e incidencias solo consulta) y consulta Inventario. Gerente consulta casi todo, captura Facturacion y CRM, edita Operaciones y autoriza proyectos. Jefe de taller captura Operaciones. Almacenista administra Inventario y captura Logistica. Los roles de restaurante solo operan su pantalla. Todos consultan Configuracion. Es el punto de partida: en cada instalacion el administrador pudo cambiarlo en el Gestor, que es la fuente de verdad.

## Como crear y administrar equipos de usuarios
1. Engrane, **Equipos**, boton **Nuevo equipo**.
2. Escribe el nombre (por ejemplo Taller nocturno) y guarda.
3. Selecciona el equipo en la lista; a la izquierda estan los miembros actuales y a la derecha puedes buscar y agregar usuarios con el icono de agregar, o quitarlos con el de quitar.
Una persona puede estar en varios equipos. Eliminar un equipo quita tambien a sus miembros. Los equipos son la base del alcance **Mis grupos**, que hoy no filtra todavia (ver Fase 2). No es lo mismo que el **Grupo** del menu, que solo agrupa visualmente las pantallas.

## Como dar permiso a un rol para ver un KPI
1. Engrane, **Permisos de KPIs**.
2. Elige el rol.
3. Marca **Ver** en cada KPI que podra consultar; los KPI se agrupan por modulo. El cambio se guarda al marcar.
Los KPI se ven en el panel de inicio (Dashboard). Un rol ve un KPI solo si tiene acceso al modulo KPIs, el modulo que mide ese KPI esta en el plan de la instalacion y tiene marcado Ver. Por omision solo Administrator tiene el modulo KPIs. Aqui solo existe ver o no ver, sin niveles de alcance.

## Como activar MFA (segundo factor) en tu cuenta
1. Engrane, **Configurar MFA**, boton **Generar QR**.
2. Escanea el QR con una app autenticadora (Google Authenticator, Microsoft Authenticator u otra TOTP). Si no puedes escanear, usa la clave manual junto al QR.
3. Escribe el codigo de 6 digitos de la app y presiona **Confirmar codigo**.
Desde entonces, cada inicio de sesion pide usuario, contrasena y el codigo de 6 digitos. Una vez confirmado ya no puedes regenerarlo ni quitarlo tu mismo: si cambias de telefono o pierdes la app, pide a un administrador que restablezca tu MFA. Un codigo vencido o incorrecto se rechaza; los codigos cambian cada 30 segundos.

## Como restablecer el MFA de otra persona
Un administrador entra a **Usuarios**, busca a la persona y presiona el boton **MFA** (Restablecer MFA) de su fila; confirma. El MFA de esa persona queda desactivado y la siguiente vez que entre puede activarlo de nuevo desde Configurar MFA. No aplica a la cuenta de arranque. Requiere ser administrador y poder editar usuarios.

## Como cambiar tu contrasena
1. Engrane, **Cambiar contrasena** (la ve cualquier usuario, sin importar el rol).
2. Escribe tu contrasena actual, la nueva y la confirmacion.
3. Presiona **Guardar contrasena**.
La nueva debe tener minimo 8 caracteres, con al menos una letra y un numero. Solo cambia la tuya. Si la actual esta mal escrita, el sistema avisa sin cerrar tu sesion. El cambio queda anotado en la bitacora, sin guardar la contrasena. Para la de otra persona, un administrador edita su usuario y escribe una nueva.

## Como crear y revocar una llave API
Las llaves API permiten que el catalogo web publico consulte productos desde un sitio externo.
1. **Catalogo Web** (acceso rapido bajo la barra superior), pestana **API Keys** (solo aparece si tu rol puede administrar llaves).
2. Captura **Etiqueta**, **Dominios permitidos** (lista JSON de sitios autorizados, por ejemplo ["https://tienda.ejemplo.com"]) y **Limite por minuto** (60 por omision) y presiona **Crear API key**.
3. Copia la llave en cuanto aparece: solo se muestra una vez; despues se ve solo su prefijo.
Para anularla usa **Revocar**; si se pierde, revoca y crea otra. Puedes editar etiqueta, dominios y limite en la misma tabla.

## Bitacora de eventos: que registra y quien la ve
El **Registro de eventos** guarda quien hizo que y cuando: altas, cambios y bajas (con el valor antes y despues), accesos denegados por falta de permiso, cambios de estatus y otras acciones. Los campos sensibles, como contrasenas, aparecen ocultos. Cada renglon muestra Tabla, Campo, Accion, Antes, Despues, Creado por y Fecha. Hoy solo la ve la cuenta de arranque (soporte): los administradores de la empresa no tienen pantalla propia para consultarla. No documentado: como puede acceder un administrador del cliente a esta bitacora.

## Reglas y permisos importantes de Seguridad
1. Sin permiso de la accion, la pantalla muestra "Sin permiso de lectura" o el sistema responde que no tienes acceso.
2. El plan de la instalacion es el techo: no se puede dar acceso a un modulo que no esta contratado.
3. La cuenta de arranque (soporte) y el rol base del sistema estan protegidos: ocultos, sin poder editarse ni borrarse.
4. Los permisos por campo y el alcance se guardan por rol, no por persona.
5. Un administrador solo puede cambiar permisos desde el Gestor; el asistente BI respeta exactamente lo mismo.
6. Las tablas de seguridad (roles, permisos, llaves, bitacora) no las ve nadie salvo un administrador, ni en el asistente BI.

## Preguntas frecuentes de Seguridad
**No veo el Gestor de roles.** Es solo para usuarios de tipo administrador.
**Guarde permisos y no veo cambios.** Recarga la pagina; si cambiaste el rol de la persona, que cierre sesion y vuelva a entrar.
**Puse Propios y veo todo.** Es lo esperado hoy: el filtrado por Propios y Mis grupos aun no esta conectado.
**Perdi mi telefono con el MFA.** Pide a un administrador que restablezca tu MFA.
**No me deja guardar permisos.** Un modulo con acceso necesita al menos un campo visible.
**Mi llave API ya no se ve.** Solo se muestra al crearla; revoca y crea otra.
**Quien me ayuda.** El administrador de tu empresa; para el plan o la instalacion, soporte de TYAKXA.

## Preguntas de datos que se pueden hacer al asistente BI sobre Seguridad
- cuantos usuarios hay por rol
- cuantos roles hay y de que departamento son
- equipos y numero de miembros
- usuarios que no pertenecen a ningun equipo
- usuarios con MFA activo (solo administrador)
- llaves API activas (solo administrador)
- usuarios por departamento del rol
Los roles que no son administrador no pueden consultar las tablas de seguridad con el asistente.
