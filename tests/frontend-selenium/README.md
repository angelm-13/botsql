# TYAKXA tests-frontend-selenium

Genera pruebas Selenium para frontend React con login MFA, navegación, CRUD visual, responsive, accesibilidad ligera y link checking.

## Uso

```bash
cd TYAKXA_SCRIPTS/tests-frontend-selenium
python3 main.py --project "../proyect 1" --clean
cd "../proyect 1/tests/frontend-selenium"
./run_tests.sh
```

## Variables

```bash
export FRONTEND_URL=http://localhost:3000
export BACKEND_URL=http://localhost:5001
export E2E_USERNAME=admin1
export E2E_PASSWORD=Admin1234
export E2E_MFA_CODE=123456
export SELENIUM_HEADLESS=1
export SELENIUM_BROWSER=chrome
```

Recomendación: el frontend generado debe mantener `data-testid` estables en login y controles principales.
