-- TYAKXA migration (initial schema)
-- Created UTC: 2026-08-17T02:01:00.044554Z
-- Apply with: psql -v ON_ERROR_STOP=1 -f <file>

-- TYAKXA ERP-CRM-SCM PostgreSQL schema
-- Generated from CSV project definition
-- Database: tyakxa_db

BEGIN;

CREATE TABLE IF NOT EXISTS "user" (
  "id_user" SERIAL NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "date_born" TIMESTAMP NULL,
  "date_start" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  "email" VARCHAR(100) NULL,
  "first_name" VARCHAR(50) NULL,
  "id_permission" INTEGER NOT NULL DEFAULT 1,
  "full_name" VARCHAR(150) NOT NULL,
  "id_proyect" INTEGER NOT NULL DEFAULT 1,
  "last_name_father" VARCHAR(50) NULL,
  "last_name_mother" VARCHAR(50) NULL,
  "last_update_date" TIMESTAMP NULL,
  "national_id" VARCHAR(50) NULL,
  "password" VARCHAR(256) NULL,
  "principal_phone" VARCHAR(15) NULL,
  "secundary_phone" VARCHAR(15) NULL,
  "ssn" VARCHAR(50) NULL,
  "supervisor" INTEGER NOT NULL DEFAULT 1,
  "base_salary" NUMERIC(12,2) NULL,
  "hire_date" DATE NULL,
  "id_status" INTEGER NOT NULL DEFAULT 1,
  "tax_id" VARCHAR(50) NULL,
  "title" VARCHAR(50) NULL,
  "user_type" TEXT NULL CHECK ("user_type" IN ('admin', 'client', 'supplier', 'employee', 'web_shopper')),
  "username" VARCHAR(50) NULL,
  "puesto" VARCHAR(50) NULL,
  "accepts_marketing" BOOLEAN NULL DEFAULT FALSE,
  PRIMARY KEY ("id_user")
);

CREATE TABLE IF NOT EXISTS "user_mfa" (
  "id_user_mfa" SERIAL NOT NULL,
  "id_user" INTEGER NOT NULL,
  "secret" BYTEA NOT NULL,
  "secret_iv" BYTEA NOT NULL,
  "enabled" BOOLEAN NOT NULL DEFAULT FALSE,
  "failed_attempts" INTEGER NOT NULL DEFAULT 0,
  "locked_until" TIMESTAMP NULL,
  "last_used_at" TIMESTAMP NULL,
  "backup_codes" JSONB NULL,
  "created_at" TIMESTAMP NOT NULL,
  "updated_at" TIMESTAMP NOT NULL,
  PRIMARY KEY ("id_user_mfa")
);

CREATE TABLE IF NOT EXISTS "payroll_period" (
  "id_payroll_period" SERIAL NOT NULL,
  "period_start" DATE NULL,
  "period_end" DATE NULL,
  "payment_date" DATE NULL,
  "id_status" INTEGER NOT NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_payroll_period")
);

CREATE TABLE IF NOT EXISTS "payroll_detail" (
  "id_payroll_detail" SERIAL NOT NULL,
  "id_payroll_period" INTEGER NOT NULL DEFAULT 1,
  "id_user" INTEGER NOT NULL DEFAULT 1,
  "gross_salary" NUMERIC(12,2) NULL,
  "total_earnings" NUMERIC(12,2) NULL,
  "total_deductions" NUMERIC(12,2) NULL,
  "net_pay" NUMERIC(12,2) NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_payroll_detail")
);

CREATE TABLE IF NOT EXISTS "payroll_concept" (
  "id_payroll_concept" SERIAL NOT NULL,
  "payroll_code" VARCHAR(20) NULL,
  "payroll_concept_description" VARCHAR(150) NOT NULL,
  "type" TEXT NULL CHECK ("type" IN ('earning', 'deduction', 'employer_contribution')),
  "is_taxable" BOOLEAN NOT NULL DEFAULT TRUE,
  "is_imss" BOOLEAN NOT NULL DEFAULT TRUE,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_payroll_concept")
);

CREATE TABLE IF NOT EXISTS "payroll_movement" (
  "id_payroll_movement" SERIAL NOT NULL,
  "id_payroll_detail" INTEGER NOT NULL DEFAULT 1,
  "id_payroll_concept" INTEGER NOT NULL DEFAULT 1,
  "amount" NUMERIC(12,2) NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_payroll_movement")
);

CREATE TABLE IF NOT EXISTS "customer_supplier" (
  "id_customer_supplier" SERIAL NOT NULL,
  "postal_code" VARCHAR(10) NULL,
  "name" VARCHAR(150) NOT NULL,
  "title" VARCHAR(50) NULL,
  "contact_name" VARCHAR(150) NULL,
  "phone" VARCHAR(30) NULL,
  "email" VARCHAR(100) NULL,
  "web_site" VARCHAR(50) NULL,
  "street" VARCHAR(100) NULL,
  "number_ext" VARCHAR(5) NULL,
  "number_int" VARCHAR(5) NULL,
  "neighborhood" VARCHAR(50) NULL,
  "city" VARCHAR(50) NULL,
  "geographic_state" VARCHAR(20) NULL,
  "fiscal_type" VARCHAR(150) NULL,
  "last_fiscal_certification_date" TIMESTAMP NULL,
  "tax_id" VARCHAR(50) NULL,
  "type" TEXT NULL CHECK ("type" IN ('client', 'supplier')),
  "id_user" INTEGER NOT NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  "path_logo" VARCHAR(150) NULL,
  PRIMARY KEY ("id_customer_supplier")
);

CREATE TABLE IF NOT EXISTS "proyect" (
  "id_proyect" SERIAL NOT NULL,
  "id_customer_supplier" INTEGER NOT NULL DEFAULT 1,
  "leader" INTEGER NOT NULL DEFAULT 1,
  "proyect_description" VARCHAR(200) NOT NULL,
  "title" VARCHAR(50) NULL,
  "proyect_status" VARCHAR(20) NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_proyect")
);

CREATE TABLE IF NOT EXISTS "bank" (
  "id_bank" SERIAL NOT NULL,
  "bank_name" VARCHAR(200) NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_bank")
);

CREATE TABLE IF NOT EXISTS "bank_account" (
  "id_bank_account" SERIAL NOT NULL,
  "id_bank" INTEGER NOT NULL DEFAULT 1,
  "bank_account_description" VARCHAR(200) NOT NULL,
  "branch" VARCHAR(30) NULL,
  "type" VARCHAR(30) NULL,
  "ordinary_interest" NUMERIC(10,2) NULL,
  "moratorium_interest" NUMERIC(10,2) NULL,
  "anuality" NUMERIC(10,2) NULL,
  "reimbursement" NUMERIC(10,2) NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_bank_account")
);

CREATE TABLE IF NOT EXISTS "invoice" (
  "id_invoice" SERIAL NOT NULL,
  "date_emision" TIMESTAMP NULL,
  "date_expiration" TIMESTAMP NULL,
  "subtotal" NUMERIC(10,2) NULL,
  "tax" NUMERIC(10,2) NULL,
  "total" NUMERIC(10,2) NULL,
  "invoice_status" VARCHAR(20) NULL,
  "payment_method" VARCHAR(50) NULL,
  "note" VARCHAR(300) NULL,
  "id_customer_supplier" INTEGER NOT NULL DEFAULT 1,
  "fiscal_reference" VARCHAR(50) NULL,
  "serie_csd" VARCHAR(150) NULL,
  "internationalization" TEXT NULL CHECK ("internationalization" IN ('exported', 'imported', 'local')),
  "currency" VARCHAR(30) NULL,
  "type_exchange_rate" NUMERIC(10,2) NULL,
  "tax_certification_supplier" INTEGER NOT NULL DEFAULT 1,
  "fiscal_certify_serie" VARCHAR(150) NULL,
  "certification_date" TIMESTAMP NULL,
  "cfdi_code" VARCHAR(500) NULL,
  "sat_code" VARCHAR(500) NULL,
  "sat_certification_code" VARCHAR(500) NULL,
  "id_status" INTEGER NOT NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  "nombre_emisor" VARCHAR(150) NULL,
  "lugar_expedicion" VARCHAR(120) NULL,
  "tipo_de_comprobante" VARCHAR(50) NULL,
  "rfc_receptor" VARCHAR(20) NULL,
  "nombre_receptor" VARCHAR(150) NULL,
  "regimen_fiscal_receptor" VARCHAR(100) NULL,
  "domicilio_fiscal_receptor" VARCHAR(250) NULL,
  "id_proveedor_de_sello" INTEGER NULL,
  "folio_fiscal" VARCHAR(50) NULL,
  "exportacion" VARCHAR(50) NULL,
  "folio" VARCHAR(30) NULL,
  "no_certificado_sat" VARCHAR(50) NULL,
  "sello_sat" VARCHAR(500) NULL,
  "sello_certificacion_sat" VARCHAR(500) NULL,
  "no_certificado" VARCHAR(50) NULL,
  "descuento" NUMERIC(10,2) NULL,
  "metodo_pago" VARCHAR(50) NULL,
  "condiciones_pago" VARCHAR(100) NULL,
  "id_issuer_customer_supplier" INTEGER NOT NULL DEFAULT 1,
  "id_proyect" INTEGER NULL,
  "apply_tax" BOOLEAN NOT NULL DEFAULT TRUE,
  "tax_rate" NUMERIC(5,2) NULL DEFAULT 16.00,
  "commercial_terms" VARCHAR(500) NULL,
  PRIMARY KEY ("id_invoice")
);

CREATE TABLE IF NOT EXISTS "invoice_material_service" (
  "id_invoice_material_service" SERIAL NOT NULL,
  "id_invoice" INTEGER NOT NULL DEFAULT 1,
  "id_material" INTEGER NULL,
  "id_service" INTEGER NULL,
  "invoice_material_service_description" VARCHAR(200) NOT NULL,
  "max_requirement_date" TIMESTAMP NULL,
  "is_directly_related_to_product_service_creation" BOOLEAN NOT NULL DEFAULT TRUE,
  "id_authorized" INTEGER NOT NULL DEFAULT 1,
  "id_status" INTEGER NOT NULL DEFAULT 1,
  "id_buyer" INTEGER NOT NULL DEFAULT 1,
  "id_customer_supplier" INTEGER NOT NULL DEFAULT 1,
  "gross_price" NUMERIC(10,2) NULL,
  "quantity" NUMERIC(10,2) NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  "id_product" INTEGER NULL,
  "line_type" TEXT NOT NULL DEFAULT 'custom' CHECK ("line_type" IN ('product', 'service', 'custom')),
  "tax_applicable" BOOLEAN NOT NULL DEFAULT TRUE,
  "line_tax" NUMERIC(10,2) NULL DEFAULT 0.00,
  "line_total" NUMERIC(10,2) NULL DEFAULT 0.00,
  "id_unit" INTEGER NULL,
  "authorization_status" TEXT NOT NULL DEFAULT 'pending' CHECK ("authorization_status" IN ('pending', 'authorized', 'rejected')),
  "authorization_note" VARCHAR(500) NULL,
  "authorization_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_invoice_material_service")
);

CREATE TABLE IF NOT EXISTS "product_family" (
  "id_product_family" SERIAL NOT NULL,
  "product_family_description" VARCHAR(200) NOT NULL,
  "type" TEXT NULL CHECK ("type" IN ('tool', 'consumable')),
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_product_family")
);

CREATE TABLE IF NOT EXISTS "incident_type" (
  "id_incident_type" SERIAL NOT NULL,
  "incident_type_description" VARCHAR(200) NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_incident_type")
);

CREATE TABLE IF NOT EXISTS "incident" (
  "id_incident" SERIAL NOT NULL,
  "incident_date" TIMESTAMP NULL,
  "id_incident_type" INTEGER NOT NULL DEFAULT 1,
  "note" VARCHAR(300) NULL,
  "id_user" INTEGER NOT NULL DEFAULT 1,
  "incident_status" VARCHAR(20) NULL,
  "close_date" TIMESTAMP NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  "id_lider" INTEGER NULL,
  PRIMARY KEY ("id_incident")
);

CREATE TABLE IF NOT EXISTS "incident_detail" (
  "id_incident_detail" SERIAL NOT NULL,
  "id_incident_type" INTEGER NOT NULL DEFAULT 1,
  "incident_detail_name" VARCHAR(50) NOT NULL,
  "incident_detail_description" VARCHAR(200) NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_incident_detail")
);

CREATE TABLE IF NOT EXISTS "brand" (
  "id_brand" SERIAL NOT NULL,
  "brand_description" VARCHAR(200) NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_brand")
);

CREATE TABLE IF NOT EXISTS "unit" (
  "id_unit" SERIAL NOT NULL,
  "unit_code" VARCHAR(20) NULL,
  "unit_name" VARCHAR(100) NOT NULL,
  "unit_category" VARCHAR(50) NULL,
  "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
  "symbol" VARCHAR(20) NULL,
  "measurement_system" TEXT NOT NULL DEFAULT 'metric' CHECK ("measurement_system" IN ('metric', 'imperial', 'mixed')),
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_unit")
);

CREATE TABLE IF NOT EXISTS "material" (
  "id_material" SERIAL NOT NULL,
  "material_description" VARCHAR(200) NOT NULL,
  "id_unit" INTEGER NOT NULL DEFAULT 1,
  "id_brand" INTEGER NOT NULL DEFAULT 1,
  "id_product_family" INTEGER NOT NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_material")
);

CREATE TABLE IF NOT EXISTS "material_component" (
  "id_material_component" SERIAL NOT NULL,
  "id_material" INTEGER NOT NULL DEFAULT 1,
  "id_component" INTEGER NOT NULL DEFAULT 1,
  "relation" NUMERIC(10,2) NULL,
  "id_unit" INTEGER NOT NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_material_component")
);

CREATE TABLE IF NOT EXISTS "movement" (
  "id_movement" SERIAL NOT NULL,
  "id_fiscal_account" INTEGER NOT NULL DEFAULT 1,
  "date" TIMESTAMP NULL,
  "type" TEXT NULL CHECK ("type" IN ('income', 'expense')),
  "amount" NUMERIC(10,2) NULL,
  "currency" TEXT NULL CHECK ("currency" IN ('usd', 'mxn', 'eur')),
  "type_exchange_rate" NUMERIC(10,2) NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_movement")
);

CREATE TABLE IF NOT EXISTS "location_type" (
  "id_location_type" SERIAL NOT NULL,
  "location_type_description" VARCHAR(200) NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_location_type")
);

CREATE TABLE IF NOT EXISTS "location" (
  "id_location" SERIAL NOT NULL,
  "id_location_type" INTEGER NOT NULL DEFAULT 1,
  "location_description" VARCHAR(200) NOT NULL,
  "id_location_reference" INTEGER NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_location")
);

CREATE TABLE IF NOT EXISTS "product" (
  "id_product" SERIAL NOT NULL,
  "id_invoice" INTEGER NOT NULL DEFAULT 1,
  "id_location" INTEGER NOT NULL DEFAULT 1,
  "id_material" INTEGER NOT NULL DEFAULT 1,
  "gross_price" NUMERIC(10,2) NULL,
  "color" VARCHAR(100) NULL,
  "is_directly_related_to_product_service" BOOLEAN NOT NULL DEFAULT TRUE,
  "product_status" VARCHAR(20) NULL,
  "path_imagen" VARCHAR(100) NULL,
  "product_code" VARCHAR(30) NULL,
  "note" VARCHAR(300) NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  "descripcion" VARCHAR(250) NULL,
  "cantidad" INTEGER NULL,
  "id_marca" INTEGER NULL,
  "id_familia" INTEGER NULL,
  PRIMARY KEY ("id_product")
);

CREATE TABLE IF NOT EXISTS "nm_incident_product" (
  "id_nm_incident_product" SERIAL NOT NULL,
  "id_incident" INTEGER NOT NULL DEFAULT 1,
  "id_product" INTEGER NOT NULL DEFAULT 1,
  "note" VARCHAR(300) NULL,
  "quantity" INTEGER NOT NULL DEFAULT 1,
  "close_date" TIMESTAMP NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_nm_incident_product")
);

CREATE TABLE IF NOT EXISTS "task" (
  "id_task" SERIAL NOT NULL,
  "task_code" VARCHAR(11) NULL,
  "start_date" TIMESTAMP NULL,
  "duration" NUMERIC(10,2) NULL,
  "type" TEXT NULL CHECK ("type" IN ('personal', 'business')),
  "owner" INTEGER NOT NULL DEFAULT 1,
  "analyst" INTEGER NOT NULL DEFAULT 1,
  "dependency" INTEGER NOT NULL DEFAULT 1,
  "leader" INTEGER NOT NULL DEFAULT 1,
  "validation" INTEGER NOT NULL DEFAULT 1,
  "task_description" VARCHAR(200) NOT NULL,
  "estimated_effort" VARCHAR(50) NULL,
  "task_status" VARCHAR(20) NULL,
  "fase" VARCHAR(100) NULL,
  "priority" VARCHAR(50) NULL,
  "title" VARCHAR(50) NULL,
  "id_proyect" INTEGER NOT NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_task")
);

CREATE TABLE IF NOT EXISTS "task_note" (
  "id_task_note" SERIAL NOT NULL,
  "date" TIMESTAMP NULL,
  "id_task" INTEGER NOT NULL DEFAULT 1,
  "task_note_description" VARCHAR(600) NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_task_note")
);

CREATE TABLE IF NOT EXISTS "ticket" (
  "id_ticket" SERIAL NOT NULL,
  "ticket_description" VARCHAR(200) NOT NULL,
  "ticket_status" VARCHAR(20) NULL,
  "note" VARCHAR(300) NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_ticket")
);

CREATE TABLE IF NOT EXISTS "fiscal_account" (
  "id_fiscal_account" SERIAL NOT NULL,
  "fiscal_account_description" VARCHAR(200) NOT NULL,
  "balance" NUMERIC(10,2) NULL,
  "id_fiscal_account_reference" INTEGER NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_fiscal_account")
);

CREATE TABLE IF NOT EXISTS "fiscal_stamp" (
  "id_fiscal_stamp" SERIAL NOT NULL,
  "concept" VARCHAR(50) NOT NULL DEFAULT 'concept',
  "reviewed_by" INTEGER NOT NULL DEFAULT 1,
  "authorized_by" INTEGER NOT NULL DEFAULT 1,
  "auxiliar" VARCHAR(50) NULL,
  "num_policy" VARCHAR(20) NOT NULL DEFAULT 'num_policy',
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_fiscal_stamp")
);

CREATE TABLE IF NOT EXISTS "fiscal_record" (
  "id_fiscal_record" SERIAL NOT NULL,
  "fiscal_record_name" VARCHAR(150) NOT NULL DEFAULT 'name',
  "id_fiscal_account" INTEGER NOT NULL DEFAULT 1,
  "amount" NUMERIC(10,2) NOT NULL DEFAULT 0,
  "type" VARCHAR(30) NULL,
  "id_fiscal_stamp" INTEGER NOT NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_fiscal_record")
);

CREATE TABLE IF NOT EXISTS "service" (
  "id_service" SERIAL NOT NULL,
  "service_description" VARCHAR(500) NOT NULL,
  "average_time_cost" NUMERIC(10,2) NULL,
  "id_brand" INTEGER NOT NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_service")
);

CREATE TABLE IF NOT EXISTS "status" (
  "id_status" SERIAL NOT NULL,
  "status_description" VARCHAR(150) NOT NULL DEFAULT 'name',
  "category" VARCHAR(150) NOT NULL DEFAULT 'name',
  "is_terminal" BOOLEAN NOT NULL DEFAULT TRUE,
  "sort_order" TEXT NULL CHECK ("sort_order" IN ('desc', 'asc')),
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_status")
);

CREATE TABLE IF NOT EXISTS "theme" (
  "id_theme" SERIAL NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  "tenant_id" INTEGER NOT NULL DEFAULT 1,
  "primary_color" VARCHAR(10) NOT NULL DEFAULT '#0D47A1',
  "secondary_color" VARCHAR(10) NOT NULL DEFAULT '#1565C0',
  "background_color" VARCHAR(10) NOT NULL DEFAULT '#F5F6FA',
  "text_color" VARCHAR(10) NOT NULL DEFAULT '#212121',
  "highlight_color" VARCHAR(10) NOT NULL DEFAULT '#1E88E5',
  "success_color" VARCHAR(10) NOT NULL DEFAULT '#2E7D32',
  "error_color" VARCHAR(10) NOT NULL DEFAULT '#C62828',
  PRIMARY KEY ("id_theme")
);

CREATE TABLE IF NOT EXISTS "department" (
  "id_department" SERIAL NOT NULL,
  "department_description" VARCHAR(100) NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_department")
);

CREATE TABLE IF NOT EXISTS "subdepartment" (
  "id_subdepartment" SERIAL NOT NULL,
  "subdepartment_description" VARCHAR(100) NOT NULL,
  "id_department" INTEGER NOT NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_subdepartment")
);

CREATE TABLE IF NOT EXISTS "level" (
  "id_level" SERIAL NOT NULL,
  "level_description" VARCHAR(100) NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_level")
);

CREATE TABLE IF NOT EXISTS "field" (
  "id_field" SERIAL NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  "table_name" VARCHAR(50) NOT NULL DEFAULT 'user',
  "field_name" VARCHAR(50) NOT NULL DEFAULT 'id_user',
  PRIMARY KEY ("id_field")
);

CREATE TABLE IF NOT EXISTS "permission" (
  "id_permission" SERIAL NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  "authorized_by" INTEGER NOT NULL DEFAULT 1,
  "permission_description" VARCHAR(250) NOT NULL,
  "id_department" INTEGER NOT NULL DEFAULT 1,
  "id_subdepartment" INTEGER NOT NULL DEFAULT 1,
  "id_level" INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY ("id_permission")
);

CREATE TABLE IF NOT EXISTS "nm_field_permission" (
  "id_nm_field_permission" SERIAL NOT NULL,
  "id_field" INTEGER NOT NULL DEFAULT 1,
  "id_permission" INTEGER NOT NULL DEFAULT 1,
  "control_type" TEXT NOT NULL DEFAULT '1' CHECK ("control_type" IN ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15')),
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_nm_field_permission")
);

CREATE TABLE IF NOT EXISTS "event_log" (
  "id_event_log" SERIAL NOT NULL,
  "table_name" VARCHAR(50) NOT NULL,
  "field_name" VARCHAR(50) NOT NULL,
  "action" TEXT NOT NULL DEFAULT 'create' CHECK ("action" IN ('create', 'update', 'delete')),
  "before_value" JSONB NOT NULL,
  "after_value" JSONB NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_event_log")
);

CREATE TABLE IF NOT EXISTS "task_type" (
  "id_task_type" SERIAL NOT NULL,
  "task_type_description" VARCHAR(250) NOT NULL,
  "task_type_scope" VARCHAR(500) NULL,
  "task_type_limit" VARCHAR(500) NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_task_type")
);

CREATE TABLE IF NOT EXISTS "template" (
  "id_template" SERIAL NOT NULL,
  "template_description" VARCHAR(250) NOT NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_template")
);

CREATE TABLE IF NOT EXISTS "nm_template_task" (
  "id_nm_template_task" SERIAL NOT NULL,
  "id_task" INTEGER NOT NULL DEFAULT 1,
  "id_template" INTEGER NOT NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_nm_template_task")
);

CREATE TABLE IF NOT EXISTS "survey_question" (
  "id_survey_question" SERIAL NOT NULL,
  "question" VARCHAR(300) NOT NULL,
  "question_type" TEXT NOT NULL CHECK ("question_type" IN ('multiple_option', 'single_option', 'boolean', 'score', 'short_text', 'long_text')),
  "owner" INTEGER NOT NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_survey_question")
);

CREATE TABLE IF NOT EXISTS "survey_multiple_answer" (
  "id_survey_multiple_answer" SERIAL NOT NULL,
  "id_survey_question" INTEGER NOT NULL DEFAULT 1,
  "survey_answer_description" VARCHAR(300) NOT NULL,
  "score" INTEGER NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_survey_multiple_answer")
);

CREATE TABLE IF NOT EXISTS "nm_survey_user" (
  "id_nm_survey_user" SERIAL NOT NULL,
  "id_survey_question" INTEGER NOT NULL DEFAULT 1,
  "id_survey_multiple_answer" INTEGER NOT NULL DEFAULT 1,
  "id_user" INTEGER NOT NULL DEFAULT 1,
  "nm_survey_user_description" VARCHAR(300) NOT NULL,
  "score" INTEGER NULL,
  "status" INTEGER NOT NULL DEFAULT 1,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_nm_survey_user")
);

CREATE TABLE IF NOT EXISTS "entity_permission" (
  "id_entity_permission" SERIAL NOT NULL,
  "id_permission" INTEGER NOT NULL DEFAULT 1,
  "entity_name" VARCHAR(120) NOT NULL,
  "control_type" TEXT NOT NULL DEFAULT '15' CHECK ("control_type" IN ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15')),
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_entity_permission")
);

CREATE TABLE IF NOT EXISTS "inventory_status" (
  "id_inventory_status" SERIAL NOT NULL,
  "inventory_status_code" VARCHAR(50) NOT NULL DEFAULT 'ENTRADA',
  "inventory_status_description" VARCHAR(120) NOT NULL DEFAULT 'Entrada',
  "color" VARCHAR(20) NOT NULL DEFAULT '#22c55e',
  "entity_scope" VARCHAR(80) NOT NULL DEFAULT 'product',
  "flow_scope" VARCHAR(80) NOT NULL DEFAULT 'inventory',
  "id_department" INTEGER NOT NULL DEFAULT 4,
  "id_subdepartment" INTEGER NULL DEFAULT 4,
  "id_minimum_level" INTEGER NOT NULL DEFAULT 2,
  "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
  "is_terminal" BOOLEAN NOT NULL DEFAULT FALSE,
  "visible_to_other_departments" BOOLEAN NOT NULL DEFAULT FALSE,
  "sort_order" INTEGER NOT NULL DEFAULT 100,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_inventory_status")
);

CREATE TABLE IF NOT EXISTS "product_sale_config" (
  "id_product_sale_config" SERIAL NOT NULL,
  "id_product" INTEGER NOT NULL DEFAULT 1,
  "margin_percent" NUMERIC(5,2) NULL,
  "manual_price" NUMERIC(12,2) NULL,
  "id_inventory_status" INTEGER NOT NULL DEFAULT 1001,
  "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_product_sale_config")
);

CREATE TABLE IF NOT EXISTS "public_api_key" (
  "id_public_api_key" SERIAL NOT NULL,
  "label" VARCHAR(120) NOT NULL,
  "key_hash" VARCHAR(255) NOT NULL,
  "key_prefix" VARCHAR(12) NOT NULL,
  "allowed_domains" TEXT NOT NULL,
  "rate_limit_per_min" INTEGER NOT NULL DEFAULT 60,
  "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
  "last_used_at" TIMESTAMP NULL,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NULL,
  "last_update_date" TIMESTAMP NULL,
  "deletion_date" TIMESTAMP NULL,
  PRIMARY KEY ("id_public_api_key")
);

CREATE TABLE IF NOT EXISTS "password_reset_token" (
  "id_password_reset_token" SERIAL NOT NULL,
  "id_user" INTEGER NOT NULL DEFAULT 1,
  "token_hash" VARCHAR(255) NOT NULL,
  "expires_at" TIMESTAMP NOT NULL,
  "used_at" TIMESTAMP NULL,
  "requested_ip" VARCHAR(45) NULL,
  "created_at" TIMESTAMP NOT NULL DEFAULT 'datetime.now()',
  PRIMARY KEY ("id_password_reset_token")
);

CREATE INDEX IF NOT EXISTS "idx_user_created_by" ON "user" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_user_id_permission" ON "user" ("id_permission");
CREATE INDEX IF NOT EXISTS "idx_user_id_proyect" ON "user" ("id_proyect");
CREATE INDEX IF NOT EXISTS "idx_user_national_id" ON "user" ("national_id");
CREATE INDEX IF NOT EXISTS "idx_user_supervisor" ON "user" ("supervisor");
CREATE INDEX IF NOT EXISTS "idx_user_id_status" ON "user" ("id_status");
CREATE INDEX IF NOT EXISTS "idx_user_mfa_id_user" ON "user_mfa" ("id_user");
CREATE INDEX IF NOT EXISTS "idx_payroll_period_id_status" ON "payroll_period" ("id_status");
CREATE INDEX IF NOT EXISTS "idx_payroll_period_created_by" ON "payroll_period" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_payroll_detail_id_payroll_period" ON "payroll_detail" ("id_payroll_period");
CREATE INDEX IF NOT EXISTS "idx_payroll_detail_id_user" ON "payroll_detail" ("id_user");
CREATE INDEX IF NOT EXISTS "idx_payroll_detail_created_by" ON "payroll_detail" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_payroll_concept_created_by" ON "payroll_concept" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_payroll_movement_id_payroll_detail" ON "payroll_movement" ("id_payroll_detail");
CREATE INDEX IF NOT EXISTS "idx_payroll_movement_id_payroll_concept" ON "payroll_movement" ("id_payroll_concept");
CREATE INDEX IF NOT EXISTS "idx_payroll_movement_created_by" ON "payroll_movement" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_customer_supplier_id_user" ON "customer_supplier" ("id_user");
CREATE INDEX IF NOT EXISTS "idx_customer_supplier_created_by" ON "customer_supplier" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_proyect_id_customer_supplier" ON "proyect" ("id_customer_supplier");
CREATE INDEX IF NOT EXISTS "idx_proyect_leader" ON "proyect" ("leader");
CREATE INDEX IF NOT EXISTS "idx_proyect_created_by" ON "proyect" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_bank_created_by" ON "bank" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_bank_account_id_bank" ON "bank_account" ("id_bank");
CREATE INDEX IF NOT EXISTS "idx_bank_account_created_by" ON "bank_account" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_invoice_id_customer_supplier" ON "invoice" ("id_customer_supplier");
CREATE INDEX IF NOT EXISTS "idx_invoice_id_status" ON "invoice" ("id_status");
CREATE INDEX IF NOT EXISTS "idx_invoice_created_by" ON "invoice" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_invoice_id_issuer_customer_supplier" ON "invoice" ("id_issuer_customer_supplier");
CREATE INDEX IF NOT EXISTS "idx_invoice_id_proyect" ON "invoice" ("id_proyect");
CREATE INDEX IF NOT EXISTS "idx_invoice_material_service_id_invoice" ON "invoice_material_service" ("id_invoice");
CREATE INDEX IF NOT EXISTS "idx_invoice_material_service_id_material" ON "invoice_material_service" ("id_material");
CREATE INDEX IF NOT EXISTS "idx_invoice_material_service_id_service" ON "invoice_material_service" ("id_service");
CREATE INDEX IF NOT EXISTS "idx_invoice_material_service_id_authorized" ON "invoice_material_service" ("id_authorized");
CREATE INDEX IF NOT EXISTS "idx_invoice_material_service_id_status" ON "invoice_material_service" ("id_status");
CREATE INDEX IF NOT EXISTS "idx_invoice_material_service_id_buyer" ON "invoice_material_service" ("id_buyer");
CREATE INDEX IF NOT EXISTS "idx_invoice_material_service_id_customer_supplier" ON "invoice_material_service" ("id_customer_supplier");
CREATE INDEX IF NOT EXISTS "idx_invoice_material_service_created_by" ON "invoice_material_service" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_invoice_material_service_id_product" ON "invoice_material_service" ("id_product");
CREATE INDEX IF NOT EXISTS "idx_invoice_material_service_id_unit" ON "invoice_material_service" ("id_unit");
CREATE INDEX IF NOT EXISTS "idx_invoice_material_service_authorization_status" ON "invoice_material_service" ("authorization_status");
CREATE INDEX IF NOT EXISTS "idx_product_family_created_by" ON "product_family" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_incident_type_created_by" ON "incident_type" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_incident_id_incident_type" ON "incident" ("id_incident_type");
CREATE INDEX IF NOT EXISTS "idx_incident_id_user" ON "incident" ("id_user");
CREATE INDEX IF NOT EXISTS "idx_incident_created_by" ON "incident" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_incident_detail_id_incident_type" ON "incident_detail" ("id_incident_type");
CREATE INDEX IF NOT EXISTS "idx_incident_detail_created_by" ON "incident_detail" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_brand_created_by" ON "brand" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_unit_created_by" ON "unit" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_material_id_unit" ON "material" ("id_unit");
CREATE INDEX IF NOT EXISTS "idx_material_id_brand" ON "material" ("id_brand");
CREATE INDEX IF NOT EXISTS "idx_material_id_product_family" ON "material" ("id_product_family");
CREATE INDEX IF NOT EXISTS "idx_material_created_by" ON "material" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_material_component_id_material" ON "material_component" ("id_material");
CREATE INDEX IF NOT EXISTS "idx_material_component_id_component" ON "material_component" ("id_component");
CREATE INDEX IF NOT EXISTS "idx_material_component_id_unit" ON "material_component" ("id_unit");
CREATE INDEX IF NOT EXISTS "idx_material_component_created_by" ON "material_component" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_movement_id_fiscal_account" ON "movement" ("id_fiscal_account");
CREATE INDEX IF NOT EXISTS "idx_movement_created_by" ON "movement" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_location_type_created_by" ON "location_type" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_location_id_location_type" ON "location" ("id_location_type");
CREATE INDEX IF NOT EXISTS "idx_location_created_by" ON "location" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_product_id_invoice" ON "product" ("id_invoice");
CREATE INDEX IF NOT EXISTS "idx_product_id_location" ON "product" ("id_location");
CREATE INDEX IF NOT EXISTS "idx_product_id_material" ON "product" ("id_material");
CREATE INDEX IF NOT EXISTS "idx_product_created_by" ON "product" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_nm_incident_product_id_incident" ON "nm_incident_product" ("id_incident");
CREATE INDEX IF NOT EXISTS "idx_nm_incident_product_id_product" ON "nm_incident_product" ("id_product");
CREATE INDEX IF NOT EXISTS "idx_nm_incident_product_created_by" ON "nm_incident_product" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_task_owner" ON "task" ("owner");
CREATE INDEX IF NOT EXISTS "idx_task_id_proyect" ON "task" ("id_proyect");
CREATE INDEX IF NOT EXISTS "idx_task_created_by" ON "task" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_task_note_id_task" ON "task_note" ("id_task");
CREATE INDEX IF NOT EXISTS "idx_task_note_created_by" ON "task_note" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_ticket_created_by" ON "ticket" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_fiscal_account_created_by" ON "fiscal_account" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_fiscal_stamp_created_by" ON "fiscal_stamp" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_fiscal_record_id_fiscal_account" ON "fiscal_record" ("id_fiscal_account");
CREATE INDEX IF NOT EXISTS "idx_fiscal_record_id_fiscal_stamp" ON "fiscal_record" ("id_fiscal_stamp");
CREATE INDEX IF NOT EXISTS "idx_fiscal_record_created_by" ON "fiscal_record" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_service_id_brand" ON "service" ("id_brand");
CREATE INDEX IF NOT EXISTS "idx_service_created_by" ON "service" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_status_created_by" ON "status" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_theme_created_by" ON "theme" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_department_created_by" ON "department" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_subdepartment_id_department" ON "subdepartment" ("id_department");
CREATE INDEX IF NOT EXISTS "idx_subdepartment_created_by" ON "subdepartment" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_level_created_by" ON "level" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_field_created_by" ON "field" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_permission_created_by" ON "permission" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_permission_authorized_by" ON "permission" ("authorized_by");
CREATE INDEX IF NOT EXISTS "idx_permission_id_department" ON "permission" ("id_department");
CREATE INDEX IF NOT EXISTS "idx_permission_id_subdepartment" ON "permission" ("id_subdepartment");
CREATE INDEX IF NOT EXISTS "idx_permission_id_level" ON "permission" ("id_level");
CREATE INDEX IF NOT EXISTS "idx_nm_field_permission_id_field" ON "nm_field_permission" ("id_field");
CREATE INDEX IF NOT EXISTS "idx_nm_field_permission_id_permission" ON "nm_field_permission" ("id_permission");
CREATE INDEX IF NOT EXISTS "idx_nm_field_permission_created_by" ON "nm_field_permission" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_event_log_created_by" ON "event_log" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_task_type_created_by" ON "task_type" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_template_created_by" ON "template" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_nm_template_task_id_task" ON "nm_template_task" ("id_task");
CREATE INDEX IF NOT EXISTS "idx_nm_template_task_id_template" ON "nm_template_task" ("id_template");
CREATE INDEX IF NOT EXISTS "idx_nm_template_task_created_by" ON "nm_template_task" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_survey_question_owner" ON "survey_question" ("owner");
CREATE INDEX IF NOT EXISTS "idx_survey_question_created_by" ON "survey_question" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_survey_multiple_answer_id_survey_question" ON "survey_multiple_answer" ("id_survey_question");
CREATE INDEX IF NOT EXISTS "idx_survey_multiple_answer_created_by" ON "survey_multiple_answer" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_nm_survey_user_id_survey_question" ON "nm_survey_user" ("id_survey_question");
CREATE INDEX IF NOT EXISTS "idx_nm_survey_user_id_survey_multiple_answer" ON "nm_survey_user" ("id_survey_multiple_answer");
CREATE INDEX IF NOT EXISTS "idx_nm_survey_user_id_user" ON "nm_survey_user" ("id_user");
CREATE INDEX IF NOT EXISTS "idx_nm_survey_user_status" ON "nm_survey_user" ("status");
CREATE INDEX IF NOT EXISTS "idx_nm_survey_user_created_by" ON "nm_survey_user" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_entity_permission_id_permission" ON "entity_permission" ("id_permission");
CREATE INDEX IF NOT EXISTS "idx_entity_permission_entity_name" ON "entity_permission" ("entity_name");
CREATE INDEX IF NOT EXISTS "idx_entity_permission_created_by" ON "entity_permission" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_inventory_status_inventory_status_code" ON "inventory_status" ("inventory_status_code");
CREATE INDEX IF NOT EXISTS "idx_inventory_status_inventory_status_description" ON "inventory_status" ("inventory_status_description");
CREATE INDEX IF NOT EXISTS "idx_inventory_status_entity_scope" ON "inventory_status" ("entity_scope");
CREATE INDEX IF NOT EXISTS "idx_inventory_status_flow_scope" ON "inventory_status" ("flow_scope");
CREATE INDEX IF NOT EXISTS "idx_inventory_status_id_department" ON "inventory_status" ("id_department");
CREATE INDEX IF NOT EXISTS "idx_inventory_status_id_subdepartment" ON "inventory_status" ("id_subdepartment");
CREATE INDEX IF NOT EXISTS "idx_inventory_status_id_minimum_level" ON "inventory_status" ("id_minimum_level");
CREATE INDEX IF NOT EXISTS "idx_inventory_status_is_active" ON "inventory_status" ("is_active");
CREATE INDEX IF NOT EXISTS "idx_inventory_status_visible_to_other_departments" ON "inventory_status" ("visible_to_other_departments");
CREATE INDEX IF NOT EXISTS "idx_inventory_status_created_by" ON "inventory_status" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_product_sale_config_id_product" ON "product_sale_config" ("id_product");
CREATE INDEX IF NOT EXISTS "idx_product_sale_config_id_inventory_status" ON "product_sale_config" ("id_inventory_status");
CREATE INDEX IF NOT EXISTS "idx_product_sale_config_created_by" ON "product_sale_config" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_public_api_key_created_by" ON "public_api_key" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_password_reset_token_id_user" ON "password_reset_token" ("id_user");
CREATE INDEX IF NOT EXISTS "idx_password_reset_token_token_hash" ON "password_reset_token" ("token_hash");
CREATE INDEX IF NOT EXISTS "idx_password_reset_token_expires_at" ON "password_reset_token" ("expires_at");
CREATE INDEX IF NOT EXISTS "idx_password_reset_token_created_at" ON "password_reset_token" ("created_at");

-- Foreign keys

DO $$ BEGIN
  ALTER TABLE "user" ADD CONSTRAINT "fk_user_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "user" ADD CONSTRAINT "fk_user_id_permission" FOREIGN KEY ("id_permission") REFERENCES "permission"("id_permission") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "user" ADD CONSTRAINT "fk_user_id_proyect" FOREIGN KEY ("id_proyect") REFERENCES "proyect"("id_proyect") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "user" ADD CONSTRAINT "fk_user_supervisor" FOREIGN KEY ("supervisor") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "user" ADD CONSTRAINT "fk_user_id_status" FOREIGN KEY ("id_status") REFERENCES "status"("id_status") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "user_mfa" ADD CONSTRAINT "fk_user_mfa_id_user" FOREIGN KEY ("id_user") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "payroll_period" ADD CONSTRAINT "fk_payroll_period_id_status" FOREIGN KEY ("id_status") REFERENCES "status"("id_status") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "payroll_period" ADD CONSTRAINT "fk_payroll_period_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "payroll_detail" ADD CONSTRAINT "fk_payroll_detail_id_payroll_period" FOREIGN KEY ("id_payroll_period") REFERENCES "payroll_period"("id_payroll_period") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "payroll_detail" ADD CONSTRAINT "fk_payroll_detail_id_user" FOREIGN KEY ("id_user") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "payroll_detail" ADD CONSTRAINT "fk_payroll_detail_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "payroll_concept" ADD CONSTRAINT "fk_payroll_concept_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "payroll_movement" ADD CONSTRAINT "fk_payroll_movement_id_payroll_detail" FOREIGN KEY ("id_payroll_detail") REFERENCES "payroll_detail"("id_payroll_detail") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "payroll_movement" ADD CONSTRAINT "fk_payroll_movement_id_payroll_concept" FOREIGN KEY ("id_payroll_concept") REFERENCES "payroll_concept"("id_payroll_concept") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "payroll_movement" ADD CONSTRAINT "fk_payroll_movement_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "customer_supplier" ADD CONSTRAINT "fk_customer_supplier_id_user" FOREIGN KEY ("id_user") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "customer_supplier" ADD CONSTRAINT "fk_customer_supplier_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "proyect" ADD CONSTRAINT "fk_proyect_id_customer_supplier" FOREIGN KEY ("id_customer_supplier") REFERENCES "customer_supplier"("id_customer_supplier") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "proyect" ADD CONSTRAINT "fk_proyect_leader" FOREIGN KEY ("leader") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "proyect" ADD CONSTRAINT "fk_proyect_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "bank" ADD CONSTRAINT "fk_bank_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "bank_account" ADD CONSTRAINT "fk_bank_account_id_bank" FOREIGN KEY ("id_bank") REFERENCES "bank"("id_bank") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "bank_account" ADD CONSTRAINT "fk_bank_account_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice" ADD CONSTRAINT "fk_invoice_id_customer_supplier" FOREIGN KEY ("id_customer_supplier") REFERENCES "customer_supplier"("id_customer_supplier") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice" ADD CONSTRAINT "fk_invoice_id_status" FOREIGN KEY ("id_status") REFERENCES "status"("id_status") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice" ADD CONSTRAINT "fk_invoice_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice" ADD CONSTRAINT "fk_invoice_id_issuer_customer_supplier" FOREIGN KEY ("id_issuer_customer_supplier") REFERENCES "customer_supplier"("id_customer_supplier") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice" ADD CONSTRAINT "fk_invoice_id_proyect" FOREIGN KEY ("id_proyect") REFERENCES "proyect"("id_proyect") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice_material_service" ADD CONSTRAINT "fk_invoice_material_service_id_invoice" FOREIGN KEY ("id_invoice") REFERENCES "invoice"("id_invoice") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice_material_service" ADD CONSTRAINT "fk_invoice_material_service_id_material" FOREIGN KEY ("id_material") REFERENCES "material"("id_material") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice_material_service" ADD CONSTRAINT "fk_invoice_material_service_id_service" FOREIGN KEY ("id_service") REFERENCES "service"("id_service") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice_material_service" ADD CONSTRAINT "fk_invoice_material_service_id_authorized" FOREIGN KEY ("id_authorized") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice_material_service" ADD CONSTRAINT "fk_invoice_material_service_id_status" FOREIGN KEY ("id_status") REFERENCES "status"("id_status") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice_material_service" ADD CONSTRAINT "fk_invoice_material_service_id_buyer" FOREIGN KEY ("id_buyer") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice_material_service" ADD CONSTRAINT "fk_invoice_material_service_id_customer_supplier" FOREIGN KEY ("id_customer_supplier") REFERENCES "customer_supplier"("id_customer_supplier") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice_material_service" ADD CONSTRAINT "fk_invoice_material_service_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice_material_service" ADD CONSTRAINT "fk_invoice_material_service_id_product" FOREIGN KEY ("id_product") REFERENCES "product"("id_product") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "invoice_material_service" ADD CONSTRAINT "fk_invoice_material_service_id_unit" FOREIGN KEY ("id_unit") REFERENCES "unit"("id_unit") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "product_family" ADD CONSTRAINT "fk_product_family_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "incident_type" ADD CONSTRAINT "fk_incident_type_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "incident" ADD CONSTRAINT "fk_incident_id_incident_type" FOREIGN KEY ("id_incident_type") REFERENCES "incident_type"("id_incident_type") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "incident" ADD CONSTRAINT "fk_incident_id_user" FOREIGN KEY ("id_user") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "incident" ADD CONSTRAINT "fk_incident_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "incident_detail" ADD CONSTRAINT "fk_incident_detail_id_incident_type" FOREIGN KEY ("id_incident_type") REFERENCES "incident_type"("id_incident_type") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "incident_detail" ADD CONSTRAINT "fk_incident_detail_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "brand" ADD CONSTRAINT "fk_brand_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "unit" ADD CONSTRAINT "fk_unit_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "material" ADD CONSTRAINT "fk_material_id_unit" FOREIGN KEY ("id_unit") REFERENCES "unit"("id_unit") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "material" ADD CONSTRAINT "fk_material_id_brand" FOREIGN KEY ("id_brand") REFERENCES "brand"("id_brand") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "material" ADD CONSTRAINT "fk_material_id_product_family" FOREIGN KEY ("id_product_family") REFERENCES "product_family"("id_product_family") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "material" ADD CONSTRAINT "fk_material_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "material_component" ADD CONSTRAINT "fk_material_component_id_material" FOREIGN KEY ("id_material") REFERENCES "material"("id_material") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "material_component" ADD CONSTRAINT "fk_material_component_id_component" FOREIGN KEY ("id_component") REFERENCES "material"("id_material") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "material_component" ADD CONSTRAINT "fk_material_component_id_unit" FOREIGN KEY ("id_unit") REFERENCES "unit"("id_unit") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "material_component" ADD CONSTRAINT "fk_material_component_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "movement" ADD CONSTRAINT "fk_movement_id_fiscal_account" FOREIGN KEY ("id_fiscal_account") REFERENCES "fiscal_account"("id_fiscal_account") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "movement" ADD CONSTRAINT "fk_movement_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "location_type" ADD CONSTRAINT "fk_location_type_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "location" ADD CONSTRAINT "fk_location_id_location_type" FOREIGN KEY ("id_location_type") REFERENCES "location_type"("id_location_type") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "location" ADD CONSTRAINT "fk_location_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "product" ADD CONSTRAINT "fk_product_id_invoice" FOREIGN KEY ("id_invoice") REFERENCES "invoice"("id_invoice") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "product" ADD CONSTRAINT "fk_product_id_location" FOREIGN KEY ("id_location") REFERENCES "location"("id_location") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "product" ADD CONSTRAINT "fk_product_id_material" FOREIGN KEY ("id_material") REFERENCES "material"("id_material") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "product" ADD CONSTRAINT "fk_product_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_incident_product" ADD CONSTRAINT "fk_nm_incident_product_id_incident" FOREIGN KEY ("id_incident") REFERENCES "incident"("id_incident") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_incident_product" ADD CONSTRAINT "fk_nm_incident_product_id_product" FOREIGN KEY ("id_product") REFERENCES "product"("id_product") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_incident_product" ADD CONSTRAINT "fk_nm_incident_product_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "task" ADD CONSTRAINT "fk_task_owner" FOREIGN KEY ("owner") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "task" ADD CONSTRAINT "fk_task_id_proyect" FOREIGN KEY ("id_proyect") REFERENCES "proyect"("id_proyect") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "task" ADD CONSTRAINT "fk_task_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "task_note" ADD CONSTRAINT "fk_task_note_id_task" FOREIGN KEY ("id_task") REFERENCES "task"("id_task") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "task_note" ADD CONSTRAINT "fk_task_note_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "ticket" ADD CONSTRAINT "fk_ticket_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "fiscal_account" ADD CONSTRAINT "fk_fiscal_account_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "fiscal_stamp" ADD CONSTRAINT "fk_fiscal_stamp_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "fiscal_record" ADD CONSTRAINT "fk_fiscal_record_id_fiscal_account" FOREIGN KEY ("id_fiscal_account") REFERENCES "fiscal_account"("id_fiscal_account") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "fiscal_record" ADD CONSTRAINT "fk_fiscal_record_id_fiscal_stamp" FOREIGN KEY ("id_fiscal_stamp") REFERENCES "fiscal_stamp"("id_fiscal_stamp") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "fiscal_record" ADD CONSTRAINT "fk_fiscal_record_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "service" ADD CONSTRAINT "fk_service_id_brand" FOREIGN KEY ("id_brand") REFERENCES "brand"("id_brand") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "service" ADD CONSTRAINT "fk_service_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "status" ADD CONSTRAINT "fk_status_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "theme" ADD CONSTRAINT "fk_theme_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "department" ADD CONSTRAINT "fk_department_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "subdepartment" ADD CONSTRAINT "fk_subdepartment_id_department" FOREIGN KEY ("id_department") REFERENCES "department"("id_department") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "subdepartment" ADD CONSTRAINT "fk_subdepartment_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "level" ADD CONSTRAINT "fk_level_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "field" ADD CONSTRAINT "fk_field_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "permission" ADD CONSTRAINT "fk_permission_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "permission" ADD CONSTRAINT "fk_permission_authorized_by" FOREIGN KEY ("authorized_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "permission" ADD CONSTRAINT "fk_permission_id_department" FOREIGN KEY ("id_department") REFERENCES "department"("id_department") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "permission" ADD CONSTRAINT "fk_permission_id_subdepartment" FOREIGN KEY ("id_subdepartment") REFERENCES "subdepartment"("id_subdepartment") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "permission" ADD CONSTRAINT "fk_permission_id_level" FOREIGN KEY ("id_level") REFERENCES "level"("id_level") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_field_permission" ADD CONSTRAINT "fk_nm_field_permission_id_field" FOREIGN KEY ("id_field") REFERENCES "field"("id_field") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_field_permission" ADD CONSTRAINT "fk_nm_field_permission_id_permission" FOREIGN KEY ("id_permission") REFERENCES "permission"("id_permission") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_field_permission" ADD CONSTRAINT "fk_nm_field_permission_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "event_log" ADD CONSTRAINT "fk_event_log_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "task_type" ADD CONSTRAINT "fk_task_type_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "template" ADD CONSTRAINT "fk_template_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_template_task" ADD CONSTRAINT "fk_nm_template_task_id_task" FOREIGN KEY ("id_task") REFERENCES "task"("id_task") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_template_task" ADD CONSTRAINT "fk_nm_template_task_id_template" FOREIGN KEY ("id_template") REFERENCES "template"("id_template") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_template_task" ADD CONSTRAINT "fk_nm_template_task_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "survey_question" ADD CONSTRAINT "fk_survey_question_owner" FOREIGN KEY ("owner") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "survey_question" ADD CONSTRAINT "fk_survey_question_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "survey_multiple_answer" ADD CONSTRAINT "fk_survey_multiple_answer_id_survey_question" FOREIGN KEY ("id_survey_question") REFERENCES "survey_question"("id_survey_question") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "survey_multiple_answer" ADD CONSTRAINT "fk_survey_multiple_answer_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_survey_user" ADD CONSTRAINT "fk_nm_survey_user_id_survey_question" FOREIGN KEY ("id_survey_question") REFERENCES "survey_question"("id_survey_question") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_survey_user" ADD CONSTRAINT "fk_nm_survey_user_id_survey_multiple_answer" FOREIGN KEY ("id_survey_multiple_answer") REFERENCES "survey_multiple_answer"("id_survey_multiple_answer") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_survey_user" ADD CONSTRAINT "fk_nm_survey_user_id_user" FOREIGN KEY ("id_user") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_survey_user" ADD CONSTRAINT "fk_nm_survey_user_status" FOREIGN KEY ("status") REFERENCES "status"("id_status") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "nm_survey_user" ADD CONSTRAINT "fk_nm_survey_user_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "entity_permission" ADD CONSTRAINT "fk_entity_permission_id_permission" FOREIGN KEY ("id_permission") REFERENCES "permission"("id_permission") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "entity_permission" ADD CONSTRAINT "fk_entity_permission_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "inventory_status" ADD CONSTRAINT "fk_inventory_status_id_department" FOREIGN KEY ("id_department") REFERENCES "department"("id_department") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "inventory_status" ADD CONSTRAINT "fk_inventory_status_id_subdepartment" FOREIGN KEY ("id_subdepartment") REFERENCES "subdepartment"("id_subdepartment") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "inventory_status" ADD CONSTRAINT "fk_inventory_status_id_minimum_level" FOREIGN KEY ("id_minimum_level") REFERENCES "level"("id_level") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "inventory_status" ADD CONSTRAINT "fk_inventory_status_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "product_sale_config" ADD CONSTRAINT "fk_product_sale_config_id_product" FOREIGN KEY ("id_product") REFERENCES "product"("id_product") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "product_sale_config" ADD CONSTRAINT "fk_product_sale_config_id_inventory_status" FOREIGN KEY ("id_inventory_status") REFERENCES "inventory_status"("id_inventory_status") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "product_sale_config" ADD CONSTRAINT "fk_product_sale_config_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "public_api_key" ADD CONSTRAINT "fk_public_api_key_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "password_reset_token" ADD CONSTRAINT "fk_password_reset_token_id_user" FOREIGN KEY ("id_user") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMIT;
