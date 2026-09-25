# Procedimiento completo

De cero a un módulo de BI funcionando sobre la base de un proyecto nuevo.
Cada paso dice **qué hacer**, **cómo comprobar que salió bien** y **qué hacer
si no**. Los tiempos son de una máquina de escritorio normal con GPU.

| Parte | Cuándo se hace | Tiempo |
|---|---|---|
| A. Probarlo aislado | Una vez, para conocerlo | 5 min |
| B. Conectarlo a una base real | Por cada proyecto | 30–60 min |
| C. Afinar qué ve el modelo | Iterativo, los primeros días | 1–2 h |
| D. Integrarlo a la aplicación | Si va dentro de un ERP existente | 2–4 h |
| E. Ponerlo en producción | Una vez por despliegue | 1 h |

---

## Parte A — Probarlo aislado (5 min, sin base ni modelo)

Sirve para ver de qué se trata antes de tocar nada de un cliente.

```bash
git clone <url-del-repositorio> modulo_bi
cd modulo_bi/backend
pip install -r requirements.txt
python demo.py
```

En otra terminal:

```bash
cd modulo_bi/frontend
npm install
npm run dev
```

Abra `http://localhost:5173` y pruebe las cuatro preguntas de ejemplo, más
`borra todas las ventas`.

**Cómo comprobar que salió bien.** El dashboard muestra 5 widgets (2 tarjetas,
línea, pastel, barras); la pregunta destructiva devuelve un aviso de rechazo y
no una gráfica; el encabezado marca *Base: ok* y *Modelo: ok*.

**Qué es lo que está viendo.** `demo.py` detecta solo si hay un Ollama real
disponible (`ollama serve` + el modelo descargado) y lo usa por omisión: en
ese caso ya se le puede preguntar cualquier cosa, no solo las cuatro de
ejemplo -- verificado con tres preguntas libres que devolvieron los mismos
números, al centavo, que una consulta escrita a mano. Sin GPU, cuente 60-100
segundos por pregunta (medido, no estimado).

Sin un modelo real a mano, cae solo a uno **simulado** que devuelve JSON fijo
para esas cuatro preguntas y dice honestamente cuando una no está cubierta.
Sirve igual para probar el módulo -- validación, ejecución, dibujo --, solo
que ahí lo que se prueba es el módulo, no el modelo.

---

## Parte B — Conectarlo a una base real (30–60 min)

### B1. Levantar el modelo

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b
ollama serve
```

Comprobación: `curl -s localhost:11434/api/tags` lista el modelo.

### B2. Crear el rol de solo lectura

**No se salte este paso ni "por ahora".** Las instrucciones por motor están en
[DESPLIEGUE.md §1](DESPLIEGUE.md#1-antes-de-nada-el-rol-de-solo-lectura).

Comprobación:

```sql
-- Conectado como bi_lector, esto tiene que FALLAR:
CREATE TABLE prueba_de_permisos (x int);
```

Si no falla, el rol está mal y todo lo demás pierde su red de seguridad.

### B3. Apuntar el módulo a la base

```bash
cd backend
export BI_DATABASE_URL="postgresql+psycopg2://bi_lector:...@host:5432/erp"
python app.py
```

Comprobación:

```bash
curl -s localhost:5001/api/v1/bi/health | python -m json.tool
```

`base_de_datos.conecta: true`, `modelo.disponible: true`, `advertencias: []`.

**Si `advertencias` menciona un superusuario**, vuelva a B2: está conectando
con un rol que puede escribir.

### B4. Mirar lo que ve el modelo — **el paso que la gente se salta**

```bash
curl -s "localhost:5001/api/v1/bi/schema?ddl=1" | python -c "import json,sys; print(json.load(sys.stdin)['ddl'])"
```

Léalo entero. Es literalmente el texto que se le inyecta al modelo, y el 80 %
de las respuestas malas se explican aquí. Pregúntese:

- ¿Está la tabla que la gente va a consultar? Si no, `BI_EXCLUDE_TABLES` la
  filtró o `BI_MAX_TABLES` la cortó.
- ¿Se ven las llaves foráneas como `-- FK -> clientes.id`? Sin ellas el modelo
  inventa los JOIN.
- ¿Aparece alguna columna sensible? Agréguela a `BI_HIDDEN_COLUMNS` **ahora**.
- ¿Dice `AVISO: el esquema se truncó`? Suba `BI_MAX_TABLES` o, mejor, use
  lista blanca.

### B5. Primera pregunta real

```bash
curl -s localhost:5001/api/v1/bi/query -H 'Content-Type: application/json' \
  -d '{"prompt":"¿cuántos registros hay en total?"}' | python -m json.tool
```

**Lea el `sql` de la respuesta y verifique el número a mano** contra una
consulta escrita por usted. Un SQL que compila, corre y devuelve el número
equivocado es el peor resultado posible, porque nadie lo nota.

### B6. Comprobar la barrera

```bash
curl -s localhost:5001/api/v1/bi/query -H 'Content-Type: application/json' \
  -d '{"prompt":"borra todos los registros de ventas"}'
```

Y después, en la base: el conteo de filas de esa tabla **no cambió**. No se
conforme con que la respuesta diga que la rechazó — compruebe el dato.

---

## Parte C — Afinar qué ve el modelo (iterativo)

Es donde está la diferencia entre "a veces acierta" y "se puede usar".

### C1. Pase a lista blanca

```bash
BI_INCLUDE_TABLES=ventas,ventas_detalle,clientes,productos
```

Menos tablas = prompt más corto = respuestas más rápidas y menos JOIN
inventados. Empiece por las cuatro o cinco sobre las que la gente realmente
pregunta, no por todas.

### C2. Encienda los valores de ejemplo

```bash
BI_SAMPLE_VALUES=1
```

Es la mejora de precisión más grande por el menor esfuerzo. Sin esto el modelo
escribe `WHERE estatus = 'pagada'` cuando la base guarda `'PAGADO'`; con esto
ve los valores reales de cada columna categórica. Cuesta unas consultas más al
arrancar la caché de esquema.

### C3. Ponga comentarios en las columnas ambiguas

El módulo los lee del catálogo y los inyecta en el DDL:

```sql
COMMENT ON COLUMN ventas.total IS 'Importe con IVA. Para venta neta use subtotal.';
COMMENT ON COLUMN ventas.estatus IS 'Solo cuenta como venta si es FACTURADA o PAGADA.';
```

Esto es lo que el esquema **no** dice y el modelo no puede adivinar. Una
columna mal entendida produce un número creíble y equivocado.

### C4. Exponga vistas en lugar de tablas

Si "venta" significa `invoice` con ciertos filtros, no le pida al modelo que
los recuerde en cada consulta: hornéelos en una vista y exponga solo las
vistas (`BI_INCLUDE_TABLES=v_*`). Es además donde se incrusta el filtro por
inquilino o por proyecto.

### C5. Lleve una lista de preguntas reales

Anote las preguntas que la gente hace de verdad, con la respuesta correcta
verificada a mano. Esa lista es lo que le permite comparar dos modelos, o
decidir si un cambio de configuración mejoró o empeoró las cosas. Sin ella,
"parece que ahora responde mejor" es una opinión.

---

## Parte D — Integrarlo a una aplicación existente (2–4 h)

Solo si el módulo va dentro de un ERP que ya tiene sesiones y permisos.

1. Copie `backend/bi/` al proyecto (no importa nada de fuera: es autónomo).
2. Registre el blueprint con los tres ganchos —`contexto`, `gancho_sql`,
   `relaciones`— como muestra [DESPLIEGUE.md §6](DESPLIEGUE.md#6-autenticación-lo-que-este-módulo-no-hace).
3. Póngalo detrás del decorador de sesión que ya use la aplicación.
4. Copie los componentes de `frontend/src/components/` o consuma la API desde
   su propio frontend: el contrato de la respuesta está en
   `frontend/src/types.ts`.

**Regla de permisos.** El módulo no debe poder leer nada que ese usuario no
pudiera ver por la interfaz normal. Se consigue con `relaciones` (qué vistas)
y con `gancho_sql` (qué filas dentro de ellas). Si su aplicación ya tiene una
función de "¿este usuario puede leer esta entidad?", reúsela — no escriba una
segunda, porque dos se separan en la tercera migración.

---

## Parte E — Ponerlo en producción (1 h)

1. Recorra la **lista de comprobación** de
   [DESPLIEGUE.md §9](DESPLIEGUE.md#9-lista-de-comprobación-antes-de-producción).
2. `cd backend && python -m pytest` en el ambiente de despliegue (74 pruebas).
3. Despliegue (Docker Compose o gunicorn + nginx, §4 y §5).
4. Repita las comprobaciones B3, B5 y **B6** contra el despliegue real, no
   contra su máquina.
5. Avise a quienes lo van a usar de dos cosas: que **cada respuesta trae el SQL
   que se ejecutó**, y que un número raro se reporta con esa consulta a la
   vista.

---

## Cómo se desarrolló y verificó este módulo

Para quien tenga que mantenerlo o auditar de dónde salen las afirmaciones de
los documentos.

**Orden de construcción.** Extractor de esquema → validador de seguridad →
ejecutor → cliente del modelo → parser de la directiva → orquestador → API →
frontend → suite de pruebas. Primero lo que se puede probar sin modelo; el
modelo fue lo último en conectarse.

**Cómo se verificó cada parte.**

| Parte | Verificación |
|---|---|
| Extractor | Base SQLite con tablas de fontanería y columnas sensibles a propósito; se comprobó que quedan fuera del DDL y que las FK sí aparecen |
| Validador | 13 ataques con su motivo exacto **y** 8 consultas legítimas que no deben caer (un validador que rechaza todo es seguro e inútil) |
| Ejecutor | `Decimal`, fechas, `NaN`, columnas duplicadas; y un `INSERT` metido a la fuerza saltándose el validador, que la base tiene que rechazar |
| Parser | JSON envuelto en markdown, con prosa alrededor, con llaves dentro de literales, con `chart_type` en español |
| Frontend | Navegador real: dashboard de 5 widgets, respuesta simple, rechazo por seguridad, modo claro y oscuro, alternancia gráfica/tabla |
| Paleta | Validador de accesibilidad ejecutado, no criterio propio: seis pruebas en modo claro y oscuro |
| Gráficas | Se midió por DOM que cada rebanada del pastel empareja con su entrada de leyenda, y la altura de las barras contra el área de trazado |

**Tres defectos que solo aparecieron al verificar, no al escribir.**

1. **Animación congelada.** Las barras se dibujaban a 11 px con los ejes
   correctos. `requestAnimationFrame` se frena en una pestaña que no se está
   dibujando y la animación queda a medias. Se desactivó la animación: en un
   tablero no aporta información y sí introduce este fallo. Tras el arreglo,
   217 px sobre un área de 226.
2. **Acentos.** `"gráfico de líneas"` degradaba a tabla porque el
   emparejamiento por palabra clave no normalizaba acentos — y el modelo
   contesta en el idioma de la pregunta. Lo detectó la suite de pruebas.
3. **Literales borrados.** El validador inspecciona un "esqueleto" con los
   literales vaciados, para que `WHERE nota = 'update'` no cuente como un
   `UPDATE`. En la primera versión se ejecutaba **ese** esqueleto, así que
   `WHERE ciudad = 'CDMX'` se habría ejecutado como `WHERE ciudad = ''`: cero
   filas, sin error y sin ninguna pista. Ahora se inspecciona el esqueleto y
   se ejecuta el SQL real.

Este tercer defecto existía también en un módulo previo de otro proyecto del
que se tomó la idea del validador; se corrigió allá igual, con cuatro pruebas
de regresión nuevas.

**Lo que no se verificó**, dicho de frente: rendimiento con una base grande,
concurrencia real, construcción de las imágenes de Docker, y los motores
distintos de SQLite (el código es agnóstico y las reglas por motor están
probadas de forma unitaria, pero solo SQLite se ejecuta de verdad en la
suite). Antes de conectar a MySQL o SQL Server en serio, corra la matriz de
validación contra ese motor.
