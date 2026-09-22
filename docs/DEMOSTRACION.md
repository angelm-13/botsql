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

## 2. Los dos modos, y cuál usar

| Modo | Comando | Qué hace |
|---|---|---|
| **Simulado** (por omisión) | `python demo.py` | El "modelo" devuelve consultas fijas para las preguntas de ejemplo. Funciona en cualquier máquina. |
| **Real** | `BI_DEMO_OLLAMA=1 python demo.py` | Modelo de lenguaje de verdad sobre la misma base: contesta preguntas libres. Requiere Ollama y el modelo descargado. |

**Dígalo de frente al presentar.** Si usa el modo simulado y su asesor escribe
una pregunta libre, el sistema responderá que esa pregunta no está en el
guion — está hecho así a propósito, para no aparentar que entiende algo que no
entendió. Presentarlo como "modelo real" y que eso ocurra a media
demostración es peor que explicarlo antes.

Si quiere el modo real y tiene unos minutos:

```bash
ollama pull qwen2.5-coder:7b-instruct
BI_DEMO_OLLAMA=1 python demo.py
```

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
> en segundos, sin ella en decenas de segundos.

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
