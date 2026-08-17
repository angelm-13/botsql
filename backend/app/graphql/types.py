from __future__ import annotations
import graphene
from graphene.types.json import JSONString

class UserType(graphene.ObjectType):
    """GraphQL type for user."""
    id_user = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    date_born = graphene.String()
    date_start = graphene.String()
    deletion_date = graphene.String()
    email = graphene.String()
    first_name = graphene.String()
    id_permission = graphene.Int()
    full_name = graphene.String()
    id_proyect = graphene.Int()
    last_name_father = graphene.String()
    last_name_mother = graphene.String()
    last_update_date = graphene.String()
    national_id = graphene.String()
    password = graphene.String()
    principal_phone = graphene.String()
    secundary_phone = graphene.String()
    ssn = graphene.String()
    supervisor = graphene.Int()
    base_salary = graphene.Float()
    hire_date = graphene.String()
    id_status = graphene.Int()
    tax_id = graphene.String()
    title = graphene.String()
    user_type = graphene.String()
    username = graphene.String()
    puesto = graphene.String()
    accepts_marketing = graphene.Boolean()

class UserMfaType(graphene.ObjectType):
    """GraphQL type for user_mfa."""
    id_user_mfa = graphene.Int()
    id_user = graphene.Int()
    secret = graphene.String()
    secret_iv = graphene.String()
    enabled = graphene.Boolean()
    failed_attempts = graphene.Int()
    locked_until = graphene.String()
    last_used_at = graphene.String()
    backup_codes = graphene.JSONString()
    created_at = graphene.String()
    updated_at = graphene.String()

class PayrollPeriodType(graphene.ObjectType):
    """GraphQL type for payroll_period."""
    id_payroll_period = graphene.Int()
    period_start = graphene.String()
    period_end = graphene.String()
    payment_date = graphene.String()
    id_status = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class PayrollDetailType(graphene.ObjectType):
    """GraphQL type for payroll_detail."""
    id_payroll_detail = graphene.Int()
    id_payroll_period = graphene.Int()
    id_user = graphene.Int()
    gross_salary = graphene.Float()
    total_earnings = graphene.Float()
    total_deductions = graphene.Float()
    net_pay = graphene.Float()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class PayrollConceptType(graphene.ObjectType):
    """GraphQL type for payroll_concept."""
    id_payroll_concept = graphene.Int()
    payroll_code = graphene.String()
    payroll_concept_description = graphene.String()
    type = graphene.String()
    is_taxable = graphene.Boolean()
    is_imss = graphene.Boolean()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class PayrollMovementType(graphene.ObjectType):
    """GraphQL type for payroll_movement."""
    id_payroll_movement = graphene.Int()
    id_payroll_detail = graphene.Int()
    id_payroll_concept = graphene.Int()
    amount = graphene.Float()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class CustomerSupplierType(graphene.ObjectType):
    """GraphQL type for customer_supplier."""
    id_customer_supplier = graphene.Int()
    postal_code = graphene.String()
    name = graphene.String()
    title = graphene.String()
    contact_name = graphene.String()
    phone = graphene.String()
    email = graphene.String()
    web_site = graphene.String()
    street = graphene.String()
    number_ext = graphene.String()
    number_int = graphene.String()
    neighborhood = graphene.String()
    city = graphene.String()
    geographic_state = graphene.String()
    fiscal_type = graphene.String()
    last_fiscal_certification_date = graphene.String()
    tax_id = graphene.String()
    type = graphene.String()
    id_user = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()
    path_logo = graphene.String()

class ProyectType(graphene.ObjectType):
    """GraphQL type for proyect."""
    id_proyect = graphene.Int()
    id_customer_supplier = graphene.Int()
    leader = graphene.Int()
    proyect_description = graphene.String()
    title = graphene.String()
    proyect_status = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class BankType(graphene.ObjectType):
    """GraphQL type for bank."""
    id_bank = graphene.Int()
    bank_name = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class BankAccountType(graphene.ObjectType):
    """GraphQL type for bank_account."""
    id_bank_account = graphene.Int()
    id_bank = graphene.Int()
    bank_account_description = graphene.String()
    branch = graphene.String()
    type = graphene.String()
    ordinary_interest = graphene.Float()
    moratorium_interest = graphene.Float()
    anuality = graphene.Float()
    reimbursement = graphene.Float()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class InvoiceType(graphene.ObjectType):
    """GraphQL type for invoice."""
    id_invoice = graphene.Int()
    date_emision = graphene.String()
    date_expiration = graphene.String()
    subtotal = graphene.Float()
    tax = graphene.Float()
    total = graphene.Float()
    invoice_status = graphene.String()
    payment_method = graphene.String()
    note = graphene.String()
    id_customer_supplier = graphene.Int()
    fiscal_reference = graphene.String()
    serie_csd = graphene.String()
    internationalization = graphene.String()
    currency = graphene.String()
    type_exchange_rate = graphene.Float()
    tax_certification_supplier = graphene.Int()
    fiscal_certify_serie = graphene.String()
    certification_date = graphene.String()
    cfdi_code = graphene.String()
    sat_code = graphene.String()
    sat_certification_code = graphene.String()
    id_status = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()
    nombre_emisor = graphene.String()
    lugar_expedicion = graphene.String()
    tipo_de_comprobante = graphene.String()
    rfc_receptor = graphene.String()
    nombre_receptor = graphene.String()
    regimen_fiscal_receptor = graphene.String()
    domicilio_fiscal_receptor = graphene.String()
    id_proveedor_de_sello = graphene.String()
    folio_fiscal = graphene.String()
    exportacion = graphene.String()
    folio = graphene.String()
    no_certificado_sat = graphene.String()
    sello_sat = graphene.String()
    sello_certificacion_sat = graphene.String()
    no_certificado = graphene.String()
    descuento = graphene.Float()
    metodo_pago = graphene.String()
    condiciones_pago = graphene.String()
    id_issuer_customer_supplier = graphene.Int()
    id_proyect = graphene.Int()
    apply_tax = graphene.Boolean()
    tax_rate = graphene.Float()
    commercial_terms = graphene.String()

class InvoiceMaterialServiceType(graphene.ObjectType):
    """GraphQL type for invoice_material_service."""
    id_invoice_material_service = graphene.Int()
    id_invoice = graphene.Int()
    id_material = graphene.Int()
    id_service = graphene.Int()
    invoice_material_service_description = graphene.String()
    max_requirement_date = graphene.String()
    is_directly_related_to_product_service_creation = graphene.Boolean()
    id_authorized = graphene.Int()
    id_status = graphene.Int()
    id_buyer = graphene.Int()
    id_customer_supplier = graphene.Int()
    gross_price = graphene.Float()
    quantity = graphene.Float()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()
    id_product = graphene.Int()
    line_type = graphene.String()
    tax_applicable = graphene.Boolean()
    line_tax = graphene.Float()
    line_total = graphene.Float()
    id_unit = graphene.Int()
    authorization_status = graphene.String()
    authorization_note = graphene.String()
    authorization_date = graphene.String()

class ProductFamilyType(graphene.ObjectType):
    """GraphQL type for product_family."""
    id_product_family = graphene.Int()
    product_family_description = graphene.String()
    type = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class IncidentTypeType(graphene.ObjectType):
    """GraphQL type for incident_type."""
    id_incident_type = graphene.Int()
    incident_type_description = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class IncidentType(graphene.ObjectType):
    """GraphQL type for incident."""
    id_incident = graphene.Int()
    incident_date = graphene.String()
    id_incident_type = graphene.Int()
    note = graphene.String()
    id_user = graphene.Int()
    incident_status = graphene.String()
    close_date = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()
    id_lider = graphene.String()

class IncidentDetailType(graphene.ObjectType):
    """GraphQL type for incident_detail."""
    id_incident_detail = graphene.Int()
    id_incident_type = graphene.Int()
    incident_detail_name = graphene.String()
    incident_detail_description = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class BrandType(graphene.ObjectType):
    """GraphQL type for brand."""
    id_brand = graphene.Int()
    brand_description = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class UnitType(graphene.ObjectType):
    """GraphQL type for unit."""
    id_unit = graphene.Int()
    unit_code = graphene.String()
    unit_name = graphene.String()
    unit_category = graphene.String()
    is_active = graphene.Boolean()
    symbol = graphene.String()
    measurement_system = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class MaterialType(graphene.ObjectType):
    """GraphQL type for material."""
    id_material = graphene.Int()
    material_description = graphene.String()
    id_unit = graphene.Int()
    id_brand = graphene.Int()
    id_product_family = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class MaterialComponentType(graphene.ObjectType):
    """GraphQL type for material_component."""
    id_material_component = graphene.Int()
    id_material = graphene.Int()
    id_component = graphene.Int()
    relation = graphene.Float()
    id_unit = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class MovementType(graphene.ObjectType):
    """GraphQL type for movement."""
    id_movement = graphene.Int()
    id_fiscal_account = graphene.Int()
    date = graphene.String()
    type = graphene.String()
    amount = graphene.Float()
    currency = graphene.String()
    type_exchange_rate = graphene.Float()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class LocationTypeType(graphene.ObjectType):
    """GraphQL type for location_type."""
    id_location_type = graphene.Int()
    location_type_description = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class LocationType(graphene.ObjectType):
    """GraphQL type for location."""
    id_location = graphene.Int()
    id_location_type = graphene.Int()
    location_description = graphene.String()
    id_location_reference = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class ProductType(graphene.ObjectType):
    """GraphQL type for product."""
    id_product = graphene.Int()
    id_invoice = graphene.Int()
    id_location = graphene.Int()
    id_material = graphene.Int()
    gross_price = graphene.Float()
    color = graphene.String()
    is_directly_related_to_product_service = graphene.Boolean()
    product_status = graphene.String()
    path_imagen = graphene.String()
    product_code = graphene.String()
    note = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()
    descripcion = graphene.String()
    cantidad = graphene.String()
    id_marca = graphene.String()
    id_familia = graphene.String()

class NmIncidentProductType(graphene.ObjectType):
    """GraphQL type for nm_incident_product."""
    id_nm_incident_product = graphene.Int()
    id_incident = graphene.Int()
    id_product = graphene.Int()
    note = graphene.String()
    quantity = graphene.Int()
    close_date = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class TaskType(graphene.ObjectType):
    """GraphQL type for task."""
    id_task = graphene.Int()
    task_code = graphene.String()
    start_date = graphene.String()
    duration = graphene.Float()
    type = graphene.String()
    owner = graphene.Int()
    analyst = graphene.Int()
    dependency = graphene.Int()
    leader = graphene.Int()
    validation = graphene.Int()
    task_description = graphene.String()
    estimated_effort = graphene.String()
    task_status = graphene.String()
    fase = graphene.String()
    priority = graphene.String()
    title = graphene.String()
    id_proyect = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class TaskNoteType(graphene.ObjectType):
    """GraphQL type for task_note."""
    id_task_note = graphene.Int()
    date = graphene.String()
    id_task = graphene.Int()
    task_note_description = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class TicketType(graphene.ObjectType):
    """GraphQL type for ticket."""
    id_ticket = graphene.Int()
    ticket_description = graphene.String()
    ticket_status = graphene.String()
    note = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class FiscalAccountType(graphene.ObjectType):
    """GraphQL type for fiscal_account."""
    id_fiscal_account = graphene.Int()
    fiscal_account_description = graphene.String()
    balance = graphene.Float()
    id_fiscal_account_reference = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class FiscalStampType(graphene.ObjectType):
    """GraphQL type for fiscal_stamp."""
    id_fiscal_stamp = graphene.Int()
    concept = graphene.String()
    reviewed_by = graphene.Int()
    authorized_by = graphene.Int()
    auxiliar = graphene.String()
    num_policy = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class FiscalRecordType(graphene.ObjectType):
    """GraphQL type for fiscal_record."""
    id_fiscal_record = graphene.Int()
    fiscal_record_name = graphene.String()
    id_fiscal_account = graphene.Int()
    amount = graphene.Float()
    type = graphene.String()
    id_fiscal_stamp = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class ServiceType(graphene.ObjectType):
    """GraphQL type for service."""
    id_service = graphene.Int()
    service_description = graphene.String()
    average_time_cost = graphene.Float()
    id_brand = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class StatusType(graphene.ObjectType):
    """GraphQL type for status."""
    id_status = graphene.Int()
    status_description = graphene.String()
    category = graphene.String()
    is_terminal = graphene.Boolean()
    sort_order = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class ThemeType(graphene.ObjectType):
    """GraphQL type for theme."""
    id_theme = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()
    tenant_id = graphene.Int()
    primary_color = graphene.String()
    secondary_color = graphene.String()
    background_color = graphene.String()
    text_color = graphene.String()
    highlight_color = graphene.String()
    success_color = graphene.String()
    error_color = graphene.String()

class DepartmentType(graphene.ObjectType):
    """GraphQL type for department."""
    id_department = graphene.Int()
    department_description = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class SubdepartmentType(graphene.ObjectType):
    """GraphQL type for subdepartment."""
    id_subdepartment = graphene.Int()
    subdepartment_description = graphene.String()
    id_department = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class LevelType(graphene.ObjectType):
    """GraphQL type for level."""
    id_level = graphene.Int()
    level_description = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class FieldType(graphene.ObjectType):
    """GraphQL type for field."""
    id_field = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()
    table_name = graphene.String()
    field_name = graphene.String()

class PermissionType(graphene.ObjectType):
    """GraphQL type for permission."""
    id_permission = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()
    authorized_by = graphene.Int()
    permission_description = graphene.String()
    id_department = graphene.Int()
    id_subdepartment = graphene.Int()
    id_level = graphene.Int()

class NmFieldPermissionType(graphene.ObjectType):
    """GraphQL type for nm_field_permission."""
    id_nm_field_permission = graphene.Int()
    id_field = graphene.Int()
    id_permission = graphene.Int()
    control_type = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class EventLogType(graphene.ObjectType):
    """GraphQL type for event_log."""
    id_event_log = graphene.Int()
    table_name = graphene.String()
    field_name = graphene.String()
    action = graphene.String()
    before_value = graphene.JSONString()
    after_value = graphene.JSONString()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class TaskTypeType(graphene.ObjectType):
    """GraphQL type for task_type."""
    id_task_type = graphene.Int()
    task_type_description = graphene.String()
    task_type_scope = graphene.String()
    task_type_limit = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class TemplateType(graphene.ObjectType):
    """GraphQL type for template."""
    id_template = graphene.Int()
    template_description = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class NmTemplateTaskType(graphene.ObjectType):
    """GraphQL type for nm_template_task."""
    id_nm_template_task = graphene.Int()
    id_task = graphene.Int()
    id_template = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class SurveyQuestionType(graphene.ObjectType):
    """GraphQL type for survey_question."""
    id_survey_question = graphene.Int()
    question = graphene.String()
    question_type = graphene.String()
    owner = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class SurveyMultipleAnswerType(graphene.ObjectType):
    """GraphQL type for survey_multiple_answer."""
    id_survey_multiple_answer = graphene.Int()
    id_survey_question = graphene.Int()
    survey_answer_description = graphene.String()
    score = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class NmSurveyUserType(graphene.ObjectType):
    """GraphQL type for nm_survey_user."""
    id_nm_survey_user = graphene.Int()
    id_survey_question = graphene.Int()
    id_survey_multiple_answer = graphene.Int()
    id_user = graphene.Int()
    nm_survey_user_description = graphene.String()
    score = graphene.Int()
    status = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class EntityPermissionType(graphene.ObjectType):
    """GraphQL type for entity_permission."""
    id_entity_permission = graphene.Int()
    id_permission = graphene.Int()
    entity_name = graphene.String()
    control_type = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class InventoryStatusType(graphene.ObjectType):
    """GraphQL type for inventory_status."""
    id_inventory_status = graphene.Int()
    inventory_status_code = graphene.String()
    inventory_status_description = graphene.String()
    color = graphene.String()
    entity_scope = graphene.String()
    flow_scope = graphene.String()
    id_department = graphene.Int()
    id_subdepartment = graphene.Int()
    id_minimum_level = graphene.Int()
    is_active = graphene.Boolean()
    is_terminal = graphene.Boolean()
    visible_to_other_departments = graphene.Boolean()
    sort_order = graphene.Int()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class ProductSaleConfigType(graphene.ObjectType):
    """GraphQL type for product_sale_config."""
    id_product_sale_config = graphene.Int()
    id_product = graphene.Int()
    margin_percent = graphene.Float()
    manual_price = graphene.Float()
    id_inventory_status = graphene.Int()
    is_active = graphene.Boolean()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()

class PublicApiKeyType(graphene.ObjectType):
    """GraphQL type for public_api_key."""
    id_public_api_key = graphene.Int()
    label = graphene.String()
    key_hash = graphene.String()
    key_prefix = graphene.String()
    allowed_domains = graphene.String()
    rate_limit_per_min = graphene.Int()
    is_active = graphene.Boolean()
    last_used_at = graphene.String()
    created_by = graphene.Int()
    creation_date = graphene.String()
    last_update_date = graphene.String()
    deletion_date = graphene.String()
