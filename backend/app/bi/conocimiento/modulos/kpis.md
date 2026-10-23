---
modulo: kpis
entidades_clave: [kpi_definition, kpi_dashboard]
---
# KPIs

## Que es y para que sirve
El modulo KPIs muestra indicadores clave del negocio (ventas, egresos, desempeno de tareas, vales vencidos, inventario, laboratorio y mas) en tableros graficos. Los indicadores (KPI) vienen predefinidos en el sistema: tu no los creas, solo eliges cual ver, de que fechas, de que personas y con que tipo de grafica. Cada persona arma sus propios tableros, que son privados. Un administrador decide que KPIs puede ver cada rol.

## Pantallas y donde encontrarlas
- **Dashboard** (pantalla de inicio, titulo Tableros de KPIs): tus tableros y sus graficos. No tiene apartado propio en el menu lateral; es la pagina inicial.
- **Permisos de KPIs** (engrane, solo administradores): decide que KPIs ve cada rol.
En el Dashboard hay pestanas con el nombre de cada tablero, un boton + para crear uno nuevo, un panel Agregar grafico y la cuadricula de graficos. Si no tienes KPIs asignados, ves el aviso No tienes KPIs asignados.

## Como crear un tablero
1. En el Dashboard pulsa el boton + (o Nuevo tablero si aun no tienes ninguno).
2. Escribe el nombre del tablero y acepta.
3. Para cambiarle el nombre pulsa el lapiz de su pestana; para eliminarlo, el bote de basura.
Cada persona solo ve y modifica sus propios tableros: nadie mas, ni otro rol, los ve. Eliminar un tablero lo quita de tu lista (la baja es logica: el registro se conserva).

## Como agregar un grafico a un tablero
1. Elige el tablero y usa el panel Agregar grafico.
2. Elige la Categoria (modulo) y el KPI o KPIs (Variables).
3. Elige el Tipo de grafico: numero, barras, linea, area o dona.
4. Elige Fecha inicio y Fecha fin (hay atajos de fecha). El rango no puede pasar de un anio, salvo que tu plan permita otro limite.
5. Elige Agrupar por (empleado, producto o periodo para ver tendencia) y, si quieres, filtra por empleados o por departamento.
6. Pulsa Agregar grafico.
Solo barras, linea y area aceptan varios KPIs en el mismo grafico; numero y dona, uno solo. Puedes cambiar el color de cada KPI.

## Como comparar dos periodos
1. Al crear o editar el grafico, activa Comparar contra otro periodo.
2. Elige las fechas del Periodo B (comparacion); el Periodo A es el rango principal.
3. Guarda.
El grafico muestra ambos periodos para compararlos (vs. periodo anterior), con los mismos filtros. Si activas la comparacion, el rango B es obligatorio y tampoco puede pasar de un anio.

## Como editar, reordenar y quitar graficos
1. Para cambiar un grafico pulsa el lapiz del grafico, ajusta KPI, fechas, tipo o filtros y pulsa Actualizar.
2. Para reordenar, arrastra el grafico desde su asa a otra posicion.
3. Para quitarlo, pulsa el bote de basura y confirma.
Un grafico sin KPI o sin rango de fechas muestra el aviso de que falta configurarlo; editalo para completarlo. Quitar un grafico solo lo da de baja de tu tablero: no cambia ningun dato.

## Como generar un reporte en PDF
1. En el panel Agregar grafico pulsa Generar reporte PDF.
2. Elige si quieres solo el Panel actual o Todos los paneles.
3. Espera el aviso Generando reporte PDF y se descarga el archivo.
Los paneles sin graficos no aportan nada al reporte; si ninguno tiene graficos, el sistema avisa que no hay que incluir.

## Como dar permiso de un KPI a un rol (administrador)
1. En el engrane abre Permisos de KPIs.
2. Elige el rol.
3. Marca o desmarca cada KPI; estan agrupados por modulo. El cambio se guarda al instante.
Cada persona ve solo los KPIs asignados a su rol (la cuenta de arranque ve todos). Ademas, el KPI debe pertenecer a un modulo que el plan de tu empresa tenga contratado, y el rol necesita tener el modulo de KPIs. Este permiso es de ver o no ver, no de crear.

## Catalogo de KPIs: facturacion
- **Ventas por empleado** (moneda): subtotal (antes de IVA) de las facturas emitidas, por quien las creo, por fecha de emision. No cuenta canceladas, cotizaciones ni facturas de compra.
- **Egresos por empleado** (moneda): igual, pero solo facturas de compra.
- **Ingresos totales** (moneda): las ventas de toda la empresa, por dia, sin desglose por persona.
- **Egresos totales** (moneda): las compras de toda la empresa, por dia.
Se acotan al proyecto de quien consulta. Para que una factura cuente como compra, su direccion debe ser compra (por ejemplo, XML cargado). No documentado: si las cotizaciones del tablero (borrador, enviada, etc.) se excluyen del calculo.

## Catalogo de KPIs: operaciones y laboratorio
- **Desarrollo por empleado** (porcentaje): tareas terminadas entre tareas del responsable, por fecha de creacion de la tarea.
- **Vales vencidos por responsable** (numero): renglones de vale sin devolver cuya fecha limite ya paso.
- **Incidentes resueltos por empleado** (porcentaje): incidentes resueltos o cerrados entre todos los creados; los cancelados no cuentan como resueltos.
- **Cancelaciones por empleado** (numero): incidentes cancelados, por fecha de cierre.
- **Ordenes de laboratorio entregadas por tecnico** (numero).
- **Tiempo promedio de reparacion por tecnico** (dias entre recepcion y entrega).
- **Costo promedio de reparacion por tecnico** (moneda; solo ordenes con costo capturado).
- **Documentos vencidos por responsable** (numero): documentos firmados con fecha de vencimiento ya pasada.

## Catalogo de KPIs: inventario
- **Material prestado por responsable** (numero): prestamos de piezas iniciados por dia, por quien recibio la pieza.
- **Prestamos de material vencidos por responsable** (numero): piezas prestadas cuya fecha de regreso paso y siguen sin devolverse, por quien las tiene.
- **Lotes proximos a caducar** (numero, por producto): lotes cuya caducidad cae dentro del rango de fechas que elijas; ese rango es el umbral.
- **Articulos bajo stock** (numero, por producto): existencia actual de cada producto. Captura el Umbral de stock bajo en el grafico para decidir que cuenta como bajo.
Los KPIs de vales, incidentes, cancelaciones, prestamos, lotes y stock no se acotan por proyecto; los de facturacion, tareas, laboratorio y documentos si.

## Cuando se actualizan los datos de los KPIs
Los graficos no leen las tablas en vivo: leen resultados ya calculados (snapshots), que una tarea automatica recalcula cada noche (a la 1:00 a.m.) para los ultimos 7 dias. Por eso lo capturado hoy puede no aparecer hasta la siguiente corrida, y una factura corregida unos dias despues si se refleja. Los KPIs de existencia actual y de vencimiento usan el momento real de calculo. No documentado: un boton para forzar el recalculo desde la pantalla (existe un recalculo manual por rango de fechas para el equipo tecnico).

## Estatus y que significan
Los KPIs no tienen estatus propios de flujo. Lo que si existe:
- **Tablero**: activo o eliminado; cada uno tiene un orden y pertenece a un usuario.
- **Grafico (widget)**: tipo numero, barras, linea, area o dona; con parametros de fechas, filtros y color.
- **Permiso de KPI**: el rol puede ver (puede_ver) o no ver ese KPI.
- **Unidad del KPI**: numero, moneda, porcentaje o dias.
- **Dimension**: por empleado, por producto o global (sin desglose).
No documentado: otros estatus.

## Reglas y permisos importantes
- Los tableros y graficos son privados por usuario: ni un administrador de otro usuario los ve por esta pantalla.
- Para ver un KPI hacen falta tres cosas: que tu rol tenga el modulo KPIs, que el administrador te asigne ese KPI en Permisos de KPIs y que el modulo al que pertenece el KPI este en el plan de la empresa (por ejemplo, sin Facturacion contratada no hay KPIs de facturacion).
- Por omision solo el Administrador tiene el modulo KPIs; otros roles lo reciben cuando el administrador lo decide en el Gestor de roles y permisos.
- Un usuario no puede guardar un grafico con un KPI que no tiene permitido.
- Un rango de fechas no puede pasar de un anio (el plan puede cambiar el limite).
- Los KPIs acotados por proyecto exigen que el usuario tenga proyecto asignado.

## Campos importantes
- **Clave y Etiqueta** del KPI: su nombre interno y el que ves.
- **Modulo**: de que area es (facturacion, operaciones, laboratorio, documentos, inventario).
- **Unidad**: numero, moneda, porcentaje o dias.
- **Dimensiones**: empleado, producto o global.
- **Tablero**: nombre, orden y dueno.
- **Grafico**: tipo, KPIs, rango A y B, empleados, departamentos, colores, agrupar por y umbral de stock.
- **Permiso de KPI**: rol, KPI y puede ver.

## Preguntas frecuentes
- **No veo ningun KPI.** Pide a un administrador que te asigne KPIs en Permisos de KPIs.
- **Mi grafico sale vacio.** No hay datos en ese rango o aun no corre el calculo nocturno; amplia el rango.
- **Por que no puedo juntar varios KPIs en un grafico de numero?** Numero y dona aceptan un solo KPI.
- **El rango de fechas esta rechazado.** Excede el maximo permitido (aprox. un anio); acortalo.
- **Los numeros de ventas no incluyen el IVA.** Correcto: se suma el subtotal.
- **Puedo ver los tableros de otra persona?** No; son privados.
- **Puedo crear un KPI nuevo?** No; los KPIs son predefinidos.
- **Cuantos KPIs hay?** Dieciseis en el catalogo.

## Preguntas de datos que se pueden hacer al asistente BI
- Cuantos KPIs hay por modulo.
- Que KPIs miden en moneda o en porcentaje.
- Cuantos tableros de KPIs tiene cada usuario.
- Graficos por tipo de grafica.
- Cuantos graficos tiene cada tablero.
- Que KPIs tiene asignados cada rol.
Para ver ventas, vales vencidos o inventario como dato, pregunta directamente por esos temas (por ejemplo: ventas del mes por cliente, vales vencidos); el asistente los calcula desde las tablas, no desde los tableros.
