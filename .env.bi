# === BASES DE DATOS ===
DATABASE_URL=postgresql+psycopg2://tyakxa:tyakxa@db_bi:5432/tyakxa
SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://tyakxa:tyakxa@db_bi:5432/tyakxa

# === PUERTOS ===
BACKEND_PORT=8091
FRONTEND_PORT=3001

# === JWT ===
JWT_SECRET=dev-secret-tyakxa-bi
JWT_SS=dev-ss-tyakxa-bi

# === MFA ===
MFA_ISSUER=TYAKXA Test Con BI

# === BI MODULE ===
BI_OLLAMA_URL=http://host.docker.internal:11434
BI_MODEL=qwen2.5-coder:3b
BI_LLM_TIMEOUT=270
BI_DATABASE_URL=postgresql+psycopg2://bi_lector:CAMBIEME@db_bi:5432/tyakxa
BI_QUESTION_CACHE_TTL=3600
BI_ROW_LIMIT=1000
BI_SQL_TIMEOUT_MS=15000
BI_INCLUDE_TABLES=ventas,facturas,clientes,productos,empleados,inventario,incidentes,tickets
BI_HIDDEN_COLUMNS=password*,*api_key*,*secret*,*token*
