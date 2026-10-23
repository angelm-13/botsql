---
modulo: rh
entidades_clave: [payroll_period, payroll_detail, payroll_movement, payroll_concept]
---
# Recursos humanos

## Que es el modulo Recursos humanos y para que sirve
Recursos humanos reune dos cosas: la **nomina** (periodos de pago, catalogo de conceptos, detalle por empleado y movimientos de cada detalle) y **Kronos**, la consulta de asistencias y personas de un dispositivo de control de acceso Hikvision. Las personas empleadas no se dan de alta aqui: son usuarios con la casilla "Es empleado" marcada, que se capturan en Usuarios (modulo Seguridad). Este manual describe el flujo y los conceptos, no cifras.

## Pantallas y donde encontrarlas en Recursos humanos
Menu lateral, grupo Recursos humanos: **Periodos de nomina**, **Conceptos**, **Movimientos**, **Detalle** y **Asistencias** (Kronos). La pantalla **Conexion al dispositivo** vive en el engrane de configuracion. Las cuatro de nomina son listas con formulario de alta y edicion, paginacion y buscador. Asistencias tiene dos pestanas: Asistencias y Personas.

## Flujo de la nomina en Recursos humanos
El orden natural es: 1) dar de alta los **Conceptos** (percepciones, deducciones, aportaciones); 2) crear el **Periodo de nomina**; 3) crear un **Detalle** por cada empleado dentro del periodo, con sus totales; 4) agregar los **Movimientos** de cada detalle, uno por concepto con su importe. Los registros se enlazan entre si: el detalle apunta a un periodo y a un empleado; el movimiento apunta a un detalle y a un concepto. El sistema no suma los movimientos por ti: los totales del detalle se capturan tal cual.

## Como crear un periodo de nomina en Recursos humanos
1. Abre **Periodos de nomina** y despliega el formulario de alta.
2. Captura **Periodo inicio**, **Periodo fin** y **Pago fecha** (fecha de pago).
3. Elige el **Estado** en la lista (obligatorio).
4. Guarda.
La fecha de fin no puede ser anterior a la de inicio. Al guardar el periodo aparece en la lista y ya puede elegirse al crear detalles.

## Como dar de alta un concepto de nomina en Recursos humanos
1. Abre **Conceptos**.
2. Escribe la **Descripcion** (obligatoria) y, si quieres, un **Codigo**.
3. Elige el **Tipo**: earning (percepcion), deduction (deduccion) o employer_contribution (aportacion patronal).
4. Marca o desmarca **Es gravable** y **Es IMSS** segun corresponda.
5. Guarda.
El concepto queda disponible al registrar movimientos de nomina.

## Como capturar el detalle de nomina de un empleado
1. Abre **Detalle**.
2. Elige el **Periodo de nomina** y el **Usuario** (el empleado).
3. Captura **Bruto salario**, **Total percepciones**, **Total deducciones** y **Neto pago**. Ninguno puede ser negativo.
4. Guarda.
Queda un renglon por empleado y periodo. Para desglosar de donde salen los totales se usan los Movimientos. No documentado: validacion que impida dos detalles del mismo empleado en el mismo periodo.

## Como registrar movimientos de nomina de un detalle
1. Abre **Movimientos**.
2. Elige el **Detalle de nomina** al que pertenece y el **Concepto de nomina**.
3. Captura el **Importe**.
4. Guarda.
Un detalle puede tener varios movimientos, uno por cada percepcion, deduccion o aportacion. Para corregir, edita el movimiento; para quitarlo, eliminalo (el borrado retira el registro y queda anotado en la bitacora de eventos).

## Como consultar asistencias en Kronos (Asistencias)
1. Primero configura la conexion al dispositivo (ver seccion de Conexion).
2. Abre **Asistencias**, pestana Asistencias.
3. Elige **Desde**, **Hasta** y la **Zona horaria** (-06:00, -05:00, -04:00 o +00:00).
4. Pulsa **Generar reporte**.
Aparecen cuatro totales (personas, jornadas, marcaciones, hora de actualizacion), la tabla **Estadisticas** por persona y el **Detalle diario**. El buscador filtra por nombre o numero y el boton **CSV** descarga el detalle filtrado. Si no hay conexion configurada el sistema lo avisa.

## Que significan las estadisticas de asistencia de Kronos
Por cada persona y dia se toma la **primera marca** (entrada) y la **ultima marca** (salida) y se cuenta el numero de **marcas**. En Estadisticas: **Dias** con registro, **Marcas** totales, **Entrada promedio**, **Salida promedio** y **Horas estimadas**, que suman la diferencia entre la ultima y la primera marca de cada dia. Son estimaciones: no descuentan comidas ni identifican retardos. No documentado: vinculo automatico entre asistencias y nomina; las asistencias no se guardan en la base del sistema, se consultan al dispositivo cada vez.

## Como configurar la conexion al dispositivo Kronos
1. Abre el engrane de configuracion y entra a **Conexion al dispositivo**.
2. Captura la **URL del dispositivo**, el **Usuario** y la **Contrasena**.
3. Opcional: **SessionTag**, **Cookie** y la casilla **Permitir certificado autofirmado**.
4. Pulsa **Guardar conexion**.
Los datos se conservan solo durante la sesion del navegador: al cerrar la pestana o sesion hay que volver a capturarlos. Requiere el permiso especial "Conexion al dispositivo Kronos". Esta pantalla no prueba la conexion; el resultado se ve al consultar Asistencias.

## Como administrar las personas del dispositivo Kronos
1. En **Asistencias** abre la pestana **Personas** y pulsa **Consultar** para traer el directorio.
2. **Nueva persona**: captura Numero de empleado, Nombre, Tipo (Normal o Visitante), Genero y vigencia (Valido desde / hasta; por omision hasta 2037-12-31) y pulsa **Guardar persona**.
3. **Editar**: el numero de empleado no se puede cambiar.
4. **Eliminar**: pide confirmacion y retira a la persona del dispositivo.
Estos cambios se hacen en el dispositivo, no en la lista de usuarios del sistema.

## Estatus en Recursos humanos
La nomina no tiene un flujo de estatus propio (no hay "calculada", "pagada" ni "cerrada" con transiciones). El Periodo de nomina lleva un **Estado** tomado del catalogo general de estados de la instalacion (en una instalacion nueva existen valores como Activo e Inactivo, y se pueden agregar otros). No documentado: que estado significa periodo cerrado o pagado. Los conceptos si tienen tipo: earning (percepcion), deduction (deduccion) y employer_contribution (aportacion patronal). En Kronos, el estado de la conexion es Sin consultar, Consultando o Conectado.

## Reglas y permisos importantes de Recursos humanos
- Por defecto Administrator tiene control total y Gerente solo consulta; cada instalacion puede cambiarlo en el Gestor de roles y permisos.
- Consultar asistencias y personas de Kronos requiere lectura de periodos de nomina; crear o editar personas requiere actualizar; eliminarlas requiere eliminar.
- El Gestor de permisos puede ocultar campos concretos (por ejemplo los importes) a ciertos roles; esas columnas dejan de verse en pantalla y en el asistente BI.
- Eliminar un registro de nomina lo retira de la base; no hay papelera.
- Fin de periodo no puede ser anterior al inicio; los importes del detalle no pueden ser negativos.

## Campos importantes de Recursos humanos
- **Periodo inicio / fin / Pago fecha**: rango que cubre la nomina y dia de pago.
- **Estado** (periodo): estado del catalogo general.
- **Codigo y Descripcion** (concepto): nombre y clave del concepto.
- **Tipo** (concepto): percepcion, deduccion o aportacion patronal.
- **Es gravable / Es IMSS**: si el concepto causa impuesto o cotiza al IMSS.
- **Bruto salario, Total percepciones, Total deducciones, Neto pago** (detalle): totales del empleado en el periodo.
- **Importe** (movimiento): monto de un concepto dentro de un detalle.
- **Es empleado** (usuario): marca que convierte a un usuario en empleado.

## Preguntas frecuentes de Recursos humanos
- **Donde doy de alta a un empleado?** En Usuarios, marcando "Es empleado".
- **El Detalle calcula el neto solo?** No, se captura.
- **Por que Asistencias dice que configure la conexion?** Falta guardar la conexion al dispositivo en esta sesion.
- **Las marcaciones de Kronos se guardan?** No, se consultan al dispositivo cada vez; guarda el CSV si las necesitas.
- **Por que no veo los importes?** Tu rol puede tener ocultos esos campos.
- **Que hago si Kronos dice que no se pudo comunicar?** Revisa la URL, el usuario y que el equipo este encendido y en red.

## Preguntas de datos que se pueden hacer al asistente BI sobre Recursos humanos
Solo se responden si tu rol puede leer esas tablas y columnas.
- "periodos de nomina por estado"
- "cuantos empleados tiene un periodo de nomina" (conteo de detalles)
- "conceptos de nomina por tipo"
- "conceptos gravables" o "conceptos que cotizan al IMSS"
- "cuantos movimientos tiene cada periodo"
- "empleados activos" (usuarios marcados como empleado)
Tablas usadas: payroll_period, payroll_concept, payroll_detail y payroll_movement.
