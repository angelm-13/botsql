from __future__ import annotations
import graphene
from graphene.types.json import JSONString

class UserInput(graphene.InputObjectType):
    """Create/update payload for user."""
    created_by = graphene.Int()
    date_born = graphene.String()
    date_start = graphene.String()
    email = graphene.String()
    first_name = graphene.String()
    id_permission = graphene.Int()
    full_name = graphene.String()
    id_proyect = graphene.Int()
    last_name_father = graphene.String()
    last_name_mother = graphene.String()
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

class UserMfaInput(graphene.InputObjectType):
    """Create/update payload for user_mfa."""
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

class PayrollPeriodInput(graphene.InputObjectType):
    """Create/update payload for payroll_period."""
    period_start = graphene.String()
    period_end = graphene.String()
    payment_date = graphene.String()
    id_status = graphene.Int()
    created_by = graphene.Int()

class PayrollDetailInput(graphene.InputObjectType):
    """Create/update payload for payroll_detail."""
    id_payroll_period = graphene.Int()
    id_user = graphene.Int()
    gross_salary = graphene.Float()
    total_earnings = graphene.Float()
    total_deductions = graphene.Float()
    net_pay = graphene.Float()
    created_by = graphene.Int()

class PayrollConceptInput(graphene.InputObjectType):
    """Create/update payload for payroll_concept."""
    payroll_code = graphene.String()
    payroll_concept_description = graphene.String()
    type = graphene.String()
    is_taxable = graphene.Boolean()
    is_imss = graphene.Boolean()
    created_by = graphene.Int()

class PayrollMovementInput(graphene.InputObjectType):
    """Create/update payload for payroll_movement."""
    id_payroll_detail = graphene.Int()
    id_payroll_concept = graphene.Int()
    amount = graphene.Float()
    created_by = graphene.Int()

class CustomerSupplierInput(graphene.InputObjectType):
    """Create/update payload for customer_supplier."""
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
    path_logo = graphene.String()

class ProyectInput(graphene.InputObjectType):
    """Create/update payload for proyect."""
    id_customer_supplier = graphene.Int()
    leader = graphene.Int()
    proyect_description = graphene.String()
    title = graphene.String()
    proyect_status = graphene.String()
    created_by = graphene.Int()

class BankInput(graphene.InputObjectType):
    """Create/update payload for bank."""
    bank_name = graphene.String()
    created_by = graphene.Int()

class BankAccountInput(graphene.InputObjectType):
    """Create/update payload for bank_account."""
    id_bank = graphene.Int()
    bank_account_description = graphene.String()
    branch = graphene.String()
    type = graphene.String()
    ordinary_interest = graphene.Float()
    moratorium_interest = graphene.Float()
    anuality = graphene.Float()
    reimbursement = graphene.Float()
    created_by = graphene.Int()

class InvoiceInput(graphene.InputObjectType):
    """Create/update payload for invoice."""
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

class InvoiceMaterialServiceInput(graphene.InputObjectType):
    """Create/update payload for invoice_material_service."""
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
    id_product = graphene.Int()
    line_type = graphene.String()
    tax_applicable = graphene.Boolean()
    line_tax = graphene.Float()
    line_total = graphene.Float()
    id_unit = graphene.Int()
    authorization_status = graphene.String()
    authorization_note = graphene.String()
    authorization_date = graphene.String()

class ProductFamilyInput(graphene.InputObjectType):
    """Create/update payload for product_family."""
    product_family_description = graphene.String()
    type = graphene.String()
    created_by = graphene.Int()

class IncidentTypeInput(graphene.InputObjectType):
    """Create/update payload for incident_type."""
    incident_type_description = graphene.String()
    created_by = graphene.Int()

class IncidentInput(graphene.InputObjectType):
    """Create/update payload for incident."""
    incident_date = graphene.String()
    id_incident_type = graphene.Int()
    note = graphene.String()
    id_user = graphene.Int()
    incident_status = graphene.String()
    close_date = graphene.String()
    created_by = graphene.Int()
    id_lider = graphene.String()

class IncidentDetailInput(graphene.InputObjectType):
    """Create/update payload for incident_detail."""
    id_incident_type = graphene.Int()
    incident_detail_name = graphene.String()
    incident_detail_description = graphene.String()
    created_by = graphene.Int()

class BrandInput(graphene.InputObjectType):
    """Create/update payload for brand."""
    brand_description = graphene.String()
    created_by = graphene.Int()

class UnitInput(graphene.InputObjectType):
    """Create/update payload for unit."""
    unit_code = graphene.String()
    unit_name = graphene.String()
    unit_category = graphene.String()
    is_active = graphene.Boolean()
    symbol = graphene.String()
    measurement_system = graphene.String()
    created_by = graphene.Int()

class MaterialInput(graphene.InputObjectType):
    """Create/update payload for material."""
    material_description = graphene.String()
    id_unit = graphene.Int()
    id_brand = graphene.Int()
    id_product_family = graphene.Int()
    created_by = graphene.Int()

class MaterialComponentInput(graphene.InputObjectType):
    """Create/update payload for material_component."""
    id_material = graphene.Int()
    id_component = graphene.Int()
    relation = graphene.Float()
    id_unit = graphene.Int()
    created_by = graphene.Int()

class MovementInput(graphene.InputObjectType):
    """Create/update payload for movement."""
    id_fiscal_account = graphene.Int()
    date = graphene.String()
    type = graphene.String()
    amount = graphene.Float()
    currency = graphene.String()
    type_exchange_rate = graphene.Float()
    created_by = graphene.Int()

class LocationTypeInput(graphene.InputObjectType):
    """Create/update payload for location_type."""
    location_type_description = graphene.String()
    created_by = graphene.Int()

class LocationInput(graphene.InputObjectType):
    """Create/update payload for location."""
    id_location_type = graphene.Int()
    location_description = graphene.String()
    id_location_reference = graphene.Int()
    created_by = graphene.Int()

class ProductInput(graphene.InputObjectType):
    """Create/update payload for product."""
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
    descripcion = graphene.String()
    cantidad = graphene.String()
    id_marca = graphene.String()
    id_familia = graphene.String()

class NmIncidentProductInput(graphene.InputObjectType):
    """Create/update payload for nm_incident_product."""
    id_incident = graphene.Int()
    id_product = graphene.Int()
    note = graphene.String()
    quantity = graphene.Int()
    close_date = graphene.String()
    created_by = graphene.Int()

class TaskInput(graphene.InputObjectType):
    """Create/update payload for task."""
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

class TaskNoteInput(graphene.InputObjectType):
    """Create/update payload for task_note."""
    date = graphene.String()
    id_task = graphene.Int()
    task_note_description = graphene.String()
    created_by = graphene.Int()

class TicketInput(graphene.InputObjectType):
    """Create/update payload for ticket."""
    ticket_description = graphene.String()
    ticket_status = graphene.String()
    note = graphene.String()
    created_by = graphene.Int()

class FiscalAccountInput(graphene.InputObjectType):
    """Create/update payload for fiscal_account."""
    fiscal_account_description = graphene.String()
    balance = graphene.Float()
    id_fiscal_account_reference = graphene.Int()
    created_by = graphene.Int()

class FiscalStampInput(graphene.InputObjectType):
    """Create/update payload for fiscal_stamp."""
    concept = graphene.String()
    reviewed_by = graphene.Int()
    authorized_by = graphene.Int()
    auxiliar = graphene.String()
    num_policy = graphene.String()
    created_by = graphene.Int()

class FiscalRecordInput(graphene.InputObjectType):
    """Create/update payload for fiscal_record."""
    fiscal_record_name = graphene.String()
    id_fiscal_account = graphene.Int()
    amount = graphene.Float()
    type = graphene.String()
    id_fiscal_stamp = graphene.Int()
    created_by = graphene.Int()

class ServiceInput(graphene.InputObjectType):
    """Create/update payload for service."""
    service_description = graphene.String()
    average_time_cost = graphene.Float()
    id_brand = graphene.Int()
    created_by = graphene.Int()

class StatusInput(graphene.InputObjectType):
    """Create/update payload for status."""
    status_description = graphene.String()
    category = graphene.String()
    is_terminal = graphene.Boolean()
    sort_order = graphene.String()
    created_by = graphene.Int()

class ThemeInput(graphene.InputObjectType):
    """Create/update payload for theme."""
    created_by = graphene.Int()
    tenant_id = graphene.Int()
    primary_color = graphene.String()
    secondary_color = graphene.String()
    background_color = graphene.String()
    text_color = graphene.String()
    highlight_color = graphene.String()
    success_color = graphene.String()
    error_color = graphene.String()

class DepartmentInput(graphene.InputObjectType):
    """Create/update payload for department."""
    department_description = graphene.String()
    created_by = graphene.Int()

class SubdepartmentInput(graphene.InputObjectType):
    """Create/update payload for subdepartment."""
    subdepartment_description = graphene.String()
    id_department = graphene.Int()
    created_by = graphene.Int()

class LevelInput(graphene.InputObjectType):
    """Create/update payload for level."""
    level_description = graphene.String()
    created_by = graphene.Int()

class FieldInput(graphene.InputObjectType):
    """Create/update payload for field."""
    created_by = graphene.Int()
    table_name = graphene.String()
    field_name = graphene.String()

class PermissionInput(graphene.InputObjectType):
    """Create/update payload for permission."""
    created_by = graphene.Int()
    authorized_by = graphene.Int()
    permission_description = graphene.String()
    id_department = graphene.Int()
    id_subdepartment = graphene.Int()
    id_level = graphene.Int()

class NmFieldPermissionInput(graphene.InputObjectType):
    """Create/update payload for nm_field_permission."""
    id_field = graphene.Int()
    id_permission = graphene.Int()
    control_type = graphene.String()
    created_by = graphene.Int()

class EventLogInput(graphene.InputObjectType):
    """Create/update payload for event_log."""
    table_name = graphene.String()
    field_name = graphene.String()
    action = graphene.String()
    before_value = graphene.JSONString()
    after_value = graphene.JSONString()
    created_by = graphene.Int()

class TaskTypeInput(graphene.InputObjectType):
    """Create/update payload for task_type."""
    task_type_description = graphene.String()
    task_type_scope = graphene.String()
    task_type_limit = graphene.String()
    created_by = graphene.Int()

class TemplateInput(graphene.InputObjectType):
    """Create/update payload for template."""
    template_description = graphene.String()
    created_by = graphene.Int()

class NmTemplateTaskInput(graphene.InputObjectType):
    """Create/update payload for nm_template_task."""
    id_task = graphene.Int()
    id_template = graphene.Int()
    created_by = graphene.Int()

class SurveyQuestionInput(graphene.InputObjectType):
    """Create/update payload for survey_question."""
    question = graphene.String()
    question_type = graphene.String()
    owner = graphene.Int()
    created_by = graphene.Int()

class SurveyMultipleAnswerInput(graphene.InputObjectType):
    """Create/update payload for survey_multiple_answer."""
    id_survey_question = graphene.Int()
    survey_answer_description = graphene.String()
    score = graphene.Int()
    created_by = graphene.Int()

class NmSurveyUserInput(graphene.InputObjectType):
    """Create/update payload for nm_survey_user."""
    id_survey_question = graphene.Int()
    id_survey_multiple_answer = graphene.Int()
    id_user = graphene.Int()
    nm_survey_user_description = graphene.String()
    score = graphene.Int()
    status = graphene.Int()
    created_by = graphene.Int()

class EntityPermissionInput(graphene.InputObjectType):
    """Create/update payload for entity_permission."""
    id_permission = graphene.Int()
    entity_name = graphene.String()
    control_type = graphene.String()
    created_by = graphene.Int()

class InventoryStatusInput(graphene.InputObjectType):
    """Create/update payload for inventory_status."""
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

class ProductSaleConfigInput(graphene.InputObjectType):
    """Create/update payload for product_sale_config."""
    id_product = graphene.Int()
    margin_percent = graphene.Float()
    manual_price = graphene.Float()
    id_inventory_status = graphene.Int()
    is_active = graphene.Boolean()
    created_by = graphene.Int()

class PublicApiKeyInput(graphene.InputObjectType):
    """Create/update payload for public_api_key."""
    label = graphene.String()
    key_hash = graphene.String()
    key_prefix = graphene.String()
    allowed_domains = graphene.String()
    rate_limit_per_min = graphene.Int()
    is_active = graphene.Boolean()
    last_used_at = graphene.String()
    created_by = graphene.Int()
