const dictionaries = {
  "es": {
    "appName": "TYAKXA Mobile",
    "common": {
      "login": "Iniciar sesión",
      "logout": "Cerrar sesión",
      "username": "Usuario",
      "password": "Contraseña",
      "mfaCode": "Código MFA",
      "mfaTitle": "Verificación MFA",
      "mfaSubtitle": "Ingresa el código de 6 dígitos",
      "verify": "Verificar código",
      "loading": "Cargando...",
      "save": "Guardar",
      "cancel": "Cancelar",
      "create": "Crear",
      "edit": "Editar",
      "delete": "Eliminar",
      "search": "Buscar",
      "empty": "No hay registros",
      "retry": "Reintentar",
      "newRecord": "Nuevo registro",
      "mfaHelp": "Ingresa el código de 6 dígitos de tu app.",
      "secureAccess": "Acceso seguro ERP-CRM-SCM",
      "dashboard": "Inicio",
      "loginTitle": "Acceso seguro",
      "loginSubtitle": "Ingresa tus credenciales",
      "submitLogin": "Iniciar sesión",
      "signIn": "Entrar",
      "confirmDelete": "¿Eliminar este registro?",
      "mfaRequired": "Se requiere MFA",
      "invalidCredentials": "Credenciales inválidas",
      "networkError": "Error de conexión",
      "validationFailed": "Revisa los campos marcados"
    },
    "menu": {
      "user": "User",
      "user_mfa": "User Mfa",
      "payroll_period": "Payroll Period",
      "payroll_detail": "Payroll Detail",
      "payroll_concept": "Payroll Concept",
      "payroll_movement": "Payroll Movement",
      "customer_supplier": "Customer Supplier",
      "proyect": "Proyect",
      "bank": "Bank",
      "bank_account": "Bank Account",
      "invoice": "Invoice",
      "invoice_material_service": "Invoice Material Service",
      "product_family": "Product Family",
      "incident_type": "Incident Type",
      "incident": "Incident",
      "incident_detail": "Incident Detail",
      "brand": "Brand",
      "unit": "Unit",
      "material": "Material",
      "material_component": "Material Component",
      "movement": "Movement",
      "location_type": "Location Type",
      "location": "Location",
      "product": "Product",
      "nm_incident_product": "Nm Incident Product",
      "task": "Task",
      "task_note": "Task Note",
      "ticket": "Ticket",
      "fiscal_account": "Fiscal Account",
      "fiscal_stamp": "Fiscal Stamp",
      "fiscal_record": "Fiscal Record",
      "service": "Service",
      "status": "Status",
      "theme": "Theme",
      "department": "Department",
      "subdepartment": "Subdepartment",
      "level": "Level",
      "field": "Field",
      "permission": "Permission",
      "nm_field_permission": "Nm Field Permission",
      "event_log": "Event Log",
      "task_type": "Task Type",
      "template": "Template",
      "nm_template_task": "Nm Template Task",
      "survey_question": "Survey Question",
      "survey_multiple_answer": "Survey Multiple Answer",
      "nm_survey_user": "Nm Survey User",
      "entity_permission": "Entity Permission",
      "inventory_status": "Inventory Status",
      "product_sale_config": "Product Sale Config",
      "public_api_key": "Public Api Key"
    },
    "fields": {
      "user": {
        "date_born": "Date Born",
        "date_start": "Date Start",
        "email": "Email",
        "first_name": "First Name",
        "id_permission": "Id Permission",
        "full_name": "Full Name",
        "id_proyect": "Id Proyect",
        "last_name_father": "Last Name Father",
        "last_name_mother": "Last Name Mother",
        "national_id": "National Id",
        "password": "Password",
        "principal_phone": "Principal Phone",
        "secundary_phone": "Secundary Phone",
        "ssn": "Ssn",
        "supervisor": "Supervisor",
        "base_salary": "Base Salary"
      },
      "user_mfa": {
        "id_user": "Id User",
        "secret": "Secret",
        "secret_iv": "Secret Iv",
        "enabled": "Enabled",
        "failed_attempts": "Failed Attempts",
        "locked_until": "Locked Until",
        "last_used_at": "Last Used At",
        "backup_codes": "Backup Codes",
        "created_at": "Created At",
        "updated_at": "Updated At"
      },
      "payroll_period": {
        "period_start": "Period Start",
        "period_end": "Period End",
        "payment_date": "Payment Date",
        "id_status": "Id Status"
      },
      "payroll_detail": {
        "id_payroll_period": "Id Payroll Period",
        "id_user": "Id User",
        "gross_salary": "Gross Salary",
        "total_earnings": "Total Earnings",
        "total_deductions": "Total Deductions",
        "net_pay": "Net Pay"
      },
      "payroll_concept": {
        "payroll_code": "Payroll Code",
        "payroll_concept_description": "Payroll Concept Description",
        "type": "Type",
        "is_taxable": "Is Taxable",
        "is_imss": "Is Imss"
      },
      "payroll_movement": {
        "id_payroll_detail": "Id Payroll Detail",
        "id_payroll_concept": "Id Payroll Concept",
        "amount": "Amount"
      },
      "customer_supplier": {
        "postal_code": "Postal Code",
        "name": "Name",
        "title": "Title",
        "contact_name": "Contact Name",
        "phone": "Phone",
        "email": "Email",
        "web_site": "Web Site",
        "street": "Street",
        "number_ext": "Number Ext",
        "number_int": "Number Int",
        "neighborhood": "Neighborhood",
        "city": "City",
        "geographic_state": "Geographic State",
        "fiscal_type": "Fiscal Type",
        "last_fiscal_certification_date": "Last Fiscal Certification Date",
        "tax_id": "Tax Id"
      },
      "proyect": {
        "id_customer_supplier": "Id Customer Supplier",
        "leader": "Leader",
        "proyect_description": "Proyect Description",
        "title": "Title",
        "proyect_status": "Proyect Status"
      },
      "bank": {
        "bank_name": "Bank Name"
      },
      "bank_account": {
        "id_bank": "Id Bank",
        "bank_account_description": "Bank Account Description",
        "branch": "Branch",
        "type": "Type",
        "ordinary_interest": "Ordinary Interest",
        "moratorium_interest": "Moratorium Interest",
        "anuality": "Anuality",
        "reimbursement": "Reimbursement"
      },
      "invoice": {
        "date_emision": "Date Emision",
        "date_expiration": "Date Expiration",
        "subtotal": "Subtotal",
        "tax": "Tax",
        "total": "Total",
        "invoice_status": "Invoice Status",
        "payment_method": "Payment Method",
        "note": "Note",
        "id_customer_supplier": "Id Customer Supplier",
        "fiscal_reference": "Fiscal Reference",
        "serie_csd": "Serie Csd",
        "internationalization": "Internationalization",
        "currency": "Currency",
        "type_exchange_rate": "Type Exchange Rate",
        "tax_certification_supplier": "Tax Certification Supplier",
        "fiscal_certify_serie": "Fiscal Certify Serie"
      },
      "invoice_material_service": {
        "id_invoice": "Id Invoice",
        "id_material": "Id Material",
        "id_service": "Id Service",
        "invoice_material_service_description": "Invoice Material Service Description",
        "max_requirement_date": "Max Requirement Date",
        "is_directly_related_to_product_service_creation": "Is Directly Related To Product Service Creation",
        "id_authorized": "Id Authorized",
        "id_status": "Id Status",
        "id_buyer": "Id Buyer",
        "id_customer_supplier": "Id Customer Supplier",
        "gross_price": "Gross Price",
        "quantity": "Quantity",
        "id_product": "Id Product",
        "line_type": "Line Type",
        "tax_applicable": "Tax Applicable",
        "line_tax": "Line Tax"
      },
      "product_family": {
        "product_family_description": "Product Family Description",
        "type": "Type"
      },
      "incident_type": {
        "incident_type_description": "Incident Type Description"
      },
      "incident": {
        "incident_date": "Incident Date",
        "id_incident_type": "Id Incident Type",
        "note": "Note",
        "id_user": "Id User",
        "incident_status": "Incident Status",
        "close_date": "Close Date",
        "id_lider": "Id Lider"
      },
      "incident_detail": {
        "id_incident_type": "Id Incident Type",
        "incident_detail_name": "Incident Detail Name",
        "incident_detail_description": "Incident Detail Description"
      },
      "brand": {
        "brand_description": "Brand Description"
      },
      "unit": {
        "unit_code": "Unit Code",
        "unit_name": "Unit Name",
        "unit_category": "Unit Category",
        "is_active": "Is Active",
        "symbol": "Symbol",
        "measurement_system": "Measurement System"
      },
      "material": {
        "material_description": "Material Description",
        "id_unit": "Id Unit",
        "id_brand": "Id Brand",
        "id_product_family": "Id Product Family"
      },
      "material_component": {
        "id_material": "Id Material",
        "id_component": "Id Component",
        "relation": "Relation",
        "id_unit": "Id Unit"
      },
      "movement": {
        "id_fiscal_account": "Id Fiscal Account",
        "date": "Date",
        "type": "Type",
        "amount": "Amount",
        "currency": "Currency",
        "type_exchange_rate": "Type Exchange Rate"
      },
      "location_type": {
        "location_type_description": "Location Type Description"
      },
      "location": {
        "id_location_type": "Id Location Type",
        "location_description": "Location Description",
        "id_location_reference": "Id Location Reference"
      },
      "product": {
        "id_invoice": "Id Invoice",
        "id_location": "Id Location",
        "id_material": "Id Material",
        "gross_price": "Gross Price",
        "color": "Color",
        "is_directly_related_to_product_service": "Is Directly Related To Product Service",
        "product_status": "Product Status",
        "path_imagen": "Path Imagen",
        "product_code": "Product Code",
        "note": "Note",
        "descripcion": "Descripcion",
        "cantidad": "Cantidad",
        "id_marca": "Id Marca",
        "id_familia": "Id Familia"
      },
      "nm_incident_product": {
        "id_incident": "Id Incident",
        "id_product": "Id Product",
        "note": "Note",
        "quantity": "Quantity",
        "close_date": "Close Date"
      },
      "task": {
        "task_code": "Task Code",
        "start_date": "Start Date",
        "duration": "Duration",
        "type": "Type",
        "owner": "Owner",
        "analyst": "Analyst",
        "dependency": "Dependency",
        "leader": "Leader",
        "validation": "Validation",
        "task_description": "Task Description",
        "estimated_effort": "Estimated Effort",
        "task_status": "Task Status",
        "fase": "Fase",
        "priority": "Priority",
        "title": "Title",
        "id_proyect": "Id Proyect"
      },
      "task_note": {
        "date": "Date",
        "id_task": "Id Task",
        "task_note_description": "Task Note Description"
      },
      "ticket": {
        "ticket_description": "Ticket Description",
        "ticket_status": "Ticket Status",
        "note": "Note"
      },
      "fiscal_account": {
        "fiscal_account_description": "Fiscal Account Description",
        "balance": "Balance",
        "id_fiscal_account_reference": "Id Fiscal Account Reference"
      },
      "fiscal_stamp": {
        "concept": "Concept",
        "reviewed_by": "Reviewed By",
        "authorized_by": "Authorized By",
        "auxiliar": "Auxiliar",
        "num_policy": "Num Policy"
      },
      "fiscal_record": {
        "fiscal_record_name": "Fiscal Record Name",
        "id_fiscal_account": "Id Fiscal Account",
        "amount": "Amount",
        "type": "Type",
        "id_fiscal_stamp": "Id Fiscal Stamp"
      },
      "service": {
        "service_description": "Service Description",
        "average_time_cost": "Average Time Cost",
        "id_brand": "Id Brand"
      },
      "status": {
        "status_description": "Status Description",
        "category": "Category",
        "is_terminal": "Is Terminal",
        "sort_order": "Sort Order"
      },
      "theme": {
        "tenant_id": "Tenant Id",
        "primary_color": "Primary Color",
        "secondary_color": "Secondary Color",
        "background_color": "Background Color",
        "text_color": "Text Color",
        "highlight_color": "Highlight Color",
        "success_color": "Success Color",
        "error_color": "Error Color"
      },
      "department": {
        "department_description": "Department Description"
      },
      "subdepartment": {
        "subdepartment_description": "Subdepartment Description",
        "id_department": "Id Department"
      },
      "level": {
        "level_description": "Level Description"
      },
      "field": {
        "table_name": "Table Name",
        "field_name": "Field Name"
      },
      "permission": {
        "authorized_by": "Authorized By",
        "permission_description": "Permission Description",
        "id_department": "Id Department",
        "id_subdepartment": "Id Subdepartment",
        "id_level": "Id Level"
      },
      "nm_field_permission": {
        "id_field": "Id Field",
        "id_permission": "Id Permission",
        "control_type": "Control Type"
      },
      "event_log": {
        "table_name": "Table Name",
        "field_name": "Field Name",
        "action": "Action",
        "before_value": "Before Value",
        "after_value": "After Value"
      },
      "task_type": {
        "task_type_description": "Task Type Description",
        "task_type_scope": "Task Type Scope",
        "task_type_limit": "Task Type Limit"
      },
      "template": {
        "template_description": "Template Description"
      },
      "nm_template_task": {
        "id_task": "Id Task",
        "id_template": "Id Template"
      },
      "survey_question": {
        "question": "Question",
        "question_type": "Question Type",
        "owner": "Owner"
      },
      "survey_multiple_answer": {
        "id_survey_question": "Id Survey Question",
        "survey_answer_description": "Survey Answer Description",
        "score": "Score"
      },
      "nm_survey_user": {
        "id_survey_question": "Id Survey Question",
        "id_survey_multiple_answer": "Id Survey Multiple Answer",
        "id_user": "Id User",
        "nm_survey_user_description": "Nm Survey User Description",
        "score": "Score",
        "status": "Status"
      },
      "entity_permission": {
        "id_permission": "Id Permission",
        "entity_name": "Entity Name",
        "control_type": "Control Type"
      },
      "inventory_status": {
        "inventory_status_code": "Inventory Status Code",
        "inventory_status_description": "Inventory Status Description",
        "color": "Color",
        "entity_scope": "Entity Scope",
        "flow_scope": "Flow Scope",
        "id_department": "Id Department",
        "id_subdepartment": "Id Subdepartment",
        "id_minimum_level": "Id Minimum Level",
        "is_active": "Is Active",
        "is_terminal": "Is Terminal",
        "visible_to_other_departments": "Visible To Other Departments",
        "sort_order": "Sort Order"
      },
      "product_sale_config": {
        "id_product": "Id Product",
        "margin_percent": "Margin Percent",
        "manual_price": "Manual Price",
        "id_inventory_status": "Id Inventory Status",
        "is_active": "Is Active"
      },
      "public_api_key": {
        "label": "Label",
        "key_hash": "Key Hash",
        "key_prefix": "Key Prefix",
        "allowed_domains": "Allowed Domains",
        "rate_limit_per_min": "Rate Limit Per Min",
        "is_active": "Is Active",
        "last_used_at": "Last Used At"
      }
    }
  },
  "en": {
    "appName": "TYAKXA Mobile",
    "common": {
      "login": "Sign in",
      "logout": "Sign out",
      "username": "Username",
      "password": "Password",
      "mfaCode": "MFA Code",
      "mfaTitle": "MFA Verification",
      "mfaSubtitle": "Enter the 6-digit code",
      "verify": "Verify Code",
      "loading": "Loading...",
      "save": "Save",
      "cancel": "Cancel",
      "create": "Create",
      "edit": "Edit",
      "delete": "Delete",
      "search": "Search",
      "empty": "No records",
      "retry": "Retry",
      "newRecord": "New Record",
      "mfaHelp": "Enter the 6-digit code from your app.",
      "secureAccess": "Secure Access ERP-CRM-SCM",
      "dashboard": "Home",
      "loginTitle": "Secure Access",
      "loginSubtitle": "Enter your credentials",
      "submitLogin": "Sign in",
      "signIn": "Sign In",
      "confirmDelete": "Delete this record?",
      "mfaRequired": "MFA required",
      "invalidCredentials": "Invalid credentials",
      "networkError": "Connection error",
      "validationFailed": "Check the highlighted fields"
    },
    "menu": {
      "user": "User",
      "user_mfa": "User Mfa",
      "payroll_period": "Payroll Period",
      "payroll_detail": "Payroll Detail",
      "payroll_concept": "Payroll Concept",
      "payroll_movement": "Payroll Movement",
      "customer_supplier": "Customer Supplier",
      "proyect": "Proyect",
      "bank": "Bank",
      "bank_account": "Bank Account",
      "invoice": "Invoice",
      "invoice_material_service": "Invoice Material Service",
      "product_family": "Product Family",
      "incident_type": "Incident Type",
      "incident": "Incident",
      "incident_detail": "Incident Detail",
      "brand": "Brand",
      "unit": "Unit",
      "material": "Material",
      "material_component": "Material Component",
      "movement": "Movement",
      "location_type": "Location Type",
      "location": "Location",
      "product": "Product",
      "nm_incident_product": "Nm Incident Product",
      "task": "Task",
      "task_note": "Task Note",
      "ticket": "Ticket",
      "fiscal_account": "Fiscal Account",
      "fiscal_stamp": "Fiscal Stamp",
      "fiscal_record": "Fiscal Record",
      "service": "Service",
      "status": "Status",
      "theme": "Theme",
      "department": "Department",
      "subdepartment": "Subdepartment",
      "level": "Level",
      "field": "Field",
      "permission": "Permission",
      "nm_field_permission": "Nm Field Permission",
      "event_log": "Event Log",
      "task_type": "Task Type",
      "template": "Template",
      "nm_template_task": "Nm Template Task",
      "survey_question": "Survey Question",
      "survey_multiple_answer": "Survey Multiple Answer",
      "nm_survey_user": "Nm Survey User",
      "entity_permission": "Entity Permission",
      "inventory_status": "Inventory Status",
      "product_sale_config": "Product Sale Config",
      "public_api_key": "Public Api Key"
    },
    "fields": {
      "user": {
        "date_born": "Date Born",
        "date_start": "Date Start",
        "email": "Email",
        "first_name": "First Name",
        "id_permission": "Id Permission",
        "full_name": "Full Name",
        "id_proyect": "Id Proyect",
        "last_name_father": "Last Name Father",
        "last_name_mother": "Last Name Mother",
        "national_id": "National Id",
        "password": "Password",
        "principal_phone": "Principal Phone",
        "secundary_phone": "Secundary Phone",
        "ssn": "Ssn",
        "supervisor": "Supervisor",
        "base_salary": "Base Salary"
      },
      "user_mfa": {
        "id_user": "Id User",
        "secret": "Secret",
        "secret_iv": "Secret Iv",
        "enabled": "Enabled",
        "failed_attempts": "Failed Attempts",
        "locked_until": "Locked Until",
        "last_used_at": "Last Used At",
        "backup_codes": "Backup Codes",
        "created_at": "Created At",
        "updated_at": "Updated At"
      },
      "payroll_period": {
        "period_start": "Period Start",
        "period_end": "Period End",
        "payment_date": "Payment Date",
        "id_status": "Id Status"
      },
      "payroll_detail": {
        "id_payroll_period": "Id Payroll Period",
        "id_user": "Id User",
        "gross_salary": "Gross Salary",
        "total_earnings": "Total Earnings",
        "total_deductions": "Total Deductions",
        "net_pay": "Net Pay"
      },
      "payroll_concept": {
        "payroll_code": "Payroll Code",
        "payroll_concept_description": "Payroll Concept Description",
        "type": "Type",
        "is_taxable": "Is Taxable",
        "is_imss": "Is Imss"
      },
      "payroll_movement": {
        "id_payroll_detail": "Id Payroll Detail",
        "id_payroll_concept": "Id Payroll Concept",
        "amount": "Amount"
      },
      "customer_supplier": {
        "postal_code": "Postal Code",
        "name": "Name",
        "title": "Title",
        "contact_name": "Contact Name",
        "phone": "Phone",
        "email": "Email",
        "web_site": "Web Site",
        "street": "Street",
        "number_ext": "Number Ext",
        "number_int": "Number Int",
        "neighborhood": "Neighborhood",
        "city": "City",
        "geographic_state": "Geographic State",
        "fiscal_type": "Fiscal Type",
        "last_fiscal_certification_date": "Last Fiscal Certification Date",
        "tax_id": "Tax Id"
      },
      "proyect": {
        "id_customer_supplier": "Id Customer Supplier",
        "leader": "Leader",
        "proyect_description": "Proyect Description",
        "title": "Title",
        "proyect_status": "Proyect Status"
      },
      "bank": {
        "bank_name": "Bank Name"
      },
      "bank_account": {
        "id_bank": "Id Bank",
        "bank_account_description": "Bank Account Description",
        "branch": "Branch",
        "type": "Type",
        "ordinary_interest": "Ordinary Interest",
        "moratorium_interest": "Moratorium Interest",
        "anuality": "Anuality",
        "reimbursement": "Reimbursement"
      },
      "invoice": {
        "date_emision": "Date Emision",
        "date_expiration": "Date Expiration",
        "subtotal": "Subtotal",
        "tax": "Tax",
        "total": "Total",
        "invoice_status": "Invoice Status",
        "payment_method": "Payment Method",
        "note": "Note",
        "id_customer_supplier": "Id Customer Supplier",
        "fiscal_reference": "Fiscal Reference",
        "serie_csd": "Serie Csd",
        "internationalization": "Internationalization",
        "currency": "Currency",
        "type_exchange_rate": "Type Exchange Rate",
        "tax_certification_supplier": "Tax Certification Supplier",
        "fiscal_certify_serie": "Fiscal Certify Serie"
      },
      "invoice_material_service": {
        "id_invoice": "Id Invoice",
        "id_material": "Id Material",
        "id_service": "Id Service",
        "invoice_material_service_description": "Invoice Material Service Description",
        "max_requirement_date": "Max Requirement Date",
        "is_directly_related_to_product_service_creation": "Is Directly Related To Product Service Creation",
        "id_authorized": "Id Authorized",
        "id_status": "Id Status",
        "id_buyer": "Id Buyer",
        "id_customer_supplier": "Id Customer Supplier",
        "gross_price": "Gross Price",
        "quantity": "Quantity",
        "id_product": "Id Product",
        "line_type": "Line Type",
        "tax_applicable": "Tax Applicable",
        "line_tax": "Line Tax"
      },
      "product_family": {
        "product_family_description": "Product Family Description",
        "type": "Type"
      },
      "incident_type": {
        "incident_type_description": "Incident Type Description"
      },
      "incident": {
        "incident_date": "Incident Date",
        "id_incident_type": "Id Incident Type",
        "note": "Note",
        "id_user": "Id User",
        "incident_status": "Incident Status",
        "close_date": "Close Date",
        "id_lider": "Id Lider"
      },
      "incident_detail": {
        "id_incident_type": "Id Incident Type",
        "incident_detail_name": "Incident Detail Name",
        "incident_detail_description": "Incident Detail Description"
      },
      "brand": {
        "brand_description": "Brand Description"
      },
      "unit": {
        "unit_code": "Unit Code",
        "unit_name": "Unit Name",
        "unit_category": "Unit Category",
        "is_active": "Is Active",
        "symbol": "Symbol",
        "measurement_system": "Measurement System"
      },
      "material": {
        "material_description": "Material Description",
        "id_unit": "Id Unit",
        "id_brand": "Id Brand",
        "id_product_family": "Id Product Family"
      },
      "material_component": {
        "id_material": "Id Material",
        "id_component": "Id Component",
        "relation": "Relation",
        "id_unit": "Id Unit"
      },
      "movement": {
        "id_fiscal_account": "Id Fiscal Account",
        "date": "Date",
        "type": "Type",
        "amount": "Amount",
        "currency": "Currency",
        "type_exchange_rate": "Type Exchange Rate"
      },
      "location_type": {
        "location_type_description": "Location Type Description"
      },
      "location": {
        "id_location_type": "Id Location Type",
        "location_description": "Location Description",
        "id_location_reference": "Id Location Reference"
      },
      "product": {
        "id_invoice": "Id Invoice",
        "id_location": "Id Location",
        "id_material": "Id Material",
        "gross_price": "Gross Price",
        "color": "Color",
        "is_directly_related_to_product_service": "Is Directly Related To Product Service",
        "product_status": "Product Status",
        "path_imagen": "Path Imagen",
        "product_code": "Product Code",
        "note": "Note",
        "descripcion": "Descripcion",
        "cantidad": "Cantidad",
        "id_marca": "Id Marca",
        "id_familia": "Id Familia"
      },
      "nm_incident_product": {
        "id_incident": "Id Incident",
        "id_product": "Id Product",
        "note": "Note",
        "quantity": "Quantity",
        "close_date": "Close Date"
      },
      "task": {
        "task_code": "Task Code",
        "start_date": "Start Date",
        "duration": "Duration",
        "type": "Type",
        "owner": "Owner",
        "analyst": "Analyst",
        "dependency": "Dependency",
        "leader": "Leader",
        "validation": "Validation",
        "task_description": "Task Description",
        "estimated_effort": "Estimated Effort",
        "task_status": "Task Status",
        "fase": "Fase",
        "priority": "Priority",
        "title": "Title",
        "id_proyect": "Id Proyect"
      },
      "task_note": {
        "date": "Date",
        "id_task": "Id Task",
        "task_note_description": "Task Note Description"
      },
      "ticket": {
        "ticket_description": "Ticket Description",
        "ticket_status": "Ticket Status",
        "note": "Note"
      },
      "fiscal_account": {
        "fiscal_account_description": "Fiscal Account Description",
        "balance": "Balance",
        "id_fiscal_account_reference": "Id Fiscal Account Reference"
      },
      "fiscal_stamp": {
        "concept": "Concept",
        "reviewed_by": "Reviewed By",
        "authorized_by": "Authorized By",
        "auxiliar": "Auxiliar",
        "num_policy": "Num Policy"
      },
      "fiscal_record": {
        "fiscal_record_name": "Fiscal Record Name",
        "id_fiscal_account": "Id Fiscal Account",
        "amount": "Amount",
        "type": "Type",
        "id_fiscal_stamp": "Id Fiscal Stamp"
      },
      "service": {
        "service_description": "Service Description",
        "average_time_cost": "Average Time Cost",
        "id_brand": "Id Brand"
      },
      "status": {
        "status_description": "Status Description",
        "category": "Category",
        "is_terminal": "Is Terminal",
        "sort_order": "Sort Order"
      },
      "theme": {
        "tenant_id": "Tenant Id",
        "primary_color": "Primary Color",
        "secondary_color": "Secondary Color",
        "background_color": "Background Color",
        "text_color": "Text Color",
        "highlight_color": "Highlight Color",
        "success_color": "Success Color",
        "error_color": "Error Color"
      },
      "department": {
        "department_description": "Department Description"
      },
      "subdepartment": {
        "subdepartment_description": "Subdepartment Description",
        "id_department": "Id Department"
      },
      "level": {
        "level_description": "Level Description"
      },
      "field": {
        "table_name": "Table Name",
        "field_name": "Field Name"
      },
      "permission": {
        "authorized_by": "Authorized By",
        "permission_description": "Permission Description",
        "id_department": "Id Department",
        "id_subdepartment": "Id Subdepartment",
        "id_level": "Id Level"
      },
      "nm_field_permission": {
        "id_field": "Id Field",
        "id_permission": "Id Permission",
        "control_type": "Control Type"
      },
      "event_log": {
        "table_name": "Table Name",
        "field_name": "Field Name",
        "action": "Action",
        "before_value": "Before Value",
        "after_value": "After Value"
      },
      "task_type": {
        "task_type_description": "Task Type Description",
        "task_type_scope": "Task Type Scope",
        "task_type_limit": "Task Type Limit"
      },
      "template": {
        "template_description": "Template Description"
      },
      "nm_template_task": {
        "id_task": "Id Task",
        "id_template": "Id Template"
      },
      "survey_question": {
        "question": "Question",
        "question_type": "Question Type",
        "owner": "Owner"
      },
      "survey_multiple_answer": {
        "id_survey_question": "Id Survey Question",
        "survey_answer_description": "Survey Answer Description",
        "score": "Score"
      },
      "nm_survey_user": {
        "id_survey_question": "Id Survey Question",
        "id_survey_multiple_answer": "Id Survey Multiple Answer",
        "id_user": "Id User",
        "nm_survey_user_description": "Nm Survey User Description",
        "score": "Score",
        "status": "Status"
      },
      "entity_permission": {
        "id_permission": "Id Permission",
        "entity_name": "Entity Name",
        "control_type": "Control Type"
      },
      "inventory_status": {
        "inventory_status_code": "Inventory Status Code",
        "inventory_status_description": "Inventory Status Description",
        "color": "Color",
        "entity_scope": "Entity Scope",
        "flow_scope": "Flow Scope",
        "id_department": "Id Department",
        "id_subdepartment": "Id Subdepartment",
        "id_minimum_level": "Id Minimum Level",
        "is_active": "Is Active",
        "is_terminal": "Is Terminal",
        "visible_to_other_departments": "Visible To Other Departments",
        "sort_order": "Sort Order"
      },
      "product_sale_config": {
        "id_product": "Id Product",
        "margin_percent": "Margin Percent",
        "manual_price": "Manual Price",
        "id_inventory_status": "Id Inventory Status",
        "is_active": "Is Active"
      },
      "public_api_key": {
        "label": "Label",
        "key_hash": "Key Hash",
        "key_prefix": "Key Prefix",
        "allowed_domains": "Allowed Domains",
        "rate_limit_per_min": "Rate Limit Per Min",
        "is_active": "Is Active",
        "last_used_at": "Last Used At"
      }
    }
  }
};

let currentLanguage = 'es';

export function setLanguage(lang) { 
  currentLanguage = dictionaries[lang] ? lang : 'es'; 
}

export function t(key, fallback = key) {
  const parts = key.split('.');
  let value = dictionaries[currentLanguage];
  for (const part of parts) {
    value = value?.[part];
  }
  return value || fallback;
}
