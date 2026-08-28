-- TYAKXA seed data
-- Note: Each INSERT has ON CONFLICT to handle idempotent seeds
BEGIN;

INSERT INTO "user" ("id_user", "created_by", "creation_date", "date_born", "date_start", "deletion_date", "email", "first_name", "id_permission", "full_name", "id_proyect", "last_name_father", "last_name_mother", "last_update_date", "national_id", "password", "principal_phone", "secundary_phone", "ssn", "supervisor", "base_salary", "hire_date", "id_status", "tax_id", "title", "user_type", "username", "puesto", "accepts_marketing")
VALUES (1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00', 'admin1@tyakxa.local', 'Admin', 1, 'test first_name', 1, 'test last_name_father', 'test last_name_mother', '2026-01-01 00:00:00', 'test national_id', '$2b$12$RxTtZtblFwu6ZsmtfNP9Meg6tYSZOCsVIZQLMe260W9seWcdrUma6', 'test principal_', 'test secundary_', 'test ssn', 1, 1, '2026-01-01 00:00:00', 1, 'test tax_id', 'test title', 'admin', 'admin1', 'sample_puesto', TRUE)
ON CONFLICT ("id_user") DO NOTHING;

INSERT INTO "user_mfa" ("id_user_mfa", "id_user", "secret", "secret_iv", "enabled", "failed_attempts", "locked_until", "last_used_at", "backup_codes", "created_at", "updated_at")
VALUES (1, 1, 'test_user', 'test_user', FALSE, 0, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '{}', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_user_mfa") DO NOTHING;

INSERT INTO "payroll_period" ("id_payroll_period", "period_start", "period_end", "payment_date", "id_status", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00', 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_payroll_period") DO NOTHING;

INSERT INTO "payroll_detail" ("id_payroll_detail", "id_payroll_period", "id_user", "gross_salary", "total_earnings", "total_deductions", "net_pay", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, 1, 1, 1, 1, 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_payroll_detail") DO NOTHING;

INSERT INTO "payroll_concept" ("id_payroll_concept", "payroll_code", "payroll_concept_description", "type", "is_taxable", "is_imss", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test title', 'test title', 'earning', TRUE, TRUE, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_payroll_concept") DO NOTHING;

INSERT INTO "payroll_movement" ("id_payroll_movement", "id_payroll_detail", "id_payroll_concept", "amount", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, 1, 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_payroll_movement") DO NOTHING;

INSERT INTO "customer_supplier" ("id_customer_supplier", "postal_code", "name", "title", "contact_name", "phone", "email", "web_site", "street", "number_ext", "number_int", "neighborhood", "city", "geographic_state", "fiscal_type", "last_fiscal_certification_date", "tax_id", "type", "id_user", "created_by", "creation_date", "last_update_date", "deletion_date", "path_logo")
VALUES (1, '00000', 'test razon_social', 'test title', 'test contact_name', 'test phone', 'contacto@example.com', 'test web_site', 'test street', '1', '1', 'test neighborhood', 'test city', 'test state', 'test fiscal_type', '2026-01-01 00:00:00', 'test tax_id', 'client', 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00', 'uploads/customer_suppliers/logos/logo.png')
ON CONFLICT ("id_customer_supplier") DO NOTHING;

INSERT INTO "proyect" ("id_proyect", "id_customer_supplier", "leader", "proyect_description", "title", "proyect_status", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, 1, 'test description', 'test title', 'test state', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_proyect") DO NOTHING;

INSERT INTO "bank" ("id_bank", "bank_name", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test bank_name', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_bank") DO NOTHING;

INSERT INTO "bank_account" ("id_bank_account", "id_bank", "bank_account_description", "branch", "type", "ordinary_interest", "moratorium_interest", "anuality", "reimbursement", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, 'test description', 'test branch', 'test type', 1, 1, 1, 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_bank_account") DO NOTHING;

INSERT INTO "invoice" ("id_invoice", "date_emision", "date_expiration", "subtotal", "tax", "total", "invoice_status", "payment_method", "note", "id_customer_supplier", "fiscal_reference", "serie_csd", "internationalization", "currency", "type_exchange_rate", "tax_certification_supplier", "fiscal_certify_serie", "certification_date", "cfdi_code", "sat_code", "sat_certification_code", "id_status", "created_by", "creation_date", "last_update_date", "deletion_date", "nombre_emisor", "lugar_expedicion", "tipo_de_comprobante", "rfc_receptor", "nombre_receptor", "regimen_fiscal_receptor", "domicilio_fiscal_receptor", "id_proveedor_de_sello", "folio_fiscal", "exportacion", "folio", "no_certificado_sat", "sello_sat", "sello_certificacion_sat", "no_certificado", "descuento", "metodo_pago", "condiciones_pago", "id_issuer_customer_supplier", "id_proyect", "apply_tax", "tax_rate", "commercial_terms")
VALUES (1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', 1, 1, 1, 'test state', 'test payment_method', 'test notes', 1, 'test fiscal_reference', 'test serie_csd', 'exported', 'test currency', 1, 1, 'test fiscal_certify_serie', '2026-01-01 00:00:00', 'test cfdi_code', 'test sat_code', 'test sat_certification_code', 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00', 'sample_nombre_emisor', 'sample_lugar_expedicion', 'factura', 'sample_rfc_receptor', 'sample_nombre_receptor', 'Empresa Moral', 'Paseos de Jerez 541, Las arboledas', 1, 'sample_folio_fiscal', 'sample_exportacion', 'sample_folio', 'sample_no_certificado_sat', 'sample_sello_sat', 'sample_sello_certificacion_sat', 'sample_no_certificado', 1, 'sample_metodo_pago', 'sample_condiciones_pago', 1, 1, TRUE, 1, 'Vigencia sujeta a disponibilidad.')
ON CONFLICT ("id_invoice") DO NOTHING;

INSERT INTO "invoice_material_service" ("id_invoice_material_service", "id_invoice", "id_material", "id_service", "invoice_material_service_description", "max_requirement_date", "is_directly_related_to_product_service_creation", "id_authorized", "id_status", "id_buyer", "id_customer_supplier", "gross_price", "quantity", "created_by", "creation_date", "last_update_date", "deletion_date", "id_product", "line_type", "tax_applicable", "line_tax", "line_total", "id_unit", "authorization_status", "authorization_note", "authorization_date")
VALUES (1, 1, 1, 1, 'test description', '2026-01-01 00:00:00', TRUE, 1, 1, 1, 1, 1, 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00', 1, 'custom', TRUE, 1, 1, 1, 'pending', 'Pendiente de revision.', '2026-01-01 00:00:00')
ON CONFLICT ("id_invoice_material_service") DO NOTHING;

INSERT INTO "product_family" ("id_product_family", "product_family_description", "type", "created_by", "creation_date", "last_update_date")
VALUES (1, 'test description', 'tool', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_product_family") DO NOTHING;

INSERT INTO "incident_type" ("id_incident_type", "incident_type_description", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test description', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_incident_type") DO NOTHING;

INSERT INTO "incident" ("id_incident", "incident_date", "id_incident_type", "note", "id_user", "incident_status", "close_date", "created_by", "creation_date", "last_update_date", "deletion_date", "id_lider")
VALUES (1, '2026-01-01 00:00:00', 1, 'test note', 1, 'test state', '2026-01-01 00:00:00', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00', 1)
ON CONFLICT ("id_incident") DO NOTHING;

INSERT INTO "incident_detail" ("id_incident_detail", "id_incident_type", "incident_detail_name", "incident_detail_description", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, 'test description', 'test description', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_incident_detail") DO NOTHING;

INSERT INTO "brand" ("id_brand", "brand_description", "created_by", "creation_date", "last_update_date")
VALUES (1, 'test description', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_brand") DO NOTHING;

INSERT INTO "unit" ("id_unit", "unit_code", "unit_name", "unit_category", "is_active", "symbol", "measurement_system", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test description', 'test description', 'test description', TRUE, 'test description', 'metric', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_unit") DO NOTHING;

INSERT INTO "material" ("id_material", "material_description", "id_unit", "id_brand", "id_product_family", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test description', 1, 1, 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_material") DO NOTHING;

INSERT INTO "material_component" ("id_material_component", "id_material", "id_component", "relation", "id_unit", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, 1, 1, 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_material_component") DO NOTHING;


INSERT INTO "location_type" ("id_location_type", "location_type_description", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test description', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_location_type") DO NOTHING;

INSERT INTO "location" ("id_location", "id_location_type", "location_description", "id_location_reference", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, 'test description', NULL, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_location") DO NOTHING;

INSERT INTO "product" ("id_product", "id_invoice", "id_location", "id_material", "gross_price", "color", "is_directly_related_to_product_service", "product_status", "path_imagen", "product_code", "note", "created_by", "creation_date", "last_update_date", "descripcion", "cantidad", "id_marca", "id_familia")
VALUES (1, 1, 1, 1, 1, 'test color', TRUE, 'test state', 'test path_imagen', 'test code', 'test note', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', 'sample_descripcion', 1, 1, 1)
ON CONFLICT ("id_product") DO NOTHING;

INSERT INTO "nm_incident_product" ("id_nm_incident_product", "id_incident", "id_product", "note", "quantity", "close_date", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, 1, 'test note', 1, '2026-01-01 00:00:00', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_nm_incident_product") DO NOTHING;

INSERT INTO "task" ("id_task", "task_code", "start_date", "duration", "type", "owner", "analyst", "dependency", "leader", "validation", "task_description", "estimated_effort", "task_status", "fase", "priority", "title", "id_proyect", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'C1', '2026-01-01 00:00:00', 1, 'business', 1, 1, 1, 1, 1, 'test description', 'test estimated_effort', 'test state', 'test fase', 'test priority', 'test titulo', 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_task") DO NOTHING;

INSERT INTO "task_note" ("id_task_note", "date", "id_task", "task_note_description", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, '2026-01-01 00:00:00', 1, 'test description', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_task_note") DO NOTHING;

INSERT INTO "ticket" ("id_ticket", "ticket_description", "ticket_status", "note", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test description', 'test state', 'test respuesta', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_ticket") DO NOTHING;

INSERT INTO "fiscal_account" ("id_fiscal_account", "fiscal_account_description", "balance", "id_fiscal_account_reference", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test description', 1, 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_fiscal_account") DO NOTHING;
INSERT INTO "movement" ("id_movement", "id_fiscal_account", "date", "type", "amount", "currency", "type_exchange_rate", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, '2026-01-01 00:00:00', 'income', 1, 'mxn', 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_movement") DO NOTHING;

INSERT INTO "fiscal_stamp" ("id_fiscal_stamp", "concept", "reviewed_by", "authorized_by", "auxiliar", "num_policy", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test concept', 1, 1, 'test auxiliar', 'test num_policy', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_fiscal_stamp") DO NOTHING;

INSERT INTO "fiscal_record" ("id_fiscal_record", "fiscal_record_name", "id_fiscal_account", "amount", "type", "id_fiscal_stamp", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test name', 1, 1, 'test type', 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_fiscal_record") DO NOTHING;

INSERT INTO "service" ("id_service", "service_description", "average_time_cost", "id_brand", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test description', 1, 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_service") DO NOTHING;

INSERT INTO "status" ("id_status", "status_description", "category", "is_terminal", "sort_order", "created_by", "creation_date", "last_update_date")
VALUES (1, 'Activo', 'system', FALSE, 'asc', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_status") DO NOTHING;

INSERT INTO "status" ("id_status", "status_description", "category", "is_terminal", "sort_order", "created_by", "creation_date", "last_update_date")
VALUES (2, 'Inactivo', 'system', TRUE, 'asc', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_status") DO NOTHING;

INSERT INTO "theme" ("id_theme", "created_by", "creation_date", "last_update_date", "deletion_date", "tenant_id", "primary_color", "secondary_color", "background_color", "text_color", "highlight_color", "success_color", "error_color")
VALUES (1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00', 1, '#0D47A1', '#0D47A1', '#0D47A1', '#0D47A1', '#0D47A1', '#0D47A1', '#0D47A1')
ON CONFLICT ("id_theme") DO NOTHING;

INSERT INTO "department" ("id_department", "department_description", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test description', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_department") DO NOTHING;

INSERT INTO "subdepartment" ("id_subdepartment", "subdepartment_description", "id_department", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test description', 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_subdepartment") DO NOTHING;

INSERT INTO "level" ("id_level", "level_description", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test description', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_level") DO NOTHING;

INSERT INTO "field" ("id_field", "created_by", "creation_date", "last_update_date", "deletion_date", "table_name", "field_name")
VALUES (1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00', 'user', 'id_user')
ON CONFLICT ("id_field") DO NOTHING;

INSERT INTO "permission" ("id_permission", "created_by", "creation_date", "last_update_date", "authorized_by", "permission_description", "id_department", "id_subdepartment", "id_level")
VALUES (1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', 1, 'admin', 1, 1, 1)
ON CONFLICT ("id_permission") DO NOTHING;

INSERT INTO "permission" ("id_permission", "created_by", "creation_date", "last_update_date", "authorized_by", "permission_description", "id_department", "id_subdepartment", "id_level")
VALUES (2, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', 1, 'gerente_administrativo', 1, 1, 1)
ON CONFLICT ("id_permission") DO NOTHING;

INSERT INTO "permission" ("id_permission", "created_by", "creation_date", "last_update_date", "authorized_by", "permission_description", "id_department", "id_subdepartment", "id_level")
VALUES (3, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', 1, 'vendedor', 1, 1, 1)
ON CONFLICT ("id_permission") DO NOTHING;

INSERT INTO "nm_field_permission" ("id_nm_field_permission", "id_field", "id_permission", "control_type", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, 1, '1', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_nm_field_permission") DO NOTHING;

INSERT INTO "event_log" ("id_event_log", "table_name", "field_name", "action", "before_value", "after_value", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'user', 'user_id', 'create', '{}', '{}', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_event_log") DO NOTHING;

INSERT INTO "task_type" ("id_task_type", "task_type_description", "task_type_scope", "task_type_limit", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test permission description', 'test permission description', 'test permission description', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_task_type") DO NOTHING;

INSERT INTO "template" ("id_template", "template_description", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'test permission description', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_template") DO NOTHING;

INSERT INTO "nm_template_task" ("id_nm_template_task", "id_task", "id_template", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_nm_template_task") DO NOTHING;

INSERT INTO "survey_question" ("id_survey_question", "question", "question_type", "owner", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 'sample_question', 'single_option', 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_survey_question") DO NOTHING;

INSERT INTO "survey_multiple_answer" ("id_survey_multiple_answer", "id_survey_question", "survey_answer_description", "score", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, 'sample_survey_answer_description', 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_survey_multiple_answer") DO NOTHING;

INSERT INTO "nm_survey_user" ("id_nm_survey_user", "id_survey_question", "id_survey_multiple_answer", "id_user", "nm_survey_user_description", "score", "status", "created_by", "creation_date", "last_update_date", "deletion_date")
VALUES (1, 1, 1, 1, 'sample_nm_survey_user_description', 1, 1, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_nm_survey_user") DO NOTHING;

INSERT INTO "entity_permission" ("id_entity_permission", "id_permission", "entity_name", "control_type", "created_by", "creation_date", "last_update_date")
VALUES (1001, 1, 'product_sale_config', '15', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_entity_permission") DO NOTHING;

INSERT INTO "entity_permission" ("id_entity_permission", "id_permission", "entity_name", "control_type", "created_by", "creation_date", "last_update_date")
VALUES (1002, 1, 'public_api_key', '15', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_entity_permission") DO NOTHING;

INSERT INTO "entity_permission" ("id_entity_permission", "id_permission", "entity_name", "control_type", "created_by", "creation_date", "last_update_date")
VALUES (1003, 2, 'product_sale_config', '15', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_entity_permission") DO NOTHING;

INSERT INTO "entity_permission" ("id_entity_permission", "id_permission", "entity_name", "control_type", "created_by", "creation_date", "last_update_date")
VALUES (1004, 2, 'public_api_key', '15', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_entity_permission") DO NOTHING;

INSERT INTO "entity_permission" ("id_entity_permission", "id_permission", "entity_name", "control_type", "created_by", "creation_date", "last_update_date")
VALUES (1005, 3, 'product_sale_config', '2', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_entity_permission") DO NOTHING;

INSERT INTO "inventory_status" ("id_inventory_status", "inventory_status_code", "inventory_status_description", "color", "entity_scope", "flow_scope", "id_department", "id_subdepartment", "id_minimum_level", "is_active", "is_terminal", "visible_to_other_departments", "sort_order", "created_by", "creation_date", "last_update_date")
VALUES (1, 'ENTRADA', 'Entrada', '#22c55e', 'product', 'inventory', 1, 1, 1, TRUE, FALSE, FALSE, 100, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_inventory_status") DO NOTHING;

INSERT INTO "inventory_status" ("id_inventory_status", "inventory_status_code", "inventory_status_description", "color", "entity_scope", "flow_scope", "id_department", "id_subdepartment", "id_minimum_level", "is_active", "is_terminal", "visible_to_other_departments", "sort_order", "created_by", "creation_date", "last_update_date")
VALUES (1001, 'web_published', 'Publicado en web', '#22c55e', 'product', 'web_catalog', 1, 1, 1, TRUE, FALSE, TRUE, 100, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_inventory_status") DO NOTHING;

INSERT INTO "inventory_status" ("id_inventory_status", "inventory_status_code", "inventory_status_description", "color", "entity_scope", "flow_scope", "id_department", "id_subdepartment", "id_minimum_level", "is_active", "is_terminal", "visible_to_other_departments", "sort_order", "created_by", "creation_date", "last_update_date")
VALUES (1002, 'web_unpublished', 'No publicado en web', '#64748b', 'product', 'web_catalog', 1, 1, 1, TRUE, FALSE, TRUE, 200, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_inventory_status") DO NOTHING;

INSERT INTO "inventory_status" ("id_inventory_status", "inventory_status_code", "inventory_status_description", "color", "entity_scope", "flow_scope", "id_department", "id_subdepartment", "id_minimum_level", "is_active", "is_terminal", "visible_to_other_departments", "sort_order", "created_by", "creation_date", "last_update_date")
VALUES (1003, 'web_draft', 'Borrador web', '#f59e0b', 'product', 'web_catalog', 1, 1, 1, TRUE, FALSE, TRUE, 300, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_inventory_status") DO NOTHING;

INSERT INTO "product_sale_config" ("id_product_sale_config", "id_product", "margin_percent", "id_inventory_status", "is_active", "created_by", "creation_date", "last_update_date")
VALUES (1, 1, 30.00, 1001, TRUE, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_product_sale_config") DO NOTHING;

INSERT INTO "public_api_key" ("id_public_api_key", "label", "key_hash", "key_prefix", "allowed_domains", "rate_limit_per_min", "is_active", "created_by", "creation_date", "last_update_date")
VALUES (1, 'Seed inactive API key', 'disabled_seed_key_hash', 'disabled', '[]', 60, FALSE, 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00')
ON CONFLICT ("id_public_api_key") DO NOTHING;

INSERT INTO "password_reset_token" ("id_password_reset_token", "id_user", "token_hash", "expires_at", "used_at", "requested_ip", "created_at")
VALUES (1, 1, 'disabled_token_hash', '2026-01-01 00:00:00', '2026-01-01 00:00:00', '127.0.0.1', '2026-01-01 00:00:00')
ON CONFLICT ("id_password_reset_token") DO NOTHING;

-- Device connection is a virtual module and defaults to the settings gear.
INSERT INTO "entity_permission" ("id_permission", "entity_name", "control_type", "menu_location", "menu_group", "menu_label", "menu_order", "created_by")
VALUES (1, 'kronos_device', 2, 'settings', 'Recursos humanos', 'Conexión al dispositivo', 30, 1)
ON CONFLICT ("id_permission", "entity_name") DO UPDATE SET
  "menu_location" = EXCLUDED."menu_location",
  "menu_group" = EXCLUDED."menu_group",
  "menu_label" = EXCLUDED."menu_label",
  "menu_order" = EXCLUDED."menu_order",
  "deletion_date" = NULL;

-- Restaurant profiles. Users are assigned through the existing Tyakxa user/role UI.
INSERT INTO "permission" ("id_permission", "created_by", "authorized_by", "permission_description", "id_department", "id_subdepartment", "id_level") VALUES
  (10, 1, 1, 'Mesero', 1, 1, 1),
  (11, 1, 1, 'Cocina', 1, 1, 1),
  (12, 1, 1, 'Caja Restaurante', 1, 1, 1),
  (13, 1, 1, 'Admin Restaurante', 1, 1, 1)
ON CONFLICT ("id_permission") DO NOTHING;

INSERT INTO "entity_permission" ("id_permission", "entity_name", "control_type", "menu_location", "menu_group", "menu_label", "menu_order", "created_by") VALUES
  (1, 'restaurant_waiter', 15, 'sidebar', 'Restaurante', 'Meseros', 10, 1),
  (1, 'restaurant_cashier', 15, 'sidebar', 'Restaurante', 'Caja', 20, 1),
  (1, 'restaurant_kitchen', 15, 'sidebar', 'Restaurante', 'Cocina', 30, 1),
  (1, 'restaurant_admin', 15, 'sidebar', 'Restaurante', 'Admin', 40, 1),
  (10, 'restaurant_waiter', 15, 'sidebar', 'Restaurante', 'Meseros', 10, 1),
  (11, 'restaurant_kitchen', 6, 'sidebar', 'Restaurante', 'Cocina', 30, 1),
  (12, 'restaurant_cashier', 7, 'sidebar', 'Restaurante', 'Caja', 20, 1),
  (13, 'restaurant_waiter', 15, 'sidebar', 'Restaurante', 'Meseros', 10, 1),
  (13, 'restaurant_cashier', 15, 'sidebar', 'Restaurante', 'Caja', 20, 1),
  (13, 'restaurant_kitchen', 15, 'sidebar', 'Restaurante', 'Cocina', 30, 1),
  (13, 'restaurant_admin', 15, 'sidebar', 'Restaurante', 'Admin', 40, 1)
ON CONFLICT ("id_permission", "entity_name") DO UPDATE SET
  "control_type" = EXCLUDED."control_type",
  "menu_location" = EXCLUDED."menu_location",
  "menu_group" = EXCLUDED."menu_group",
  "menu_label" = EXCLUDED."menu_label",
  "menu_order" = EXCLUDED."menu_order",
  "deletion_date" = NULL;

INSERT INTO "restaurant_table" ("id_restaurant_table", "id_proyect", "number", "capacity", "location_description", "is_active", "created_by")
SELECT number, 1, number, 4, CASE WHEN number <= 8 THEN 'Salón principal' ELSE 'Terraza' END, TRUE, 1
FROM generate_series(1, 15) AS number
ON CONFLICT ("id_restaurant_table") DO NOTHING;

INSERT INTO "restaurant_guisado" ("id_restaurant_guisado", "id_proyect", "name", "is_active", "created_by") VALUES
  (1, 1, 'Picadillo', TRUE, 1),
  (2, 1, 'Rajas con crema', TRUE, 1),
  (3, 1, 'Frijoles con chorizo', TRUE, 1),
  (4, 1, 'Chicharrón en salsa verde', TRUE, 1),
  (5, 1, 'Papa con chorizo', TRUE, 1),
  (6, 1, 'Mole', TRUE, 1),
  (7, 1, 'Tinga de pollo', TRUE, 1),
  (8, 1, 'Chicharrón prensado', TRUE, 1)
ON CONFLICT ("id_restaurant_guisado") DO NOTHING;

INSERT INTO "restaurant_dish" ("id_restaurant_dish", "id_proyect", "title", "description", "icon", "category", "price", "production_cost", "requires_guisado", "schedule", "is_active", "created_by") VALUES
  (1, 1, 'Taco de guisado', 'Tortilla y guisado a elegir', 'taco', 'taco', 18.00, 7.00, TRUE, 'all', TRUE, 1),
  (2, 1, 'Gordita de guisado', 'Gordita de maíz y guisado', 'sandwich', 'gordita', 22.00, 9.00, TRUE, 'all', TRUE, 1),
  (3, 1, 'Quesadilla de guisado', 'Quesadilla con guisado a elegir', 'sandwich', 'quesadilla', 25.00, 11.00, TRUE, 'all', TRUE, 1),
  (4, 1, 'Pozole', 'Platillo del día', 'soup', 'platillo_dia', 85.00, 36.00, FALSE, 'weekend', TRUE, 1),
  (5, 1, 'Flan', 'Flan de la casa', 'cake', 'postre', 45.00, 16.00, FALSE, 'all', TRUE, 1),
  (6, 1, 'Pastel', 'Rebanada de pastel', 'cake', 'postre', 50.00, 20.00, FALSE, 'all', TRUE, 1),
  (7, 1, 'Arroz con leche', 'Postre tradicional', 'cake', 'postre', 40.00, 14.00, FALSE, 'all', TRUE, 1),
  (8, 1, 'Gelatina', 'Gelatina del día', 'cake', 'postre', 35.00, 10.00, FALSE, 'all', TRUE, 1),
  (9, 1, 'Agua de jamaica', 'Vaso de agua fresca', 'glass-water', 'agua', 25.00, 6.00, FALSE, 'weekday', TRUE, 1),
  (10, 1, 'Agua de horchata', 'Vaso de agua fresca', 'glass-water', 'agua', 25.00, 7.00, FALSE, 'weekend', TRUE, 1),
  (11, 1, 'Coca-Cola', 'Refresco', 'cup-soda', 'refresco', 30.00, 14.00, FALSE, 'all', TRUE, 1),
  (12, 1, 'Sprite', 'Refresco', 'cup-soda', 'refresco', 28.00, 13.00, FALSE, 'all', TRUE, 1),
  (13, 1, 'Café de olla', 'Café tradicional', 'coffee', 'cafe', 30.00, 8.00, FALSE, 'all', TRUE, 1),
  (14, 1, 'Paleta', 'Dulce', 'candy', 'dulce', 12.00, 5.00, FALSE, 'all', TRUE, 1),
  (15, 1, 'Cocada', 'Dulce tradicional', 'candy', 'dulce', 18.00, 7.00, FALSE, 'all', TRUE, 1)
ON CONFLICT ("id_restaurant_dish") DO NOTHING;

INSERT INTO "proyect_event" ("id_proyect", "created_by", "event_type", "new_status", "content", "creation_date")
SELECT project."id_proyect", project."created_by", 'created', project."proyect_status",
       'Registro base incorporado al historial de proyectos',
       COALESCE(project."creation_date", CURRENT_TIMESTAMP)
FROM "proyect" project
WHERE project."deletion_date" IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM "proyect_event" event
    WHERE event."id_proyect" = project."id_proyect"
  );

-- Las secuencias se realinean AQUI, no solo al final del archivo.
-- Los INSERT anteriores fijan identificadores explicitos, lo que no avanza
-- la secuencia; el INSERT que sigue depende de nextval. Con la secuencia
-- atrasada choca contra una llave ya usada y aborta la transaccion, y con
-- ella todo lo que viniera despues.
-- Keep PostgreSQL SERIAL sequences aligned after deterministic seed IDs
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public' AND column_default LIKE 'nextval%'
  LOOP
    EXECUTE format(
      'SELECT setval(pg_get_serial_sequence(%L, %L), COALESCE((SELECT MAX(%I) FROM %I), 0) + 1, false)',
      r.table_name, r.column_name, r.column_name, r.table_name
    );
  END LOOP;
END $$;

-- Project workflow roles are created without assigning existing users.
WITH role_names(role_name) AS (
  VALUES ('Supervisor'), ('Gerente'), ('Jefe de taller')
)
INSERT INTO "permission" ("created_by", "authorized_by", "permission_description", "id_department", "id_subdepartment", "id_level")
SELECT 1, 1, role_names.role_name, 1, 1, 1
FROM role_names
WHERE NOT EXISTS (
  SELECT 1 FROM "permission"
  WHERE lower("permission_description") = lower(role_names.role_name)
    AND "deletion_date" IS NULL
);

INSERT INTO "entity_permission" ("id_permission", "entity_name", "control_type", "menu_location", "menu_group", "menu_group_icon", "menu_label", "menu_order", "created_by")
SELECT role."id_permission", capability.entity_name, capability.control_type,
       capability.menu_location, capability.menu_group, capability.menu_group_icon,
       capability.menu_label, capability.menu_order, 1
FROM "permission" role
JOIN (VALUES
  ('Supervisor', 'proyect', 7, 'sidebar', 'Operaciones', 'briefcase-business', 'Proyectos', 80),
  ('Supervisor', 'task', 15, 'sidebar', 'Operaciones', 'briefcase-business', 'Tareas', 90),
  ('Supervisor', 'task_note', 15, 'sidebar', 'Operaciones', 'briefcase-business', 'Notas de tarea', 100),
  ('Supervisor', 'task_type', 15, 'sidebar', 'Operaciones', 'briefcase-business', 'Tipos de tarea', 110),
  ('Gerente', 'proyect', 6, 'sidebar', 'Operaciones', 'briefcase-business', 'Proyectos', 80),
  ('Gerente', 'project_authorization', 2, 'hidden', NULL, NULL, NULL, 100),
  ('Jefe de taller', 'proyect', 6, 'sidebar', 'Operaciones', 'briefcase-business', 'Proyectos', 80),
  ('Jefe de taller', 'task', 15, 'sidebar', 'Operaciones', 'briefcase-business', 'Tareas', 90),
  ('Jefe de taller', 'task_note', 15, 'sidebar', 'Operaciones', 'briefcase-business', 'Notas de tarea', 100),
  ('Jefe de taller', 'task_type', 2, 'sidebar', 'Operaciones', 'briefcase-business', 'Tipos de tarea', 110),
  ('Jefe de taller', 'project_execution', 2, 'hidden', NULL, NULL, NULL, 100)
) AS capability(role_name, entity_name, control_type, menu_location, menu_group, menu_group_icon, menu_label, menu_order)
  ON lower(role."permission_description") = lower(capability.role_name)
WHERE role."deletion_date" IS NULL
ON CONFLICT ("id_permission", "entity_name") DO UPDATE SET
  "control_type" = EXCLUDED."control_type",
  "menu_location" = EXCLUDED."menu_location",
  "menu_group" = EXCLUDED."menu_group",
  "menu_group_icon" = EXCLUDED."menu_group_icon",
  "menu_label" = EXCLUDED."menu_label",
  "menu_order" = EXCLUDED."menu_order",
  "deletion_date" = NULL;

INSERT INTO "nm_field_permission" ("id_field", "id_permission", "control_type", "created_by")
SELECT field_row."id_field", role."id_permission",
       CASE WHEN role."permission_description" = 'Gerente' THEN '2'
            WHEN role."permission_description" = 'Jefe de taller' AND field_row."table_name" IN ('proyect', 'task_type') THEN '2'
            ELSE '15' END,
       1
FROM "field" field_row
JOIN "permission" role ON role."permission_description" IN ('Supervisor', 'Gerente', 'Jefe de taller')
WHERE field_row."table_name" IN ('proyect', 'task', 'task_note', 'task_type')
  AND field_row."deletion_date" IS NULL
  AND role."deletion_date" IS NULL
  AND (role."permission_description" <> 'Gerente' OR field_row."table_name" = 'proyect')
  AND NOT EXISTS (
    SELECT 1 FROM "nm_field_permission" existing
    WHERE existing."id_field" = field_row."id_field"
      AND existing."id_permission" = role."id_permission"
      AND existing."deletion_date" IS NULL
  );

-- Keep PostgreSQL SERIAL sequences aligned after deterministic seed IDs
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public' AND column_default LIKE 'nextval%'
  LOOP
    EXECUTE format(
      'SELECT setval(pg_get_serial_sequence(%L, %L), COALESCE((SELECT MAX(%I) FROM %I), 0) + 1, false)',
      r.table_name, r.column_name, r.column_name, r.table_name
    );
  END LOOP;
END $$;

COMMIT;
