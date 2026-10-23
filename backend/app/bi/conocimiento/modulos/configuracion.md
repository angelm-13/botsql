---
modulo: configuracion
entidades_clave: [user, department, subdepartment, level, theme]
---
# Configuracion

## Que es Configuracion y para que sirve
Configuracion reune lo que se prepara una vez y se consulta desde todas partes: los usuarios (quien entra al sistema), los departamentos, subdepartamentos y niveles (la estructura de la empresa), los estados (status), el tema de colores, y el plan de modulos que tiene contratado esta instalacion. Configuracion y Seguridad siempre estan activos: no se pueden quitar del plan. Casi todos los roles pueden CONSULTAR estos catalogos, porque las demas pantallas los usan para llenar sus listas desplegables.

## Pantallas y donde encontrarlas en Configuracion
Estas pantallas viven en el engrane de la barra superior, dentro del grupo Configuracion: **Usuarios**, **Departamentos**, **Subdepartamentos**, **Niveles** (y Perfiles y Equipos, que se explican en el manual de Seguridad). **Estado** y **Tema** existen como pantallas, pero por omision no tienen entrada de menu: el administrador puede mostrarlas eligiendo "Engrane" o "Menu vertical" en la columna Ubicacion del Gestor de roles y permisos. Solo ves las pantallas que tu rol puede leer.

## Como dar de alta un usuario en Configuracion
1. Engrane, **Usuarios**, y despliega el formulario de alta.
2. Captura **Usuario** (nombre de acceso, no se puede repetir), **Contrasena**, **Completo Nombre** (nombre completo) y **Correo** (tampoco se puede repetir).
3. Elige el **Rol/perfil**, el **Usuario Tipo**, el proyecto, el supervisor y el estado.
4. Guarda.
La persona ya puede iniciar sesion con ese usuario y contrasena. La contrasena que captura el administrador debe tener minimo 8 caracteres con mayuscula, minuscula, numero y simbolo, y se guarda cifrada: nadie puede leerla despues. Los campos que ves en el formulario dependen de los permisos por campo de tu rol.

## Tipos de usuario y quien puede crear a quien
El campo **Usuario Tipo** admite: admin, client, supplier, employee y web_shopper. Los compradores web (web_shopper) no entran por esta pantalla ni al sistema interno. Un usuario de tipo admin puede crear y administrar a otros administradores y a todos los de menor rango. Los demas solo pueden administrar a usuarios de rango menor al suyo (orden: admin, client y supplier, employee). Nadie puede crear ni editar a la cuenta de arranque (cuenta interna de soporte): esta oculta y protegida. Si la accion no esta permitida por jerarquia, el sistema la rechaza.

## Como editar o eliminar un usuario
1. En **Usuarios**, busca a la persona con el buscador.
2. Para cambiar datos, usa el lapiz, modifica y guarda. Si dejas la contrasena en blanco, se conserva la actual; si escribes una nueva, se reemplaza (ver "restablecer contrasena").
3. Para quitarla, usa el bote de basura y confirma.
Un usuario no puede eliminarse a si mismo. Si el usuario ya tiene registros relacionados (proyectos, vales, facturas...), el sistema no lo elimina y avisa que primero hay que desvincular esos registros. Al eliminar, tambien se borra su configuracion de MFA.

## Como restablecer la contrasena o el MFA de otro usuario
**Contrasena:** en Usuarios, edita a la persona y escribe una contrasena nueva (minimo 8 caracteres con mayuscula, minuscula, numero y simbolo); al guardar queda cifrada. Cada persona tambien puede cambiar la suya desde el engrane, en Cambiar contrasena.
**MFA:** en la fila del usuario esta el boton **MFA** (Restablecer MFA); pide confirmacion y deja el MFA de esa persona desactivado, para que lo vuelva a configurar. Requiere ser administrador y tener permiso de editar usuarios; no se puede aplicar a la cuenta de arranque.

## Como crear departamentos y subdepartamentos
1. Engrane, **Departamentos**: escribe la descripcion y guarda.
2. Engrane, **Subdepartamentos**: escribe la descripcion, elige a que departamento pertenece y guarda.
Sirven para clasificar los roles: al crear un rol en el Gestor de roles y permisos se pide Departamento, Subdepartamento y Nivel. Eliminar un departamento o subdepartamento que ya se usa en un rol puede ser rechazado por tener registros relacionados.

## Como crear niveles
Engrane, **Niveles**: escribe la descripcion y guarda. El nivel es un dato obligatorio al crear un rol; no existe todavia una jerarquia formal entre niveles. El nivel de superusuario del sistema esta protegido y oculto para quien no es la cuenta de arranque. No documentado: que el nivel cambie por si solo lo que un rol puede hacer; los permisos se dan en el Gestor de roles y permisos.

## Como administrar los estados (Estado)
La pantalla **Estado** guarda el catalogo de estados que usan otras pantallas. Cada estado tiene **Estado Descripcion**, **Categoria**, **Terminal** (si marca el fin de un proceso) y **Orden** (asc o desc). Para crear uno, abre la pantalla, captura esos datos y guarda. Todos los roles necesitan poder LEER Estado, porque sin eso las listas desplegables de otras pantallas salen vacias. Una instalacion nueva trae sembrados unos estados iniciales.

## Como usar Tema
La pantalla **Tema** guarda una paleta de colores: Inquilino ID, color primario, secundario, de fondo, de texto, destacado, de exito y de error (cada uno hasta 10 caracteres, por ejemplo un codigo hexadecimal). Se crea y edita como cualquier catalogo: abrir, capturar y guardar. No documentado: que estos colores cambien la apariencia del sistema para los usuarios; hoy la pantalla solo los almacena.

## Plan de modulos contratado (licencias) en Configuracion
Cada instalacion tiene un plan: la lista de modulos que se compraron. El plan es el techo: aunque un administrador le de al rol permisos sobre un modulo que no esta en el plan, ese modulo no existe para nadie en esa instalacion (no aparece en el menu ni en el Gestor de roles, y las llamadas se rechazan con un aviso de que el modulo no esta en el plan). Sin plan configurado, todos los modulos de negocio estan habilitados. El plan lo define TYAKXA al instalar, no se cambia desde pantalla. Para ampliarlo hay que pedirlo a TYAKXA.

## Topes del plan: almacenamiento y usuarios
El plan puede traer un tope de almacenamiento para archivos subidos (XML, PDF, estados de cuenta, fotos de producto). Al llegar al tope se bloquean las subidas nuevas, con un aviso de limite de almacenamiento alcanzado, pero NUNCA se detiene la operacion; el XML de una factura timbrada se guarda siempre. El plan tambien puede declarar un tope de usuarios. No documentado: que el sistema impida crear usuarios al llegar a ese tope.

## Etiqueta del cliente (badge) en la barra superior
Si la instalacion tiene nombre de cliente configurado, aparece una etiqueta junto al titulo TYAKXA en la barra superior y en el titulo de la pestana del navegador ("TYAKXA · Cliente"). Sirve para no confundir instalaciones cuando se trabaja con varias abiertas. Es solo visual: no cambia permisos ni modulos. Si no hay etiqueta, solo se ve TYAKXA. El nombre lo configura TYAKXA en el servidor.

## Reglas y permisos importantes de Configuracion
1. Por omision, Administrator administra todo Configuracion y casi todos los demas roles solo lo consultan (Supervisor, Gerente, Jefe de taller, Almacenista y los roles de restaurante).
2. Para ver una pantalla hay que poder LEER su tabla; para crear, editar o eliminar, tener ese permiso en el Gestor de roles y permisos.
3. La cuenta de arranque (soporte interno) no se ve en Usuarios, no se elimina y no se puede cambiar desde la aplicacion.
4. Una persona solo ve los campos de Usuarios que su rol tenga marcados como visibles.

## Preguntas frecuentes de Configuracion
**No veo Usuarios en el engrane.** Tu rol no tiene permiso de leer usuarios; pideselo al administrador.
**Me dice que no tengo acceso.** Tu rol no puede realizar esa accion sobre esa pantalla.
**No puedo borrar un usuario.** Tiene registros relacionados, o es tu propia cuenta, o es de rango igual o mayor.
**Un modulo no aparece para nadie.** Puede no estar incluido en el plan de la instalacion.
**Se me olvido mi contrasena.** No hay recuperacion por correo para personal interno: pide al administrador que te asigne una nueva.
**Donde cambio mi propia contrasena.** Engrane, Cambiar contrasena.

## Preguntas de datos que se pueden hacer al asistente BI sobre Configuracion
- cuantos usuarios hay
- usuarios por tipo
- usuarios por rol
- cuantos departamentos hay
- subdepartamentos por departamento
- lista de niveles
- estados por categoria
- usuarios que son empleados
- usuarios dados de alta este mes
(El asistente solo muestra las columnas que tu rol puede ver; datos sensibles como contrasenas nunca se muestran.)
