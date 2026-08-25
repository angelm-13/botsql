# Migraciones del Módulo Restaurante

> ⚠️ **Estado: no enganchadas.** Los archivos de Alembic están copiados en
> `database/migrations/restaurante/versions/`, pero este repo no tiene un
> entorno de Alembic para ellos (`alembic.ini` / `env.py`), y el core
> versiona su schema con archivos `.sql` planos. Los comandos
> `flask db ...` de más abajo **no funcionan todavía**: primero hay que
> decidir cuál de los dos mecanismos gobierna las tablas del restaurante.
> El resto de este documento describe el contenido de las migraciones y
> cómo se usaban en el proyecto original.

Las migraciones del restaurante están en `database/migrations/restaurante/versions/`.

## Estructura

El restaurante usa **Flask-Migrate + Alembic** para versionado de schema, mientras que tyakxa_tny usa **migraciones SQL puras**.

```
database/migrations/
├── restaurante/
│   └── versions/
│       ├── dc4363ab55f3_baseline_esquema_ya_existente_creado_.py
│       ├── 1bf4aa90e648_add_indices_and_non_negative_check_.py
│       └── e039e46192a6_add_demo_config_table.py
└── *.sql (Migraciones de tyakxa_tny)
```

## Aplicar Migraciones del Restaurante

### Opción 1: Usando Flask-Migrate (Recomendado)

```bash
cd backend
flask db upgrade
```

Esto aplicará todas las migraciones de Alembic, incluyendo las del restaurante.

### Opción 2: Script Manual

Las migraciones generan SQL que puede ser ejecutado manualmente en PostgreSQL:

```bash
python backend/init_db.py  # Inicializa schema inicial del restaurante
```

## Migraciones Incluidas

### 1. `dc4363ab55f3_baseline_esquema_ya_existente_creado_.py`
- **Descripción**: Schema base del restaurante (todas las tablas y relaciones)
- **Tablas creadas**:
  - user, waiter, table, visit, order, order_item
  - dish, category, guisado
  - invoice, invoice_item
  - inventory_item, recipe_item, inventory_movement
  - cash_session
  - audit_log
  - company, pac_config
  - reservation, login_attempt, rate_limit_hit
  - demo_config
- **Características**:
  - Foreign keys con CASCADE DELETE
  - Índices en columnas críticas (status, foreign keys)
  - Soft deletes con `is_active` boolean
  - Timestamp columns (created_at, updated_at)

### 2. `1bf4aa90e648_add_indices_and_non_negative_check_.py`
- **Descripción**: Índices de performance y CHECK constraints
- **Cambios**:
  - Índices adicionales en columnas de búsqueda frecuente
  - CHECK constraints para garantizar montos no-negativos:
    - tip_amount, discount_amount, tax_amount
    - received_amount, cash_amount
    - price, production_cost, quantity, unit_price
  - Garantiza integridad de datos financieros

### 3. `e039e46192a6_add_demo_config_table.py`
- **Descripción**: Tabla singleton para configuración de modo freemium
- **Características**:
  - `demo_config`: Singleton table (máx 1 fila)
  - Almacena timestamp de expiración y límites de freemium
  - Controla acceso a features premium del restaurante

## Integración con tyakxa_tny

El restaurante usa **la misma instancia de base de datos PostgreSQL** que tyakxa_tny.

**Configuración en `.env`**:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/tyakxa
```

Ambos sistemas (tyakxa_tny y restaurante) leen/escriben la misma BD.

## Rollback

Para revertir migraciones del restaurante:

```bash
cd backend
flask db downgrade -1  # Revierte la última migración
```

O especificar una revisión específica:

```bash
flask db downgrade e039e46192a6
```

## Crear Nueva Migración

Si se modifica un modelo del restaurante (`backend/app/restaurante/models/entities.py`):

```bash
cd backend
flask db migrate -m "Descripción del cambio"  # Genera nueva migración
flask db upgrade  # Aplica la migración
```

## Nota Importante

Las migraciones del restaurante se aplican **automáticamente** al iniciar el servicio si están pendientes. No es necesario ejecutarlas manualmente en producción si se usa Flask-Migrate.

Sin embargo, en ambientes con **gunicorn + múltiples workers**, solo aplica **UNA vez al inicio**:

```bash
# En el entrypoint o healthcheck:
flask db upgrade
gunicorn -w 4 ...
```
