
# TYAKXA security-permissions

Genera y documenta RBAC por entidad para ERP-CRM-SCM.

## Permisos por bitmask

- `1`: create
- `2`: read
- `4`: update
- `8`: delete
- `15`: full CRUD

## Entidades detectadas

```json
[
  "bank",
  "bank_account",
  "brand",
  "customer_supplier",
  "department",
  "entity_permission",
  "event_log",
  "field",
  "fiscal_account",
  "fiscal_record",
  "fiscal_stamp",
  "incident",
  "incident_detail",
  "incident_type",
  "inventory_status",
  "invoice",
  "invoice_material_service",
  "level",
  "location",
  "location_type",
  "material",
  "material_component",
  "movement",
  "nm_field_permission",
  "nm_incident_product",
  "nm_survey_user",
  "nm_template_task",
  "password_reset_token",
  "payroll_concept",
  "payroll_detail",
  "payroll_movement",
  "payroll_period",
  "permission",
  "product",
  "product_family",
  "product_sale_config",
  "proyect",
  "public_api_key",
  "service",
  "status",
  "subdepartment",
  "survey_multiple_answer",
  "survey_question",
  "task",
  "task_note",
  "task_type",
  "template",
  "theme",
  "ticket",
  "unit",
  "user",
  "user_mfa"
]
```

## Instalacion generada

Este grupo escribe archivos integrables en:

```text
backend/app/security/
backend/app/routes/routes_security.py
backend/app/models/entity_permission.py
backend/app/models/audit_log.py
backend/tests/test_security_permissions.py
security-permissions/sql/
security-permissions/docs/
```

## Como probar

```bash
cd TYAKXA_SCRIPTS/security-permissions
python3 main.py --project "../proyect 1" --clean
cd "../proyect 1/backend"
python -m unittest discover -s tests -p "test_security*.py"
```
