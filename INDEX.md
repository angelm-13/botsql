# 📑 ÍNDICE RÁPIDO — MÓDULO BI TEXT-TO-SQL

## 🎯 INICIA AQUÍ

**¿Qué necesitas?**

- 🚀 **Levantar el sistema** → [`docker compose up -d`](#-levantar)
- 📖 **Entender la arquitectura** → [`GUIA_TECNICA_MODULO_BI_v1.0.docx`](#documentación-técnica)
- 🔐 **Revisar seguridad** → [`SECURITY_ARCHITECTURE.md`](#documentación-de-seguridad)
- ⚙️ **Configurar queue** → [`QUEUE_GUIDE.md`](#documentación-de-operación)
- 💬 **Usar el módulo BI** → [`BiPage.jsx`](#frontend)
- 📊 **Ver diagramas** → [Galería de HTML](#diagramas)

---

## 🐳 INFRAESTRUCTURA

### Levantar

```bash
cd C:\Users\TDW3\tyakxa_tny_con_bi
docker compose up -d
docker compose ps                    # Verificar
```

### URLs

| Componente | URL | Credenciales |
|------------|-----|--------------|
| **Frontend BI** | http://localhost:3001 | JWT token |
| **API REST** | http://localhost:8091/api/v1/bi | JWT token |
| **RabbitMQ UI** | http://localhost:15672 | guest / guest |
| **Nginx** | http://localhost:8080 | - |
| **PostgreSQL** | localhost:5432 | tyakxa / tyakxa |

### Containers

```
✅ db-with-bi             PostgreSQL (5432)
✅ backend-with-bi        FastAPI (8091)
✅ frontend-with-bi       React/Vite (3001)
✅ rabbitmq               RabbitMQ (5672, 15672)
✅ celery-worker          Async task processor
✅ celery-beat            Scheduler
✅ nginx                  Reverse proxy (8080)
```

---

## 📚 DOCUMENTACIÓN

### Documentación Técnica

**Archivo:** `GUIA_TECNICA_MODULO_BI_v1.0.docx`

**Contiene:**
- Stack técnico (Ollama, Celery, PostgreSQL, FastAPI)
- 6-layer architecture diagram
- 5-layer security model (detalle)
- Modelos de base de datos
- API REST endpoints (swagger-style)
- Query examples
- Performance metrics

**Para:** Arquitectos, desarrolladores, auditoría técnica

---

### Documentación de Seguridad

**Archivo:** `SECURITY_ARCHITECTURE.md`

**Contiene:**
- ✅ 7 capas de defensa en profundidad
- ✅ Validación SQL (5 sub-capas)
- ✅ RBAC en PostgreSQL
- ✅ Tabla `bi_query_log` (auditoría)
- ✅ Compliance (GDPR, SOC 2, PCI-DSS)
- ✅ Procedures de incidentes
- ✅ Checklist de auditoría
- ✅ Roadmap Fase 2-3

**Para:** CISOs, auditoría, compliance officers

**Temas clave:**
1. **Capa 1:** Autenticación JWT
2. **Capa 2:** Validación de entrada (sanitización)
3. **Capa 3:** Extracción segura de schema
4. **Capa 4:** LLM local (Ollama)
5. **Capa 5:** Validación SQL (5 sub-capas)
6. **Capa 6:** RBAC en BD (rol read-only)
7. **Capa 7:** Filtrado de resultados

---

### Documentación de Operación

**Archivo:** `QUEUE_GUIDE.md`

**Contiene:**
- ✅ Cómo usar desde cliente (4 métodos)
- ✅ Ejemplos curl + código React
- ✅ Monitoreo (Flower, logs, estadísticas)
- ✅ Troubleshooting (stuck tasks, RabbitMQ down)
- ✅ Performance esperado
- ✅ Checklist de implementación

**Para:** DevOps, operadores, desarrolladores frontend

**Métodos de uso:**
1. **Sincrónico (bloqueante):** POST `/query`
2. **Asincrónico (queue):** POST `/query/async` + polling
3. **Cancelación:** DELETE `/task/{id}`
4. **Estadísticas:** GET `/stats`

---

### Resumen Completación

**Archivo:** `README_COMPLETACION.md`

**Contiene:**
- ✅ Resumen ejecutivo
- ✅ Estructura de archivos
- ✅ Cómo usar (3 opciones)
- ✅ Checklist de validación
- ✅ Roadmap futuro (Fase 2-4)
- ✅ Timeline de entrega

**Para:** Stakeholders, project managers

---

## 🎨 DIAGRAMAS

**Formato:** HTML interactivo (abrir en navegador)

| Diagrama | Archivo | Descripción |
|----------|---------|-------------|
| 📋 **Casos de Uso** | `casos_uso.html` | 8 actores × 12 casos (usuarios, admin, LLM, BD) |
| 📦 **Paquetes** | `paquetes.html` | 6 capas: Frontend → API → Service → Security → LLM → DB |
| 🗄️ **Entidad-Relación** | `er.html` | Tablas: user, bi_query_log, entity_permission, roles |
| 🏗️ **Arquitectura** | `arquitectura.html` | Sistema completo: containers, redes, volúmenes |
| 🔄 **Flujo Pregunta** | `flujo_pregunta.html` | Secuencia: Input → LLM → Validación → SQL → BD → Output |
| 💼 **Modelo Negocios** | `modelo_negocios.html` | Business Model Canvas (9 bloques) |
| 🎞️ **Presentación** | `slides.html` | 14 diapositivas para defensa (vision, tech, roadmap) |

**Abre en Chrome/Firefox/Edge. Haz click en elementos para más detalles.**

---

## 💻 CÓDIGO FUENTE

### Backend (`backend/app/bi/`)

| Archivo | Responsabilidad | Líneas |
|---------|-----------------|--------|
| `__init__.py` | Inicialización + auto-registro blueprint | 20 |
| `api.py` | Endpoints POST /query, GET /schema, POST /run | 150 |
| `api_queue.py` | Endpoints POST /query/async, GET /task/{id}, DELETE /task/{id} | 175 |
| `config.py` | Variables de configuración (timeouts, límites, tablas) | 50 |
| `llm_provider.py` | Interface + Ollama provider (prompt engineering) | 120 |
| `service.py` | Orquestación: BIService.responder() | 200 |
| `security.py` | 5 capas de validación SQL | 300 |
| `queue_service.py` | Celery + QueueManager (async task handling) | 175 |
| `cache.py` | Cache en memoria (TTL 3600s) | 80 |

### Frontend (`frontend/src/`)

| Archivo | Responsabilidad |
|---------|-----------------|
| `pages/BiPage.jsx` | Página principal (layout + lógica) |
| `components/BiQuery.jsx` | Input de pregunta + envío |
| `components/BiResults.jsx` | Tabla de resultados |
| `components/BiProgressBar.jsx` | Barra de progreso (polling) |
| `api/bi.js` | Cliente HTTP (fetch wrapper) |

### Base de Datos (`database/`)

| Archivo | Cambios |
|---------|---------|
| `migrations/20261012_*.sql` | Nueva tabla `bi_query_log` |
| `seed.sql` | Datos de prueba (opcional) |

---

## 🔌 API REST

### Endpoint Principal (Sincrónico)

```http
POST /api/v1/bi/query
Content-Type: application/json
Authorization: Bearer <JWT>

{
  "prompt": "¿Cuántas facturas hay?"
}

# Respuesta (espera 60-100s):
{
  "sql": "SELECT COUNT(*) FROM facturas",
  "resultados": [{"count": 1234}],
  "ms_modelo": 85000,
  "ms_bd": 45
}
```

### Queue (Asincrónico, Recomendado para Prod)

```http
POST /api/v1/bi/query/async
Content-Type: application/json

# → Respuesta inmediata (100ms):
{
  "task_id": "abc-123-xyz",
  "status": "queued"
}

# Poll con:
GET /api/v1/bi/task/abc-123-xyz

# Respuesta:
{
  "status": "SUCCESS",
  "result": {...},
  "progress_percent": 100
}
```

### Schema (Read-only)

```http
GET /api/v1/bi/schema
# Retorna: {"tablas_permitidas": {...}, "columnas_permitidas": {...}}
```

### Health

```http
GET /api/v1/bi/health
# {"status": "ok", "llm": "ready"}
```

---

## 🧪 TESTING

### Test Suite

```bash
# Unit tests
docker compose exec backend pytest tests/test_bi/ -v

# Integration test (curl)
curl -X POST http://localhost:8091/api/v1/bi/query \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "¿Total de ventas?"}'

# Queue test
curl -X POST http://localhost:8091/api/v1/bi/query/async \
  -H "Authorization: Bearer test-token" \
  -d '{"prompt": "¿Ventas por mes?"}'
```

### Security Test (SQL Injection)

```bash
# Intento malicioso
curl -X POST http://localhost:8091/api/v1/bi/query \
  -d '{"prompt": "¿Facturas? DROP TABLE facturas; --"}'

# Esperado: 400/403 (bloqueado en Capa 2 o Capa 5)
```

---

## 🛠️ TROUBLESHOOTING

### Problema: "Backend no responde"

```bash
# 1. Verificar container
docker compose ps backend-with-bi

# 2. Ver logs
docker compose logs backend-with-bi -f

# 3. Verificar DB está sana
docker compose exec db-with-bi psql -U tyakxa -d tyakxa -c "SELECT 1"

# 4. Restart
docker compose restart backend-with-bi
```

### Problema: "LLM timeout"

```bash
# 1. Verificar Ollama
docker exec backend-with-bi curl http://ollama:11434/api/tags

# 2. Restart
docker compose restart backend-with-bi

# 3. Revisar logs
docker compose logs backend-with-bi | grep "LLM\|timeout"
```

### Problema: "Queue stuck"

```bash
# 1. Ver estadísticas
curl http://localhost:8091/api/v1/bi/stats

# 2. Ver RabbitMQ
curl -u guest:guest http://localhost:15672/api/queues

# 3. Cancelar tarea
curl -X DELETE http://localhost:8091/api/v1/bi/task/{task_id}

# 4. Restart worker
docker compose restart celery-worker
```

Ver detalles completos en **`QUEUE_GUIDE.md`** sección "Troubleshooting".

---

## 📊 AUDITORÍA

### Tabla de Query Log

```sql
SELECT id, id_user, question_original, sql_generated, 
       result_rows_count, time_ms_llm, time_ms_db, error, executed_at
FROM bi_query_log
WHERE executed_at > NOW() - INTERVAL '7 days'
ORDER BY executed_at DESC;
```

### Seguridad por Capa

| # | Capa | Validación | Log Level |
|---|------|-----------|-----------|
| 1 | JWT | Token inválido → 401 | WARN |
| 2 | Input | Input > 5000 chars → 400 | WARN |
| 3 | Schema | Tabla no permitida → 400 | ALERT |
| 4 | LLM | Timeout → error | WARN |
| 5 | SQL | DDL detectado → 403 | ALERT |
| 6 | RBAC | INSERT rechazado por BD | N/A (BD logs) |
| 7 | Resultados | Columna sensible → omitida | INFO |

---

## 📅 PRÓXIMAS FASES

### Fase 2: Filtrado Real por Usuario
- [ ] Implementar `scope_read` en `entity_permission`
- [ ] Filtrar query por usuario/grupo
- [ ] Rate limiting por usuario

### Fase 3: Hardening
- [ ] SAST (SonarQube)
- [ ] Pen testing
- [ ] SOC 2 audit externo

### Fase 4: Optimización
- [ ] Modelo 7B LLM
- [ ] GPU support
- [ ] Cache distribuido

---

## 🆘 CONTACTO

**Responsable:** Angel Mendoza (angel.mendoza@tyakxa.com.mx)  
**Slack:** @angelm-13  
**GitHub:** angelm-13

**En caso de emergencia:**
1. Revisar logs: `docker logs backend-with-bi`
2. Contactar responsable
3. Adjuntar: logs + tabla `bi_query_log` + estado del queue

---

## ✅ VALIDACIÓN FINAL

```
✅ Backend BI completo
✅ Frontend funcional
✅ Queue asincrónico
✅ Seguridad 7-capas
✅ Auditoría implementada
✅ Docker con BI
✅ Documentación completa
✅ Diagrama+Presentación
✅ Tests básicos
✅ Listo para Producción
```

---

**Última actualización:** 2026-10-12  
**Versión:** 1.0  
**Estado:** ✅ ENTREGA COMPLETA
