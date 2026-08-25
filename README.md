# Tyakxa - Plataforma Unificada

Una plataforma integral que unifica múltiples aplicaciones empresariales, incluyendo un sistema completo de gestión de restaurante.

## 🏗️ Arquitectura

Este es un **monorepo unificado** que integra múltiples módulos:

### Módulos Principales

1. **Restaurante** (Integrado)
   - Sistema POS completo para restaurantes
   - Gestión de mesas, órdenes, inventario
   - Integración CFDI para facturación mexicana
   - Tablero de cocina en tiempo real
   - Reportes y análisis

   📍 Ubicación: `backend/app/restaurante/` y `frontend/src/modules/restaurante/`

2. **Core de Tyakxa** (Plataforma Principal)
   - Gestión de proyectos, recursos, finanzas
   - Gestión de usuarios y permisos
   - Análisis e informes

   📍 Ubicación: `backend/app/routes/` y `frontend/src/pages/`

### Estructura del Repositorio

```
tyakxa_tny/
├── backend/
│   ├── app/
│   │   ├── restaurante/          ← Módulo integrado
│   │   │   ├── models/           - Entidades SQLAlchemy
│   │   │   ├── routes/           - Blueprints de API
│   │   │   ├── services/         - Lógica de facturación, PDF
│   │   │   └── utils/            - Utilidades específicas
│   │   ├── routes/               ← Rutas del core
│   │   ├── models/               ← Modelos del core
│   │   └── ...
│   ├── requirements.txt
│   └── init_db.py
├── frontend/
│   ├── src/
│   │   ├── modules/restaurante/  ← Módulo integrado
│   │   │   ├── features/         - Apps por rol (waiter, kitchen, admin)
│   │   │   ├── components/       - Componentes compartidos
│   │   │   ├── services/         - Cliente API
│   │   │   ├── types/            - Tipos TypeScript
│   │   │   └── contexts/         - Estado global
│   │   ├── pages/                ← Páginas del core
│   │   ├── components/           ← Componentes del core
│   │   └── ...
│   └── package.json
├── database/
│   ├── migrations/               ← Migraciones
│   │   ├── *.sql                 - Migraciones del core (tyakxa_tny)
│   │   └── restaurante/          - Migraciones del restaurante
│   └── ...
├── modules/                      ← Submódulos git
│   └── restaurante/              - Repositorio original de demo_restaurante
├── docs/
├── infra/
└── README.md
```

## 🚀 Comenzar

### Requisitos
- Python 3.11+
- Node.js 18+
- PostgreSQL 12+
- Docker & Docker Compose (opcional)

### Setup Inicial

```bash
# Backend
cd backend
pip install -r requirements.txt
flask db upgrade  # Aplicar migraciones (incluyendo restaurante)
python run.py

# Frontend
cd frontend
npm install
npm run dev
```

### Variables de Entorno

```bash
cp .env.example .env
# Editar .env con configuración local
```

## 📦 Rutas de API

### Core (tyakxa_tny)
- `/api/auth/` - Autenticación
- `/api/user/` - Gestión de usuarios
- `/api/project/` - Proyectos
- `/api/invoice/` - Facturación
- etc.

### Restaurante (Integrado)
- `/api/restaurante/auth/` - Autenticación del restaurante
- `/api/restaurante/menu/` - Catálogo de platillos
- `/api/restaurante/orders/` - Órdenes y comandas
- `/api/restaurante/tables/` - Gestión de mesas
- `/api/restaurante/kitchen/` - Tablero de cocina
- `/api/restaurante/cashier/` - Cajas y cortes
- `/api/restaurante/invoices/` - Facturación CFDI
- `/api/restaurante/inventory/` - Inventario
- `/api/restaurante/admin/` - Administración

## 📚 Documentación

- **[Integración del Restaurante](RESTAURANTE_INTEGRATION.md)** - Guía técnica de integración
- **[Migraciones de BD](database/migrations/RESTAURANTE_MIGRATIONS.md)** - Estrategia de migraciones
- **[Documentación del Restaurante](modules/restaurante/Docs/)** - Docs originales del proyecto restaurante
- **[Auditoría Técnica](AUDITORIA_TECNICA.md)** - Reporte de auditoría

## 🔄 Rama de Desarrollo

Todos los cambios se realizan en la rama **`initAngm`**:

```bash
git checkout initAngm
```

## 📋 Testing

```bash
# Backend
cd backend
python -m pytest tests/

# Frontend
cd frontend
npm test
```

## 🐳 Docker

```bash
# Desarrollo
docker-compose up -d

# Producción
docker-compose -f docker-compose.prod.yml up -d
```

## 🤝 Contribución

1. Asegurar estar en rama `initAngm`
2. Crear feature branch: `git checkout -b feature/descripcion`
3. Hacer commit: `git commit -m "feat: descripcion"`
4. Push a rama: `git push origin feature/descripcion`
5. Abrir Pull Request

## 📄 Licencia

Propiedad de Tyakxa