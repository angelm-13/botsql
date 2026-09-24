# Cómo probarlo

Tres formas, de la más simple a la más representativa de producción. Elija
según qué quiera comprobar.

| # | Forma | Necesita | Prueba |
|---|---|---|---|
| A | Sin Docker | Python (+ Node opcional) | Que el módulo funciona en esta máquina |
| B | Un contenedor Docker | Docker | Que la imagen de demostración funciona igual, aislada |
| C | Docker Compose completo | Docker + una base PostgreSQL | Que el despliegue real —nginx, proxy, base externa— funciona |

Las tres están **verificadas en esta sesión**, no solo escritas: los
resultados exactos de cada comprobación están al final de este documento.

---

## A. Sin Docker (la más rápida para iterar)

```bash
cd modulo_bi
```

**Windows:** doble clic en `demo.bat` · **Linux/macOS:** `./demo.sh`

Abre `http://localhost:5001`. Guion completo de qué preguntar en
[DEMOSTRACION.md](DEMOSTRACION.md).

---

## B. Un contenedor Docker

Prueba que la aplicación funciona empaquetada, sin nada instalado en la
máquina salvo Docker.

```bash
cd modulo_bi
docker build -f Dockerfile.demo -t bi-demo .
docker run --rm -p 5001:5001 bi-demo
```

Abre `http://localhost:5001`. `Ctrl+C` para detenerlo; `--rm` limpia el
contenedor solo.

**Para comprobar que responde correctamente sin abrir el navegador:**

```bash
curl -s localhost:5001/api/v1/bi/health | python -m json.tool

curl -s -X POST localhost:5001/api/v1/bi/query \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"hazme un dashboard"}' | python -m json.tool

# La barrera de seguridad: esto debe devolver HTTP 403.
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:5001/api/v1/bi/query \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"borra todas las ventas"}'
```

---

## C. Docker Compose completo, contra PostgreSQL real

Esta es la que de verdad prueba el despliegue: nginx haciendo de proxy,
backend con gunicorn, y una base **externa** de verdad — no SQLite. Sirve
para validar antes de tocar la base de un cliente.

### C1. Levante una base de prueba (o use la suya)

Si no tiene una PostgreSQL a mano, cree una temporal:

```bash
docker run -d --name pg-prueba \
  -e POSTGRES_USER=erp -e POSTGRES_PASSWORD=erp -e POSTGRES_DB=erp \
  -p 5432:5432 postgres:16-alpine
```

Cárguela con un par de tablas de ejemplo:

```bash
docker exec -i pg-prueba psql -U erp -d erp <<'SQL'
CREATE TABLE clientes (id serial primary key, nombre text, ciudad text);
CREATE TABLE ventas (id serial primary key, fecha date,
  id_cliente int references clientes(id), total numeric(12,2));
INSERT INTO clientes (nombre, ciudad) VALUES ('Cliente A','CDMX'),('Cliente B','Monterrey');
INSERT INTO ventas (fecha, id_cliente, total) VALUES
  ('2026-01-15',1,1200.50), ('2026-02-10',2,850.00), ('2026-03-05',1,430.25);

CREATE ROLE bi_lector LOGIN PASSWORD 'lector123';
GRANT CONNECT ON DATABASE erp TO bi_lector;
GRANT USAGE ON SCHEMA public TO bi_lector;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_lector;
SQL
```

Esto es exactamente lo que dice [DESPLIEGUE.md §1](DESPLIEGUE.md#1-antes-de-nada-el-rol-de-solo-lectura)
para un despliegue real — pruébelo aquí primero, sobre datos que no importan.

### C2. Configure y levante el compose

```bash
cp .env.example .env
```

Edite `.env` y ponga:

```
BI_DATABASE_URL=postgresql+psycopg2://bi_lector:lector123@host.docker.internal:5432/erp
```

(En Linux, si `host.docker.internal` no resuelve, use la IP del host o
conecte `pg-prueba` a la red del compose:
`docker network connect modulo_bi_default pg-prueba` después del siguiente
paso.)

```bash
docker compose up -d --build
```

### C3. Verifique

```bash
curl -s localhost:8080/api/v1/bi/health | python -m json.tool
```

Debe decir `"conecta": true`, `"motor": "postgresql"` y `"advertencias": []`
— vacío es la prueba de que está usando `bi_lector` y no un superusuario.

```bash
# El esquema real, con la llave foranea detectada:
curl -s "localhost:8080/api/v1/bi/schema?ddl=1" | python -m json.tool

# La interfaz, por el proxy de nginx:
curl -s -o /dev/null -w '%{http_code}\n' localhost:8080/
```

Sin un modelo configurado, `/query` responde `503` con
`error.tipo: "modelo_no_disponible"` en vez de un error genérico — es el
comportamiento correcto: se nota la diferencia entre "no hay modelo" y "algo
se rompió". Con Ollama arriba (`BI_OLLAMA_URL` en el `.env`), pregunte de
verdad.

### C4. Limpie

```bash
docker compose down
docker rm -f pg-prueba
```

---

## Resultados de la verificación hecha en esta sesión

Para que quien lea esto sepa exactamente qué se comprobó y qué no.

**Imagen de demostración (forma B).** Construida y corrida. `id` dentro del
contenedor confirma el usuario sin privilegios (`uid=10001`, no root). La
interfaz sirvió en `/` con `HTTP 200`, `/health` reportó `ok`, un tablero
completo devolvió 5 widgets con datos reales, y la petición destructiva
devolvió `HTTP 403`. Verificado además en un navegador real, no solo con
`curl`.

**Compose completo (forma C), contra PostgreSQL 16 real.** Las tres imágenes
compilaron. El stack completo respondió desde fuera del contenedor, por el
proxy de nginx: `/health` con `"motor": "postgresql"` y `advertencias: []`;
el esquema extraído mostró la tabla `ventas` con `id_cliente` marcado
`FK -> clientes.id`; una consulta con `JOIN` agrupando por ciudad devolvió
`{'CDMX': 1630.75, 'Monterrey': 850.0}` — la suma correcta de los datos
sembrados; un `DELETE FROM ventas` inyectado directamente (saltándose
cualquier cortesía del modelo) fue rechazado por el validador con motivo
`no_es_lectura`; y conectándose con `psql` como `bi_lector` directamente, sin
pasar por la aplicación, un `INSERT` dio `permission denied` — la barrera
que de verdad importa, confirmada en la base, no solo en el código.

**Un defecto real encontrado y corregido en el proceso**: `backend/Dockerfile`
fijaba `psycopg2-binary==2.9.9`, que no tiene rueda precompilada para
Python 3.13 — el build fallaba con `pg_config executable not found`. Subido a
`2.9.13` (sí tiene rueda) y agregado `libpq-dev`/`gcc` como red de seguridad
para el día que una plataforma distinta tampoco tenga rueda, purgados en la
misma capa para no dejarlos en la imagen final. Confirmado después: la imagen
final importa `psycopg2` y `pymysql` sin problema y pesa 511 MB.

**Lo que no se probó**: el perfil `con-modelo` del compose (Ollama dentro del
mismo stack) y el despliegue sin Docker con `gunicorn` a mano (sección 5 de
`DESPLIEGUE.md`) — ambos están escritos pero no ejecutados en esta sesión.
