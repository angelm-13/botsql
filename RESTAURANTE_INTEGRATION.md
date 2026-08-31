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

El core usa SQLAlchemy directo (`app/models/session.py`: `sessionmaker`,
`transaction_context`); el restaurante usa Flask-SQLAlchemy (`db.Model`).
Son dos capas de sesión distintas sobre **la misma base PostgreSQL**:
`_register_restaurante()` fija `SQLALCHEMY_DATABASE_URI` con el mismo
`database_url()` que usa el core, de modo que ambas comparten base y modo
`TESTING`.

`app/extensions.py` (nuevo) expone la instancia `db` de Flask-SQLAlchemy que
importan los modelos del módulo.

## Integración Técnica

### Backend

#### 1. Importación de Blueprints
Los blueprints se importan en `backend/app/__init__.py`:

```python
from app.restaurante import blueprints_restaurante, URL_PREFIX as RESTAURANTE_PREFIX

# _register_restaurante(app), llamado desde create_app():
for blueprint, name, suffix in blueprints_restaurante:
    app.register_blueprint(blueprint, url_prefix=RESTAURANTE_PREFIX + suffix, name=name)
```

Dos detalles no obvios:

- **`name=`**: el core ya registra un blueprint llamado `auth`
  (`app/routes/auth.py`). Flask exige nombres únicos, así que los del módulo
  se registran como `restaurante_auth`, `restaurante_menu`, etc. Sin esto el
  arranque aborta con `ValueError`.
- **`suffix`**: cada blueprint traía su propio `url_prefix` en la app
  original (`/api/menu`, `/api/orders`, …). Hay que replicarlo o los 12
  blueprints colapsan sobre la misma ruta base.

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

#### 1. Rutas — PENDIENTE de montar

⚠️ El código del módulo está copiado en `frontend/src/modules/restaurante/`
pero **todavía no está montado** en el router de `frontend/src/App.jsx`.
Hasta que se monte, las pantallas del restaurante no son alcanzables.

Falta decidir cómo conviven las dos sesiones: el restaurante trae su propio
login, sus propias cookies JWT y sus propios roles (mesero/cocina/cajero/
admin/superadmin), independientes del `ProtectedRoute` y del sistema de
permisos del core.

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

Las migraciones del restaurante se encuentran en
`database/migrations/restaurante/versions/`:
```
dc4363ab55f3_baseline_esquema_ya_existente_creado_...
1bf4aa90e648_add_indices_and_non_negative_check_...
e039e46192a6_add_demo_config_table.py
```

⚠️ Estas migraciones son de Alembic y **aún no están enganchadas** a un
entorno de Alembic dentro de este repo (no hay `alembic.ini` ni `env.py`
para ellas). El core versiona su schema con archivos `.sql` planos en
`database/migrations/`. Antes de poder correr `flask db upgrade` hay que
decidir cuál de los dos mecanismos gobierna las tablas del restaurante.

## Variables de Entorno

Las variables del restaurante deben añadirse al `.env`:
```env
# Base de datos: el módulo reusa la misma URL que el core, construida a
# partir de DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME
# (ver backend/app/models/session.py::database_url).

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

Archivo: `backend/app/restaurante/config.py` (clases Config/Development/
Production/Testing heredadas del proyecto original).

Nota: `create_app()` del core no usa esas clases; sólo fija las claves que
el módulo necesita (`SQLALCHEMY_DATABASE_URI`, `JWT_SECRET_KEY`) en
`_register_restaurante()`.

## Testing

Verificación hecha hasta ahora (arranque y ruteo, con `TESTING=1`):

```bash
cd backend
python -c "import app; a=app.create_app(testing=True); print(len(list(a.url_map.iter_rules())))"
```

- 77 rutas del módulo registradas bajo `/restaurante/*`, sin colisiones de
  ruta+método.
- `GET /restaurante/demo/status` → 200; `GET /restaurante/menu/dishes` → 401
  (viva y protegida); `GET /health` del core → 200 (sin regresión).

No se ha ejecutado la suite de tests del restaurante ni se ha probado ningún
flujo contra una base de datos real.

## Próximos Pasos

Bloqueantes para que el módulo sea usable:

1. **Montar el frontend** en `frontend/src/App.jsx` y resolver la
   convivencia de las dos sesiones (login/roles propios del restaurante vs.
   `ProtectedRoute` del core).
2. **Decidir el mecanismo de migraciones** (Alembic vs. `.sql` del core) y
   aplicar el schema del restaurante a la base.
3. **Instalar las dependencias nuevas** de `backend/requirements.txt`
   (Flask-SQLAlchemy, Flask-Migrate, alembic, Flask-JWT-Extended, reportlab,
   qrcode, Pillow).
4. **Correr la suite del restaurante** contra la base integrada.

Mejoras posteriores:

5. **Merge de i18n** - Combinar traducciones en `i18n/` si es necesario
6. **Tema compartido** - Alinear estilos con el design system de tyakxa_tny
7. **Reporting** - Dashboards unificados con datos de múltiples módulos

## Soporte

Para preguntas sobre la arquitectura del restaurante:
- Backend: `backend/app/restaurante/`
- Frontend: `frontend/src/modules/restaurante/`
- Docs: `modules/restaurante/Docs/`
