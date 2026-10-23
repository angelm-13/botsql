---
modulo: operaciones
entidades_clave: [proyect, task, incident, nm_incident_product]   # basta leer una para ver este manual
---
# Operaciones

## Qué es y para qué sirve el módulo Operaciones
Operaciones lleva el trabajo del taller: proyectos (órdenes de trabajo) con sus tareas, notas e historial, y las incidencias. Un proyecto tiene cliente, responsable, folio, cotización, orden de compra, fecha de entrega y dos recorridos que avanzan por separado: el de taller (borrador, autorizado, en proceso, completado, entregado...) y el comercial de Gerencia (pendiente de orden de compra, autorizado, cobrado, cancelado), con parcialidades de pago. Una incidencia registra un hecho con tipo, responsable y estatus; en el negocio un "vale" de almacén ES una incidencia (se explica en el manual de Inventario).

## Pantallas y dónde encontrarlas en Operaciones
Menú Operaciones, en el orden del flujo de trabajo:
- Proyectos (título "Gestión de proyectos"): lista o tablero de proyectos, su expediente y los cambios de estado.
- Tareas: lista o tablero kanban de tareas.
- Incidencias: lista o kanban de incidencias.
- Tipos de incidencia y Subtipos de incidencia: catálogos.
- Plantillas de tarea y Tipos de tarea: catálogos.
Las notas de una tarea no tienen pantalla propia: se escriben dentro de la tarea, en el expediente del proyecto. El Calendario aparece en este grupo del menú pero pertenece al módulo CRM.

## Cómo crear un proyecto en Operaciones > Proyectos
1. Abre Operaciones > Proyectos y pulsa "Nuevo proyecto" (solo si tu rol puede crear).
2. Escribe el Título (máximo 50 caracteres) y elige el Cliente, que se escoge como contacto "Empresa - Persona".
3. Opcional: Partida (folio), Cotización (folio del sistema o de uno externo), Fecha de entrega. La Orden de compra solo la captura Gerente.
4. Guarda.
Al terminar, el proyecto queda en estado Borrador, tú quedas como Responsable (no se puede elegir a otra persona) y se anota "Proyecto creado" en su historial.

## Cómo editar o eliminar un proyecto en Operaciones
Editar: pulsa el lápiz en la fila. Quien creó o lidera el proyecto solo puede editarlo mientras esté en Borrador o Bloqueado; Gerente puede editarlo en cualquier estado y el taller solo los que lidera. El estado no se edita en el formulario: se cambia con "Cambiar estado".
Eliminar: solo en estado Borrador, solo quien lo creó, y solo si su rol tiene permiso de eliminar (por omisión, administración). Una cotización no puede estar ligada a dos proyectos a la vez.

## Cómo cambiar el estado de un proyecto en Operaciones > Proyectos
1. Busca el proyecto y abre el selector "Cambiar estado" de su fila (solo ofrece los cambios que tu rol puede hacer desde el estado actual).
2. Elige el nuevo estado.
3. Escribe el motivo si lo pide (obligatorio al Denegar, Bloquear o Detener) y, si quieres, una observación; al bloquear puedes poner fecha de revisión.
4. Pulsa "Confirmar cambio".
Al terminar, el cambio queda en el historial del proyecto con quién, cuándo y por qué. Para Entregar, todas las tareas deben estar terminadas o canceladas; si no, el sistema lo rechaza.

## Cómo ver el expediente de un proyecto y escribir mensajes
1. En Proyectos pulsa el ojo ("Ver detalle").
2. El expediente muestra: orden de trabajo (folio, quién lo pidió, cotización, orden de compra, entrega), Gerencia y parcialidades (solo Gerente), adjuntos, material prestado, incidencias del proyecto, calendario, tareas e historial.
3. Para avisar al equipo, escribe en "Nuevo mensaje" y pulsa Publicar.
Adjuntos: se suben PDF o DOCX con "Subir archivo", con título opcional. "Material prestado" suma por producto lo sacado con vales de este proyecto y lo que sigue sin devolver.

## Cómo llevar la parte comercial y las parcialidades de pago de un proyecto
Solo Gerente (o un administrador sin restricción), en el expediente del proyecto, sección Gerencia:
1. Cambia el estado comercial con los botones que aparecen: pendiente de orden de compra > autorizado o cancelado; autorizado > cobrado o cancelado; cobrado y cancelado son finales.
2. En "Parcialidades de pago" pulsa "Acordar parcialidad" con fecha acordada, monto (mayor a cero), % pactado y nota.
3. Cuando entra el dinero, marca la parcialidad con la fecha real de cobro.
El resumen muestra acordado, cobrado, pendiente y % pactado. No se fuerza a que los porcentajes sumen 100.

## Cómo crear y mover una tarea en Operaciones > Tareas
1. Abre Operaciones > Tareas y pulsa Nuevo (requiere permiso de crear tareas).
2. Escribe la descripción (máximo 200), elige el Proyecto y la Fase.
3. Guarda. La tarea nace Pendiente y en fase "En espera". No se pueden crear tareas en un proyecto completado, entregado o denegado.
Para mover su estado formal: Proyectos > ver detalle > pulsa la tarea > "Cambiar estado" (motivo obligatorio al Bloquear o Cancelar). Cambiar la Fase desde Tareas también actualiza el estado sin pedir motivo.

## Cómo escribir una nota en una tarea
1. En Operaciones > Proyectos abre el detalle del proyecto.
2. Pulsa la tarea para abrir su "Bitácora de la tarea".
3. Escribe en "Nueva nota" el avance o el impedimento y pulsa Publicar.
Al terminar, la nota queda en la bitácora de la tarea y también aparece como "Nota de tarea" en el historial del proyecto, para leer todo en una sola línea de tiempo. Una nota no existe sin su tarea.

## Cómo registrar una incidencia en Operaciones > Incidencias
1. Abre Operaciones > Incidencias y pulsa Nuevo.
2. Llena la fecha (no puede ser futura), el Tipo, la Nota (máximo 300), el Usuario responsable y, si aplica, el Líder.
3. Deja el Estado vacío (nace "abierta") o escribe uno del catálogo.
4. Guarda.
Para cerrarla pasa su estado a resuelta o cerrada: la fecha de cierre se llena sola y no puede ser anterior a la fecha de la incidencia. Para cancelarla escribe el motivo en la Nota. Una incidencia resuelta puede reabrirse (vuelve a en proceso y se borra su fecha de cierre).

## Estatus y qué significan: proyecto (recorrido de taller)
- Borrador: recién capturado.
- En revisión: existe por compatibilidad, hoy nadie puede pedirlo.
- Autorizado: Gerente lo aprobó, el taller ya lo ve.
- Denegado: rechazado; es final.
- Bloqueado: detenido por Gerente o por el taller, con motivo.
- En proceso: el taller trabaja en él.
- En espera de material: el trabajo va bien pero falta que llegue material.
- Detenido: alguien lo paró, con motivo.
- Completado: el taller terminó.
- Entregado: salió al cliente; es final.
Denegado y Entregado no tienen salida.

## Estatus y qué significan: transiciones permitidas de un proyecto
- Borrador: a autorizado, denegado, bloqueado (o en revisión).
- En revisión: a autorizado, denegado, bloqueado.
- Bloqueado: a en revisión, autorizado o denegado. Un proyecto bloqueado en curso vuelve a pasar por Gerente.
- Autorizado: a en proceso.
- En proceso: a en espera de material, detenido, completado o bloqueado.
- En espera de material: a en proceso o detenido.
- Detenido: a en proceso.
- Completado: a entregado.
No documentado: quién puede pasar un proyecto a "En espera de material"; en lo revisado ningún rol tiene ese cambio habilitado.

## Estatus y qué significan: tarea y fase
Estado de la tarea: pendiente, en proceso, bloqueada, en revisión, terminada, cancelada.
Transiciones: pendiente a en proceso o cancelada; en proceso a en revisión, bloqueada, terminada o cancelada; bloqueada a en proceso o cancelada; en revisión a terminada o en proceso; terminada y cancelada son finales. Motivo obligatorio al bloquear o cancelar.
Fase (columna del tablero del taller): en espera, en proceso, bloqueado, terminado, entregado. Equivalen a pendiente, en proceso, bloqueada, terminada y terminada; no existe un estado "entregada" distinto.

## Estatus y qué significan: incidencia, vale y estado comercial
Incidencia: abierta, en proceso, resuelta, cerrada, cancelada. Transiciones: abierta a en proceso, resuelta o cancelada; en proceso a resuelta o cancelada; resuelta a cerrada o de vuelta a en proceso; cerrada y cancelada son finales. Cancelar exige motivo.
Vale de almacén (también incidencia): borrador, abierto, cerrado, cancelado (los datos migrados pueden decir abierta o cerrada). Un vale está vencido cuando sigue abierto y una herramienta no volvió después de su fecha límite; "vencido" no es un estatus.
Estado comercial del proyecto: pendiente orden de compra, autorizado, cobrado, cancelado.

## Reglas y permisos importantes: quién autoriza y quién ejecuta proyectos
- Autorizar, denegar o bloquear antes de iniciar: solo quien tiene el permiso de autorizar proyectos (Gerente). El responsable no aprueba su propio proyecto.
- Iniciar, detener, completar o bloquear en curso: el taller (Jefe de taller) o el responsable del proyecto.
- Entregar al cliente: el responsable del proyecto (normalmente Supervisor).
- Estado comercial y parcialidades de pago: solo Gerente.
- Supervisor crea proyectos y ve solo los suyos (los que creó o lidera); en Tareas e Incidencias solo consulta. Jefe de taller ve los proyectos autorizados y en adelante, más los que lidera.
- Gerente ve todos los proyectos.
Son permisos por omisión; el Gestor de roles y permisos de cada instalación manda.

## Reglas y permisos importantes: tareas, incidencias y avisos
- Tareas: se ven según los proyectos que puedes ver; crear tareas pide permiso de crear (Supervisor no lo tiene por omisión).
- Incidencias: cada persona ve las que reportó, atiende o lidera; quien tiene el permiso "Supervisar incidencias ajenas" (Supervisor, Gerente, Jefe de taller) las ve todas.
- Algunos campos pueden estar ocultos según el rol.
- Quien tenga el permiso de eliminar puede borrar tareas e incidencias que ve.
- Avisos y bitácora del supervisor: existen las tablas notification (avisos por usuario), supervisor_activity_log (bitácora diaria) y supervisor_daily_attachment (adjuntos de la bitácora: txt, docx, pdf e imágenes hasta 25 MB). No documentado: la pantalla y el menú donde se abren, y qué eventos del proyecto generan aviso; el recordatorio de bitácora faltante a supervisores no está programado en esta versión.

## Campos importantes: proyecto
- Título y Partida (folio): cómo se reconoce; si no tiene folio se muestra PRJ- y su número.
- Cliente (contacto Empresa - Persona) y "Lo pidió" (sale del contacto).
- Responsable: quien lo creó.
- Cotización: folio de una factura/cotización del sistema o de uno externo.
- Orden de compra: la del cliente, la captura Gerente.
- Fecha de entrega.
- Estado (taller) y estado comercial.
- Fecha de creación y de actualización.
- Parcialidad: fecha acordada, monto, % pactado, fecha de cobro, nota.

## Campos importantes: tarea, incidencia y renglón de vale
Tarea: descripción, proyecto, fase, estado, prioridad (baja, media, alta, urgente), duración, fecha de inicio y responsable.
Incidencia: fecha, tipo, nota, usuario responsable, líder, estatus, fecha de cierre y proyecto (nulo en un vale de almacén).
Renglón de vale: producto, cantidad, pieza, dirección (sale, entra, cambia de sitio), fecha límite de regreso (due_date) y fecha de cierre; sin fecha de cierre el renglón sigue fuera.
Catálogos: Tipo de incidencia (Préstamo Material, Jornada, Comida, Salida por Permiso o accidente, Vacaciones, Maternidad, Reparación, Destrucción, Dañado, Extraviado), Subtipo (pertenece a un tipo), Plantilla de tarea y Tipo de tarea (descripción, alcance y límite, hoy sin uso en las tareas).

## Preguntas frecuentes de Operaciones: proyectos
- ¿Por qué no veo un proyecto? Supervisor solo ve los suyos; Jefe de taller, los autorizados en adelante.
- ¿Quién autoriza un proyecto? Gerente.
- ¿Por qué no me deja entregar? Hay tareas sin terminar ni cancelar, o no eres el responsable.
- ¿Por qué no puedo editarlo? Solo se edita en Borrador o Bloqueado si eres quien lo creó o lidera.
- ¿Cómo registro un pago? Gerente, en el expediente, con "Acordar parcialidad".
- ¿Puedo cambiar el responsable? No, siempre es quien creó el proyecto.
- ¿Hay módulo de compras o necesidades de material? No documentado en Operaciones; el material se pide con prevales en Inventario.

## Preguntas frecuentes de Operaciones: tareas, incidencias y vales
- ¿Por qué no puedo crear una tarea? El proyecto está cerrado o tu rol no puede crear tareas.
- ¿Cómo bloqueo una tarea? Cambiar estado y escribir el motivo.
- ¿Qué es un vale? Una incidencia con renglones de material; se maneja en Inventario > Vales de almacén.
- ¿Cuándo está vencido un vale? Cuando sigue abierto y un renglón pasó su fecha de regreso sin devolverse.
- ¿Por qué no me deja cancelar una incidencia? Falta el motivo.
- ¿Cómo aplico una plantilla de tarea? No documentado: solo se capturan plantillas y su enlace con tareas.

## Preguntas de datos que se pueden hacer al asistente BI sobre Operaciones
- Proyectos por estatus.
- Proyectos del cliente X.
- Proyectos completados o entregados este mes.
- Proyectos sin fecha de entrega.
- Tareas por fase o por estado.
- Tareas bloqueadas por proyecto.
- Incidencias por tipo.
- Incidencias abiertas por responsable.
- Vales vencidos.
- Herramientas del vale 140.
- Material que sigue fuera por proyecto.
- Parcialidades de pago pendientes por proyecto.
