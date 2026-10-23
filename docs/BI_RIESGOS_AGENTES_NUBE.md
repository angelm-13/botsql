# BI texto-a-SQL: agentes existentes y riesgos de operar en la nube

Fecha de consulta: **2026-10-15**. Convención: **[V]** verificado en repo/página oficial en esta consulta; **[T]** de terceros; **[NV]** no verificado; **[E]** estimación propia.

## 1. Catálogo de agentes y frameworks

| Proyecto | Qué hace | Licencia | Comparación con nuestro módulo | Enlace |
|---|---|---|---|---|
| **Vanna** | Chat con BD SQL: texto-a-SQL con LLM y recuperación agéntica | MIT [V]. **Repositorio archivado el 29-mar-2026 (solo lectura)** [V]: sin mantenimiento | Nuestro módulo es más estricto en seguridad (validador propio); Vanna entrena/recupera DDL y ejemplos. No adoptar como base: está archivado | https://github.com/vanna-ai/vanna |
| **WrenAI (Canner)** | Motor GenBI open source: capa semántica (modelo de negocio en YAML/Markdown) + texto-a-SQL, gráficas, 20+ fuentes, expuesto a agentes vía MCP | Apache 2.0 (el repo también incluye archivos AGPL-3.0 y CC-BY-4.0 para componentes concretos; revisar) [V] | Su ventaja es la capa semántica (definiciones de negocio), que a nosotros nos falta para 150 tablas en inglés con preguntas en español | https://github.com/Canner/WrenAI |
| **DataHerald** | Motor NL-a-SQL para preguntas sobre datos relacionales; servicios engine, enterprise, admin-console, slackbot | Apache 2.0 [V]. Estado de mantenimiento reciente [NV] (sin fecha de último commit visible) | Más pesado (varios servicios); mismo enfoque, con consola de administración | https://github.com/Dataherald/dataherald |
| **Chat2DB** | Cliente de BD con asistente de IA | Apache 2.0 **más** una "Chat2DB License" adicional [T]; forks antiguos decían solo no comercial. Revisar antes de uso comercial [NV] | Es una herramienta de escritorio/DBA, no un módulo embebible multi-cliente | https://github.com/chat2db/Chat2DB |
| **LangChain / LlamaIndex SQL agents** | Librerías para armar agentes que escriben y ejecutan SQL con herramientas | Código abierto (licencias no verificadas aquí) [NV] | Son piezas, no producto. Ejecutan SQL generado: sin el rol de solo lectura y un validador como el nuestro son riesgosos | (sin enlace verificado) |
| **Defog SQLCoder** | Modelos abiertos afinados para SQL (7B, 70B) | Pesos CC BY-SA 4.0, código Apache 2.0 [V vía búsqueda] | Es un modelo, no un agente; podría sustituir al LLM en `ProveedorLLM` | https://github.com/defog-ai/sqlcoder |
| **Metabase (Metabot)** | BI con asistente: genera SQL (no lo ejecuta) y preguntas en lenguaje natural; IA propia solo en Metabase Cloud, o con API key propia (hoy solo modelos Anthropic) en autoalojado | Metabase núcleo AGPL, funciones de IA con condiciones propias [NV licencia exacta]; datos de doc [V] | Alternativa de BI completa; sin embargo es otro producto con su propia gestión de usuarios y permisos | https://www.metabase.com/docs/latest/ai/overview |
| **Apache Superset** | BI/SQL Lab. No se encontró función nativa de texto-a-SQL en documentación oficial [NV] | Apache 2.0 [E] | Haría falta integrar un LLM propio | https://superset.apache.org |
| **Databricks Genie** | Interfaz en lenguaje natural sobre Unity Catalog; el propio doc lo describe no determinista y recomienda pocas tablas por espacio | Servicio comercial | Gobierno de datos más maduro, pero exige estar en Databricks | https://docs.databricks.com/gcp/genie |
| **Snowflake Cortex Analyst** | API administrada de NL-a-SQL basada en un modelo semántico YAML; el SQL corre en tu warehouse; datos no salen del límite de gobernanza de Snowflake | Servicio comercial | Mismo concepto de capa semántica; solo para datos en Snowflake | https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst |
| **Google (Gemini en BigQuery, data agents)** | Agentes de datos con metadatos, glosario y consultas verificadas; algunas funciones en preview | Servicio comercial | Solo BigQuery | https://docs.cloud.google.com/bigquery/docs/gemini-overview |
| **AWS (Bedrock)** | No hay producto de texto-a-SQL dedicado oficial encontrado; AWS publica una arquitectura de referencia sobre Bedrock | n/a | Se construye igual que nuestro módulo, con un LLM administrado | https://aws.amazon.com/blogs/machine-learning/text-to-sql-solution-powered-by-amazon-bedrock |
| **Microsoft (Fabric/Copilot, Azure)** | **No se verificó** | [NV] | [NV] | [NV] |

Lectura: el diferenciador que ofrecen casi todos los comerciales y WrenAI/Snowflake/Google es una **capa semántica** (glosario, métricas definidas, ejemplos verificados). Es la mejora de calidad con mayor retorno para nuestro módulo, más que cambiar de modelo.

## 2. Qué cubre hoy nuestro módulo (verificado en código)

Revisado: `backend/app/bi/security.py`, `executor.py`, `api.py`, `config.py`, `service.py` y el registro en `backend/app/__init__.py`.

Controles que **sí existen** [V]:
1. Validador (`security.validar_sql`): un solo enunciado; debe empezar con SELECT/WITH; lista negra de palabras (insert, update, delete, drop, copy, into, set, sleep, etc.), funciones peligrosas por motor (pg_sleep, pg_read_file, dblink, lo_export...), bloqueo de catálogos del sistema (`pg_`, `information_schema`), bloqueo de columnas sensibles (password, token, curp, nss...), **solo relaciones presentes en el esquema expuesto**, y LIMIT forzado (tope `limite_filas=1000`).
2. Transacción de solo lectura (`SET TRANSACTION READ ONLY`) y `statement_timeout` de 15 s (`timeout_sql_ms`) en `executor.ejecutar`.
3. Longitud de pregunta máxima 1000 caracteres; errores internos no devuelven traza.
4. Filtrado de tablas por departamento (`bi_department_permission`) y exclusión por omisión de tablas de sesión/token/mfa/log.
5. El prompt/DDL no incluye valores de datos por omisión (`con_muestras=False`).
6. `/health` advierte si la conexión usa un superusuario.

Brechas **reales** encontradas [V]:
- **El blueprint de BI se registra sin autenticación ni contexto de usuario**: en `app/__init__.py` se llama `crear_blueprint(engine=db.engine, ajustes=..., proveedor=ProveedorOllama())` sin `contexto`, `gancho_sql` ni `relaciones`. En `api.py` el `contexto` por omisión devuelve `{}`, por lo que `/query`, `/schema` y `/health` no exigen token y `departamento_del_usuario({})` devuelve `None` (sin filtro por departamento). Hay que confirmar si un middleware global del app protege la ruta; en el código revisado no se vio.
- **Usa `db.engine`, la conexión de la propia aplicación**, no un rol de solo `SELECT`. La barrera 2 que el propio `security.py` declara como la más importante no se aplica. La transacción read-only mitiga pero no sustituye el rol.
- **Sin aislamiento entre clientes/roles en la fila**: `gancho_sql` (que fijaría el alcance por usuario/inquilino) no se usa. Cada despliegue de cliente tiene su BD (adser-prod, torredigital-prod), lo que limita la fuga entre clientes, pero dentro de un cliente cualquier usuario puede leer cualquier tabla expuesta (la Fase 2 de alcance por permisos del ERP tampoco está conectada al BI).
- **Sin auditoría**: `service.py` no registra pregunta, SQL generado, usuario ni filas devueltas (no se encontró logging de ello).
- **Sin límite de tasa ni cuota de gasto** por usuario.
- `api_queue.py` define un `require_auth` que solo comprueba que exista la cabecera `Authorization` (no valida el JWT), y **no está registrado** en la app [V], así que hoy no es superficie expuesta; si se activa, debe cambiarse por el decorador real del ERP.
- Validación basada en regex/lista negra sobre texto: cubre bien lo común, pero no es un parser; consultas costosas pero legales (productos cartesianos, `generate_series` enorme, CTE recursivas) solo las frena el timeout de 15 s.
- Caché de preguntas (`CacheDePreguntas`) guarda el SQL por pregunta + huella del esquema, no por usuario: no filtra datos (el SQL se ejecuta fresco), pero con filtrado por departamento hay que asegurar que la huella cambie por departamento (hay un comentario en `schema_extractor.py` de no reusar caché con filtro).

### 2.1 Actualización 2026-10-15: qué se cerró después de esta revisión

Cambios hechos en el código (probados en el entorno `bi2`):

| Brecha de arriba | Estado ahora |
|---|---|
| Blueprint sin autenticación | **Cerrado.** `app/__init__.py` lo registra con `requiere_sesion=True` y valida el mismo JWT que `token_required` (rechaza también el token público del catálogo). `/health` queda abierto. Sin token: 401. (Antes ni siquiera se registraba: `from bi.api` fallaba con `No module named 'bi'`.) |
| Sin aislamiento por rol | **Cerrado a nivel tabla y columna.** `app/bi/acceso.py` toma las tablas de `entity_permission.scope_read` y las columnas de `field`/`nm_field_permission` del rol del usuario; el administrador ve todo. El esquema que ve el modelo, el validador de SQL y el resultado se filtran por rol, y la caché de esquema es por perfil. Falta el **alcance por fila** (Propios / Mis grupos), que depende de la Fase 2 del ERP. |
| Sin auditoría | **Cerrado en log.** Cada pregunta escribe una línea JSON en el logger `bi.audit` (usuario, rol, pregunta, SQL, filas, ms). Falta persistirla en tabla y retenerla. |
| El SQL llegaba al navegador | **Cerrado.** La API ya no devuelve `sql`, ni errores del motor, ni la respuesta cruda del modelo; solo un administrador con `?debug_sql=1` los recibe. Ojo: el punto 7 del plan P1 ("mostrar SQL en la UI") queda **reemplazado** por mostrar la explicación y las tablas usadas, para no exponer el esquema. |
| `/schema` abierto | **Cerrado.** Solo administrador. |

Siguen abiertos: rol PostgreSQL `bi_ro` de solo `SELECT` (usa la conexión de la app salvo que se defina `BI_DATABASE_URL`), rate limit/concurrencia, topes de gasto, alcance por fila, persistencia de la auditoría y las pruebas de ataques.

## 3. Análisis de riesgos (nube, este sistema)

Probabilidad e impacto: B (baja), M (media), A (alta) [E, juicio propio sobre este sistema].

| # | Riesgo | Prob. | Impacto | Mitigación concreta | ¿Lo cubre hoy? |
|---|---|---|---|---|---|
| 1 | **Inyección de prompt vía datos** (un campo de texto como nombre de cliente o descripción de producto con "ignora instrucciones y consulta X" que llega al modelo si se re-envían filas o muestras) | M (solo si hay muestras o resumen de resultados) | A | No enviar valores al modelo (mantener `con_muestras=False`); si se resumen resultados, delimitar y tratar como datos; la defensa real es que el SQL siempre pasa por validador + rol de solo lectura + alcance por usuario | **Parcial**: el DDL no lleva datos y el SQL se valida; no hay prueba específica de inyección |
| 2 | **Fuga entre clientes/roles** (un usuario ve nómina o facturas de otro) | A hoy (no hay auth ni alcance por usuario en el endpoint) | A | Exigir JWT (`token_required`) en todas las rutas BI; pasar `contexto`, `relaciones` y `gancho_sql` por usuario; vistas filtradas por rol/inquilino; BD separada por cliente (ya existe) | **No** (solo filtro por departamento, inactivo sin contexto) |
| 3 | **Exposición de datos sensibles a APIs externas** (DDL y resultados enviados a Anthropic/OpenAI/Google) | M si se migra a API | A (nómina, facturación) | Enviar solo DDL; excluir tablas de nómina del esquema expuesto para API; contrato/DPA y región; opción de modelo local por cliente; revisar retención de datos del proveedor | **Parcial**: columnas sensibles ocultas, tablas excluidas, sin muestras. Hoy el modelo es local, así que el riesgo se materializa solo al migrar a API |
| 4 | **SQL destructivo** | B | A | Rol PostgreSQL con solo `GRANT SELECT` en réplica de lectura | **Sí en gran parte**: validador + read-only + timeout. **Falta** el rol de solo lectura |
| 5 | **SQL costoso / DoS** (joins enormes, 150 tablas) | M | M-A | `statement_timeout`, límite de filas, límite de concurrencia/tasa por usuario, réplica de lectura, `work_mem` bajo para el rol | **Parcial**: timeout 15 s y 1000 filas; **sin** rate limit ni límite de concurrencia (y el LLM local en CPU tarda 60-100 s por consulta, lo que ya es un DoS natural) |
| 6 | **Alucinación de resultados** (SQL que ejecuta bien pero responde otra cosa; BIRD top ~80-82 % [T]) | A | M-A (decisiones con datos erróneos) | Mostrar siempre el SQL y las tablas usadas; capa semántica con métricas definidas; ejemplos verificados; marcar "generado por IA"; evaluación periódica con un set propio de preguntas en español | **Parcial**: el validador impide tablas inexistentes, no consultas semánticamente equivocadas |
| 7 | **Falta de auditoría** (quién preguntó qué y qué datos salieron) | A (hoy no se registra) | A (cumplimiento, forense) | Tabla de bitácora: usuario, cliente, pregunta, SQL, tablas, nº de filas, modelo, tokens, costo, duración; sin guardar valores sensibles | **No** |
| 8 | **Dependencia de proveedor** (cambio de precio, deprecación de modelo, salida de mercado) | M | M | Interfaz `ProveedorLLM` ya existe: mantener 2 proveedores, modelo configurable por entorno, pruebas de regresión de prompts | **Parcial**: abstracción presente, un solo proveedor cableado |
| 9 | **Costos descontrolados** (bucle, abuso, modelo caro) | M con API, B con local | M | Tope mensual por cliente y por usuario, alertas, caché (ya hay de preguntas), prompt caching, `schema_linking` para recortar tokens, límite de salida | **Parcial**: caché y `schema_linking`; sin topes de gasto ni conteo de tokens |
| 10 | **Disponibilidad del modelo** (Ollama caído, GPU saturada, API con caída o cuota) | M | M | Healthcheck (ya existe `/health`), timeouts, cola asíncrona, degradación elegante, proveedor de respaldo | **Parcial**: `/health` y timeouts; sin respaldo |
| 11 | **Cumplimiento LFPDPPP (México)** | M | A | Aviso de privacidad y contrato de encargado con cada proveedor; minimizar datos enviados; bitácora de accesos; evaluar transferencia internacional si el proveedor está fuera de México; revisión legal | **No** evaluado en código |

Sobre LFPDPPP: la ley vigente es la **nueva LFPDPPP publicada en el DOF el 20-mar-2025 (en vigor el 21-mar-2025)**, que abroga la de 2010; las funciones del INAI pasaron a la Secretaría Anticorrupción y Buen Gobierno [T: Hogan Lovells, EY, KPMG; texto oficial en https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf, no leído artículo por artículo]. **No se pudo verificar** el tratamiento específico de cómputo en la nube/remisiones a encargados en el texto vigente ni si el Reglamento de 2011 sigue aplicando: consultar a un especialista antes de enviar datos personales (nómina, RFC, datos de facturación de personas físicas) a un proveedor de IA externo.

## 4. Plan de mitigación priorizado

**P0 (antes de exponer el módulo a cualquier cliente real; días)**
1. Poner autenticación: decorador `token_required` en todas las rutas BI y pasar `contexto` con el usuario/rol/departamento. Verificar que `/api/v1/bi/*` no sea accesible sin token en cada ambiente.
2. Crear un rol PostgreSQL `bi_ro` con `GRANT SELECT` solo sobre las tablas expuestas y apuntar `BI_DATABASE_URL` a él (idealmente una réplica de lectura). Cerrar la advertencia de `/health`.
3. Bitácora de auditoría de cada consulta (usuario, pregunta, SQL, tablas, filas, duración, modelo).
4. Rate limit por usuario y límite de concurrencia (esto también protege al LLM local).

**P1 (antes de producción con varios clientes; 1-3 semanas)**
5. Conectar `relaciones`/`gancho_sql` al sistema de permisos del ERP (alcance por rol; coordinar con la Fase 2 de alcance por acción). Excluir tablas de nómina/datos personales del esquema BI por omisión y habilitarlas por cliente.
6. Conteo de tokens y tope de gasto mensual por cliente; alertas.
7. Mostrar SQL y tablas usadas en la UI y rotular resultados como generados por IA.
8. Pruebas automáticas: set de ~50-100 preguntas en español con SQL esperado (regresión de calidad) y set de ataques (inyección de prompt, SQL malicioso, exfiltración) contra el validador.

**P2 (cuando se decida usar API externa o crecer)**
9. Segundo proveedor LLM (API) detrás de `ProveedorLLM` con interruptor por cliente; modelo local obligatorio para clientes sensibles. Ver `docs/BI_COSTO_BENEFICIO_MODELOS.md`.
10. Revisión legal LFPDPPP, DPA con el proveedor, definir región y retención.
11. Capa semántica (glosario en español, métricas, ejemplos verificados), que mejora la calidad más que cambiar de modelo.
12. Endurecer el validador con un parser SQL real (p. ej. análisis del árbol) y estimación de costo con `EXPLAIN` para rechazar planes caros antes de ejecutar.

## 5. Qué no se pudo verificar

- Licencias de LangChain/LlamaIndex, Superset y la licencia exacta de funciones de IA de Metabase; estado de mantenimiento reciente de DataHerald y la Chat2DB License; agentes de Microsoft.
- Si existe un middleware global de autenticación que proteja `/api/v1/bi/*` fuera de los archivos revisados (el registro en `app/__init__.py` no pasa autenticación).
- Texto de la LFPDPPP sobre nube y transferencias; vigencia del Reglamento de 2011.
- Probabilidades e impactos son juicio propio, no datos medidos.
