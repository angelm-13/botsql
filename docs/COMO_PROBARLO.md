# Cómo probarlo

Tres formas, de la más simple a la más representativa de producción. Elija
según qué quiera comprobar.

| # | Forma | Necesita | Prueba |
|---|---|---|---|
| A | Sin Docker | Python (+ Node opcional) | Que el módulo funciona en esta máquina |
| B | Un contenedor Docker | Docker | Que la imagen de demostración funciona igual, aislada |
| C | Docker Compose completo | Docker + una base PostgreSQL | Que el despliegue real —nginx, proxy, base externa— funciona |
| D | Preguntas libres, con modelo real | Ollama | Que responde CUALQUIER pregunta con datos exactos, no solo las de un guion |

Las tres están **verificadas en esta sesión**, no solo escritas: los
resultados exactos de cada comprobación están al final de este documento.

---

## A. Sin Docker (la más rápida para iterar)

```bash
cd modulo_bi
```

**Windows:** doble clic en `demo.bat` · **Linux/macOS:** `./demo.sh`

Abre `http://localhost:8500`. Guion completo de qué preguntar en
[DEMOSTRACION.md](DEMOSTRACION.md).

---

## B. Un contenedor Docker

Prueba que la aplicación funciona empaquetada, sin nada instalado en la
máquina salvo Docker.

```bash
cd modulo_bi
docker build -f Dockerfile.demo -t bi-demo .
docker run --rm -p 8500:5001 bi-demo
```

Abre `http://localhost:8500`. `Ctrl+C` para detenerlo; `--rm` limpia el
contenedor solo.

**Para comprobar que responde correctamente sin abrir el navegador:**

```bash
curl -s localhost:8500/api/v1/bi/health | python -m json.tool

curl -s -X POST localhost:8500/api/v1/bi/query \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"hazme un dashboard"}' | python -m json.tool

# La barrera de seguridad: esto debe devolver HTTP 403.
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8500/api/v1/bi/query \
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

## D. Preguntas libres, con modelo real y datos exactos

Esta es la prueba que de verdad importa: que el módulo responde **cualquier**
pregunta —no solo las de un guion de ejemplo— traduciéndola a SQL real y
ejecutándola contra datos reales.

```bash
ollama pull qwen2.5-coder:7b     # si no lo tiene ya (unos 4.7 GB)
ollama serve                     # si no está corriendo
cd modulo_bi/backend
python demo.py
```

`demo.py` detecta el modelo solo — no hace falta ninguna variable de entorno.
El arranque dice `Modelo: qwen2.5-coder:7b (real, vía Ollama en ...)`.
Pregunte lo que se le ocurra sobre `clientes`, `productos`, `empleados` o
`ventas`. **Sin GPU, cuente 60 a 100 segundos por pregunta** — es tiempo real
medido, no una estimación.

**Para comprobar que el número es exacto y no solo "parece razonable"**,
calcule la respuesta a mano contra la misma base y compárela:

```bash
python3 -c "
import sqlite3
con = sqlite3.connect('demo_bi.db')
for fila in con.execute('SELECT su-propia-consulta-de-referencia-aqui'):
    print(fila)
"
```

Y compare contra lo que devuelve `curl -s localhost:8500/api/v1/bi/query ... | python -m json.tool` para la misma pregunta en español. El `sql` que trae la respuesta es exactamente lo que se ejecutó — léalo para saber si el modelo entendió la pregunta como usted esperaba.

---

## Resultados de la verificación hecha en esta sesión

Para que quien lea esto sepa exactamente qué se comprobó y qué no.

**Modelo real, preguntas libres (forma D) — la prueba central.** Contra
`qwen2.5-coder:7b` real vía Ollama, en CPU pura (sin GPU), tres preguntas
**nunca vistas por ningún guion**, cada una comparada contra una consulta
SQL escrita a mano sobre la misma base:

| Pregunta (tal cual, en español libre) | SQL que escribió el modelo | Resultado | Verdad de referencia |
|---|---|---|---|
| "muéstrame el importe vendido por cada uno de los empleados, de mayor a menor" | `SELECT e.nombre, SUM(v.total) FROM empleados e JOIN ventas v ... GROUP BY e.id ORDER BY ... DESC` | Ana Rivas 65791.68, Sofía Lara 61536.73, Hugo Márquez 61265.30... | **Idéntico, al centavo, en las 6 filas** |
| "que producto genero mas ingresos en febrero de 2026" | `... WHERE v.fecha BETWEEN '2026-02-01' AND '2026-02-29' GROUP BY p.nombre ORDER BY ... LIMIT 1` | Producto 18, 3798.00 | **Idéntico** |
| "cuales son los 3 clientes que mas han comprado y de que ciudad son" | `SELECT c.nombre, c.ciudad, SUM(v.total) ... GROUP BY c.id ORDER BY ... LIMIT 3` | Cliente 08/Puebla/37764.34, Cliente 10/CDMX/32521.30, Cliente 01/Monterrey/31361.29 | **Idéntico en las 3 filas y las 2 columnas de texto** |
| "cuales son los 3 productos con menos ventas y cuanto vendieron" (en el navegador) | `SELECT p.nombre, SUM(v.cantidad) ... ORDER BY total_ventas ASC LIMIT 3` | Producto 10 (44), Producto 02 (57), Producto 15 (58) | **Idéntico** -- y es un caso interesante: "ventas" es ambiguo (¿ingreso o unidades?), el modelo lo leyó como unidades, y esa lectura se ejecutó exacta. La ambigüedad del lenguaje, no el cálculo, es el riesgo real -- por eso siempre se muestra el SQL |

En esta cuarta pregunta, hecha desde el navegador, se vio ademas en vivo el
sistema de autocorreccion de ejes: el modelo propuso columnas para el eje X/Y
que no coincidian con las que la consulta devolvio, y la interfaz lo avisó
(`⚠ el eje X que propuso el modelo no existe; se usa 'nombre'`) y dibujó con
las columnas reales en vez de una gráfica en blanco.

Las cuatro tardaron entre 79 y 92 segundos de punta a punta (`ms_modelo` en la
respuesta), en CPU sin GPU. La detección automática funcionó sin ninguna
variable de entorno: el arranque de `demo.py` ya decía
`Modelo: qwen2.5-coder:7b (real, vía Ollama en ...)`. El camino de respaldo
también se probó a propósito, apuntando a un puerto de Ollama inexistente: la
demostración cayó sola al modelo simulado, con el motivo exacto impreso
(`Ollama no responde en ...`), y siguió respondiendo bien a las preguntas de
ejemplo.

**Un defecto real encontrado en el camino**: el timeout por omisión del
proveedor de Ollama era de 120s, y una pregunta real en este hardware mide
90s+ — quedaba sin margen. Subido a 240s en `bi/config.py`,
`bi/llm_provider.py`, `.env.example` y `docker-compose.yml`. Y el tag de
modelo por omisión era `qwen2.5-coder:7b-instruct`; esta máquina tenía
descargado `qwen2.5-coder:7b` (mismo modelo, tag distinto en el registro de
Ollama) — Ollama compara el tag exacto, así que la generación fallaría con
"modelo no encontrado" aunque `/health` reportara el modelo como disponible
(esa comprobación sí tolera la diferencia de tag; la generación no). Corregido
el valor por omisión en todo el código y la documentación.

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

**Lo que no se probó**: el modelo real dentro de Docker (formas B y C usaron
el modelo simulado o ningún modelo, no `qwen2.5-coder:7b` con GPU real -- solo
la forma A/D, sin Docker, se probó con el modelo real); el perfil
`con-modelo` del compose (Ollama dentro del mismo stack); un modelo más
grande que `7b`; y el despliegue sin Docker con `gunicorn` a mano (sección 5
de `DESPLIEGUE.md`).
