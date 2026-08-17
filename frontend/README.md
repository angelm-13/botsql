# TYAKXA frontend-react generator

## Ruta recomendada

`TYAKXA_SCRIPTS/frontend-react/`

## Uso

```bash
python3 main.py --project "../proyect 1" --clean
cd "../proyect 1/frontend"
npm install
cp .env.example .env
npm run dev
```

## Entrada

Lee:

`project/.tyakxa-generator/project_definition.json`

Ese archivo debe generarse antes con `generator-core`.

## Salida

Genera una app Vite + React en:

`project/frontend/`

Incluye:

- API client centralizado
- Rutas por entidad
- Layout responsive
- CRUD por entidad
- Tabla y kanban
- Dashboard
- i18n `es/en`
- Login visual con MFA/TOTP
- Rutas protegidas y logout
- Estados loading/error/empty
