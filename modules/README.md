# Módulos del Proyecto Tyakxa

Este directorio contiene submódulos git de diferentes proyectos que se integran como módulos dentro de la plataforma unificada.

## Estructura

### restaurante/
- **Repositorio**: https://github.com/Tyakxa/demo_restaurante.git
- **Rama**: `plantilla-base`
- **Descripción**: Sistema de gestión de restaurante incluyendo backend (Python/FastAPI) y frontend (Node.js/TypeScript)
- **Componentes**:
  - `backend/`: API REST con Python/FastAPI
  - `frontend/`: Interfaz web con React/TypeScript
  - `scripts/`: Herramientas y utilidades
  - `Docs/`: Documentación

## Actualizar submódulos

Para inicializar y descargar todos los submódulos después de clonar:

```bash
git submodule update --init --recursive
```

Para actualizar submódulos a la última versión:

```bash
git submodule update --remote
```

Para cambiar a una rama específica en un submódulo:

```bash
cd modules/restaurante
git checkout plantilla-base
cd ../..
```

## Agregar nuevos módulos

```bash
git submodule add --branch <rama> <url-repo> modules/<nombre-modulo>
git commit -m "feat: add <nombre-modulo> as submodule in modules/<nombre-modulo>"
```
