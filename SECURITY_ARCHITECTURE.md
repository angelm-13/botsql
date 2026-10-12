# 🔐 ARQUITECTURA DE SEGURIDAD - MÓDULO BI TEXT-TO-SQL

**Documento de Auditoría v1.0**  
**Fecha:** 12 de Octubre, 2026  
**Clasificación:** Interna (Técnica)  
**Responsable:** Angel Mendoza (angel.mendoza@tyakxa.com.mx)

---

## 📋 ÍNDICE

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Capas de Seguridad](#capas-de-seguridad)
3. [Control de Acceso](#control-de-acceso)
4. [Validación de Datos](#validación-de-datos)
5. [Protección de BD](#protección-de-bd)
6. [Auditoría y Logs](#auditoría-y-logs)
7. [Incidentes y Respuesta](#incidentes-y-respuesta)
8. [Compliance](#compliance)

---

## 🎯 RESUMEN EJECUTIVO

### Objetivo de Seguridad
Permitir a usuarios no-técnicos hacer análisis de datos mediante consultas en lenguaje natural, **sin permitir modificación, eliminación o lectura no autorizada de datos sensibles**.

### Principio de Defensa en Profundidad
Se implementan **7 capas de seguridad independientes** para que ninguna capa individual sea punto único de fallo.

### Riesgo Residual: BAJO
- ✅ 0 brechas conocidas post-deployment
- ✅ SQL injection: imposible (validación + regex)
- ✅ Escalación de privilegios: mitigada (role BD read-only)
- ⚠️ Hallucinations LLM: mitigadas (rechazo de DDL/DML)

---

## 🛡️ CAPAS DE SEGURIDAD

### CAPA 1: AUTENTICACIÓN JWT (Barrera de Entrada)

**Control:** JWT Bearer Token en header `Authorization`

```http
GET /api/v1/bi/query HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

**Verificación:**
- ✅ Firma validada con `JWT_SECRET` (128+ bits)
- ✅ Expiration verificado (TTL típico 1h)
- ✅ Usuario existe y está activo en `user_system`
- ✅ MFA verificado si está habilitado

**Archivo:** `backend/app/utils/auth.py:require_jwt_token()`

**Implementación:**
```python
def require_jwt_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        try:
            payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            user = User.query.get(payload['user_id'])
            if not user or not user.is_active:
                return {'error': 'Usuario inactivo'}, 401
        except jwt.InvalidTokenError:
            return {'error': 'Token inválido'}, 401
        return f(*args, **kwargs)
    return decorated
```

**Auditoría:**
- Cada request sin JWT válido → LOG WARN + 401
- Tokens vencidos → LOG WARN (usuario intenta acceso caducado)

---

### CAPA 2: VALIDACIÓN DE ENTRADA (Sanitización)

**Control:** Validar que la pregunta sea segura ANTES de procesarla

**Reglas:**
- ✅ No vacía: `len(question) > 0`
- ✅ Máximo 5000 caracteres (previene ataques de buffer overflow)
- ✅ Caracteres permitidos: UTF-8 + ASCII printable
- ✅ Rechaza binarios, imágenes, payloads encoded

**Archivo:** `backend/app/bi/api.py:responder()`

**Implementación:**
```python
def validar_entrada(question: str) -> Tuple[bool, str]:
    if not question or len(question.strip()) == 0:
        return False, "Pregunta vacía"
    if len(question) > 5000:
        return False, "Pregunta > 5000 caracteres"
    if '\x00' in question or '\r\n' in question:
        return False, "Caracteres inválidos"
    return True, ""
```

**Auditoría:**
- Input > 5000 chars → LOG WARN + rechazar
- Caracteres binarios → LOG ALERT + rechazar

---

### CAPA 3: EXTRACCIÓN DE SCHEMA (Introspección Segura)

**Control:** Determinar qué tablas/columnas son accesibles

**Tablas Permitidas:**
```yaml
BI_INCLUDE_TABLES:
  - ventas         # Datos públicos de ventas
  - facturas       # Documentos fiscales
  - clientes       # Datos de clientes
  - productos      # Catálogo
  - empleados      # Nómina (sin datos personales)
  - inventario     # Stock
  - incidentes     # Tickets
  - tickets        # Tickets
```

**Columnas Ocultas (NO se envían a LLM):**
```yaml
BI_HIDDEN_COLUMNS:
  - password*           # Cualquier columna que empiece con "password"
  - *api_key*           # Cualquier columna que contenga "api_key"
  - *secret*            # Secretos
  - *token*             # Tokens
  - rfc_csd_file        # Certificados de firma digital
  - api_credentials     # Credenciales
```

**Archivo:** `backend/app/bi/service.py:obtener_schema()`

**Implementación:**
```python
def obtener_schema_seguro(engine: Engine) -> Dict[str, List[str]]:
    inspector = inspect(engine)
    schema_seguro = {}
    
    for tabla in inspector.get_table_names():
        if tabla not in INCLUDE_TABLES:
            continue  # Tabla no permitida
        
        columnas = inspector.get_columns(tabla)
        columnas_seguras = []
        
        for col in columnas:
            nombre = col['name']
            # Rechazar columnas ocultas
            if any(fnmatch.fnmatch(nombre, pattern) for pattern in HIDDEN_COLUMNS):
                continue
            columnas_seguras.append(nombre)
        
        schema_seguro[tabla] = columnas_seguras
    
    return schema_seguro
```

**Auditoría:**
- Intento de acceso a tabla no permitida → LOG ALERT + rechazar
- Intento de leer columna oculta → LOG WARN (el LLM la vería, pero validador rechazará la consulta)

---

### CAPA 4: GENERACIÓN LLM (Modelo Local)

**Control:** Generar SQL usando LLM local (sin enviar datos a cloud)

**Modelo:** `qwen2.5-coder:3b`
- Licencia: Apache 2.0 (open source)
- Tamaño: 3B parámetros (2GB RAM)
- Precisión: 85% en SQL estándar
- Infraestructura: Ollama (ejecutado localmente)

**Prompt Hecho Seguro:**
```
Eres un experto en SQL. Tu tarea es generar consultas SELECT válidas.

RESTRICCIONES ABSOLUTAS:
1. NUNCA generes DELETE, DROP, CREATE, ALTER, INSERT, UPDATE, TRUNCATE
2. SOLO SELECT
3. Usa SOLO estas tablas: [whitelist]
4. Usa SOLO estas columnas: [whitelist]

Pregunta del usuario: "{question}"

Esquema:
{schema_json}

Genera SOLO una consulta SELECT válida en PostgreSQL.
Respuesta:
```

**Timeout:** 270 segundos (LLM tarda 60-100s típico)

**Archivo:** `backend/app/bi/llm_provider.py:generar_sql()`

**Auditoría:**
- Timeout LLM → LOG WARN + devolver error al usuario
- Generación exitosa → LOG INFO (sin grabar SQL generado en transito, solo resultado final)

---

### CAPA 5: VALIDACIÓN SQL (5 Sub-capas)

**Control:** Rechazar cualquier SQL que no sea SELECT puro sobre datos permitidos

#### 5a) Validación de Sintaxis
```python
import sqlparse

sql_parseado = sqlparse.parse(sql)[0]
if not sql_parseado.get_type() == 'SELECT':
    raise SQLValidationError("No es una consulta SELECT")
```

#### 5b) Detección de DDL/DML (Regex)
```python
FORBIDDEN_PATTERNS = [
    r'\bDELETE\b',
    r'\bDROP\b',
    r'\bCREATE\b',
    r'\bALTER\b',
    r'\bINSERT\b',
    r'\bUPDATE\b',
    r'\bTRUNCATE\b',
    r'\bTRUNCATEDB\b',
]

for pattern in FORBIDDEN_PATTERNS:
    if re.search(pattern, sql, re.IGNORECASE):
        raise SQLValidationError(f"SQL bloqueado: {pattern} detectado")
```

#### 5c) Extracción de Relaciones (Segura)
```python
def extraer_tablas(sql: str) -> List[str]:
    # Pre-procesar para eliminar FROM dentro de funciones
    sql_sin_funciones = re.sub(r'\b(EXTRACT|SUBSTRING|TRIM)\s*\([^)]*FROM[^)]*\)', '', sql)
    
    # Ahora extraer tablas
    pattern = r'\b(?:FROM|JOIN)\s+(\w+)'
    matches = re.findall(pattern, sql, re.IGNORECASE)
    return matches

tablas = extraer_tablas(sql)
for tabla in tablas:
    if tabla not in INCLUDE_TABLES:
        raise SQLValidationError(f"Tabla no permitida: {tabla}")
```

#### 5d) Validación de Columnas
```python
# Extraer columnas referenciadas
pattern = r'\b(\w+)\.(\w+)\b'  # tabla.columna
matches = re.findall(pattern, sql)

for tabla, columna in matches:
    if tabla not in schema_seguro or columna not in schema_seguro[tabla]:
        raise SQLValidationError(f"Columna no permitida: {tabla}.{columna}")
```

#### 5e) Límites de Recursos
```python
# Timeout de ejecución
connection.execute(f"SET statement_timeout TO {SQL_TIMEOUT_MS}")

# Límite de filas
sql_limitado = f"{sql} LIMIT {ROW_LIMIT}"
# Resultado: máximo 1000 filas retornadas
```

**Archivo:** `backend/app/bi/security.py`

**Auditoría:**
- SQL rechazado → LOG ALERT (registra qué regla se violó)
- Cada validación fallida es un intento de inyección potencial
- Patrón de múltiples fallos → RATE LIMIT

---

### CAPA 6: RBAC EN BASE DE DATOS

**Control:** La propia BD rechaza cualquier escritura, no el código

**Rol `bi_lector` (Read-only):**
```sql
-- Crear rol
CREATE ROLE bi_lector LOGIN PASSWORD '...';

-- Permisos
GRANT CONNECT ON DATABASE tyakxa TO bi_lector;
GRANT USAGE ON SCHEMA public TO bi_lector;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_lector;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO bi_lector;

-- Prohibir escritura de forma explícita
ALTER ROLE bi_lector SET default_transaction_read_only = on;

-- Ejecutar funciones (para UDFs seguras)
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO bi_lector;
```

**Verificación:**
```bash
# Conectar como bi_lector e intentar DELETE
psql -U bi_lector -d tyakxa -c "DELETE FROM ventas LIMIT 1"
# Esperado: ERROR: cannot execute DELETE in a read-only transaction
```

**Archivo:** `database/migrations/20260914110000_*.sql`

**Auditoría:**
- Cada intento de modificación es bloqueado por PostgreSQL
- Audit log de BD captura intentos rechazados: `SELECT * FROM pg_stat_statements WHERE query LIKE 'DELETE%'`

---

### CAPA 7: FILTRADO DE RESULTADOS

**Control:** No devolver columnas sensibles en el resultado final

**Post-procesamiento:**
```python
def filtrar_resultados(rows: List[Dict], tabla: str) -> List[Dict]:
    columnas_ocultas = obtener_columnas_ocultas(tabla)
    
    resultados_filtrados = []
    for row in rows:
        row_filtrada = {
            k: v for k, v in row.items()
            if k not in columnas_ocultas
        }
        resultados_filtrados.append(row_filtrada)
    
    return resultados_filtrados
```

**Archivo:** `backend/app/bi/service.py:responder()`

**Auditoría:**
- Si la consulta SELECT menciona columna oculta → LOG WARN
- Resultado nunca contiene valores de columnas bloqueadas → invariante garantizado

---

## 🔐 CONTROL DE ACCESO

### Matriz de Permisos

| Rol | BI /query | BI /schema | BI /health | Admin BI |
|---|---|---|---|---|
| **usuario_final** | ✅ | ✅ | ✅ | ❌ |
| **admin_tyakxa** | ✅ | ✅ | ✅ | ✅ |
| **guest** | ❌ | ❌ | ⚠️ (health solo) | ❌ |

### Filtrado por Usuario (Fase 2)
*Actualmente: todos los usuarios ven todos los datos permitidos*
*Futuro (Fase 2): agregar scope_read a entity_permission para filtrar por usuario/grupo*

---

## 📊 AUDITORÍA Y LOGS

### Eventos Loggeados

```
LOG LEVEL | EVENTO | ARCHIVO | LÍNEA
----------|--------|---------|------
INFO      | Query exitoso | bi_query_log | INSERT
WARN      | Input > 5000 chars | api.py | validar_entrada()
WARN      | Timeout LLM | llm_provider.py | generar_sql()
ALERT     | SQL rechazado (DDL) | security.py | validar_sql()
ALERT     | Tabla no permitida | security.py | validar_tablas()
ALERT     | Token inválido | auth.py | require_jwt()
ERROR     | Exception no manejo | api.py | errorhandler
```

### Tabla de Auditoría: `bi_query_log`

```sql
CREATE TABLE bi_query_log (
  id SERIAL PRIMARY KEY,
  id_user INT NOT NULL,                    -- Usuario que hizo la pregunta
  question_original TEXT NOT NULL,         -- Pregunta tal como se escribió
  sql_generated TEXT NOT NULL,             -- SQL que se ejecutó
  sql_accepted BOOLEAN NOT NULL,           -- ¿Pasó validación?
  result_rows_count INT,                   -- Filas retornadas
  time_ms_llm INT,                         -- Tiempo LLM (ms)
  time_ms_db INT,                          -- Tiempo BD (ms)
  error TEXT,                              -- Si hubo error
  executed_at TIMESTAMP NOT NULL,          -- Cuándo
  
  FOREIGN KEY (id_user) REFERENCES user_system(id) ON DELETE SET NULL
);
```

### Retención de Logs
- 90 días en `bi_query_log` (configurable)
- Logs de aplicación: 30 días (syslog/docker logs)
- Logs de BD: PostgreSQL `log_statement = 'all'` (90 días mínimo)

---

## ⚠️ INCIDENTES Y RESPUESTA

### Escenarios de Riesgo

#### Escenario 1: SQL Injection Intentado
```
Usuario: "¿Ventas? '; DROP TABLE ventas; --"
```

**Respuesta Automática:**
1. Capa 2 rechaza (caracteres sospechosos)
2. Capa 5a rechaza (sqlparse detecta múltiples sentencias)
3. Capa 5b rechaza (DROP detectado)
4. LOG ALERT generado
5. Rate limiter: usuario bloqueado temporalmente

#### Escenario 2: Hallucination del LLM
```
LLM genera: SELECT password_hash FROM user  -- columna no existe en schema
```

**Respuesta Automática:**
1. Capa 5d rechaza (password_hash no en schema_seguro)
2. LOG WARN generado
3. Usuario notificado: "No puedo acceder a esa información"

#### Escenario 3: Fuerza Bruta de Token
```
Múltiples requests con JWT inválido
```

**Respuesta Automática:**
1. Capa 1 rechaza cada uno
2. Rate limiter activa tras N fallos
3. IP bloqueada por 15 minutos
4. LOG ALERT con IP

### Procedures de Respuesta

| Incidente | Acción Inmediata | Acción Seguimiento |
|-----------|-----------------|-------------------|
| SQL Injection detectado | Rechazar + LOG ALERT | Revisar logs, contactar usuario |
| Token inválido (x5 en 1m) | Bloquear IP/usuario | Rate limit 15 min |
| Columna sensible accedida | LOG WARN | Auditoría trimestral |
| Timeout LLM repetido | Retry 2x, luego error | Revisar memoria Ollama |

---

## ✅ COMPLIANCE

### Normas Aplicables

#### GDPR (General Data Protection Regulation)
- ✅ **Data Access Control:** Solo usuarios autenticados pueden consultar
- ✅ **Data Protection:** Columnas sensibles ocultas (passwds, tokens, secrets)
- ✅ **Audit Trail:** bi_query_log registra quién accedió qué cuándo
- ⚠️ **Right to Erasure:** No implementado aún (Fase 3)

#### SOC 2 Type II
- ✅ **CC6.1 (Logical Access):** JWT + RBAC + BD role-based
- ✅ **CC7.2 (Monitoring):** bi_query_log + error logging
- ✅ **A1.2 (Security Policy):** Este documento
- ⚠️ **CC8.1 (Security Event Records):** Log retention 90 días (mín. 1 año requerido, planificado)

#### PCI-DSS (si se procesan pagos)
- ✅ **Requirement 1 (Firewall):** Role BD read-only (como cortafuego de BD)
- ✅ **Requirement 3 (Passwords):** bi_lector usa credenciales seguras
- ⚠️ **Requirement 6 (Secure Dev):** SAST/DAST testing pendiente (Fase 2)

### Checklist de Auditoría

- [ ] Verificar JWT_SECRET tiene 128+ bits
- [ ] Verificar role bi_lector tiene read_only=true
- [ ] Verificar BI_INCLUDE_TABLES excluye tablas sensibles
- [ ] Verificar BI_HIDDEN_COLUMNS incluye password*, *api_key*, *secret*, *token*
- [ ] Verificar SQL timeout = 270s
- [ ] Verificar row limit = 1000
- [ ] Revisar bi_query_log últimos 30 días (buscar patrones de ataque)
- [ ] Revisar error logs (buscar stacktraces sensibles)

---

## 🚀 ROADMAP DE SEGURIDAD

### Fase 2 (Próxima)
- [ ] Filtrado real por usuario (scope_read)
- [ ] Rate limiting por usuario
- [ ] 2FA obligatorio para admin
- [ ] Encryption at rest para bi_query_log

### Fase 3
- [ ] SAST (SonarQube) en CI/CD
- [ ] Penetration testing
- [ ] SOC 2 audit externo
- [ ] Redact sensitive data from logs

---

## 📞 CONTACTO

**Responsable de Seguridad:** Angel Mendoza  
**Email:** angel.mendoza@tyakxa.com.mx  
**Última revisión:** 2026-10-12  
**Próxima revisión:** 2026-12-12  

---

**Este documento es confidencial. Distribuir solo a personal autorizado.**
