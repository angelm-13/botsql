---
modulo: sistema_general
entidades_clave: []
---
# Sistema general de TYAKXA

## Que es TYAKXA y para que sirve
TYAKXA es un sistema ERP, CRM y de cadena de suministro: una sola aplicacion web con varios modulos (Facturacion, Inventario, Operaciones, Logistica, Restaurante, Punto de venta, CRM, Documentos, Laboratorio, Recursos humanos y KPIs), mas dos de infraestructura, Configuracion y Seguridad. No todas las empresas tienen todos los modulos: cada instalacion tiene un plan con los modulos contratados. Y dentro de ellos, cada persona ve solo lo que su rol permite. Esta guia explica lo comun a todas las pantallas.

## Como iniciar sesion
1. Abre la direccion del sistema de tu empresa; aparece la pantalla de acceso.
2. Escribe tu **Usuario** y tu **Contrasena** (el icono del ojo muestra u oculta la contrasena) y presiona **Iniciar sesion**.
3. Si tu cuenta tiene MFA, aparece un segundo paso: escribe el codigo de 6 digitos de tu app autenticadora y presiona **Verificar codigo**. Con **Volver al login** regresas al paso uno.
Si el usuario o la contrasena son incorrectos el sistema lo dice; tras varios intentos fallidos seguidos bloquea un rato y pide esperar unos minutos. La sesion dura varias horas (unas 8 por omision); al vencer, el sistema te regresa a la pantalla de acceso.

## Como cerrar sesion
En la barra superior, a la derecha, presiona **Cerrar sesion**. Te lleva a la pantalla de acceso y borra la sesion de ese navegador. Hazlo siempre en equipos compartidos. Junto al boton, la etiqueta "Sesion protegida" muestra con que usuario estas trabajando. Si ves un nombre de empresa junto al titulo TYAKXA, es la etiqueta de tu instalacion y tambien aparece en la pestana del navegador.

## La barra superior y el menu lateral
La **barra lateral** de la izquierda agrupa las pantallas por modulo: Dashboard arriba, luego un grupo por cada modulo al que tienes acceso; presiona un grupo para desplegarlo. El boton de flechas junto al menu lo contrae a solo iconos, y en pantallas pequenas se abre con el boton de hamburguesa. En la **barra superior** estan el selector de Idioma, el boton **Analisis BI**, el **engrane** y Cerrar sesion. Bajo ella pueden aparecer accesos rapidos, como Catalogo Web, si tu rol los tiene.

## El engrane de configuracion
El engrane de la barra superior abre un menu con las pantallas de configuracion y de cuenta. Todos los usuarios ven **Configurar MFA** y **Cambiar contrasena**. Segun el rol aparecen ademas Usuarios, Perfiles, Departamentos, Subdepartamentos, Niveles, Equipos, y, solo para administradores, el Gestor de roles y permisos y Permisos de KPIs. El administrador decide por rol que pantallas van al engrane, al menu lateral o se ocultan. Si dice "Sin opciones configuradas", tu rol no tiene pantallas ahi.

## Pantalla de inicio (Dashboard)
**Dashboard** es la primera entrada del menu lateral y la pueden abrir todos los usuarios. Ahi se ven los tableros de indicadores (KPIs): puedes tener varios tableros en pestanas, renombrarlos, borrarlos y editar sus tarjetas. Cada persona ve solo los KPI que el administrador le permitio; por omision, el modulo KPIs lo tiene solo el rol Administrator. Si no ves indicadores, pideselos al administrador de tu empresa.

## Idiomas disponibles
El selector **Idioma** esta en la pantalla de acceso y en la barra superior. Hay ocho opciones: Español, English, Portugues, Deutsch, japones, chino simplificado, chino tradicional y Nahuatl. La eleccion se guarda en tu navegador, no en tu cuenta, y se aplica de inmediato sin cerrar sesion. El idioma mas completo es el español: en los demas puede haber textos sin traducir, que se muestran en español. Los datos que captura la gente (nombres, descripciones) no se traducen.

## Notificaciones
No documentado: en esta version no hay campana ni entrada de menu de Notificaciones accesible para los usuarios, y no esta documentado cuando o como llegan los avisos. Si alguien te menciona una notificacion, consulta con el administrador de tu empresa.

## Como pedir acceso a un modulo o pantalla
1. Anota el nombre de la pantalla o modulo y que necesitas hacer: solo verla, capturar, editar o eliminar.
2. Pidelo al administrador de tu empresa (un usuario de tipo administrador): el cambia tu rol en el Gestor de roles y permisos.
3. Despues de que lo confirme, cierra sesion y vuelve a entrar para ver el menu actualizado.
Si el administrador ya te lo dio y sigue sin aparecer, puede que el modulo no este en el plan contratado de la instalacion: eso solo se amplia con TYAKXA. El acceso lo da el rol, no la persona, y hay una diferencia entre ver y operar (ver exige Leer).

## Que significa el aviso "No tienes acceso"
Aparece cuando intentas algo que tu rol no puede hacer: abrir una pantalla, ver un dato, crear, editar o eliminar. No es un error del sistema: significa que falta ese permiso en tu rol. Otro aviso parecido indica que el modulo no esta incluido en el plan de la instalacion; ahi ni el administrador puede darlo. Un tercero, "Sin permiso de lectura", sale dentro de una pantalla a la que puedes entrar pero no leer. En los tres casos: avisa al administrador con el nombre de la pantalla y la accion.

## Como cambiar mi contrasena
Engrane, **Cambiar contrasena**: escribe la actual, la nueva y la confirmacion, y presiona **Guardar contrasena**. La nueva necesita minimo 8 caracteres, con al menos una letra y un numero. Todos los usuarios pueden hacerlo, sin importar su rol. Si olvidaste la actual, no hay recuperacion por correo para el personal: pide al administrador que te asigne una nueva contrasena (el la escribe al editar tu usuario). Mas detalle en el manual de Seguridad.

## Como activar el segundo factor (MFA)
Engrane, **Configurar MFA**: presiona Generar QR, escanealo con una app autenticadora (por ejemplo Google Authenticator), escribe el codigo de 6 digitos y presiona Confirmar codigo. Desde ese momento cada inicio de sesion pide ese codigo. Una vez activo no se puede quitar tu mismo: si pierdes el telefono, pide al administrador que restablezca tu MFA.

## Que es el Analisis BI y donde esta
**Analisis BI** es el boton verde de la barra superior (junto al engrane); lo puede abrir cualquier usuario con sesion. Es un asistente al que le escribes una pregunta en lenguaje natural, con dos usos: preguntas de datos (cuantos, cuales, por mes, top N) y preguntas de ayuda sobre como funciona el sistema. Al abrirlo ves cajas de sugerencias, el historial de tus ultimas preguntas y dos indicadores: Modelo de IA y PostgreSQL (la base de datos), que deben decir "funcionando".

## Como hacer una pregunta en Analisis BI
1. Abre **Analisis BI**.
2. Escribe tu pregunta (hasta 1000 caracteres), por ejemplo "top 8 productos por existencias", o pulsa una sugerencia.
3. Presiona **Analizar** y espera: las preguntas nuevas pueden tardar de uno a tres minutos; una repetida o frecuente responde al instante.
4. Lee el resultado: por omision es una tabla; un total unico sale como tarjeta; pide "en grafica de barras", "en pastel" o "tendencia" para una grafica.
Con **Nueva consulta** vuelves a preguntar. El asistente solo consulta, nunca modifica, borra ni inserta datos.

## Que puede ver cada rol en Analisis BI
El asistente usa exactamente los permisos del Gestor de roles y permisos: solo consulta las tablas que tu rol puede LEER, y de ellas solo las columnas que tu rol tiene marcadas como visibles. Un administrador ve todo lo que el plan de la instalacion permita. Por ejemplo, un rol de operaciones puede no ver los importes de facturacion; un mesero casi no ve datos. Si preguntas por algo fuera de tu rol, responde que la consulta no esta permitida. Las tablas de seguridad (roles, permisos, llaves, bitacora) solo las consulta un administrador.

## Que no hace el Analisis BI
No inserta, actualiza ni elimina nada. No muestra contrasenas, tokens ni secretos, ni la consulta tecnica ni la estructura de la base. Si el resultado parece incompleto, puede deberse a que tu rol no ve alguna columna o tabla. Si dice que el modelo de IA no esta disponible, es una falla del servicio y no de tu pregunta: avisa a soporte. "Tu rol no tiene acceso a ninguna tabla" significa que tu rol aun no tiene permisos de lectura.

## Que modulos y roles trae un sistema nuevo
Los roles iniciales son: Administrator (todo), Supervisor, Gerente, Jefe de taller, Almacenista, Mesero, Cocina, Caja Restaurante y Admin Restaurante. Supervisor, Jefe de taller y Gerente trabajan en Operaciones; Almacenista en Inventario; los cuatro ultimos solo en Restaurante. Todos consultan Configuracion. Documentos, Laboratorio y KPIs solo los tiene Administrator hasta que se amplie. Es el punto de partida: cada empresa puede ajustar los permisos, asi que lo que tu ves es lo que tu rol tiene asignado.

## A quien acudir
- **Acceso, permisos, contrasena olvidada o MFA perdido:** el administrador de tu empresa (usuario tipo admin).
- **Modulo que no esta contratado, ampliar el plan, usuarios o espacio:** soporte de TYAKXA.
- **El asistente BI no responde o dice que el modelo no esta disponible:** soporte o el responsable tecnico de tu empresa.
- **No entiendes como se usa una pantalla:** pregunta al asistente BI, por ejemplo "como se crea un usuario".

## Preguntas frecuentes del sistema general
**No veo un modulo en el menu.** Tu rol no tiene acceso o no esta en el plan.
**Mi sesion se cerro sola.** Vencio el tiempo de sesion; vuelve a entrar.
**Cambie de idioma y algo sigue en español.** Esa parte no esta traducida aun.
**El engrane esta vacio.** Tu rol no tiene pantallas de configuracion asignadas.
**Que significa el codigo de 6 digitos.** Es el MFA de tu app autenticadora; cambia cada 30 segundos.
**El BI tarda mucho.** Es normal la primera vez, hasta unos minutos.
