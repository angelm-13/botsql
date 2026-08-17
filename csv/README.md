# CSVs complementarios para ERP-CRM-SCM

Supuestos aplicados:
- `entities.csv` conserva la definición física de tablas/campos.
- Estos CSVs completan navegación, funciones de negocio, vistas, bindings por cliente, cálculos, validaciones, documentos y pruebas.
- Todas las claves visibles se modelan como i18n keys; frontend/mobile resuelven textos desde catálogos.
- Backend debe emitir códigos/keys traducibles, no texto final.

Archivos:
- entities-2.csv: navegación, rutas, layout, módulos y permisos.
- entities-3.csv: funciones ERP/CRM/SCM multi-entidad y tareas Celery/GraphQL.
- entities-4.csv: tipos de vista por tabla.
- entities-5.csv: relación tabla-vista-cliente.
- calculated.csv: campos calculados.
- validations.csv: validaciones cliente/backend.
- documents.csv: documentos generables.
- document-bindings.csv: eventos/rutas/tareas de generación documental.
- tests.csv: unittest, Selenium, mobile smoke y flujos e2e.

Prueba rápida:
```bash
python - <<'PY'
import csv, glob
for p in glob.glob("*.csv"):
    with open(p, newline="", encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    print(p, len(rows), "rows")
PY
```
