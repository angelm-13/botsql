
# Guia para proteger rutas generadas

En cada ruta REST generada, agrega decoradores despues de `@token_required`:

```python
from app.security import (
    require_create_permission,
    require_read_permission,
    require_update_permission,
    require_delete_permission,
)

@bp_invoice.route('/', methods=['POST'])
@token_required
@require_create_permission('invoice')
def create_invoice(user_data):
    ...
```

Recomendacion por metodo:

- GET list/detail: `require_read_permission(entity)`
- POST: `require_create_permission(entity)`
- PUT/PATCH: `require_update_permission(entity)`
- DELETE: `require_delete_permission(entity)`
