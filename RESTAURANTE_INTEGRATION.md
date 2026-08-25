# Integración del Módulo Restaurante en Tyakxa

Este documento describe cómo el proyecto de `demo_restaurante` fue integrado como un módulo dentro de la plataforma unificada `tyakxa_tny`, respetando la arquitectura y convenciones existentes.

## Estructura General

### Backend (Python/Flask)
```
backend/app/restaurante/
├── models/          # Entidades SQLAlchemy (mesas, órdenes, inventario, etc.)
├── routes/          # Blueprints de API (/api/restaurante/*)
├── services/        # Lógica de facturación, PDF, etc.
└── utils/           # Utilidades (auditoria, seguridad, validaciones, etc.)
```

**Prefijo de rutas:** `/api/restaurante`

Ejemplos:
- `POST /api/restaurante/auth/login` - Autenticación
- `GET /api/restaurante/menu/dishes` - Catálogo de platillos
- `POST /api/restaurante/orders/add_item` - Agregar a orden
- `GET /api/restaurante/kitchen/board` - Tablero de cocina
- `POST /api/restaurante/invoices/create` - Crear factura

### Frontend (React/TypeScript)
```
frontend/src/modules/restaurante/
├── features/        # Aplicaciones por rol (waiter, kitchen, admin)
├── components/      # Componentes compartidos
├── contexts/        # Estado global (categorías, toasts, confirmaciones)
├── services/        # Cliente API
├── types/           # Tipos TypeScript
├── styles/          # Estilos CSS específicos del restaurante
├── utils/           # Utilidades
└── i18n/            # Internacionalización
```

### Database
- Las migraciones están en `database/migrations/` junto con el resto del proyecto
- Se usa PostgreSQL
- Modelos compartidos con el resto de tyakxa_tny a través de `app.extensions.db`

## Integración Técnica

### Backend

#### 1. Importación de Blueprints
Los blueprints se importan en `backend/app/__init__.py`:

```python
from app.restaurante import blueprints_restaurante

# En create_app():
for blueprint, url_prefix in blueprints_restaurante:
    app.register_blueprint(blueprint, url_prefix=url_prefix)
```

#### 2. Ruta de Modelos
Los modelos del restaurante están en:
- `app.restaurante.models` - Clases de entidades
- Comparten la instancia de base de datos: `app.extensions.db`

#### 3. Rutas y Servicios
Todos los imports fueron adaptados para reflejar la estructura modular:
- `from app.restaurante.models import ...` - Modelos del restaurante
- `from app.restaurante.utils import ...` - Utilidades específicas
- `from app.restaurante.services import ...` - Servicios específicos
- `from app.extensions import db` - Base de datos compartida
- `from app.utils.errors import AppError` - Utilidades compartidas de tyakxa_tny (cuando sea aplicable)

### Frontend

#### 1. Rutas
El módulo de restaurante es accesible desde:
- `/restaurante/mesero/*` - Interfaz del mesero
- `/restaurante/cocina/*` - Tablero de cocina
- `/restaurante/admin/*` - Panel de administración
- `/restaurante/login` - Autenticación específica del restaurante

#### 2. Independencia de Contextos
El restaurante mantiene sus propios contextos de estado:
- `CategoriesContext` - Caché de categorías
- `ToastContext` - Notificaciones
- `ConfirmContext` - Diálogos de confirmación

#### 3. API Client
El servicio `frontend/src/modules/restaurante/services/api.ts` proporciona métodos para todas las operaciones contra `/api/restaurante/*`

## Convenciones Respetadas

### Backend (tyakxa_tny)
✅ Arquitectura MVC con blueprints de Flask
✅ Modelos SQLAlchemy con `to_dict()` para serialización
✅ Utilidades compartidas en `app.utils`
✅ Manejo de errores centralizado en `app.utils.errors`
✅ Validaciones y formateo de código (Black, isort, pycodestyle)

### Frontend (tyakxa_tny)
✅ Estructura modular por features
✅ Contextos de React para estado global
✅ Cliente API centralizado
✅ TypeScript para seguridad de tipos
✅ i18n integrado

## Migraciones de Base de Datos

Las migraciones del restaurante se encuentran en `database/migrations/versions/`:
```
dc4363ab55f3_baseline_esquema_ya_existente_creado_...
1bf4aa90e648_add_indices_and_non_negative_check_...
e039e46192a6_add_demo_config_table.py
```

Para aplicarlas:
```bash
flask db upgrade
```

## Variables de Entorno

Las variables del restaurante deben añadirse al `.env`:
```env
# Restaurante - Database
DATABASE_URL=postgresql://...

# Restaurante - JWT
JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
JWT_ACCESS_MINUTES=30

# Restaurante - Features
DEMO_MODE=false
FREEMIUM_LIMITS=false

# Restaurante - Facturación (CFDI)
PAC_PROVIDER=mock  # o 'facturama'
PAC_USER=...
PAC_PASSWORD=...
```

## Roles del Restaurante

El sistema de roles del restaurante es independiente del de tyakxa_tny:

| Rol | Acceso |
|-----|--------|
| **mesero** | Tomar órdenes, ver mesas |
| **cocina** | Ver tablero de órdenes pendientes |
| **cajero** | Cobrar, corte de caja, reportes de ventas |
| **admin** | CRUD de catálogo, inventario, configuración |
| **superadmin** | Todo + auditoría, configuración de PAC |

## Configuración Específica del Restaurante

Archivo: `backend/app/restaurante/utils/config.py`

Contiene configuración específica del dominio:
- Tiempos de preparación (guisados)
- Horarios de disponibilidad de platillos
- Configuración de horarios
- Validaciones de negocio

## Testing

```bash
# Tests del restaurante (si existen)
cd backend
python -m pytest tests/restaurante/

# Frontend tests
cd frontend
npm test
```

## Próximos Pasos

1. **Merge de i18n** - Combinar traducciones en `i18n/` si es necesario
2. **Tema compartido** - Alinear estilos con diseño system de tyakxa_tny
3. **Webhooks** - Integración con eventos de tyakxa_tny si es aplicable
4. **Reporting** - Dashboards unificados para ver datos de múltiples módulos

## Soporte

Para preguntas sobre la arquitectura del restaurante:
- Backend: `backend/app/restaurante/`
- Frontend: `frontend/src/modules/restaurante/`
- Docs: `modules/restaurante/Docs/`
