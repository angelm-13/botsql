# Datasets de prueba

| Dataset | Qué es | Cómo se carga |
|---|---|---|
| **Sintético** | ~9,000 filas verosímiles en casi todas las tablas (nombres, RFC, importes, fechas del último año). Sirve para entornos vacíos. | `docker compose exec backend python scripts/seed_datos_prueba.py --yes` (acepta `--filas`, `--semilla`, `--solo tabla1,tabla2`). Es repetible y completa hasta el objetivo. |
| **Adser (migrado)** | Datos reales ya migrados a Postgres (productos, materiales, incidencias…). Solo en bases de desarrollo; no versionar. | Copia de otra base de desarrollo: `pg_dump --no-owner` → `psql` sobre la base destino. |
| **Preguntas del módulo BI** | 25 preguntas con tablas esperadas, filas exactas (top N), casos monetarios y casos que deben rechazarse. | `docker compose exec backend python scripts/bi_evaluar_dataset.py` |

Los datos sintéticos **nunca** deben cargarse en una base de un cliente real.
