# Plan de validación

Dos cosas distintas se validan por separado, y confundirlas es el error de
método más común al montar un text-to-SQL:

| Qué se valida | Cómo | Dónde |
|---|---|---|
| **El módulo** — que dado un JSON del modelo, haga lo correcto | Determinista, con `ProveedorDeGuion` | `backend/tests/` |
| **El modelo** — que produzca ese JSON | Estadístico, contra Ollama real | `evaluar.py` (abajo) |

Si se mezclan, una prueba roja no dice si se rompió el código o si el modelo
tuvo un mal día. Las pruebas del módulo **no llaman a ningún modelo**.

## Matriz de casos

Ejecutable: `cd backend && python -m pytest`. Estado actual: **74 pasan**.

| # | Caso | Pregunta | Se espera | Prueba |
|---|------|----------|-----------|--------|
| 1 | KPI simple | "ventas totales" | `kpi_card`, 1 fila, valor numérico (no cadena: el `NUMERIC` llega como `Decimal`) | `test_caso_1_kpi_simple` |
| 2 | Tendencia temporal | "ventas por mes" | `line`, 12 filas, eje X = `mes`, serie ordenada | `test_caso_2_tendencia_temporal` |
| 3 | Ranking top N | "top productos" | `bar`, 5 filas, orden descendente real | `test_caso_3_ranking_top_n` |
| 4 | Distribución | "importe por ciudad" | `pie`, 5 partes que **suman el total** verificado contra la base | `test_caso_4_distribucion_por_categoria` |
| 5 | Dashboard completo | "hazme un dashboard" | `is_dashboard`, 5 widgets, 2 KPI + línea + pastel + barras, todos con su SQL | `test_caso_5_dashboard_completo` |
| 6 | Inyección SQL | "borra todas las ventas" | HTTP 403, cero widgets, **conteo de filas idéntico antes y después** | `test_caso_6_peticion_destructiva` |
| 6b | Inyección encubierta | dashboard con un `DELETE` colado entre widgets | Cae ese widget y solo ese; los otros 5 responden; nada se escribe | `test_caso_6_bis_...` |

El caso 6b es el que de verdad importa: el 6 depende de que el modelo se
niegue, que es una cortesía, no una barrera. El 6b asume que el modelo
colaboró con el ataque y verifica que el módulo lo detenga igual.

### Batería de seguridad (`test_security.py`)

13 ataques que deben caer, con su motivo exacto:
enunciado encadenado · escritura directa · `UPDATE` directo · CTE que escribe ·
`SELECT INTO` · tabla filtrada por política · tabla inexistente · catálogo del
sistema · columna sensible por nombre · `UNION` hacia lo filtrado · `ATTACH` ·
consulta sin origen · vacío.

Más 5 funciones peligrosas específicas por motor (`pg_read_file`, `pg_sleep`,
`load_file`, `xp_cmdshell`, `load_extension`) — lo inofensivo en un motor es
una fuga en otro.

8 consultas legítimas que **no** deben caer: literales que dicen `update` o
`drop`, la función `REPLACE`, CTE de lectura, join de tres tablas, subconsulta,
comentario al final, punto y coma final. Un validador que rechaza todo es
seguro y también inútil.

## Evaluar un modelo real

Las pruebas de arriba no dicen nada sobre si `qwen2.5-coder:7b` acierta. Para
eso, la misma base de demostración con el modelo de verdad:

```bash
cd backend
BI_DEMO_OLLAMA=1 python demo.py
```

Se pregunta lo mismo que cubre la matriz y se compara contra el guion de
`demo.py`, que hace de respuesta de referencia. Lo que hay que medir por
pregunta:

1. ¿Devolvió JSON con la forma del contrato? (lo dice `error.tipo = directiva_invalida`)
2. ¿El SQL pasó el validador? (`error.tipo = sql_rechazado` y su motivo)
3. ¿El SQL corrió? (`error.tipo = fallo_de_ejecucion`)
4. ¿El número es **correcto**? — esto no lo puede juzgar el módulo, hay que
   compararlo contra una consulta escrita a mano.

El cuarto es el único que importa de verdad y el único que no se puede
automatizar sin una respuesta de referencia por pregunta. Un SQL que compila,
corre y devuelve el número equivocado es el peor resultado posible, porque
nadie lo nota.

## Lo que este plan NO cubre, dicho de frente

- **Rendimiento con una base grande.** Toda la suite corre sobre SQLite con
  360 filas. El comportamiento del `statement_timeout` en PostgreSQL bajo
  carga real no está probado aquí.
- **Concurrencia.** La caché de esquema tiene candado y se probó su lógica,
  no su comportamiento con N peticiones simultáneas.
- **El frontend.** Se verificó a mano en navegador (dashboard de 5 widgets,
  respuesta de una sola gráfica, rechazo por seguridad, modo claro y oscuro,
  alternancia gráfica/tabla, emparejamiento color↔categoría en el pastel).
  No hay pruebas automatizadas de interfaz.
- **Otros motores.** El código es agnóstico y las reglas por motor están
  probadas de forma unitaria, pero solo SQLite se ejecuta de verdad en la
  suite. Antes de conectar a MySQL o SQL Server en serio, correr la matriz
  contra ese motor.
