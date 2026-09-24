# Módulo de BI — Text-to-SQL y visualización dinámica

Módulo **agnóstico y desacoplado**: se conecta a la base de cualquier proyecto
(ERP, CRM, POS, SCM) inyectando una cadena de conexión, extrae el DDL en
tiempo de ejecución y traduce preguntas en lenguaje natural a SQL, datos y
directivas de visualización. 100% open source; el modelo corre local con
Ollama.

No importa nada del proyecto anfitrión: `grep -r "import app\." bi/` no
devuelve nada. Se puede copiar la carpeta `backend/bi/` a otro repositorio tal
cual.

## Estado

| Paso | Entregable | Estado |
|------|-----------|--------|
| 1 | `bi/schema_extractor.py` — extractor dinámico de esquema | ✅ hecho y verificado |
| 2 | `app.py` + `bi/{security,executor,directive,service,api,llm_provider,prompt}.py` | ✅ hecho y verificado |
| 3 | Frontend React + TS (`BIChat`, `DynamicChartViewer`, `DashboardGrid`) | ✅ hecho, compilado y visto en navegador |
| 4 | Matriz de validación y casos de prueba | ✅ hecha, 74 pruebas en verde |

## Documentación

| Documento | Para qué |
|---|---|
| [docs/COMO_PROBARLO.md](docs/COMO_PROBARLO.md) | Tres formas de probarlo ahora mismo (sin Docker, un contenedor, compose contra PostgreSQL real), con los resultados exactos de la verificación |
| [docs/DEMOSTRACION.md](docs/DEMOSTRACION.md) | Cómo mostrarlo: arranque, guion de 10 minutos, preguntas frecuentes y qué hacer si falla |
| [docs/PROCEDIMIENTO.md](docs/PROCEDIMIENTO.md) | Paso a paso de cero a funcionando, con cómo comprobar cada paso |
| [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md) | Puesta en producción: rol de solo lectura, Docker, autenticación, lista de comprobación |
| [docs/PLAN_DE_VALIDACION.md](docs/PLAN_DE_VALIDACION.md) | Matriz de pruebas y lo que **no** cubre |

## Verlo funcionando: un comando, una URL

**Windows:** doble clic en `demo.bat` · **Linux/macOS:** `./demo.sh`

Instala lo que falte, construye la interfaz la primera vez y abre
`http://localhost:5001` — interfaz y API en el mismo puerto. No hace falta
PostgreSQL, ni Docker, ni tarjeta gráfica.

Siembra una base SQLite genérica (clientes, productos, empleados, ~380 ventas
de 2026) y usa un modelo **simulado** que responde a las preguntas de ejemplo,
incluida `borra todas las ventas` para ver la barrera de seguridad. Ante una
pregunta que no cubre, lo dice: no aparenta entender lo que no entendió.

Para preguntas libres, con el modelo real:

```bash
ollama pull qwen2.5-coder:7b-instruct
cd backend && BI_DEMO_OLLAMA=1 python demo.py
```

Para presentarlo a alguien, hay un guion de diez minutos en
[docs/DEMOSTRACION.md](docs/DEMOSTRACION.md).

## Arranque rápido

```bash
cd modulo_bi/backend
pip install -r requirements.txt

export BI_DATABASE_URL="postgresql+psycopg2://bi_lector:clave@host:5432/erp"
export BI_MODEL="qwen2.5-coder:7b-instruct"
python app.py
```

```bash
curl -s localhost:5001/api/v1/bi/query -H 'Content-Type: application/json' \
  -d '{"prompt":"dame un dashboard de ventas del último trimestre"}'
```

## Endpoints

| Método | Ruta | Para qué |
|--------|------|----------|
| POST | `/api/v1/bi/query` | `{"prompt": "..."}` → SQL, datos y directiva de gráfica |
| GET | `/api/v1/bi/schema` | Qué ve el modelo (`?ddl=1`, `?refresh=1`) |
| GET | `/api/v1/bi/health` | Base, modelo, caché y advertencias de despliegue |

La respuesta siempre trae `widgets[]`, aunque sea uno solo, para que el
frontend tenga una sola forma que dibujar. Cada widget lleva su propio `ok`:
**un widget que falla no tumba al dashboard**.

## Variables de entorno

| Variable | Por omisión | Para qué |
|----------|-------------|----------|
| `BI_DATABASE_URL` | — | Cadena de conexión (gana sobre `DATABASE_URL`) |
| `BI_OLLAMA_URL` | `http://localhost:11434` | Dónde vive el modelo |
| `BI_MODEL` | `qwen2.5-coder:7b-instruct` | Modelo a usar |
| `BI_INCLUDE_TABLES` | — | Lista blanca de patrones; manda sobre la negra |
| `BI_EXCLUDE_TABLES` | fontanería típica | Lista negra de patrones |
| `BI_HIDDEN_COLUMNS` | `password*`, `*token*`, … | Columnas que no llegan ni al DDL |
| `BI_MAX_TABLES` | `60` | Tope de relaciones en el prompt |
| `BI_ROW_LIMIT` | `1000` | Tope duro de filas por consulta |
| `BI_SQL_TIMEOUT_MS` | `15000` | Reloj de cada consulta |
| `BI_SAMPLE_VALUES` | `0` | Valores de ejemplo de columnas categóricas |
| `BI_SCHEMA_TTL` | `300` | Cada cuánto se re-inspecciona la base |

## Integrarlo en una aplicación Flask existente

```python
from bi.api import crear_blueprint
from bi.config import AjustesBI
from bi.llm_provider import ProveedorOllama

app.register_blueprint(crear_blueprint(
    engine=mi_engine,                  # el Engine que ya usa la aplicación
    ajustes=AjustesBI.desde_entorno(),
    proveedor=ProveedorOllama(),
    contexto=lambda: g.user_data,      # quién pregunta, según el anfitrión
    gancho_sql=fijar_alcance,          # fija el inquilino en la sesión de BD
    relaciones=vistas_del_usuario,     # qué puede leer ESE usuario
))
```

Los tres ganchos son opcionales **y son lo que separa una demo de algo
montable en producción multiinquilino**. Sin `relaciones`, cualquiera que
llegue al endpoint lee todo lo que el extractor expuso.

## Modelo de seguridad

Cuatro barreras, y ninguna basta sola:

1. **Validador** (`bi/security.py`): un solo enunciado, empieza con
   `SELECT`/`WITH`, sin palabras de escritura fuera de literales, sin
   catálogos del sistema, sin columnas ocultas, solo sobre relaciones
   expuestas, con tope de filas.
2. **Rol de base de datos**: conéctese con un usuario que solo tenga
   `GRANT SELECT`. Es la única barrera que no depende de que el código sea
   perfecto. `/health` lo reclama si detecta un superusuario.
3. **Transacción de solo lectura y reloj**, con la instrucción propia de cada
   motor (`executor.py`).
4. **Tope al traer las filas** (`fetchmany`), que funciona incluso en motores
   sin `LIMIT`.

Lo que el módulo **no** hace: autenticación. Montado suelto, el endpoint es
público. Póngalo detrás del `token_required` del anfitrión, o use `contexto`.

## Motores soportados

PostgreSQL, MySQL/MariaDB, SQLite y SQL Server, sin ramas por motor en el
extractor. Lo específico de cada uno vive en tres sitios y nada más:
`SINTAXIS_DE_LIMITE` y `acotar_tiempo()` en `schema_extractor.py`,
`PROHIBIDAS_POR_MOTOR` en `security.py`, y `_poner_solo_lectura()` en
`executor.py`.

## Frontend

`frontend/` — React 19 + TypeScript + Vite + Tailwind 4 + Recharts.

| Componente | Rol |
|---|---|
| `BIChat.tsx` | La consola: pregunta, historial, cancelación en vuelo, errores explicados |
| `DynamicChartViewer.tsx` | El único archivo que sabe de Recharts; mapea `chart_type` a la gráfica |
| `DashboardGrid.tsx` | Cuadrícula adaptable; el KPI ocupa 1 columna, la gráfica 2, la tabla 4 |
| `KPICard.tsx`, `DataTable.tsx` | Las dos formas que no son gráfica |
| `theme.ts` | Paleta validada para daltonismo en claro y oscuro, y formato de números |

Reglas de dibujo que están en el código a propósito: un solo eje Y (nunca dos
escalas), los tonos no se ciclan (más de ocho categorías se pliegan a "Otros"
en gris), leyenda solo donde el color es la identidad, sin animación de
entrada, y **toda gráfica trae su tabla a un clic** — que es la vista accesible
y además lo que exige la paleta, porque tres de sus tonos quedan bajo 3:1
contra la superficie clara.

## Pruebas

```bash
cd backend && python -m pytest
```

74 pruebas, sin red y sin modelo: extractor, validador (13 ataques + 5 funciones
peligrosas por motor + 8 consultas legítimas que no deben caer), parser de la
directiva, ejecutor y la matriz de 6 casos de punta a punta. El detalle y lo
que **no** cubre está en [docs/PLAN_DE_VALIDACION.md](docs/PLAN_DE_VALIDACION.md).

## Verificado contra una base real

Extracción dinámica (filtrado, columnas sensibles fuera del DDL, FK
detectadas, vistas incluidas), batería de 9 intentos de inyección bloqueados,
7 consultas legítimas que no dan falso positivo, y el flujo completo del
endpoint —KPI, dashboard de 4 widgets con uno malicioso rechazado, JSON
envuelto en markdown, y la negativa del modelo devolviendo 403—.
