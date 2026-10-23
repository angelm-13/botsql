# Como usar el Analisis BI

El boton verde "Analisis BI" de la barra superior abre un asistente al que se le pregunta en lenguaje natural. Hay dos tipos de preguntas: de datos (cuantos, cuales, por mes, top N) y de ayuda sobre el sistema (que es, como funciona, que modulos hay).

## Preguntas de datos
El asistente convierte la pregunta en una consulta de solo lectura, la ejecuta y muestra una tabla. Nunca modifica ni borra informacion. Por omision muestra tabla; solo dibuja una grafica si la pregunta la pide (por ejemplo "en grafica de barras", "en pastel", "tendencia" o "dashboard"). Un total unico se muestra como tarjeta con el numero.

Ejemplos: "cuantos productos hay", "top 8 productos por existencias", "incidencias por tipo", "proyectos por estatus", "total de facturas por cliente", "vales vencidos", "herramientas del vale 140".

## Lo que cada persona puede ver
Cada rol ve solo las tablas y columnas que el Gestor de roles y permisos le permite leer. El administrador ve todo. Si una persona pregunta por algo que su rol no puede ver, el asistente responde que la consulta no esta permitida para su rol. Por ejemplo, un rol de operaciones puede no ver los importes de finanzas.

## Tiempos
Las preguntas frecuentes responden al instante. Una pregunta nueva puede tardar de uno a tres minutos porque el modelo de lenguaje corre en el propio equipo. Repetir la misma pregunta es inmediato porque se guarda la respuesta.

## Lo que el asistente no hace
No inserta, actualiza ni elimina datos. No muestra contrasenas, tokens ni secretos. No muestra la consulta SQL ni la estructura de la base de datos.

## Buscar cualquier dato
Escribe "busca" y lo que quieres encontrar, por ejemplo "busca ACE133", "busca Roberto" o "donde aparece BMW". El asistente revisa todas las tablas y columnas de texto que tu rol puede leer y muestra el modulo, la tabla, el campo, el valor encontrado y su numero de registro. Si tu rol no puede ver una tabla, esa tabla no se busca.

## Pronosticos (analisis predictivo)
Puedes pedir "predice los vales de los proximos 3 meses", "pronostico de herramientas prestadas", "pronostico de facturacion" o "pronostico de ventas del punto de venta". Se calcula una tendencia lineal con los meses completos que hay en la base y se muestra el historico, el valor esperado de cada mes futuro y un rango probable. Con pocos meses de historia el resultado es poco confiable y el asistente lo avisa. Es una proyeccion de tendencia: no considera estacionalidad ni eventos futuros.
