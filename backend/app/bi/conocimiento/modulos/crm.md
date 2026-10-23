---
modulo: crm
entidades_clave: [customer_supplier, customer_contact, appointment]
---
# CRM

## Que es y para que sirve
El modulo CRM guarda a las empresas con las que se trabaja (clientes y proveedores) y sus contactos, controla las citas con una agenda publica, publica productos en un catalogo web para una tienda en linea, y guarda encuestas. Los datos fiscales de cada empresa (RFC, regimen, codigo postal) son los que usa Facturacion al emitir un CFDI. La misma lista de empresas sirve para clientes, para proveedores y para la propia empresa emisora.

## Pantallas y donde encontrarlas
- **Clientes y proveedores** (menu CRM): alta, edicion y busqueda de empresas; en la vista de Clientes, debajo aparece el panel de Contactos.
- **Clientes** (menu CRM): la lista de solo clientes, con el panel de Contactos de cliente debajo. Las opciones Contactos, Direcciones, Contratos y Tarifas de ese mismo grupo pertenecen al modulo de Logistica.
- **Cotizaciones** (menu CRM): cotizaciones comerciales; se explican en el manual de Facturacion.
- **Calendario** (menu Operaciones, pantalla Agenda): tu agenda de citas.
- **Catalogo Web** y **Compradores Web**: accesos rapidos de la barra superior.
Las encuestas (Pregunta de encuesta, Respuesta multiple de encuesta, Usuario de encuesta) y las Llaves API no tienen apartado fijo en el menu. No documentado: en que lugar del menu aparecen las encuestas.

## Como dar de alta un cliente o proveedor
1. Abre Clientes y proveedores (o Clientes).
2. Abre el formulario de alta.
3. Captura Nombre (obligatorio), Tipo (cliente o proveedor), RFC, Tipo fiscal (el regimen fiscal), Codigo postal, domicilio, correo, telefono y contacto.
4. Si es necesario, captura Nivel de servicio (estandar o premium) y Limite de credito (no negativo).
5. Guarda.
Para poder facturarle, el cliente necesita RFC, razon social, regimen fiscal y codigo postal fiscal correctos; el sistema los valida al timbrar.

## Como marcar la empresa principal
1. Abre la empresa propia en Clientes y proveedores.
2. Marca la casilla Empresa principal. Debe tener RFC.
3. Si quieres, captura la Serie del CFDI por omision (hasta 25 caracteres).
4. Guarda.
Solo puede haber una empresa principal: al marcar otra, la anterior deja de serlo. Su RFC sirve para clasificar automaticamente las facturas XML cargadas como venta o compra, y la empresa principal aparece como emisor al facturar. Sin empresa principal con RFC no se pueden cargar facturas XML.

## Como registrar contactos de un cliente
1. En la vista de Clientes, baja al panel Contactos.
2. Elige la Empresa (debe ser un cliente), captura Nombre completo, Correo, Telefono y Cargo, y elige el Estado (activo o inactivo).
3. Guarda.
Solo se pueden ligar contactos a empresas de tipo cliente. Los contactos activos aparecen al elegir el cliente de un proyecto, con el formato Empresa - Contacto. Para editar o eliminar un contacto usa los botones de su fila; eliminar pide confirmacion.

## Como publicar productos en el catalogo web
1. Abre Catalogo Web, pestana Productos.
2. Busca por nombre o SKU y filtra por Estado de publicacion o Configuracion.
3. Edita un producto: captura Margen % o Precio manual, y guarda.
4. Para varios a la vez, selecciona productos y usa Aplicar margen masivo, Publicar seleccionados o Despublicar seleccionados.
Un producto nuevo en el catalogo nace en Borrador y activo. Solo se muestra en la tienda si esta Publicado, activo, tiene precio (margen o precio manual) y tiene existencia mayor a cero. Usa Preview de precio para ver el resultado.

## Como se calcula el precio publico del catalogo
- Con **Precio manual**: ese es el precio antes de IVA.
- Sin precio manual: precio base del producto por (1 + Margen % / 100).
- Al resultado se le suma el IVA (16 % por omision) y ese es el precio publico, que la tienda muestra con impuesto incluido en MXN.
- Si el producto no tiene margen ni precio manual, no se publica.
El precio base viene del producto del inventario. La imagen y la existencia tambien se toman del producto.

## Como crear y revocar una llave API del catalogo
1. En Catalogo Web, abre la pestana API Keys (solo la ven quienes administran llaves).
2. Pulsa Crear API key y captura Etiqueta, Dominios permitidos (opcional) y Limite por minuto.
3. Copia la llave en ese momento con Copiar key: solo se muestra una vez.
4. Para desactivarla, pulsa Revocar y confirma.
Un sitio web usa la llave para consultar el catalogo publico. Con dominios permitidos, solo responde a esos sitios. Si se rebasa el limite por minuto, la tienda recibe un error de demasiadas peticiones. Una llave revocada deja de funcionar y no se puede recuperar el valor de una ya creada.

## Como consume la tienda en linea el catalogo publico
- La tienda manda su llave API en cada peticion.
- Puede listar productos publicados (con busqueda por texto y por categoria, paginados hasta 100 por pagina), consultar un producto y consultar las categorias.
- Cada producto trae SKU, nombre, descripcion, categoria, marca, imagen, existencia, precio con IVA y moneda.
- Los compradores de la tienda se registran e inician sesion por separado, y en Compradores Web se pueden consultar y activar o desactivar.
No documentado: pedidos de la tienda; la columna Pedidos de Compradores Web todavia no cuenta pedidos.

## Como crear una encuesta
1. Crea la pregunta en Pregunta de encuesta: texto (hasta 300 caracteres) y tipo.
2. Si es de opcion, captura sus respuestas posibles en Respuesta multiple de encuesta (descripcion y puntaje opcional).
3. Las respuestas de una persona se guardan en Usuario de encuesta: pregunta, respuesta elegida, usuario, descripcion, puntaje y estado.
Tipos de pregunta: opcion multiple, opcion unica, si o no, puntaje, texto corto y texto largo. Cada pregunta tiene un propietario. No documentado: envio de encuestas a clientes ni reportes de resultados; solo existen estas tres pantallas de captura.

## Como crear tu agenda de citas
1. Abre Calendario.
2. Si es la primera vez, captura Nombre publico, Codigo del enlace (solo letras, numeros y guiones; debe ser unico) y Zona horaria, y pulsa Crear agenda.
3. En Tipos de cita pulsa Agregar tipo: Nombre, Duracion (de 5 a 480 minutos) y Anticipacion en minutos.
4. En Disponibilidad agrega los horarios semanales: dia, Desde y Hasta.
5. Pulsa Copiar enlace y compartelo, o Abrir pagina.
La agenda es personal y de tu proyecto. La videollamada (Google Meet, Teams, Zoom) aparece deshabilitada: solo se puede crear Sin videollamada.

## Como reserva una cita un invitado
1. El invitado abre el enlace publico de la agenda.
2. Elige el tipo de cita y un dia, y ve solo los horarios libres.
3. Captura nombre, correo y notas opcionales, y confirma.
La cita nace **confirmada**. Los horarios respetan la anticipacion minima, un horizonte maximo (60 dias por omision), la disponibilidad semanal y las citas ya reservadas, con sus tiempos antes y despues. Si dos personas eligen el mismo horario, la segunda ve que ya se ocupo. Si el correo esta configurado, el invitado recibe confirmacion y un recordatorio unas 24 horas antes. Tus citas se ven en Calendario, tabla Citas. No documentado: cancelar o reprogramar desde pantalla.

## Estatus y que significan
- **Cita**: pending_confirmation (Pendiente de confirmacion), confirmed (Confirmada) y cancelled (Cancelada). Las citas reservadas por el enlace publico nacen confirmed; una cancelada no se puede cancelar de nuevo.
- **Contacto**: activo o inactivo.
- **Producto del catalogo web**: Borrador (web_draft), Publicado (web_published) y Despublicado (web_unpublished). Tambien tiene un indicador activo.
- **Llave API**: activa o revocada.
- **Empresa**: tipo client o supplier. Nivel de servicio standard o premium. Estatus del CSD: none, uploaded o error (ver Facturacion).
- **Cotizacion**: ver el manual de Facturacion.

## Reglas y permisos importantes
- Cada rol tiene alcance por accion (crear, leer, actualizar, eliminar) sobre cada tabla en el Gestor de roles y permisos; por omision el Administrador tiene todo y el Gerente captura CRM.
- Al crear un proyecto se puede elegir el cliente (empresa y contacto) aunque el rol no tenga acceso completo al CRM.
- Marcar una empresa principal exige RFC y quita la marca a la anterior.
- Los contactos solo se ligan a clientes.
- Las llaves API, las citas publicas y el catalogo publico tienen limite de peticiones por minuto.
- Las llaves y los dominios se administran con permisos propios (Llaves API).
- Las agendas y citas son del usuario que las creo.
- Solo quien tiene el modulo en su plan lo ve.

## Campos importantes de empresas y contactos
- **Nombre** (name) y **Tipo** (cliente o proveedor).
- **RFC** (tax_id) y **Tipo fiscal** (fiscal_type, el regimen fiscal).
- **Codigo postal** (postal_code), calle, numero, colonia, ciudad y estado.
- **Correo, telefono, contacto y sitio web**.
- **Empresa principal** (is_principal) y **Serie del CFDI** (serie_csd).
- **Nivel de servicio** (sla_level) y **Limite de credito** (credit_limit).
- **Estatus del CSD** (csd_status) y su fecha.
- **Contacto**: nombre completo, correo, telefono, cargo, estado y empresa.

## Campos importantes de catalogo, citas y encuestas
- **Configuracion de venta web**: producto, Margen %, Precio manual, Estado de publicacion y activo.
- **Llave API**: etiqueta, prefijo, dominios permitidos, limite por minuto, activa, ultimo uso.
- **Cita**: invitado (nombre, correo, notas), inicio, fin, zona horaria, estado, tipo y agenda.
- **Tipo de cita**: duracion, tiempo antes, tiempo despues, anticipacion minima y horizonte en dias.
- **Pregunta de encuesta**: pregunta, tipo y propietario.
- **Respuesta**: descripcion y puntaje.

## Preguntas frecuentes
- **No puedo marcar la empresa principal.** Falta capturar su RFC.
- **No me deja cargar XML.** Define primero una empresa principal con RFC.
- **No puedo agregar un contacto a un proveedor.** Los contactos son solo de clientes.
- **Mi producto no sale en la tienda.** Debe estar Publicado, activo, con margen o precio manual y con existencia mayor a cero.
- **Perdi la llave API.** No se puede recuperar; revoca la llave y crea otra.
- **Dos invitados reservaron el mismo horario.** La segunda reserva se rechaza; el horario ya estaba ocupado.
- **Puedo usar Google Meet o Zoom?** Todavia no; solo citas sin videollamada.
- **Quien ve mis citas?** Solo tu usuario, dentro de tu proyecto.

## Preguntas de datos que se pueden hacer al asistente BI
- Cuantos clientes y cuantos proveedores hay.
- Clientes por ciudad o por estado.
- Empresas con limite de credito mayor a cierta cantidad.
- Clientes con nivel de servicio premium.
- Contactos activos por empresa.
- Citas por estatus o por mes.
- Cuantas citas confirmadas hay esta semana.
- Productos publicados en el catalogo web.
- Llaves API activas y su ultimo uso.
- Preguntas de encuesta por tipo.
- Total de facturas por cliente.
