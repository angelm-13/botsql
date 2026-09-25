# Despliegue

Guía para poner el módulo en producción contra la base de un proyecto real.
Para probarlo en dos minutos sin nada instalado, vea el [README](../README.md).

> **Estado de verificación.** Este despliegue se probó de punta a punta: las
> tres imágenes se construyeron (`bi-backend`, `bi-frontend`,
> `Dockerfile.demo`), el stack completo se levantó con `docker compose up`
> contra un PostgreSQL 16 real —no SQLite— con un rol `bi_lector` creado
> siguiendo exactamente la sección 1 de abajo, y se comprobó desde fuera del
> contenedor: la interfaz sirviendo por nginx, `/health` reportando la
> conexión real sin advertencias, el esquema extraído con su llave foránea
> detectada, una consulta con JOIN devolviendo el número correcto, un intento
> de `DELETE` rechazado por el validador, y el rol de solo lectura confirmado
> incapaz de escribir incluso conectándose directo con `psql`.
>
> Un defecto real apareció en esa prueba y ya está corregido: la versión de
> `psycopg2-binary` fijada en `backend/Dockerfile` (2.9.9) no tiene rueda
> precompilada para Python 3.13, y el build fallaba con
> `pg_config executable not found`. Se subió a 2.9.13 y se agregó `libpq-dev`
> como red de seguridad, purgada en la misma capa para no dejarla en la
> imagen final.

---

## 1. Antes de nada: el rol de solo lectura

Esta es la barrera que de verdad protege. El validador de SQL puede tener un
hueco; un rol sin permiso de escritura, no. **No despliegue con el
superusuario**, aunque funcione.

### PostgreSQL

```sql
CREATE ROLE bi_lector LOGIN PASSWORD 'una-clave-larga-y-unica';

GRANT CONNECT ON DATABASE erp TO bi_lector;
GRANT USAGE ON SCHEMA public TO bi_lector;

-- Solo lectura, y solo sobre lo que el módulo debe ver.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_lector;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO bi_lector;

-- Quítele lo que no tenga por qué leer, tabla por tabla.
REVOKE ALL ON usuarios, sesiones, tokens FROM bi_lector;

-- Cinturón adicional: la sesión entra en solo lectura por defecto.
ALTER ROLE bi_lector SET default_transaction_read_only = on;
```

### MySQL / MariaDB

```sql
CREATE USER 'bi_lector'@'%' IDENTIFIED BY 'una-clave-larga-y-unica';
GRANT SELECT ON erp.* TO 'bi_lector'@'%';
REVOKE SELECT ON erp.usuarios FROM 'bi_lector'@'%';
FLUSH PRIVILEGES;
```

### SQL Server

```sql
CREATE LOGIN bi_lector WITH PASSWORD = 'una-clave-larga-y-unica';
USE erp;
CREATE USER bi_lector FOR LOGIN bi_lector;
ALTER ROLE db_datareader ADD MEMBER bi_lector;
DENY SELECT ON dbo.usuarios TO bi_lector;
```

**Mejor todavía: apunte a una réplica de lectura.** Así una consulta pesada
no compite con la operación, y el daño máximo posible es leer datos viejos.

`GET /api/v1/bi/health` reclama en voz alta si detecta que la conexión usa
`postgres`, `root`, `sa` o `admin`.

---

## 2. Qué ve el modelo

Segunda decisión importante, y la que más afecta la calidad de las respuestas.

| Variable | Efecto |
|---|---|
| `BI_INCLUDE_TABLES` | Lista blanca de patrones. Si se llena, **manda sobre todo lo demás** |
| `BI_EXCLUDE_TABLES` | Lista negra (por omisión: migraciones, sesiones, tokens, claves) |
| `BI_HIDDEN_COLUMNS` | Columnas que no llegan ni al DDL (por omisión: `password*`, `*token*`, `*secret*`, `curp`, `nss`…) |
| `BI_MAX_TABLES` | Tope duro de relaciones en el prompt (60) |

**En producción, use lista blanca.** Es la diferencia entre "el modelo puede
consultar lo que decidimos" y "el modelo puede consultar lo que no se nos
ocurrió excluir":

```bash
BI_INCLUDE_TABLES=ventas,ventas_detalle,clientes,productos,v_*
```

Una columna oculta **no existe** para el módulo: no aparece en el DDL que ve
el modelo, y si aun así la nombrara, el validador rechaza la consulta con
motivo `columna_sensible`.

### Lo mejor: vistas curadas

Si la base es multiempresa o multiproyecto, exponga **vistas** en lugar de
tablas, con el filtro de alcance incrustado:

```sql
CREATE VIEW v_ventas AS
SELECT id, fecha, total, id_cliente
FROM ventas
WHERE (current_setting('bi.id_tenant', true) IS NULL
       OR id_tenant = current_setting('bi.id_tenant', true)::int);
```

```bash
BI_INCLUDE_TABLES=v_*
```

El SQL que escriba el modelo **no puede ver ni cambiar esa variable**: vive en
la definición de la vista. El backend la fija por petición con el gancho
`gancho_sql` (sección 6).

---

## 3. El modelo

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b
ollama serve
```

| Modelo | RAM/VRAM | Comentario |
|---|---|---|
| `qwen2.5-coder:7b` | ~6 GB | El equilibrio recomendado. `:7b-instruct` es el mismo modelo con otro tag -- use el que YA tenga descargado |
| `qwen2.5-coder:14b` | ~10 GB | Notablemente mejor en JOIN de 3+ tablas |
| `qwen2.5-coder:1.5b` | ~2 GB | Solo para preguntas de una tabla |
| `llama3.1:8b` | ~6 GB | Peor en SQL que Qwen-Coder a igual tamaño |

**Sin GPU funciona, pero cuente con 60–100 segundos por pregunta** en un
`7b` -- medido de verdad contra `qwen2.5-coder:7b` en CPU pura (tres
preguntas libres, ~92s cada una de punta a punta), no una estimación. Con GPU
baja a segundos. Suba `BI_LLM_TIMEOUT` si usa un modelo más grande que `7b`
sin GPU: el tiempo escala con el tamaño del modelo.

`/health` distingue "Ollama está arriba" de "el modelo está descargado" — el
error más común al estrenar es que nadie corrió `ollama pull`.

---

## 4. Desplegar con Docker

### 4a. Un solo contenedor, para probar (recomendado para esto)

```bash
docker build -f Dockerfile.demo -t bi-demo .
docker run --rm -p 5001:5001 bi-demo
```

Sin PostgreSQL, sin variables de entorno, sin Ollama. Siembra su propia base
SQLite genérica al arrancar y sirve la interfaz completa en
`http://localhost:5001`. Es la misma imagen que usan `demo.bat`/`demo.sh`
cuando corre bajo Docker Desktop.

Para probarlo con el modelo real en vez del simulado:

```bash
docker run --rm -p 5001:5001 \
  -e BI_DEMO_OLLAMA=1 \
  -e BI_OLLAMA_URL=http://host.docker.internal:11434 \
  --add-host=host.docker.internal:host-gateway \
  bi-demo
```

(`--add-host` hace falta en Linux; en Docker Desktop para Windows/Mac
`host.docker.internal` ya resuelve solo.) Requiere Ollama corriendo en el
equipo anfitrión con el modelo descargado.

Esta imagen es para probarlo, no para producción: la base vive dentro del
contenedor y se pierde al borrarlo.

### 4b. Compose completo, contra una base real

```bash
cp .env.example .env
$EDITOR .env                    # al menos BI_DATABASE_URL
docker compose up -d --build
```

Queda en `http://localhost:8080`. El frontend y la API se sirven desde el
**mismo origen** — nginx reenvía `/api/` al backend — así que no hace falta
abrir CORS.

El puerto del backend **no se publica** a propósito: solo el frontend lo
alcanza por la red interna. Publicarlo dejaría expuesta una API sin
autenticación (sección 6).

```bash
docker compose logs -f backend
docker compose ps                        # el healthcheck consulta /health
docker compose --profile con-modelo up -d    # si quiere Ollama aquí mismo
```

---

## 5. Desplegar sin Docker

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt psycopg2-binary
export BI_DATABASE_URL="postgresql+psycopg2://bi_lector:...@host/erp"
gunicorn -w 4 -b 127.0.0.1:5001 --timeout 180 wsgi:application
```

El `--timeout 180` no es adorno: el valor por omisión de gunicorn son 30 s, y
cortaría la petición justo antes de que un modelo local termine de contestar.

```bash
cd frontend && npm ci && npm run build      # queda en dist/
```

Sirva `dist/` con nginx y reenvíe `/api/` al backend, con
`proxy_read_timeout 180s` por la misma razón. Hay un `nginx.conf` listo en
`frontend/nginx.conf`.

---

## 6. Autenticación: lo que este módulo NO hace

**El módulo no autentica.** Montado suelto, cualquiera que alcance el endpoint
consulta los datos. Esto es deliberado — no le corresponde a un módulo
embebible inventar su propio esquema de sesión — pero **hay que resolverlo
antes de exponerlo**. Tres formas, de menos a más integrada:

1. **Red.** Que solo el frontend interno lo alcance (lo que hace el compose).
2. **Proxy.** nginx/Traefik con OAuth2-proxy o autenticación básica delante.
3. **Integrado en la aplicación anfitriona** — lo correcto si ya hay sesiones:

```python
from bi.api import crear_blueprint
from bi.config import AjustesBI
from bi.llm_provider import ProveedorOllama

def contexto():
    return g.user_data                      # el token ya validado

def gancho_sql(con, ctx):
    """Fija el alcance del usuario en la sesión de base de datos."""
    con.exec_driver_sql(
        "SELECT set_config('bi.id_tenant', %s, true)",
        (str(ctx.get("id_tenant") or ""),),
    )

def relaciones(ctx):
    """Qué puede leer ESTE usuario."""
    return {"v_ventas", "v_clientes"} if ctx["rol"] == "ventas" else {"v_ventas"}

app.register_blueprint(crear_blueprint(
    engine=mi_engine,
    ajustes=AjustesBI.desde_entorno(),
    proveedor=ProveedorOllama(),
    contexto=contexto,
    gancho_sql=gancho_sql,
    relaciones=relaciones,
))
```

Registre el blueprint detrás del decorador de sesión que ya use la aplicación.

---

## 7. Verificar el despliegue

```bash
curl -s localhost:8080/api/v1/bi/health | python -m json.tool
```

Revise tres cosas: `base_de_datos.conecta`, `modelo.disponible` y que
`advertencias` esté **vacío** (si menciona un superusuario, vuelva al paso 1).

```bash
# Qué ve el modelo: la primera pantalla a mirar si contesta mal.
curl -s "localhost:8080/api/v1/bi/schema?ddl=1" | python -m json.tool

# Una pregunta real.
curl -s localhost:8080/api/v1/bi/query \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"¿cuántos registros hay por mes este año?"}' | python -m json.tool
```

Y el que importa — que la barrera esté puesta:

```bash
curl -s localhost:8080/api/v1/bi/query \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"borra todos los registros de la tabla de ventas"}'
# Debe responder HTTP 403 o un widget con error.tipo = "sql_rechazado".
# Compruebe además que el conteo de filas de esa tabla no cambió.
```

---

## 8. Operación

| Qué | Dónde |
|---|---|
| Cambió el esquema de la base | `GET /api/v1/bi/schema?refresh=1`, o espere el TTL (`BI_SCHEMA_TTL`) |
| El asistente contesta mal | Mire `/schema?ddl=1` primero: casi siempre la tabla estaba filtrada o la columna se llama distinto |
| Consultas lentas | Baje `BI_ROW_LIMIT` y `BI_SQL_TIMEOUT_MS`; revise índices de las columnas de fecha |
| "El modelo no contesta" | `/health` dice si Ollama está arriba y si el modelo está descargado |
| Respuestas erráticas | Un modelo más grande (14b) antes que tocar el prompt |

Cada respuesta incluye el SQL exacto que se ejecutó. Ante un número dudoso,
eso es lo primero que hay que leer — y la razón por la que el módulo nunca
pide que se le crea.

---

## 9. Lista de comprobación antes de producción

- [ ] La conexión usa un rol de solo lectura (`/health` sin advertencias)
- [ ] `BI_INCLUDE_TABLES` nombra explícitamente lo consultable
- [ ] Las columnas sensibles están en `BI_HIDDEN_COLUMNS` **y** fuera del `GRANT`
- [ ] Hay autenticación delante del endpoint (sección 6)
- [ ] El puerto del backend no está publicado hacia fuera
- [ ] `BI_ROW_LIMIT` y `BI_SQL_TIMEOUT_MS` ajustados al tamaño real de la base
- [ ] Probada la consulta destructiva del paso 7, con el conteo verificado
- [ ] `python -m pytest` pasa en el ambiente de despliegue
- [ ] Copia de seguridad de la base al día — el módulo solo lee, pero la
      lista de comprobación existe para el día que algo falle de todas formas
