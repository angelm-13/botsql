---
modulo: inventario
entidades_clave: [product, location, material, inventory_status]   # basta leer una para ver este manual
---
# Inventario

## Qué es y para qué sirve el módulo Inventario
Inventario lleva el almacén: qué productos y herramientas existen, cuántos hay, en qué ubicación (nave, pasillo, rack) están y quién se los llevó. Hay dos tipos de cosas: consumibles (se cuentan por cantidad, como tornillos o cable) y herramienta o equipo de uso interno (se rastrea pieza por pieza, cada una con su etiqueta). El material sale y vuelve por los vales de almacén: un vale es una incidencia con renglones (producto, cantidad o pieza, fecha de regreso). Este módulo también incluye los catálogos de los que cuelga un producto: familias, marcas, unidades, materiales, ubicaciones.

## Pantallas y dónde encontrarlas en Inventario: almacén, Localizar y vales
Menú Inventario:
- Almacén: árbol de naves, zonas y racks con la existencia de cada ubicación y el porcentaje del total del almacén; se filtra por ubicación y se abre el historial de un producto.
- Localizar: busca por nombre, código o etiqueta de pieza y dice dónde está, cuánto hay, qué le pasó y quién la tiene. Permite filtrar por "Consumible" o "Uso interno" y por estado de la pieza, y subir la foto del producto.
- Vales de almacén: lista de vales y prevales, buscador por folio o responsable, vencidos, captura, autorización, devolución e impresión.
- Rastreo de piezas: no tiene entrada de menú; se llega desde una pieza en Localizar.

## Pantallas y dónde encontrarlas en Inventario: catálogos
También en el menú Inventario, en este orden: Productos, Familias de producto, Marcas, Unidades, Ubicaciones, Tipos de ubicación, Materiales, Movimientos, Componentes y Estado de inventario. Se llena primero lo de apoyo y al final el producto: familia, marca y unidad, luego el material que las une, luego el producto. Ubicaciones y Tipos de ubicación arman el árbol del almacén (un tipo marcado como "almacén" es la raíz). Estado de inventario es el catálogo de estados del producto. La pantalla Movimientos del menú registra ingresos y gastos ligados a una cuenta fiscal, no mueve la existencia del almacén.

## Cómo dar de alta un producto en Inventario
1. Entra a Inventario > Productos y pulsa Nuevo.
2. Elige el material (que ya trae familia, marca y unidad), la ubicación y escribe descripción, código, color y cantidad inicial.
3. Elige el estado del producto (nuevo, usado, etc.) y, si quieres, sube una foto.
4. Guarda.
Al terminar, la existencia queda asentada en la ubicación elegida; si no pusiste ubicación, cae en la ubicación general del almacén para que aparezca en Localizar. No hace falta factura: el sistema usa una de captura directa. Si el material no existe, créalo antes en Materiales.

## Cómo localizar un producto o una herramienta en Inventario
1. Abre Inventario > Localizar.
2. Escribe nombre, código o la etiqueta pegada a la pieza (por ejemplo TAL-001).
3. Opcional: elige "Consumible" o "Uso interno", o filtra por estado de la pieza.
4. Abre el resultado: verás dónde está y cuánto hay en cada ubicación, su historial y, si es herramienta, sus piezas con estado y responsable.
Si hay coincidencias de proyectos a los que no tienes acceso, la pantalla lo avisa y cuenta cuántas son.

## Cómo ver cuánto hay por almacén en Inventario
1. Abre Inventario > Almacén.
2. Elige un almacén o escribe en el buscador una nave, pasillo o rack.
3. Despliega o pliega las ramas del árbol: cada ubicación muestra lo asentado ahí y el total acumulado de sus sublocaciones.
4. Abre un producto para ver su historial de movimientos.
Si no hay almacenes, marca un tipo de ubicación como almacén en Tipos de ubicación.

## Cómo levantar un prevale (pedir material) en Vales de almacén
Es para quien pide material pero no lo surte (rol Supervisor).
1. Abre Inventario > Vales de almacén y pulsa "Levantar prevale".
2. Elige el tipo de vale; el responsable eres tú. Opcional: elige tu proyecto.
3. Pon la fecha en que debe volver (obligatoria, no puede ser pasada) y el motivo (obligatorio, por ejemplo "Obra Norte").
4. Busca el producto y pulsa Agregar. Herramienta de uso pieza por pieza: elige la pieza disponible. Consumible: pon cantidad y de qué ubicación sale.
5. Pulsa "Solicitar vale".
Queda en estado Borrador ("por autorizar") y no se saca nada del almacén todavía.

## Cómo autorizar un prevale y entregar el material en Vales de almacén
1. Abre Inventario > Vales de almacén y pulsa el filtro "Por autorizar".
2. Abre el prevale.
3. Pulsa "Autorizar y entregar".
Al terminar, el vale pasa a Abierto y el material sale del almacén (la existencia baja y las piezas quedan prestadas a nombre del responsable). Se vuelve a comprobar la existencia en ese momento: si ya no alcanza, se rechaza. Quien pidió el prevale no puede autorizarlo; lo hace otra persona con permiso de autorizar (Almacenista).

## Cómo levantar un vale directo en Vales de almacén
Es para quien surte (Almacenista).
1. Abre Inventario > Vales de almacén y pulsa "Levantar vale".
2. Elige tipo de vale, el responsable (a quién se le entrega), proyecto opcional, fecha de regreso y motivo.
3. Agrega los renglones (producto, pieza o cantidad, ubicación de origen).
4. Pulsa "Abrir vale".
Al terminar, el vale queda Abierto y el material sale de inmediato del almacén. Un vale sin renglones no se puede abrir.

## Cómo devolver material y cerrar un vale en Vales de almacén
1. Busca el vale por folio o responsable y ábrelo.
2. En el renglón que volvió, pulsa "Marcar devuelto".
3. Repite por cada renglón.
Al terminar, el renglón queda devuelto, el material regresa a la ubicación de donde salió y la existencia se repone. Al devolver el último renglón el vale pasa solo a Cerrado, con su fecha de cierre. El estado del vale no se captura a mano: lo deciden sus renglones. Marcar devuelto requiere el permiso de vales (Almacenista), no el de prevale.

## Cómo ver vales vencidos y quién trae qué en Vales de almacén
Arriba de Vales de almacén aparece la sección "Ya debió volver y no ha vuelto" con los renglones cuya fecha de regreso ya pasó y siguen sin devolverse; si no hay ninguno, la sección no aparece. Para ver lo que trae cada persona, abre un vale y pulsa "Ver historial" junto al responsable: muestra todo lo que ha pedido, lo devuelto, lo que sigue fuera y lo vencido. Quien solo pide material ve únicamente lo suyo; quien surte ve todo.

## Cómo imprimir un vale o el historial de una persona
1. Abre el vale en Vales de almacén.
2. Pulsa "Imprimir vale": se abre el PDF en otra pestaña para firmarlo (un prevale sale marcado como borrador).
3. Para el historial de una persona, pulsa "Ver historial" y luego "Descargar PDF".
El PDF del vale se archiva en el módulo de Documentos; si el vale no cambió desde la última vez se entrega la misma versión.

## Cómo prestar, reparar, extraviar o dar de baja una pieza en Rastreo de piezas
1. En Localizar abre la pieza y pasa a Rastreo de piezas (o busca por etiqueta).
2. Elige la acción: Asignar a alguien de la empresa, Prestar (pide responsable y fecha de regreso), Recibir de vuelta, Mandar a reparación (motivo obligatorio), Regresó de reparación, Reportar extraviada (motivo obligatorio), Dar de baja (motivo obligatorio) o Trasladar de ubicación.
3. Confirma.
Al terminar, la pieza cambia de estado, queda en su historia y el movimiento se refleja en la existencia. Para dar de alta una pieza nueva se usa "Dar de alta pieza" con producto (solo los marcados como serializados), etiqueta única, número de serie y costo.

## Cómo dar de alta una ubicación o un almacén en Inventario
1. Para un almacén nuevo, primero crea o elige en Tipos de ubicación un tipo marcado como almacén.
2. En Inventario > Ubicaciones pulsa Nuevo, escribe la descripción, elige el tipo y la ubicación padre (nave > zona > rack > posición).
3. Guarda.
Una ubicación no puede ser su propio padre ni quedar debajo de una hija. Para eliminarla no debe tener existencia ni ubicaciones hijas.

## Cómo ajustar existencias o registrar entradas y mermas
El ajuste de existencias (sumar o restar sin documento) solo lo puede hacer quien tenga el permiso "Ajustar existencias" (Almacenista) y siempre exige un motivo escrito; lo mismo la merma, destrucción, pérdida, caducidad y traslado. La existencia nunca queda negativa: una salida que no alcanza se rechaza. No documentado: la pantalla desde la que se capturan entradas y ajustes a mano; en lo revisado solo se ven el historial de movimientos y las acciones de piezas.

## Estatus y qué significan: vale de almacén
Estado del vale (incidencia):
- Borrador: prevale pedido, no ha salido nada.
- Abierto: autorizado o abierto directo; al menos un renglón sin devolver.
- Cerrado: todos los renglones devueltos.
- Cancelado: no existe botón para cancelar un vale; si aparece, no se vuelve a abrir.
Transiciones: borrador > abierto (al autorizar) > cerrado (al devolver el último renglón). Los vales traídos del sistema anterior pueden mostrar "abierta" o "cerrada" en femenino, y el glosario menciona también "en espera" y "en tránsito"; no documentado: cuándo se usan estos últimos. "Vencido" no es un estatus: es un renglón abierto cuya fecha de regreso ya pasó.

## Estatus y qué significan: renglón del vale y pieza
Renglón: sale (salida, lo que se lleva), entra (entrada, lo escribe la devolución) o cambia de sitio (traslado). Está "fuera" mientras no tenga fecha de cierre y "devuelto" cuando la tiene.
Pieza (herramienta rastreada): disponible (lista, cuenta como existencia), en uso (asignada a alguien), prestada (con responsable y fecha de regreso), en reparación, extraviada y retirada (baja definitiva). Desde disponible o en uso se puede ir a prestada, reparación, extraviada o retirada; prestada a disponible, reparación o extraviada; extraviada a disponible o retirada; retirada ya no vuelve.
Producto (catálogo Estado de inventario): nuevo, usado, en reparación, dañado, extraviado y retirado.

## Reglas y permisos importantes: quién pide, quién autoriza y quién ve
- Supervisor: pide material con prevale (permiso de prevales) y solo ve los vales a su nombre; no puede surtirlo ni marcar devuelto.
- Almacenista: opera todo el almacén, levanta vales, autoriza prevales, confirma devoluciones y ajusta existencias; ve todos los vales.
- Administrator: puede dejar prevales pero, por separación de deberes, no emite ni autoriza vales; el material lo suelta Almacenista.
- Gerente y Jefe de taller: consultan Inventario.
- Quien pidió un prevale no puede autorizarlo.
Son valores por omisión: el Gestor de roles y permisos de cada instalación manda.

## Reglas y permisos importantes: lo que bloquea el sistema en Inventario
- Todo vale exige fecha de regreso (no pasada), motivo y al menos un renglón.
- Herramienta pieza por pieza: el renglón debe nombrar la pieza; consumible: cantidad y ubicación de origen, nunca pieza.
- Un renglón de vale siempre es salida.
- Un renglón ya devuelto no se devuelve otra vez.
- La existencia no puede quedar negativa.
- No se borra una ubicación con existencia o con hijas.
- El control por lote de un producto no se enciende editando el campo.
- Los productos y las búsquedas se limitan al proyecto o instalación del usuario.

## Campos importantes: producto
- Descripción y Código de producto: cómo se reconoce.
- Cantidad: suma de la existencia en todas las ubicaciones.
- Ubicación, Material (de él salen familia, marca y unidad), Color, Precio bruto, Nota.
- Estado del producto: nuevo, usado, en reparación, dañado, extraviado, retirado; en datos antiguos puede decir ENTRADA, SALIDA, RENTA, DAÑADO, REPARACIÓN, EXTRAVIADO o DESTRUCCIÓN.
- Modo de rastreo: fungible (por cantidad) o serializado (pieza por pieza).
- Para qué sirve: mercancía (Consumible, se compra para venderse) o uso interno (herramienta; no se vende).
- Control por lote: si el producto se lleva por lotes con fecha de caducidad.

## Campos importantes: vale, renglón y pieza
Vale (incidencia): folio (el número con que se conoce el vale), tipo de vale, responsable, proyecto (obra), motivo, fecha, estado y fecha de cierre.
Renglón: producto, cantidad, pieza, ubicación de origen y de destino, dirección (sale, entra, cambia de sitio), fecha de inicio, fecha límite de regreso (due_date) y fecha de cierre.
Pieza: etiqueta (única, la pegada a la herramienta), número de serie, ubicación, estado, responsable, fecha de regreso, fecha y costo de adquisición.
Ubicación: descripción, tipo y ubicación padre; la ubicación general guarda lo que no tiene sitio propio.

## Preguntas frecuentes de Inventario: vales
- ¿Por qué mi prevale no sacó material? Porque queda en Borrador hasta que alguien con permiso lo autorice.
- ¿Puedo autorizar mi propio prevale? No.
- ¿Cómo cierro un vale? Marcando devuelto cada renglón; el último lo cierra solo.
- ¿Puedo cambiar el estado de un vale a mano? No, se deriva de los renglones.
- ¿Cómo cancelo un vale? No documentado: no hay acción de cancelar.
- ¿Por qué no me deja guardar? Falta responsable, fecha de regreso, motivo, renglones, o el origen de un consumible.
- ¿Cómo busco un vale? Por folio o por nombre del responsable.

## Preguntas frecuentes de Inventario: productos y piezas
- ¿Qué significa "pieza por pieza"? Que cada herramienta tiene etiqueta, estado y responsable propios.
- ¿Una pieza prestada cuenta en la existencia? No, solo la disponible cuenta.
- ¿Por qué no veo un producto? Puede ser de otro proyecto o instalación, o tu rol no lo puede leer.
- ¿Dónde está la herramienta X? En Localizar, por nombre, código o etiqueta.
- ¿Cómo bajo una herramienta dañada? Mándala a reparación o dala de baja en Rastreo de piezas, con motivo.
- ¿Por qué no puedo borrar una ubicación? Tiene existencia o ubicaciones dentro.

## Preguntas de datos que se pueden hacer al asistente BI sobre Inventario
- ¿Cuántos productos hay?
- Top 10 productos por existencias.
- ¿Cuánto hay de cada producto por ubicación?
- Productos con cantidad cero.
- Piezas por estado (disponible, prestada, en reparación, extraviada).
- Vales vencidos.
- Herramientas del vale 140.
- ¿Qué trae cada persona sin devolver?
- Vales abiertos por responsable.
- Vales por estado.
- Productos por familia o por marca.
- Ubicaciones con más existencia.
