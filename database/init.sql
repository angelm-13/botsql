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
  "is_employee" BOOLEAN NOT NULL DEFAULT FALSE,
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
  "sla_level" VARCHAR(20) NOT NULL DEFAULT 'standard' CHECK ("sla_level" IN ('standard', 'premium')),
  "credit_limit" NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK ("credit_limit" >= 0),
  "logistics_notes" TEXT NULL,
  "is_principal" BOOLEAN NOT NULL DEFAULT FALSE,
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
  "proyect_status" VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK ("proyect_status" IN ('draft', 'submitted', 'authorized', 'denied', 'blocked', 'in_progress', 'stopped', 'completed')),
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
  "id_proyect" INTEGER NULL,
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
  "invoice_direction" VARCHAR(20) NULL CHECK ("invoice_direction" IN ('venta', 'compra', 'sin_clasificar')),
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
  "id_location_reference" INTEGER NULL,
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

CREATE TABLE IF NOT EXISTS "proyect_event" (
  "id_proyect_event" SERIAL NOT NULL,
  "id_proyect" INTEGER NOT NULL REFERENCES "proyect"("id_proyect"),
  "id_task" INTEGER NULL REFERENCES "task"("id_task"),
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "author_role" VARCHAR(100) NULL,
  "event_type" VARCHAR(30) NOT NULL CHECK ("event_type" IN ('created', 'status_changed', 'message', 'task_event')),
  "previous_status" VARCHAR(20) NULL,
  "new_status" VARCHAR(20) NULL,
  "content" TEXT NULL,
  "reason" TEXT NULL,
  "review_date" TIMESTAMP NULL,
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id_proyect_event")
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
  "menu_location" VARCHAR(20) NOT NULL DEFAULT 'sidebar' CHECK ("menu_location" IN ('sidebar', 'settings', 'hidden')),
  "menu_group" VARCHAR(80) NULL,
  "menu_group_icon" VARCHAR(40) NULL,
  "menu_label" VARCHAR(100) NULL,
  "menu_order" INTEGER NOT NULL DEFAULT 100,
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
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
CREATE INDEX IF NOT EXISTS "ix_proyect_status" ON "proyect" ("proyect_status") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_proyect_owner" ON "proyect" ("created_by") WHERE "deletion_date" IS NULL;
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
CREATE INDEX IF NOT EXISTS "ix_proyect_event_project_date" ON "proyect_event" ("id_proyect", "creation_date", "id_proyect_event");
CREATE INDEX IF NOT EXISTS "ix_proyect_event_task" ON "proyect_event" ("id_task") WHERE "id_task" IS NOT NULL;
CREATE INDEX IF NOT EXISTS "ix_proyect_event_author" ON "proyect_event" ("created_by");
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
CREATE INDEX IF NOT EXISTS "ix_entity_permission_navigation" ON "entity_permission" ("id_permission", "menu_location", "menu_group", "menu_order") WHERE "deletion_date" IS NULL;
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
  ALTER TABLE "bank_account" ADD CONSTRAINT "fk_bank_account_id_proyect" FOREIGN KEY ("id_proyect") REFERENCES "proyect"("id_proyect") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "bank_account" ADD CONSTRAINT "fk_bank_account_created_by" FOREIGN KEY ("created_by") REFERENCES "user"("id_user") DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TABLE "bank_account" ADD CONSTRAINT "fk_bank_account_id_proyect" FOREIGN KEY ("id_proyect") REFERENCES "proyect"("id_proyect") DEFERRABLE INITIALLY DEFERRED;
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
-- uq_entity_permission_permission_entity: varios INSERT de este mismo archivo
-- (mas abajo) y de database/seed.sql usan ON CONFLICT (id_permission, entity_name),
-- que exige que este constraint ya exista.
-- Se capturan duplicate_object Y duplicate_table. Una restriccion UNIQUE crea un
-- indice con su mismo nombre, y si el indice ya existe -porque la migracion
-- 20260822122000 creo la restriccion antes- Postgres lanza duplicate_table, que
-- la guarda de duplicate_object no atrapa. Ese error abortaba init.sql ENTERO:
-- se veia como un aviso "no fatal" y dejaba sin ejecutar todo lo que sigue.
-- Medido borrando el volumen y levantando de cero.
DO $$ BEGIN
  ALTER TABLE "entity_permission" ADD CONSTRAINT "uq_entity_permission_permission_entity" UNIQUE ("id_permission", "entity_name");
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL;
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

CREATE TABLE IF NOT EXISTS "bank_statement" (
  "id_bank_statement" SERIAL PRIMARY KEY,
  "id_bank_account" INTEGER NOT NULL REFERENCES "bank_account"("id_bank_account"),
  "id_proyect" INTEGER NOT NULL REFERENCES "proyect"("id_proyect"),
  "file_hash" VARCHAR(64) NOT NULL UNIQUE,
  "original_filename" VARCHAR(255) NOT NULL,
  "period_start" DATE NULL,
  "period_end" DATE NULL,
  "total_debits" NUMERIC(14,2) NOT NULL,
  "total_credits" NUMERIC(14,2) NOT NULL,
  "status" VARCHAR(30) NOT NULL,
  "starting_balance" NUMERIC(14,2) NULL,
  "ending_balance" NUMERIC(14,2) NULL,
  "average_balance" NUMERIC(14,2) NULL,
  "parser_name" VARCHAR(80) NULL,
  "extraction_confidence" NUMERIC(5,2) NULL,
  "extraction_errors" JSONB NULL,
  "reconciliation_data" JSONB NULL,
  "created_by" INTEGER NOT NULL,
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "bank_statement_movement" (
  "id_bank_statement_movement" SERIAL PRIMARY KEY,
  "id_bank_statement" INTEGER NOT NULL REFERENCES "bank_statement"("id_bank_statement"),
  "movement_date" DATE NOT NULL,
  "description" VARCHAR(500) NOT NULL,
  "debit" NUMERIC(14,2) NOT NULL DEFAULT 0,
  "credit" NUMERIC(14,2) NOT NULL DEFAULT 0,
  "sequence_number" INTEGER NULL,
  "settlement_date" DATE NULL,
  "code" VARCHAR(30) NULL,
  "reference" VARCHAR(100) NULL,
  "order_number" VARCHAR(100) NULL,
  "origin_bank" VARCHAR(100) NULL,
  "origin_account" VARCHAR(50) NULL,
  "beneficiary" VARCHAR(200) NULL,
  "balance" NUMERIC(14,2) NULL,
  "reconciliation_note" VARCHAR(500) NULL,
  "id_invoice" INTEGER NULL REFERENCES "invoice"("id_invoice"),
  CHECK (("debit" > 0 AND "credit" = 0) OR ("credit" > 0 AND "debit" = 0))
);

CREATE INDEX IF NOT EXISTS "ix_bank_statement_movement_statement" ON "bank_statement_movement" ("id_bank_statement");
CREATE UNIQUE INDEX IF NOT EXISTS "uq_bank_statement_movement_row" ON "bank_statement_movement" ("id_bank_statement", "sequence_number") WHERE "sequence_number" IS NOT NULL;

CREATE TABLE IF NOT EXISTS "logistics_address" (
  "id_logistics_address" SERIAL PRIMARY KEY,
  "id_customer_supplier" INTEGER NOT NULL REFERENCES "customer_supplier"("id_customer_supplier"),
  "name" VARCHAR(150) NOT NULL,
  "address_line" VARCHAR(250) NOT NULL,
  "city" VARCHAR(100) NULL,
  "state" VARCHAR(100) NULL,
  "country" VARCHAR(2) NULL DEFAULT 'MX',
  "postal_code" VARCHAR(10) NULL,
  "address_type" VARCHAR(30) NOT NULL DEFAULT 'operativa',
  "status" VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK ("status" IN ('activo', 'inactivo')),
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS "logistics_contract" (
  "id_logistics_contract" SERIAL PRIMARY KEY,
  "id_customer_supplier" INTEGER NOT NULL REFERENCES "customer_supplier"("id_customer_supplier"),
  "contract_number" VARCHAR(80) NOT NULL UNIQUE,
  "start_date" DATE NOT NULL,
  "end_date" DATE NULL,
  "sla_level" VARCHAR(20) NOT NULL DEFAULT 'standard' CHECK ("sla_level" IN ('standard', 'premium')),
  "status" VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK ("status" IN ('activo', 'inactivo')),
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL,
  CHECK ("end_date" IS NULL OR "end_date" >= "start_date")
);

CREATE TABLE IF NOT EXISTS "logistics_rate" (
  "id_logistics_rate" SERIAL PRIMARY KEY,
  "id_customer_supplier" INTEGER NOT NULL REFERENCES "customer_supplier"("id_customer_supplier"),
  "service_type" VARCHAR(100) NOT NULL,
  "origin" VARCHAR(150) NULL,
  "destination" VARCHAR(150) NULL,
  "unit_type" VARCHAR(80) NULL,
  "amount" NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK ("amount" >= 0),
  "currency" VARCHAR(3) NOT NULL DEFAULT 'MXN' CHECK ("currency" IN ('MXN', 'USD')),
  "status" VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK ("status" IN ('activo', 'inactivo')),
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS "ix_logistics_address_customer" ON "logistics_address" ("id_customer_supplier") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_contract_customer" ON "logistics_contract" ("id_customer_supplier") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_rate_customer" ON "logistics_rate" ("id_customer_supplier") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_rate_route" ON "logistics_rate" ("origin", "destination") WHERE "deletion_date" IS NULL;

CREATE TABLE IF NOT EXISTS "logistics_unit" (
  "id_logistics_unit" SERIAL PRIMARY KEY,
  "plate" VARCHAR(30) NOT NULL UNIQUE,
  "unit_type" VARCHAR(80) NOT NULL,
  "mileage" NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK ("mileage" >= 0),
  "availability_status" VARCHAR(30) NOT NULL DEFAULT 'disponible' CHECK ("availability_status" IN ('disponible', 'en viaje', 'mantenimiento', 'fuera de servicio')),
  "insurance_expiration" DATE NULL,
  "verification_expiration" DATE NULL,
  "policy_number" VARCHAR(100) NULL,
  "fuel_efficiency" NUMERIC(10,2) NULL CHECK ("fuel_efficiency" >= 0),
  "status" VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK ("status" IN ('activo', 'inactivo')),
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS "logistics_trailer" (
  "id_logistics_trailer" SERIAL PRIMARY KEY,
  "plate" VARCHAR(30) NOT NULL UNIQUE,
  "trailer_type" VARCHAR(80) NOT NULL,
  "capacity" NUMERIC(12,2) NULL CHECK ("capacity" >= 0),
  "status" VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK ("status" IN ('activo', 'inactivo')),
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS "logistics_operator" (
  "id_logistics_operator" SERIAL PRIMARY KEY,
  "full_name" VARCHAR(150) NOT NULL,
  "license_number" VARCHAR(80) NOT NULL UNIQUE,
  "license_expiration" DATE NULL,
  "status" VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK ("status" IN ('activo', 'inactivo')),
  "contact_phone" VARCHAR(40) NULL,
  "performance_score" NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK ("performance_score" >= 0),
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS "logistics_maintenance" (
  "id_logistics_maintenance" SERIAL PRIMARY KEY,
  "id_logistics_unit" INTEGER NOT NULL REFERENCES "logistics_unit"("id_logistics_unit"),
  "maintenance_type" VARCHAR(80) NOT NULL,
  "scheduled_at" DATE NULL,
  "closed_at" DATE NULL,
  "cost" NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK ("cost" >= 0),
  "status" VARCHAR(20) NOT NULL DEFAULT 'abierta' CHECK ("status" IN ('abierta', 'en proceso', 'cerrada')),
  "description" TEXT NULL,
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL,
  CHECK ("closed_at" IS NULL OR "scheduled_at" IS NULL OR "closed_at" >= "scheduled_at"),
  CHECK (("status" = 'cerrada' AND "closed_at" IS NOT NULL) OR ("status" <> 'cerrada' AND "closed_at" IS NULL))
);

CREATE INDEX IF NOT EXISTS "ix_logistics_unit_availability" ON "logistics_unit" ("availability_status") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_trailer_type" ON "logistics_trailer" ("trailer_type") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_operator_status" ON "logistics_operator" ("status") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_maintenance_unit" ON "logistics_maintenance" ("id_logistics_unit") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_maintenance_status" ON "logistics_maintenance" ("status", "scheduled_at") WHERE "deletion_date" IS NULL;

CREATE TABLE IF NOT EXISTS "logistics_warehouse" (
  "id_logistics_warehouse" SERIAL PRIMARY KEY,
  "name" VARCHAR(150) NOT NULL UNIQUE,
  "address" VARCHAR(300) NULL,
  "capacity" NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK ("capacity" >= 0),
  "status" VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK ("status" IN ('activo', 'inactivo')),
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS "logistics_location" (
  "id_logistics_location" SERIAL PRIMARY KEY,
  "id_logistics_warehouse" INTEGER NOT NULL REFERENCES "logistics_warehouse"("id_logistics_warehouse"),
  "code" VARCHAR(80) NOT NULL,
  "zone" VARCHAR(80) NULL,
  "location_type" VARCHAR(80) NULL,
  "capacity" NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK ("capacity" >= 0),
  "status" VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK ("status" IN ('activo', 'inactivo')),
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL,
  CONSTRAINT "uq_logistics_location_warehouse_code" UNIQUE ("id_logistics_warehouse", "code")
);

CREATE TABLE IF NOT EXISTS "logistics_inventory" (
  "id_logistics_inventory" SERIAL PRIMARY KEY,
  "id_customer_supplier" INTEGER NOT NULL REFERENCES "customer_supplier"("id_customer_supplier"),
  "id_logistics_location" INTEGER NOT NULL REFERENCES "logistics_location"("id_logistics_location"),
  "sku" VARCHAR(100) NOT NULL,
  "description" VARCHAR(300) NULL,
  "quantity" NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK ("quantity" >= 0),
  "lot" VARCHAR(100) NULL,
  "serial_number" VARCHAR(120) NULL,
  "status" VARCHAR(30) NOT NULL DEFAULT 'activo' CHECK ("status" IN ('activo', 'pendiente_surtido', 'surtido', 'inactivo')),
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS "logistics_rack" (
  "id_logistics_rack" SERIAL PRIMARY KEY,
  "id_customer_supplier" INTEGER NOT NULL REFERENCES "customer_supplier"("id_customer_supplier"),
  "id_logistics_location" INTEGER NOT NULL REFERENCES "logistics_location"("id_logistics_location"),
  "code" VARCHAR(100) NOT NULL UNIQUE,
  "status" VARCHAR(30) NOT NULL DEFAULT 'en_cliente' CHECK ("status" IN ('en_cliente', 'en_almacen', 'pendiente_retorno', 'en_reparacion')),
  "condition" VARCHAR(20) NOT NULL DEFAULT 'bueno' CHECK ("condition" IN ('bueno', 'regular', 'dañado')),
  "quantity" INTEGER NOT NULL DEFAULT 1 CHECK ("quantity" >= 0),
  "sent_at" DATE NULL,
  "received_at" DATE NULL,
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS "ix_logistics_warehouse_status" ON "logistics_warehouse" ("status") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_location_warehouse" ON "logistics_location" ("id_logistics_warehouse") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_location_status" ON "logistics_location" ("status", "zone") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_inventory_client" ON "logistics_inventory" ("id_customer_supplier") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_inventory_location" ON "logistics_inventory" ("id_logistics_location") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_inventory_sku" ON "logistics_inventory" ("sku") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_rack_client" ON "logistics_rack" ("id_customer_supplier") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_rack_location" ON "logistics_rack" ("id_logistics_location") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_rack_status" ON "logistics_rack" ("status", "condition") WHERE "deletion_date" IS NULL;

CREATE TABLE IF NOT EXISTS "logistics_quotation" (
  "id_logistics_quotation" SERIAL PRIMARY KEY,
  "id_customer_supplier" INTEGER NOT NULL REFERENCES "customer_supplier"("id_customer_supplier"),
  "folio" VARCHAR(80) NOT NULL UNIQUE,
  "service_type" VARCHAR(100) NOT NULL,
  "origin" TEXT NOT NULL,
  "destination" TEXT NOT NULL,
  "cargo_type" VARCHAR(120),
  "unit_required" VARCHAR(120),
  "kilometers" NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK ("kilometers" >= 0),
  "maneuvers" NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK ("maneuvers" >= 0),
  "storage" NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK ("storage" >= 0),
  "additional_services" JSONB NOT NULL DEFAULT '{}'::jsonb,
  "total" NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK ("total" >= 0),
  "source_branch_reference" VARCHAR(120),
  "status" VARCHAR(30) NOT NULL DEFAULT 'borrador' CHECK ("status" IN ('borrador', 'enviada', 'aceptada', 'rechazada', 'vencida', 'cancelada')),
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS "logistics_service_request" (
  "id_logistics_service_request" SERIAL PRIMARY KEY,
  "id_customer_supplier" INTEGER NOT NULL REFERENCES "customer_supplier"("id_customer_supplier"),
  "id_logistics_quotation" INTEGER REFERENCES "logistics_quotation"("id_logistics_quotation"),
  "request_number" VARCHAR(80) NOT NULL UNIQUE,
  "request_type" VARCHAR(100) NOT NULL,
  "origin" TEXT,
  "destination" TEXT,
  "requested_pickup_at" TIMESTAMP,
  "requested_delivery_at" TIMESTAMP,
  "status" VARCHAR(30) NOT NULL DEFAULT 'solicitado' CHECK ("status" IN ('solicitado', 'aprobado', 'programado', 'cancelado')),
  "priority" VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK ("priority" IN ('baja', 'normal', 'alta', 'urgente')),
  "description" TEXT,
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL,
  CHECK ("requested_delivery_at" IS NULL OR "requested_pickup_at" IS NULL OR "requested_delivery_at" >= "requested_pickup_at")
);

CREATE TABLE IF NOT EXISTS "logistics_trip" (
  "id_logistics_trip" SERIAL PRIMARY KEY,
  "id_logistics_service_request" INTEGER NOT NULL REFERENCES "logistics_service_request"("id_logistics_service_request"),
  "id_customer_supplier" INTEGER NOT NULL REFERENCES "customer_supplier"("id_customer_supplier"),
  "folio" VARCHAR(80) NOT NULL UNIQUE,
  "id_logistics_unit" INTEGER REFERENCES "logistics_unit"("id_logistics_unit"),
  "id_logistics_trailer" INTEGER REFERENCES "logistics_trailer"("id_logistics_trailer"),
  "id_logistics_operator" INTEGER REFERENCES "logistics_operator"("id_logistics_operator"),
  "supplier_reference" VARCHAR(120),
  "route_reference" VARCHAR(120),
  "expediente_reference" VARCHAR(120),
  "status" VARCHAR(30) NOT NULL DEFAULT 'solicitado' CHECK ("status" IN ('solicitado', 'planeado', 'asignado', 'cargado', 'en tránsito', 'en ruta', 'retrasado', 'entregado', 'cerrado', 'facturado', 'cancelado')),
  "planned_pickup_at" TIMESTAMP,
  "planned_delivery_at" TIMESTAMP,
  "actual_pickup_at" TIMESTAMP,
  "actual_delivery_at" TIMESTAMP,
  "planned_cost" NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK ("planned_cost" >= 0),
  "actual_cost" NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK ("actual_cost" >= 0),
  "revenue" NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK ("revenue" >= 0),
  "kilometers" NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK ("kilometers" >= 0),
  "restrictions" TEXT,
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL,
  CHECK ("planned_delivery_at" IS NULL OR "planned_pickup_at" IS NULL OR "planned_delivery_at" >= "planned_pickup_at"),
  CHECK ("actual_delivery_at" IS NULL OR "actual_pickup_at" IS NULL OR "actual_delivery_at" >= "actual_pickup_at")
);

CREATE TABLE IF NOT EXISTS "logistics_evidence" (
  "id_logistics_evidence" SERIAL PRIMARY KEY,
  "id_logistics_trip" INTEGER NOT NULL REFERENCES "logistics_trip"("id_logistics_trip"),
  "evidence_type" VARCHAR(80) NOT NULL,
  "photo_path" VARCHAR(300),
  "signature_path" VARCHAR(300),
  "source_document_reference" VARCHAR(120),
  "latitude" NUMERIC(10,7) CHECK ("latitude" IS NULL OR "latitude" BETWEEN -90 AND 90),
  "longitude" NUMERIC(10,7) CHECK ("longitude" IS NULL OR "longitude" BETWEEN -180 AND 180),
  "comments" TEXT,
  "captured_by" INTEGER REFERENCES "user"("id_user"),
  "captured_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS "logistics_incident" (
  "id_logistics_incident" SERIAL PRIMARY KEY,
  "id_logistics_trip" INTEGER NOT NULL REFERENCES "logistics_trip"("id_logistics_trip"),
  "incident_type" VARCHAR(100) NOT NULL,
  "severity" VARCHAR(20) NOT NULL DEFAULT 'media' CHECK ("severity" IN ('baja', 'media', 'alta', 'critica')),
  "description" TEXT NOT NULL,
  "responsible_user_id" INTEGER REFERENCES "user"("id_user"),
  "status" VARCHAR(20) NOT NULL DEFAULT 'abierta' CHECK ("status" IN ('abierta', 'en_proceso', 'resuelta', 'cerrada', 'cancelada')),
  "created_by" INTEGER NOT NULL REFERENCES "user"("id_user"),
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS "ix_logistics_quotation_client" ON "logistics_quotation" ("id_customer_supplier") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_quotation_status" ON "logistics_quotation" ("status") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_service_request_client" ON "logistics_service_request" ("id_customer_supplier") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_service_request_quotation" ON "logistics_service_request" ("id_logistics_quotation") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_service_request_status" ON "logistics_service_request" ("status", "priority") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_trip_request" ON "logistics_trip" ("id_logistics_service_request") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_trip_client" ON "logistics_trip" ("id_customer_supplier") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_trip_assignment" ON "logistics_trip" ("id_logistics_unit", "id_logistics_trailer", "id_logistics_operator") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_trip_status" ON "logistics_trip" ("status", "planned_pickup_at") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_evidence_trip" ON "logistics_evidence" ("id_logistics_trip") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_incident_trip" ON "logistics_incident" ("id_logistics_trip") WHERE "deletion_date" IS NULL;
CREATE INDEX IF NOT EXISTS "ix_logistics_incident_status" ON "logistics_incident" ("status", "severity") WHERE "deletion_date" IS NULL;

-- Bootstrap minimo para romper el ciclo de FKs circulares (user <->
-- permission/proyect/status/customer_supplier, todas con created_by=1) en
-- una instalacion limpia. Sin esto, las filas de catalogo de abajo
-- (field/entity_permission con created_by=1) fallan porque no existe
-- ningun "user" todavia -- error real visto al desplegar torredigital-prod
-- desde cero, algo que tyakxa-dev nunca ejercito porque su esquema se armo
-- de forma organica con el tiempo, no desde un volumen vacio.
--
-- Password TEMPORAL (hash de "test password", el mismo default documentado
-- en init_db.py). `python init_db.py` la reemplaza por el valor real de
-- BOOTSTRAP_ADMIN_PASSWORD la primera vez que corre -- correrlo cuanto
-- antes despues del primer deploy, porque hasta entonces el admin1 real
-- queda con esta password conocida.
--
-- Todo con ON CONFLICT DO NOTHING: si estas filas ya existen (porque el
-- volumen no estaba realmente vacio), no se tocan.
INSERT INTO "department" ("id_department", "department_description", "created_by")
VALUES (1, 'General', 1)
ON CONFLICT ("id_department") DO NOTHING;

INSERT INTO "subdepartment" ("id_subdepartment", "subdepartment_description", "id_department", "created_by")
VALUES (1, 'General', 1, 1)
ON CONFLICT ("id_subdepartment") DO NOTHING;

INSERT INTO "level" ("id_level", "level_description", "created_by")
VALUES (1, 'General', 1)
ON CONFLICT ("id_level") DO NOTHING;

INSERT INTO "status" ("id_status", "status_description", "category", "is_terminal", "created_by")
VALUES (1, 'active', 'general', TRUE, 1)
ON CONFLICT ("id_status") DO NOTHING;

INSERT INTO "permission" ("id_permission", "permission_description", "created_by", "authorized_by", "id_department", "id_subdepartment", "id_level")
VALUES (1, 'Administrator', 1, 1, 1, 1, 1)
ON CONFLICT ("id_permission") DO NOTHING;

INSERT INTO "customer_supplier" ("id_customer_supplier", "name", "type", "is_principal", "id_user", "created_by")
VALUES (1, 'Interno', 'supplier', TRUE, 1, 1)
ON CONFLICT ("id_customer_supplier") DO NOTHING;

INSERT INTO "proyect" ("id_proyect", "id_customer_supplier", "leader", "proyect_description", "proyect_status", "created_by")
VALUES (1, 1, 1, 'Proyecto por defecto', 'draft', 1)
ON CONFLICT ("id_proyect") DO NOTHING;

INSERT INTO "user" (
  "id_user", "created_by", "email", "first_name", "id_permission", "full_name",
  "id_proyect", "last_name_father", "last_name_mother", "password", "supervisor",
  "id_status", "user_type", "username"
)
VALUES (
  1, 1, 'admin1@tyakxa.local', 'Admin', 1, 'Administrador Bootstrap',
  1, 'Bootstrap', 'System', '$2b$12$RxTtZtblFwu6ZsmtfNP9Meg6tYSZOCsVIZQLMe260W9seWcdrUma6', 1,
  1, 'admin', 'admin1'
)
ON CONFLICT ("id_user") DO NOTHING;

-- Las filas de arriba fijan id=1 a mano en columnas SERIAL. Eso NO avanza la
-- secuencia interna (nextval() seguiria devolviendo 1) -- el primer INSERT
-- posterior que dependa del default para generar su id chocaria contra estas
-- mismas filas con "duplicate key". Mismo patron ya usado en database/seed.sql
-- para el mismo problema.
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

INSERT INTO "field" ("table_name", "field_name", "created_by", "creation_date", "last_update_date")
SELECT source_column.table_name, source_column.column_name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM information_schema.columns source_column
WHERE source_column.table_schema = 'public'
  AND source_column.table_name IN ('logistics_quotation', 'logistics_service_request', 'logistics_trip', 'logistics_evidence', 'logistics_incident')
  AND NOT EXISTS (
    SELECT 1 FROM "field"
    WHERE "field"."table_name" = source_column.table_name
      AND "field"."field_name" = source_column.column_name
  );

CREATE TEMP TABLE tmp_ep_logistics_workflow AS
SELECT source_permission."id_permission", logistics_entity.entity_name,
       source_permission."control_type", 'sidebar'::varchar AS menu_location, 'Logística'::varchar AS menu_group,
       'truck'::varchar AS menu_group_icon, logistics_entity.menu_label, logistics_entity.menu_order,
       1 AS created_by
FROM "entity_permission" source_permission
CROSS JOIN (VALUES
  ('logistics_quotation', 'Cotizaciones', 170),
  ('logistics_service_request', 'Solicitudes', 180),
  ('logistics_trip', 'Viajes', 190),
  ('logistics_evidence', 'Evidencias', 200),
  ('logistics_incident', 'Incidencias', 210)
) AS logistics_entity(entity_name, menu_label, menu_order)
WHERE source_permission."entity_name" = 'customer_supplier'
  AND source_permission."deletion_date" IS NULL;

UPDATE "entity_permission" target SET
  "control_type" = source.control_type,
  "menu_location" = source.menu_location,
  "menu_group" = source.menu_group,
  "menu_group_icon" = source.menu_group_icon,
  "menu_label" = source.menu_label,
  "menu_order" = source.menu_order,
  "deletion_date" = NULL,
  "last_update_date" = CURRENT_TIMESTAMP
FROM tmp_ep_logistics_workflow source
WHERE target."id_permission" = source.id_permission
  AND target."entity_name" = source.entity_name;

INSERT INTO "entity_permission" (
  "id_permission", "entity_name", "control_type", "menu_location", "menu_group",
  "menu_group_icon", "menu_label", "menu_order", "created_by", "creation_date", "last_update_date"
)
SELECT source.id_permission, source.entity_name, source.control_type, source.menu_location, source.menu_group,
       source.menu_group_icon, source.menu_label, source.menu_order, source.created_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM tmp_ep_logistics_workflow source
WHERE NOT EXISTS (
    SELECT 1 FROM "entity_permission" target
    WHERE target."id_permission" = source.id_permission AND target."entity_name" = source.entity_name
);

DROP TABLE tmp_ep_logistics_workflow;

INSERT INTO "nm_field_permission" (
  "id_field", "id_permission", "control_type", "created_by", "creation_date", "last_update_date"
)
SELECT logistics_field."id_field", logistics_permission."id_permission", '15',
       1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM "field" logistics_field
JOIN "entity_permission" logistics_permission
  ON logistics_permission."entity_name" = logistics_field."table_name"
WHERE logistics_field."table_name" IN ('logistics_quotation', 'logistics_service_request', 'logistics_trip', 'logistics_evidence', 'logistics_incident')
  AND logistics_permission."deletion_date" IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM "nm_field_permission" existing
    WHERE existing."id_field" = logistics_field."id_field"
      AND existing."id_permission" = logistics_permission."id_permission"
      AND existing."deletion_date" IS NULL
  );

CREATE TABLE IF NOT EXISTS logistics_branch (
  id_logistics_branch SERIAL PRIMARY KEY,
  name VARCHAR(180) NOT NULL,
  postal_code VARCHAR(20),
  series VARCHAR(30),
  address TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (status IN ('activo', 'inactivo')),
  created_by INTEGER NOT NULL REFERENCES "user"(id_user),
  creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_shipment (
  id_logistics_shipment SERIAL PRIMARY KEY,
  id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
  shipment_number VARCHAR(80) NOT NULL UNIQUE,
  bl_number VARCHAR(120),
  provider VARCHAR(180),
  transport_mode VARCHAR(60),
  cargo_type VARCHAR(120),
  origin_port VARCHAR(180),
  destination_port VARCHAR(180),
  customs VARCHAR(180),
  status VARCHAR(30) NOT NULL DEFAULT 'registrado' CHECK (status IN ('registrado', 'en tránsito', 'en aduana', 'liberado', 'entregado')),
  tracking TEXT,
  created_by INTEGER NOT NULL REFERENCES "user"(id_user),
  creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_receivable (
  id_logistics_receivable SERIAL PRIMARY KEY,
  id_invoice INTEGER NOT NULL REFERENCES invoice(id_invoice),
  id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
  amount NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
  due_at DATE NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (status IN ('pendiente', 'pagado', 'vencido')),
  paid_at DATE,
  created_by INTEGER NOT NULL REFERENCES "user"(id_user),
  creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_file (
  id_logistics_file SERIAL PRIMARY KEY,
  id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
  folio VARCHAR(80) NOT NULL UNIQUE,
  origin TEXT NOT NULL,
  destination TEXT NOT NULL,
  id_logistics_branch INTEGER REFERENCES logistics_branch(id_logistics_branch),
  payment_form VARCHAR(10) NOT NULL DEFAULT '99',
  payment_method VARCHAR(10) NOT NULL DEFAULT 'PUE',
  cfdi_use VARCHAR(10) NOT NULL DEFAULT 'G03',
  status VARCHAR(20) NOT NULL DEFAULT 'abierto' CHECK (status IN ('abierto', 'facturando', 'facturado')),
  id_invoice INTEGER REFERENCES invoice(id_invoice),
  last_invoice_error TEXT,
  notes TEXT,
  created_by INTEGER NOT NULL REFERENCES "user"(id_user),
  creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deletion_date TIMESTAMP
);

ALTER TABLE logistics_trip ADD COLUMN IF NOT EXISTS id_logistics_file INTEGER REFERENCES logistics_file(id_logistics_file);

CREATE INDEX IF NOT EXISTS ix_logistics_shipment_client ON logistics_shipment(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_shipment_status ON logistics_shipment(status) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_branch_status ON logistics_branch(status) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_receivable_invoice ON logistics_receivable(id_invoice) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_receivable_client ON logistics_receivable(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_receivable_status ON logistics_receivable(status, due_at) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_file_client ON logistics_file(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_file_branch ON logistics_file(id_logistics_branch) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_file_invoice ON logistics_file(id_invoice) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_file_status ON logistics_file(status) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_trip_file ON logistics_trip(id_logistics_file) WHERE deletion_date IS NULL;

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT source_column.table_name, source_column.column_name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM information_schema.columns source_column
WHERE source_column.table_schema = 'public'
  AND source_column.table_name IN ('logistics_shipment', 'logistics_branch', 'logistics_receivable', 'logistics_file')
  AND NOT EXISTS (SELECT 1 FROM field WHERE field.table_name = source_column.table_name AND field.field_name = source_column.column_name);

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT 'logistics_trip', 'id_logistics_file', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM field WHERE table_name = 'logistics_trip' AND field_name = 'id_logistics_file');

CREATE TEMP TABLE tmp_ep_logistics_remaining AS
SELECT source_permission.id_permission, logistics_entity.entity_name,
       source_permission.control_type, 'sidebar'::varchar AS menu_location, 'Logística'::varchar AS menu_group,
       'truck'::varchar AS menu_group_icon, logistics_entity.menu_label, logistics_entity.menu_order,
       1 AS created_by
FROM entity_permission source_permission
JOIN (VALUES
  ('logistics_shipment', 'customer_supplier', 'Embarques', 220),
  ('logistics_branch', 'invoice', 'Sucursales', 230),
  ('logistics_receivable', 'invoice', 'Cuentas por cobrar', 240),
  ('logistics_file', 'customer_supplier', 'Expedientes', 250)
) AS logistics_entity(entity_name, source_entity, menu_label, menu_order)
  ON source_permission.entity_name = logistics_entity.source_entity
WHERE source_permission.deletion_date IS NULL;

UPDATE entity_permission target SET
  control_type = source.control_type,
  menu_location = source.menu_location,
  menu_group = source.menu_group,
  menu_group_icon = source.menu_group_icon,
  menu_label = source.menu_label,
  menu_order = source.menu_order,
  deletion_date = NULL,
  last_update_date = CURRENT_TIMESTAMP
FROM tmp_ep_logistics_remaining source
WHERE target.id_permission = source.id_permission
  AND target.entity_name = source.entity_name;

INSERT INTO entity_permission (
  id_permission, entity_name, control_type, menu_location, menu_group,
  menu_group_icon, menu_label, menu_order, created_by, creation_date, last_update_date
)
SELECT source.id_permission, source.entity_name, source.control_type, source.menu_location, source.menu_group,
       source.menu_group_icon, source.menu_label, source.menu_order, source.created_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM tmp_ep_logistics_remaining source
WHERE NOT EXISTS (
    SELECT 1 FROM entity_permission target
    WHERE target.id_permission = source.id_permission AND target.entity_name = source.entity_name
);

DROP TABLE tmp_ep_logistics_remaining;

INSERT INTO nm_field_permission (id_field, id_permission, control_type, created_by, creation_date, last_update_date)
SELECT logistics_field.id_field, logistics_permission.id_permission, '15', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM field logistics_field
JOIN entity_permission logistics_permission ON logistics_permission.entity_name = logistics_field.table_name
WHERE logistics_field.table_name IN ('logistics_shipment', 'logistics_branch', 'logistics_receivable', 'logistics_file')
  AND logistics_permission.deletion_date IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM nm_field_permission existing
    WHERE existing.id_field = logistics_field.id_field
      AND existing.id_permission = logistics_permission.id_permission
      AND existing.deletion_date IS NULL
  );

INSERT INTO nm_field_permission (id_field, id_permission, control_type, created_by, creation_date, last_update_date)
SELECT trip_field.id_field, trip_permission.id_permission, '15', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM field trip_field
JOIN entity_permission trip_permission ON trip_permission.entity_name = 'logistics_trip'
WHERE trip_field.table_name = 'logistics_trip'
  AND trip_field.field_name = 'id_logistics_file'
  AND trip_permission.deletion_date IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM nm_field_permission existing
    WHERE existing.id_field = trip_field.id_field
      AND existing.id_permission = trip_permission.id_permission
      AND existing.deletion_date IS NULL
  );

COMMIT;
