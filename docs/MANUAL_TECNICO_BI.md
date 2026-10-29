# Manual técnico del módulo BI (Análisis inteligente de datos)

Entregable 5 del anteproyecto. Describe cómo instalar, configurar, mantener y ampliar el módulo.
Código: `backend/app/bi/` (backend), `frontend/src/pages/BiPage.jsx` (interfaz).

## 1. Qué es

Un asistente que traduce preguntas en español a SQL de solo lectura sobre la base PostgreSQL del ERP
TYAKXA y devuelve indicadores, tablas y gráficas. El modelo de lenguaje corre **localmente** en Ollama,
separado del servidor del ERP. Lo que cada usuario puede ver sale del **Gestor de roles y permisos**
del ERP (tablas, columnas y alcance de filas); el modelo no decide permisos.

## 2. Requisitos

| Componente | Versión / nota |
|---|---|
| PostgreSQL | 16 (la base del ERP) |
| Python / Flask | 3.12 / 3.0 (backend del ERP; el BI es un blueprint más) |
| Ollama | servicio aparte; modelo `qwen2.5-coder:3b` (recomendado en CPU) o `:7b` (el predeterminado del código) |
| Docker y Docker Compose | para levantar el entorno |
| Hardware | sin GPU: una pregunta nueva tarda ~1–3 min; con receta o caché, < 1 s |

## 3. Instalación

1. Levantar el ERP: `docker compose up -d db rabbitmq backend frontend`.
2. Instalar el modelo en el equipo que corre Ollama: `ollama pull qwen2.5-coder:3b`.
3. Cargar datos de prueba (solo en bases de desarrollo, nunca de un cliente real):
   `docker compose exec backend python scripts/seed_datos_prueba.py --yes`.
4. (Producción) crear el rol de solo lectura, ver sección 5.
5. Abrir la página **Análisis BI** del menú de analítica con un usuario del ERP.

## 4. Configuración (variables de entorno)

| Variable | Para qué | Por omisión |
|---|---|---|
| `BI_OLLAMA_URL` | dirección del servicio Ollama | `http://localhost:11434` |
| `BI_MODEL` | modelo que genera el SQL (en equipos sin GPU se usa el `3b`) | `qwen2.5-coder:7b` |
| `BI_LLM_TIMEOUT` | segundos máximos de espera al modelo | 600 |
| `BI_DATABASE_URL` | conexión que usa el BI (usar el rol `bi_lector`) | `DATABASE_URL` |
| `BI_ROW_LIMIT` | tope de filas por consulta | 1000 |
| `BI_SQL_TIMEOUT_MS` | tiempo máximo de la consulta | 15000 |
| `BI_MAX_WIDGETS` | componentes por tablero | 8 |
| `BI_SCHEMA_TTL` / `BI_QUESTION_CACHE_TTL` | vigencia de la caché de esquema / de preguntas | 300 s / 3600 s |
| `BI_SAMPLE_VALUES` | `1` envía al modelo valores de columnas de **estatus/tipo** y de catálogos chicos (mejora la precisión). **Por omisión `0`: al modelo solo se le envían nombres de tablas y columnas** (RNF-10). | `0` |
| `BI_AUDITOR_LLM` | `1` activa un auditor LLM que solo **registra** un veredicto (no bloquea) | `0` |
| `BI_KB_ADMIN_DIRS` | carpetas técnicas visibles solo al administrador | — |
| `JWT_SECRET` | la misma del ERP; el BI valida su token | — |

## 5. Seguridad: las cuatro barreras

1. **Sesión y rol.** Sin token válido del ERP la API rechaza la petición. El rol sale de `id_permission`.
2. **Acceso por rol** (`acceso.py`): tablas con lectura (`entity_permission.scope_read ≠ 0`), columnas
   negadas (`nm_field_permission`) y las tablas de seguridad solo para el administrador.
3. **Validador** (`security.py`): un solo `SELECT`; sin DML/DDL, catálogos del sistema ni columnas ocultas;
   solo relaciones permitidas; tope de filas.
4. **Alcance de filas** (`acotar_sql`): si el rol tiene **Propios** (1) o **Mis grupos** (2) en una tabla,
   el SQL se reescribe con un CTE que filtra por `created_by` (y por `leader` en `proyect`); *Mis grupos*
   incluye a quienes comparten equipo en `nm_team_user`. Falla cerrada: tabla limitada sin columna dueño,
   nombre con esquema (`public.x`), `WITH RECURSIVE`, CTE homónimo o usuario sin id → se rechaza.
5. **Ejecución de solo lectura:** transacción de solo lectura con reloj; las filas se cortan al leer.
6. **Rol de base de datos `bi_lector`** (opcional, recomendado): solo `SELECT`. Crear con
   `psql -v pwd="'<contraseña>'" -f database/bi_lector.sql` y apuntar `BI_DATABASE_URL` a ese usuario.
   Verificado: `DELETE` y `CREATE TABLE` fallan con *read-only transaction*; no lee `bi_query_log`.

El SQL generado **no** se envía al navegador; solo un administrador puede pedirlo con `?debug_sql=1`.

## 6. Cómo decide cada rol qué ve

En **Gestor de roles y permisos** cada entidad tiene un alcance por acción (Sin acceso 0, Propios 1,
Mis grupos 2, Todos 4). El BI usa el de **Lectura**. Los equipos se administran en `/team`.
Los roles de negocio del ERP y su alcance en el BI:

| Rol | Alcance |
|---|---|
| Administrator | todo |
| Gerente | todos los datos de sus módulos |
| Supervisor | propios: vales, proyectos, tareas |
| Jefe de taller | propios: proyectos y vales |
| Almacenista | inventario y almacén; todos los vales (solo lectura) |
| Compras | solo lo relacionado con compras |

Nota: el trigger `trg_gestor_manda` impide que una migración pise lo que el gestor ya ajustó; en un
ambiente existente el alcance se ajusta desde el gestor.

## 7. Bitácora (RF-17)

Cada consulta se guarda en `bi_query_log` (usuario, rol, pregunta, SQL ejecutado, filas, ms, caché) y en
el logger `bi.audit`. Consulta de ejemplo:
`SELECT creation_date, id_user, rol, pregunta, ok, ms_total FROM bi_query_log ORDER BY 1 DESC LIMIT 50;`

## 8. Cómo ampliar el diccionario semántico (RNF-11, sin tocar la lógica)

| Qué | Dónde | Cómo |
|---|---|---|
| Glosario y ayuda | `backend/app/bi/conocimiento/*.md` | editar texto |
| Manual por módulo | `backend/app/bi/conocimiento/modulos/*.md` | cabecera `entidades_clave: [tablas]` limita quién lo ve |
| Preguntas frecuentes con SQL fijo | `backend/app/bi/recetas.py` | patrón de la pregunta + función que arma el SQL; **probar el SQL en la base** y agregar el caso a `tests/test_bi/` |
| Ejemplos verificados | `backend/app/bi/ejemplos/verificados.jsonl` | regenerar con `scripts/bi_generar_ejemplos.py` tras cambios de esquema |
| Significado de columnas/estatus | comentarios de columna en PostgreSQL | el extractor los incluye en el DDL |

## 9. Mantenimiento

- Pruebas: `docker compose exec backend bash -c "export TESTING=1 JWT_SECRET=test-secret JWT_SS=test-secret MFA_ISSUER=T; pytest -q tests/test_bi"`.
- Medir precisión: `python scripts/bi_evaluar_oro.py --dataset /database/datasets/bi_preguntas_validacion.json`
  (compara el **resultado** de cada pregunta contra una consulta de oro). Tiempos: `scripts/bi_benchmark.py`.
- Un cambio de esquema invalida solo la caché (la huella del esquema cambia); no hay que reiniciar.
- Si el modelo no responde, la API contesta **503** con un mensaje claro y el ERP sigue operando; las
  preguntas con receta siguen funcionando (`tests/test_bi/test_bi_modelo_caido.py`).
- La caché de preguntas solo guarda consultas que **se ejecutaron bien**.

## 10. Límites conocidos

- Sin GPU, las preguntas sin receta ni caché tardan minutos.
- El alcance Propios/Mis grupos lo aplica el BI; el resto de las pantallas del ERP sigue con el permiso
  de sí/no (Fase 2 del ERP).
- Una tabla limitada a Propios sin columna `created_by` se **niega** (por diseño).
- El texto de una receta se normaliza sin acentos: un valor con "ñ" (p. ej. "Dañado") no lo encuentra.
