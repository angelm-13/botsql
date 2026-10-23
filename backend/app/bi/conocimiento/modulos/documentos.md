---
modulo: documentos
entidades_clave: [document, document_version, document_category]
---
# Documentos

## Que es el modulo Documentos y para que sirve
Documentos es el archivo digital del sistema. Guarda archivos (PDF, imagenes) ligados a un cliente, proveedor o empleado, y conserva cada version del archivo con su huella de integridad (sha256), tamano y quien lo subio. Tambien es donde aparecen archivados los reportes de diagnostico del modulo Laboratorio y los vales de almacen impresos. Cada documento pertenece al proyecto del usuario que lo carga y solo se ve dentro de ese proyecto.

## Pantallas y donde encontrarlas en Documentos
Menu lateral, grupo Laboratorio (puede aparecer como grupo Documentos segun la instalacion), opcion **Documentos**. La pantalla "Documentos y evidencias" tiene dos partes: a la izquierda el formulario **Cargar documento**; a la derecha la lista con buscador por titulo, filtro de estado, boton Filtrar, y un boton **Versiones** por renglon que abre el detalle de versiones con su boton de descarga. Arriba hay un boton para actualizar la lista. No existe una pantalla para administrar las categorias: solo se eligen al cargar.

## Como cargar un documento en Documentos
1. Abre Documentos y ve al formulario **Cargar documento**.
2. Escribe el **Titulo** y elige la **Categoria**.
3. En **Relacionado con** elige "Cliente o proveedor" o "Empleado" y luego selecciona a la persona o empresa concreta (la lista de empleados solo trae empleados activos de tu proyecto).
4. Opcional: escribe una descripcion.
5. Elige el archivo (PDF, JPEG o PNG) y pulsa **Cargar**.
Al terminar se crea el documento en estado Borrador con su version 1 y aparece en la lista. Cada documento queda ligado a exactamente una relacion (un cliente, proveedor o empleado).

## Como buscar y filtrar documentos
1. Abre Documentos.
2. Escribe parte del titulo en el buscador (tambien busca en la descripcion).
3. Si quieres, elige un estado en la lista "Todos los estados".
4. Pulsa **Filtrar**.
La lista muestra Titulo, Estado y fecha de Creacion, de la mas reciente a la mas antigua (hasta 50 resultados en pantalla). Si no hay coincidencias aparece "No hay documentos para estos filtros".

## Como ver y descargar las versiones de un documento
1. En la lista pulsa **Versiones** en el renglon del documento.
2. Abajo aparece el titulo y una fila por version, con formato "v1 · origen · estado". El origen puede ser subido, generado o escaneo firmado.
3. Pulsa el icono de descarga de la version que necesitas.
Cada version nueva recibe el siguiente numero consecutivo y las anteriores se conservan; nunca se sobrescriben. Desde esta pantalla no se puede subir una version nueva a mano: las versiones nuevas llegan, por ejemplo, al generar o firmar un reporte de laboratorio.

## Documentos que se archivan solos desde otros modulos
El reporte de diagnostico (PDF) de una orden de Laboratorio se guarda aqui con el titulo "Reporte de diagnostico" mas el folio de la orden, categoria "Reporte de diagnostico", estado Emitido, ligado al cliente, al equipo y a la orden. Cada vez que se genera otro PDF se agrega una version al mismo documento. Al subir la copia firmada, el documento pasa a Firmado. Los vales de almacen impresos se archivan con la categoria "Vale de almacen".

## Estatus de un documento y que significan
Estados reales: **draft** (Borrador, lo que se crea al cargar desde la pantalla), **issued** (Emitido, por ejemplo un reporte generado), **signed** (Firmado, cuando se sube la copia firmada), **rejected** (Rechazado) y **cancelled** (Cancelado). La lista muestra el codigo en ingles dentro de una etiqueta, aunque el filtro usa nombres en espanol. Cada version tiene su propio estado con los mismos valores. No documentado: reglas de que estado puede seguir a cual; el sistema no restringe transiciones de estado de documentos.

## Reglas y permisos de Documentos
- Cada rol ve solo lo que el Gestor de roles y permisos le permite; por defecto solo el rol Administrator trae Documentos, y cada instalacion puede ampliarlo.
- Leer documentos y categorias requiere permiso de lectura en documentos; cargar requiere permiso de crear; descargar versiones requiere lectura de versiones.
- Un usuario no administrador solo ve documentos de su proyecto. Los usuarios de tipo cliente o proveedor ademas solo ven los documentos relacionados con su propio registro.
- No documentado: boton para editar o eliminar documentos desde la pantalla (el sistema permite el borrado logico pero la pantalla no lo ofrece).

## Archivos permitidos y tamano en Documentos
La pantalla acepta PDF, JPEG y PNG. El sistema revisa que el contenido real del archivo coincida con su extension; si no coincide lo rechaza. El tamano maximo por archivo es 10 MB por omision (la instalacion puede cambiarlo). Los archivos se guardan con un nombre interno generado, no con el original; el nombre original se conserva como dato de la version.

## Campos importantes de Documentos
- **Titulo**: nombre con el que se busca el documento.
- **Categoria**: tipo de documento. Las de fabrica son Empleado, Cliente, Proveedor, Certificacion, Recibo, Proceso interno, Recepcion de equipo, Reporte de diagnostico, Reporte de diagnostico firmado y Vale de almacen.
- **Estado**: borrador, emitido, firmado, rechazado o cancelado.
- **Fecha de emision / vencimiento**: existen en la base; la fecha de vencimiento no puede ser anterior a la de emision. No documentado: captura desde la pantalla.
- **Referencia de negocio** (tipo y valor): enlace opcional a otro registro, usado p. ej. por vales de almacen.
- **Relacion**: cliente, proveedor, empleado, equipo u orden de laboratorio; solo una por documento.

## Preguntas frecuentes de Documentos
- **No me aparece Documentos en el menu.** Tu rol no tiene permiso de lectura; pidelo a un administrador.
- **Por que no puedo subir un Word o Excel?** La pantalla solo acepta PDF, JPEG y PNG.
- **Puedo cambiar el estado de un documento?** No desde la pantalla actual.
- **Se pierde la version anterior al subir otra?** No, todas se conservan.
- **Donde esta el reporte firmado de laboratorio?** En Documentos, en la version con origen "escaneo firmado".
- **No veo un documento que otro compano subio.** Solo se ven los de tu proyecto y, si eres cliente o proveedor, los ligados a ti.

## Preguntas de datos que se pueden hacer al asistente BI sobre Documentos
- "cuantos documentos hay por estatus"
- "documentos por categoria"
- "documentos firmados"
- "documentos que vencen este mes" (usa la fecha de vencimiento)
- "documentos cargados este mes"
- "versiones de cada documento" o "documentos con mas de una version"
- "documentos relacionados con empleados"
Tablas usadas: document, document_category, document_version y document_relation.
