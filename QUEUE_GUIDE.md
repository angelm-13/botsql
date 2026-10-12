# 📦 GUÍA: QUEUE DE REQUESTS BI (Manejo de Concurrencia)

## 🎯 Problema Que Resuelve

**Sin Queue:**
```
Usuario A: "¿Ventas por mes?" → Espera 65s
Usuario B: Se conecta en segundo 5 → Espera 60s (por A)
Usuario C: Se conecta en segundo 10 → Espera 55s (por A y B)
```
→ El servidor está **bloqueado** por el LLM. Mala UX.

**Con Queue:**
```
Usuario A: Envía pregunta → Task ID abc123 → Retorna INMEDIATAMENTE
Usuario B: Envía pregunta → Task ID def456 → Retorna INMEDIATAMENTE
Usuario C: Envía pregunta → Task ID ghi789 → Retorna INMEDIATAMENTE

Background: Celery procesa A, luego B, luego C (sin bloquear frontend)
```
→ Frontend responde al usuario en **< 100ms**. Buena UX.

---

## 🚀 CÓMO USAR DESDE EL CLIENTE

### 1️⃣ Enviar Pregunta a Queue (No Bloquea)

```bash
curl -X POST http://localhost:8091/api/v1/bi/query/async \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "¿Cuántas facturas hay en total?",
    "priority": 5
  }'

# Respuesta (inmediata, ~100ms):
{
  "task_id": "abc123def456-7890-ghi",
  "status": "queued",
  "message": "Consulta encolada. Polling con GET /task/{task_id}",
  "check_url": "/api/v1/bi/task/abc123def456-7890-ghi",
  "priority": 5
}
```

**¡Listo!** El usuario recibe un `task_id` INMEDIATAMENTE y puede seguir usando la UI.

### 2️⃣ Monitorear Progreso (Polling)

El cliente hace polling cada 2-5 segundos:

```bash
# Minuto 0: pregunta encolada
curl http://localhost:8091/api/v1/bi/task/abc123def456-7890-ghi \
  -H "Authorization: Bearer <JWT_TOKEN>"

{
  "task_id": "abc123def456-7890-ghi",
  "status": "PENDING",
  "result": null,
  "error": null,
  "ready": false,
  "successful": false,
  "progress_percent": 0,
  "message": "En cola, esperando disponibilidad..."
}

# Minuto 0.5: LLM generando SQL
{
  "task_id": "abc123def456-7890-ghi",
  "status": "STARTED",
  "result": null,
  "error": null,
  "ready": false,
  "successful": false,
  "progress_percent": 50,
  "message": "Generando SQL (60-100s)..."
}

# Minuto 1.2: Completada
{
  "task_id": "abc123def456-7890-ghi",
  "status": "SUCCESS",
  "result": {
    "sql": "SELECT COUNT(*) FROM facturas",
    "resultados": [{"count": 1234}],
    "cache": false,
    "ms_modelo": 85000,
    "ms_bd": 45
  },
  "error": null,
  "ready": true,
  "successful": true,
  "progress_percent": 100,
  "message": "Completada"
}
```

### 3️⃣ Mostrar Progreso en UI

Pseudocódigo React:

```jsx
function BiQuery() {
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState(0);

  const handleSubmit = async (question) => {
    // Enviar a queue
    const res = await fetch('/api/v1/bi/query/async', {
      method: 'POST',
      body: JSON.stringify({ prompt: question })
    });
    const { task_id } = await res.json();
    setTaskId(task_id);
    
    // Empezar polling
    pollTask(task_id);
  };

  const pollTask = async (id) => {
    const interval = setInterval(async () => {
      const res = await fetch(`/api/v1/bi/task/${id}`);
      const data = await res.json();
      
      setStatus(data.status);
      setProgress(data.progress_percent);
      
      if (data.ready) {
        clearInterval(interval);
        if (data.successful) {
          // Mostrar resultados
          displayResults(data.result);
        } else {
          // Mostrar error
          showError(data.error);
        }
      }
    }, 2000); // Poll cada 2s
  };

  return (
    <div>
      <input onSubmit={handleSubmit} />
      {taskId && (
        <ProgressBar 
          status={status}
          percent={progress}
          message={status} 
        />
      )}
    </div>
  );
}
```

### 4️⃣ Cancelar Tarea (Si se arrepiente)

```bash
curl -X DELETE http://localhost:8091/api/v1/bi/task/abc123def456-7890-ghi \
  -H "Authorization: Bearer <JWT_TOKEN>"

{
  "task_id": "abc123def456-7890-ghi",
  "cancelled": true,
  "message": "Tarea cancelada"
}
```

---

## 🔧 CONFIGURACIÓN DEL BACKEND

### Requirements.txt (Agregar)

```
celery==5.3.0
redis==5.0.0
kombu==5.3.0
```

### Docker Compose (Ya Incluido)

```yaml
rabbitmq:
  image: rabbitmq:4-management-alpine
  environment:
    RABBITMQ_DEFAULT_USER: guest
    RABBITMQ_DEFAULT_PASS: guest
  ports:
    - "5672:5672"      # AMQP
    - "15672:15672"    # Management UI

# El worker Celery corre en el contenedor backend:
# gunicorn ... --worker-class gevent  # o:
# celery -A app.bi.queue_service worker -Q bi_queries
```

### Backend App (__init__.py)

```python
# Registrar queue blueprint en create_app()
from app.bi.api_queue import bp_bi_queue

app.register_blueprint(bp_bi_queue, url_prefix="/api/v1/bi")
```

### Environment Variables

```bash
# .env
CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_RESULT_BACKEND=db+postgresql://tyakxa:tyakxa@db_bi:5432/tyakxa_celery
BI_QUEUE_ENABLED=true
```

---

## 📊 MONITOREO

### Ver Tareas en Queue

```bash
# Flower: UI de Celery en http://localhost:5555
docker run --name flower \
  -p 5555:5555 \
  --link rabbitmq:rabbitmq \
  mher/flower \
  --broker=amqp://guest:guest@rabbitmq:5672//
```

### Estadísticas

```bash
curl http://localhost:8091/api/v1/bi/stats \
  -H "Authorization: Bearer <JWT_TOKEN>"

{
  "workers": ["celery@backend"],
  "active_tasks": 1,
  "queue": "bi_queries",
  "max_concurrent": 1
}
```

### Logs

```bash
# Ver logs del worker
docker logs backend -f | grep "\[BI Queue\]"

# Ver tabla bi_query_log
psql -U tyakxa -d tyakxa -c "
  SELECT 
    id, 
    id_user, 
    substring(question_original for 60) as q,
    time_ms_llm, 
    time_ms_db,
    executed_at
  FROM bi_query_log
  ORDER BY executed_at DESC
  LIMIT 10;
"
```

---

## ⚡ PERFORMANCE

### Latencia Esperada

| Fase | Sin Queue | Con Queue |
|------|-----------|-----------|
| Usuario hace pregunta | 65s | 100ms ✅ |
| Espera hasta resultado | 65s | 65s (en background) |
| Frontend responsivo | ❌ Bloqueado | ✅ Disponible |

### Concurrencia

| Métrica | Valor |
|---------|-------|
| Requests simultáneos | ∞ (todos quedan en cola) |
| Preguntas procesadas en paralelo | 1 (LLM es el cuello) |
| Throughput | 1 query / 65s = 0.015 queries/s |

---

## 🚨 TROUBLESHOOTING

### Problema: "Tarea stuck en STARTED"

**Síntoma:** Status no cambia después de 2 minutos

**Causa:** LLM hangueado

**Solución:**
```bash
# Cancela la tarea
curl -X DELETE http://localhost:8091/api/v1/bi/task/{task_id}

# Reinicia Ollama
docker compose restart backend  # o solo ollama
```

### Problema: "RabbitMQ connection refused"

**Síntoma:** Celery no puede conectar a queue

**Causa:** RabbitMQ no levantado

**Solución:**
```bash
# Verifica que rabbitmq esté up
docker compose up rabbitmq

# Verifica conexión
docker exec backend python -c "
  from kombu import Connection
  with Connection('amqp://guest:guest@rabbitmq:5672//') as conn:
    print('OK')
"
```

### Problema: "Task retorna null result"

**Síntoma:** Status=SUCCESS pero result=null

**Causa:** Error en el LLM pero no capturado

**Solución:**
```bash
# Revisa logs del worker
docker logs backend -f | grep "Task.*error"

# Revisa tabla de error
psql -U tyakxa -d tyakxa -c "
  SELECT id, question_original, error, executed_at 
  FROM bi_query_log 
  WHERE error IS NOT NULL 
  LIMIT 5;
"
```

---

## 📚 ARCHIVOS CLAVE

- **Queue Service:** `backend/app/bi/queue_service.py` (Celery + manager)
- **API Endpoints:** `backend/app/bi/api_queue.py` (POST /query/async, GET /task/{id})
- **Security:** `backend/app/bi/security.py` (validación SQL)
- **Config:** `backend/app/bi/config.py` (timeouts, límites)
- **Auditoría:** `bi_query_log` table en BD
- **Docs:** Este archivo + `SECURITY_ARCHITECTURE.md`

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

- [ ] Instalar Celery + Redis en requirements.txt
- [ ] Agregar RabbitMQ a docker-compose.yml
- [ ] Crear `queue_service.py` y `api_queue.py`
- [ ] Registrar blueprint en `__init__.py`
- [ ] Configurar variables de entorno
- [ ] Testear POST /query/async → GET /task/{id}
- [ ] Testear cancelación con DELETE /task/{id}
- [ ] Implementar UI con polling (React)
- [ ] Documentar en wiki de equipo
- [ ] Capacitar usuarios

---

**Versión:** 1.0  
**Actualizado:** 2026-10-12  
**Responsable:** Angel Mendoza
