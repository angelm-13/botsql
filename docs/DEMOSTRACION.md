# Cómo mostrarlo

Guía para enseñar el módulo funcionando: qué correr, qué preguntar y en qué
orden. Pensada para una presentación de unos diez minutos.

---

## 1. Arrancarlo

**Windows:** doble clic en `demo.bat`
**Linux / macOS:** `./demo.sh`

El script instala lo que falte, construye la interfaz la primera vez (tarda
alrededor de un minuto) y abre `http://localhost:5001`. Las siguientes veces
arranca en segundos.

A mano, si prefiere ver los pasos:

```bash
cd frontend && npm ci && npm run build     # solo la primera vez
cd ../backend && pip install -r requirements.txt
python demo.py
```

No hace falta PostgreSQL, ni Docker, ni tarjeta gráfica. La base es un archivo
SQLite que el propio script crea y llena.

---

## 2. Real por omisión — y qué pasa si no hay modelo a mano

`demo.py` detecta solo si hay un modelo real disponible y lo usa. No hace
falta ninguna variable de entorno para eso: si `ollama serve` está corriendo
y el modelo de `BI_MODEL` (por omisión `qwen2.5-coder:7b`) está descargado,
el arranque ya dice `Modelo: qwen2.5-coder:7b (real, vía Ollama en ...)` y se
puede preguntar **cualquier cosa** sobre los datos, en español libre.

Verificado de verdad, no solo escrito: tres preguntas distintas, nunca vistas
por ningún guion ("¿cuánto vendió cada empleado?", "¿qué producto generó más
ingresos en febrero?", "¿los 3 clientes que más compraron y de qué ciudad
son?") devolvieron **los mismos números, al centavo**, que una consulta
escrita a mano contra la misma base.

```bash
ollama serve                             # si no está corriendo ya
ollama pull qwen2.5-coder:7b             # una sola vez
python demo.py
```

**Sin GPU, cuente con 60 a 100 segundos por pregunta.** Es tiempo real de
generación en CPU, medido, no una estimación — la mayor parte es el modelo
escribiendo el JSON de respuesta token por token. Dígalo antes de preguntar
en vivo: un silencio de un minuto sin avisar se lee como que se colgó.

| Modo | Cuándo aparece | Qué hace |
|---|---|---|
| **Real** (por omisión) | Ollama arriba y el modelo descargado | Traduce cualquier pregunta a SQL de verdad y lo ejecuta contra la base real |
| **Simulado** (respaldo automático) | Ollama no responde, o el modelo no está descargado | Consultas fijas para las preguntas de ejemplo. El arranque explica por qué cayó aquí |

Se puede forzar el simulado aunque haya modelo real con `BI_DEMO_SCRIPTED=1`
— útil si quiere reproducir exactamente el guion de este documento sin
esperar la respuesta del modelo.

**Dígalo de frente al presentar.** En modo simulado, si su asesor escribe una
pregunta libre, el sistema responderá que esa pregunta no está en el guion —
hecho así a propósito, para no aparentar que entiende algo que no entendió.

---

## 3. La base de datos

Genérica a propósito: se parece a la de cualquier sistema comercial y no a la
de un cliente concreto.

| Tabla | Contenido |
|---|---|
| `clientes` | 12 clientes, con ciudad y segmento |
| `productos` | 18 productos, con categoría y precio |
| `empleados` | 6 personas, con puesto |
| `ventas` | ~380 operaciones a lo largo de 2026 |

Los importes llevan una tendencia de crecimiento y una estacionalidad suave,
para que la gráfica de tendencia muestre una forma real y no una línea plana.
La semilla es fija: dos personas que corran la demostración ven exactamente
los mismos números.

Además hay **dos tablas que el módulo debe ocultar** —`alembic_version` y
`user_mfa`— y **dos columnas sensibles** en `clientes`. Están ahí para poder
demostrar el filtrado, no por descuido.

---

## 4. Guion sugerido (10 minutos)

### Minuto 1 — El problema

> "Cualquiera de estas preguntas hoy requiere que alguien escriba SQL o que
> exista un reporte hecho de antemano. Esto permite preguntarlo directamente."

### Minuto 2 — Una pregunta simple

Escriba: **`¿Cuánto vendimos en total?`**

Sale una tarjeta con el importe. Despliegue **Ver SQL** y muestre la consulta.

> "Cada respuesta trae la consulta que la produjo. No pide que se le crea: si
> el número extraña, se audita leyendo esto."

### Minuto 3–4 — Una gráfica y su tabla

Escriba: **`Ventas por mes de este año`**

Sale la tendencia. Pulse **Ver tabla**.

> "Toda gráfica tiene su tabla a un clic. Es la vista accesible, y además la
> que exige la paleta de colores: se eligió midiendo el contraste y la
> separación para daltonismo, no a ojo."

### Minuto 5–6 — El tablero completo

Escriba: **`Hazme un dashboard general de ventas`**

Salen cinco widgets: dos indicadores, una tendencia, un reparto y una
comparativa.

> "El modelo decidió qué medir y cómo dibujarlo. La cuadrícula se acomoda
> sola: el indicador ocupa una columna, la gráfica dos, la tabla el ancho
> completo."

### Minuto 7–8 — La parte que importa: la seguridad

Escriba: **`Borra todas las ventas`**

> "Esto es lo que hace que se pueda conectar a una base real."

Explique las cuatro barreras (están en el informe, sección 3):

1. Validación previa: un solo enunciado, solo lectura, solo sobre lo expuesto.
2. Rol de base de datos con permiso únicamente de lectura.
3. Transacción de solo lectura, con tiempo máximo.
4. Tope de filas al traerlas.

> "Y ninguna depende de que la anterior funcione."

### Minuto 8b — Que pregunte él mismo

Si tiene modelo real, este es el momento que de verdad convence: pídale a su
asesor que escriba **su propia pregunta**, con sus palabras, sobre las
tablas de `clientes`, `productos`, `empleados` o `ventas` — no una de las de
ejemplo. Avise antes que puede tardar un minuto en CPU.

> "No es un guion. Pregunte lo que se le ocurra."

### Minuto 9 — Lo que el modelo puede ver

Abra `http://localhost:5001/api/v1/bi/schema?ddl=1`

> "Esto es literalmente lo que se le entrega al modelo. Las tablas internas
> del sistema no están, y las columnas sensibles tampoco: no es que estén
> ocultas, es que no existen para él."

### Minuto 10 — Cerrar

> "Es agnóstico: se conecta a la base de cualquier proyecto cambiando una
> cadena de conexión. El modelo corre local, así que ningún dato sale del
> servidor. Y está probado: 74 pruebas automatizadas, incluidas trece de
> inyección SQL."

Si hay tiempo: `cd backend && python -m pytest` delante de él. Tarda tres
segundos.

---

## 5. Preguntas que seguramente le harán

**¿Y si el modelo se equivoca en el número?**
> Puede pasar, y por eso cada respuesta trae su consulta. El módulo garantiza
> que la consulta es de solo lectura y está acotada; no puede garantizar que
> responda lo que se preguntó. Es una diferencia importante y está escrita en
> las limitaciones del informe.

**¿Cuánto cuesta?**
> Nada por uso. Todos los componentes son de código abierto y el modelo corre
> en la máquina propia. El costo es el hardware: con tarjeta gráfica responde
> en segundos; sin ella, medido de verdad, entre 60 y 100 segundos por
> pregunta.

**¿Se puede conectar al sistema de la empresa?**
> Sí, cambiando la cadena de conexión. Lo que hay que hacer antes está en la
> guía de despliegue: crear un usuario de solo lectura y decidir qué tablas se
> exponen. Lo recomendable es apuntarlo a una réplica de lectura.

**¿Cualquiera puede entrar a preguntar?**
> Tal como está montado en esta demostración, sí: el módulo no trae
> autenticación, a propósito, porque va dentro de una aplicación que ya tiene
> la suya. Hay tres puntos de extensión previstos para conectarlo con las
> sesiones y permisos del sistema anfitrión. Está declarado como pendiente en
> el informe.

**¿Por qué no usar ChatGPT y ya?**
> Porque habría que mandarle la estructura de la base y los resultados a un
> servidor ajeno. Aquí el modelo corre local: la pregunta, el esquema y los
> datos no salen de la máquina.

---

## 6. Si algo falla

| Síntoma | Causa y arreglo |
|---|---|
| "No se pudo contactar al servidor" | El backend no está corriendo, o está en otro puerto. Revise la ventana de la terminal. |
| La página carga sin estilos ni gráficas | La interfaz no está construida. Corra `npm ci && npm run build` dentro de `frontend/`. |
| *Modelo: sin conexión* en el encabezado | Solo en modo real: Ollama no está corriendo, o falta `ollama pull`. En modo simulado debe decir *ok*. |
| Responde "esa pregunta no está en el guion" | Está en modo simulado y la pregunta no es una de las de ejemplo. Es el comportamiento correcto. |
| El puerto 5001 está ocupado | `BI_PORT=5005 python demo.py` y abra ese puerto. |

Para dejarlo listo antes de la presentación: arránquelo una vez, haga las
cinco preguntas del guion y ciérrelo. Así la interfaz queda construida y el
arranque del día es inmediato.
