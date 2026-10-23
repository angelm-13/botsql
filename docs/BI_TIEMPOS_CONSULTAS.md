# Tiempos de consulta del módulo BI (local y nube)

Medido el 2026-10-15 en el entorno `bi2` (Docker Desktop, 6 CPU, Intel i5-8400T a 1.7 GHz, sin GPU, con el equipo al 100 % de carga por otros contenedores). Modelo: `qwen2.5-coder:3b` en Ollama.

## 1. Qué se midió (local)

| Etapa | Resultado | Fuente |
|---|---|---|
| Lectura del prompt (prefill) | **~9.5 tokens/s** (2,048 tokens en 215 s) | log de Ollama |
| Generación de la respuesta (decode) | **~0.9 tokens/s** (310 tokens en ~340 s) | log de Ollama |
| Prompt original | 4,569 tokens | log de Ollama |
| Prompt tras recorte (plantilla corta, DDL compacto, sin índice de tablas) | ~2,000 tokens | cálculo `chars/3` sobre el prompt real |
| Pregunta completa, Ollama **dentro de Docker**, prompt original | **no terminó en 270 s ni en 600 s** (timeout) | 2 corridas reales |
| Pregunta completa, Ollama **nativo de Windows** (`host.docker.internal:11434`), `qwen2.5-coder:3b`, prompt recortado + 5 ejemplos | **103-137 s**, con datos correctos (8 filas en el top 8; 6 tipos de incidencia) | 2 corridas reales |
| Misma pregunta repetida (caché) | **~0 s** | UI |
| `qwen2.5-coder:1.5b` (3 hilos, en Docker) | 115-146 s pero **SQL inventado** (columnas que no existen) en 3 de 3 intentos | 3 corridas reales |
| Validación + SQL + auth + filtro por rol (modelo simulado) | respuesta inmediata (<1 s por consulta en el cliente de pruebas de Flask) | `/tmp/t4.py` |

Conclusión local: **el cuello de botella es 100 % el modelo**. Lo que más ayudó: usar el Ollama nativo (el de Docker Desktop quedaba por debajo de 1 token/s generando), recortar el prompt y **no usar el 1.5B** (más rápido pero inventa columnas). Aun así, ~2 minutos por pregunta nueva es el piso en esta CPU; una GPU o una API lo bajan a segundos (ver sección 2). Los documentos previos del equipo ya medían 60-100 s en CPU de escritorio sin carga: aquí la carga del equipo lo multiplica.

Qué se hizo para bajar el tiempo (ya aplicado):
- Plantilla del prompt reducida a la mitad y **sin las tablas inventadas de la demo anterior** (tenía columnas `id, name, sku` que no existen aquí; además de lentas inducían SQL incorrecto).
- Selección de tablas por pregunta (`schema_linking.py`): 6 tablas + 3 vecinas por FK en vez de las 60 primeras.
- DDL compacto de una línea por tabla, sin columnas de bitácora.
- Caché de preguntas repetidas (ya existía): una pregunta repetida no vuelve a pasar por el modelo.

## 2. Estimación en la nube (infraestructura)

Los números de abajo son **estimaciones**, no mediciones: no hay un entorno en la nube con modelo desplegado. Para medirlos, ejecutar `backend/scripts/bi_benchmark.py` desde un pod del mismo namespace (latencia interna) y otra vez desde fuera por el Ingress (suma la red); la diferencia es la latencia de infraestructura.

| Escenario | Latencia esperada por pregunta | Base |
|---|---|---|
| VPS actual (k3s, 3.8 GB/nodo, sin GPU) | No cabe un 7B; un 3B es peor que lo medido aquí | `docs/BI_COSTO_BENEFICIO_MODELOS.md` |
| Instancia con GPU de 24 GB (p. ej. L4) con 7B-14B | segundos (decenas de tokens/s en decode) | estimación; verificar con el benchmark |
| API administrada (Haiku/Sonnet/Gemini Flash) | 2-8 s según salida | estimación; verificar con el benchmark |

Lo que **no** cambia entre local y nube: validación, ejecución SQL con `statement_timeout` de 15 s, y filtro por rol (milisegundos). Lo que sí suma en la nube: red cliente→Ingress→backend→proveedor (decenas a cientos de ms) y el arranque en frío del modelo (10-20 s si Ollama lo descarga de memoria; `keep_alive: -1` ya lo evita).

## 3. Cómo repetir la medición

```bash
# dentro del backend (o con JWT_SECRET en otro lado)
python scripts/bi_benchmark.py --url http://localhost:5001 --rol 2 > tiempos.txt
python scripts/bi_evaluar_dataset.py   # calidad: 25 preguntas del dataset
```

El benchmark pregunta cada caso dos veces (modelo y caché) como administrador y como un rol limitado, y reporta p50/p95 de modelo, SQL y total.
