# Reporte de pruebas de calidad — Módulo BI

Entregable 6 (parte de pruebas). Fecha de corte de las mediciones: 29/10/2026.
Entorno: equipo de desarrollo sin GPU, Ollama local, modelo `qwen2.5-coder:3b`, PostgreSQL 16 con datos de
prueba (169 vales, 36 proyectos, 5 facturas, ~2,200 productos). Una sola corrida por conjunto.

## 1. Asertividad (¿contesta lo correcto?)

**Método.** Conjunto de **validación** de 34 preguntas en español
(`database/datasets/bi_preguntas_validacion.json`) escritas *antes* de medir y no usadas para ajustar
recetas, ejemplos ni prompts. Cada pregunta tiene una consulta de oro escrita a mano y verificada en la
base. `scripts/bi_evaluar_oro.py` compara el **resultado** (celdas) del asistente contra el de la consulta
de oro, no el texto del SQL. Criterio estricto: el resultado debe ser idéntico (mismas columnas y filas).

| Vía | Aciertos |
|---|---|
| Receta (SQL fijo, sin modelo) | 3 / 3 |
| Modelo (Qwen2.5-Coder 3B) | 19 / 31 (61 %) |
| **Total** | **22 / 34 (64 %)** |

**Revisión manual de los 12 fallos** (el comparador estricto penaliza respuestas válidas con otra forma):

| Fallo | Pregunta | Diagnóstico |
|---|---|---|
| v17, v27 | proyecto de mayor costo; factura de mayor importe | **Respuesta correcta con columnas de más** (título/folio además del valor). Penalizado por forma |
| v19, v28, v33 | tareas por proyecto; facturado por mes; documentos por estatus | **Datos equivalentes** con otra etiqueta o columnas en otro orden. Penalizado por forma |
| v34 | materiales por marca | **Error real**: el modelo agregó `LIMIT 10` sin pedirlo y truncó el resultado |
| v31 | usuarios por rol | **Error real**: agrupó por `user_type` en vez de por el rol del ERP |
| v29 | cuántos empleados | **Error real**: contó todos los usuarios; omitió `is_employee = true` |
| v01, v02 | producto con más existencias; productos en cero | **Error real**: usó `inventory_stock` en vez de `product.cantidad` |
| v12 | herramientas pendientes de devolver | **Error real**: consultó `product` en vez de `nm_incident_product` |
| v13 | vales por estatus | **Error real**: el modelo no devolvió el JSON del contrato (`directiva_invalida`) |

Lectura honesta: 5 de los 12 fallos son de forma (la información sí es correcta) y 7 son errores reales.
Con criterio estricto la asertividad es **64 %**; con la revisión manual, **27 / 34 (79 %)** contestaron
con información correcta. Este segundo número es un juicio manual, no automático, y no debe presentarse
como la métrica oficial.

**Limitaciones de la medición:** n = 34 es pequeño (un margen de ±15 puntos aproximadamente); el conjunto
es de preguntas de conteo, agrupación y máximos sobre un solo esquema; una corrida; datos de prueba.

### 1.1 Segundo conjunto y ciclo de retroalimentación

Los fallos del conjunto 1 se corrigieron (ver sección 4). Como esas correcciones nacieron de ese
conjunto, **ya no sirve para medir**; las correcciones se midieron con un **segundo conjunto de 25
preguntas nuevas** (`database/datasets/bi_preguntas_validacion_2.json`), escritas antes de corregir.

| Conjunto | Aciertos (criterio estricto) | Modelo | Receta |
|---|---|---|---|
| 1: 34 preguntas, antes de corregir | 22 / 34 (64 %) | 19 / 31 | 3 / 3 |
| **2: 25 preguntas nuevas, después de corregir** | **16 / 25 (64 %)** | 15 / 23 | 1 / 2 |

**Conclusión honesta:** las correcciones **no movieron el porcentaje** (64 % en ambos). Eliminaron una
clase de error (agrupaciones truncadas por un `LIMIT` no pedido: ninguna en el conjunto 2), pero los
errores que quedan son de comprensión del esquema por parte del modelo de 3B (elegir la columna o la tabla
equivocada, p. ej. `user_type` en lugar del rol, o `brand` en lugar de las marcas con productos), que no se
resuelven con reglas en el prompt porque el modelo pequeño ignora parte del glosario. Con n = 25 el margen
es de ±19 puntos aproximadamente, así que la diferencia entre ambos conjuntos no es significativa.

Fallos del conjunto 2 (9): 2 por JSON inválido (corregido, abajo), 1 por un error propio de una receta
(corregido), 1 de forma (cliente con más proyectos sin `LIMIT 1`) y 5 errores reales del modelo (columna
o tabla equivocada). Tras las correcciones se volvieron a ejecutar solo esas preguntas: `w06` y `w09`
aciertan y `w07` ya devuelve JSON válido (falla por forma). Esa re-ejecución es una comprobación de la
corrección y **no** una nueva medición de asertividad.

## 2. Rendimiento

| Vía | Tiempo |
|---|---|
| Receta o caché | < 1 s (0–8 s medidos incluyendo validación y SQL) |
| Modelo 3B en CPU (31 preguntas) | media **110 s**; rango ~60–310 s |

Una pregunta nueva sin receta es lenta en este hardware (limitación declarada en el anteproyecto). La
inferencia corre en un servicio aparte y no degradó las demás peticiones del ERP durante las pruebas
(RNF-05).

## 3. Seguridad y control de acceso

**Pruebas automáticas** (`backend/tests/test_bi/`): **43 pasan**. Cubren: rechazo de DML/DDL y catálogos del
sistema, columnas ocultas, alcance Propios/Mis grupos (`acotar_sql`), falla cerrada (tabla limitada sin
columna dueño, nombre con esquema, `WITH RECURSIVE`, CTE homónimo, usuario sin id), auditor LLM que no
bloquea, y modelo caído (503 + recetas operando).

**Matriz de acceso por rol contra la base real** (API real, token por rol; 6 preguntas por rol). Resultados
verificados contra conteos directos en la base:

| Pregunta | Administrator | Jefe de taller | Supervisor | Gerente | Almacenista | Compras |
|---|---|---|---|---|---|---|
| Proyectos (36 en total) | 36 | propios | 14 (propios) | 36 | negado | negado |
| Vales (169 en total) | 169 | propios | 11 (propios) | 169 | 169 (solo lectura) | negado |
| Facturas | sí | negado | negado | sí | negado | negado |
| Tabla de usuarios | sí | negado | negado | negado | negado | negado |

Los conteos de Supervisor (14 proyectos, 11 vales) y Jefe de taller (0 proyectos propios) coinciden con la
cuenta directa `created_by = usuario OR leader = usuario`. Las consultas fuera de rol se rechazan con
«La consulta no está permitida para tu rol» sin revelar nombres de tablas.

**Rol de base de datos `bi_lector`:** `DELETE` y `CREATE TABLE` fallan con *read-only transaction*; no lee
la bitácora (`database/bi_lector.sql`).

**No verificado:** intentos de evasión por lenguaje natural ("muéstrame lo de todos") ejecutados con el
modelo de punta a punta; están cubiertos a nivel del filtro (pruebas unitarias) pero no medidos con el modelo.

## 4. Hallazgos y retroalimentación a implementación

| Hallazgo | Fase a la que regresa | Corrección (estado) |
|---|---|---|
| El modelo agregaba `LIMIT` sin que se pidiera y truncaba agrupaciones. Causa: una regla del prompt que pedía acotar filas y ejemplos de agrupaciones terminados en `LIMIT 10/20/24` | Implementación (prompt) | Hecho: el prompt indica que el sistema ya acota a 1,000 filas y que `LIMIT` solo va con «top N»; los ejemplos aprendidos pierden el `LIMIT` si la pregunta no es «top N». Efecto: sin truncados en el conjunto 2 |
| El modelo confunde el rol (`permission`) con `user_type` y las existencias con `inventory_stock` | Diseño (diccionario semántico) | Glosario y receta de «usuarios por rol» agregados; **sin efecto medible**: el modelo de 3B sigue eligiendo mal en variantes no cubiertas |
| JSON inválido: a una pregunta simple el modelo responde con un tablero y la salida se corta al llegar a 500 tokens (`no_es_json`) | Implementación | Hecho: un reintento con instrucción de una sola consulta cuando la pregunta no pide tablero (3 pruebas). Re-ejecución de las 3 preguntas afectadas: 2 de 3 aciertan, 1 devuelve JSON válido |
| Una receta propia («vales de un tipo») capturaba «vales hay de cada tipo» como si «cada tipo» fuera el nombre de un tipo | Implementación | Hecho: la receta excluye «cada», «por», «todos»; prueba de regresión agregada. Hallazgo posible solo por haber medido con preguntas nuevas |
| Ejemplos verificados generados contra una tabla antigua del esquema | Diseño | Pendiente: regenerar con `scripts/bi_generar_ejemplos.py` |

Nota metodológica: las correcciones derivadas del conjunto 1 se midieron en el conjunto 2; las derivadas
del conjunto 2 (reintento de JSON, receta) solo se comprobaron puntualmente. Una asertividad final citable
requeriría un tercer conjunto.

## 5. Opciones para mejorar la asertividad (fuera del alcance medido)

| Opción | Efecto esperado | Costo |
|---|---|---|
| Ampliar recetas con preguntas frecuentes reales de los usuarios | Alto en esas preguntas (instantáneas y exactas) | Trabajo continuo; no generaliza |
| Modelo mayor (7B) | Mejor comprensión del esquema | Más lento en CPU; necesita más memoria |
| Modelo en la nube solo para generar el SQL | Mejor precisión y 1–2 s | Costo por consulta; el esquema sale del servidor (ver `docs/BI_RIESGOS_AGENTES_NUBE.md`) |
