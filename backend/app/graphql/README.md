# TYAKXA api-graphql

Genera la capa GraphQL del backend usando `.tyakxa-generator/project_definition.json`.

## Ruta

Colocar estos scripts en:

```text
TYAKXA_SCRIPTS/api-graphql/
```

## Ejecutar

```bash
cd TYAKXA_SCRIPTS/api-graphql
python3 main.py --project "../proyect 1" --clean
```

## Salida

```text
proyect 1/backend/app/graphql/
  __init__.py
  types.py
  inputs.py
  pagination.py
  filters.py
  queries.py
  mutations.py
  schema.py
  routes.py
```

## Integración Flask

En `backend/app/__init__.py` registra el blueprint:

```python
from app.graphql.routes import bp_graphql
app.register_blueprint(bp_graphql)
```

## Dependencias backend

```text
graphene>=3.3
Flask-Babel>=4.0.0
```

## Prueba rápida

```bash
curl -X POST http://localhost:${BACKEND_PORT:-5001}/graphql   -H 'Content-Type: application/json'   -d '{"query":"{ __schema { queryType { name } } }"}'
```
