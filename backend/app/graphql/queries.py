from __future__ import annotations
import graphene
from graphene.types.json import JSONString
from app.models.session import transaction_context
from app.graphql.filters import apply_filters
from app.graphql.pagination import PageInfo, paginate_query
from app.graphql.types import UserType, UserMfaType, PayrollPeriodType, PayrollDetailType, PayrollConceptType, PayrollMovementType, CustomerSupplierType, ProyectType, BankType, BankAccountType, InvoiceType, InvoiceMaterialServiceType, ProductFamilyType, IncidentTypeType, IncidentType, IncidentDetailType, BrandType, UnitType, MaterialType, MaterialComponentType, MovementType, LocationTypeType, LocationType, ProductType, NmIncidentProductType, TaskType, TaskNoteType, TicketType, FiscalAccountType, FiscalStampType, FiscalRecordType, ServiceType, StatusType, ThemeType, DepartmentType, SubdepartmentType, LevelType, FieldType, PermissionType, NmFieldPermissionType, EventLogType, TaskTypeType, TemplateType, NmTemplateTaskType, SurveyQuestionType, SurveyMultipleAnswerType, NmSurveyUserType, EntityPermissionType, InventoryStatusType, ProductSaleConfigType, PublicApiKeyType
from app.models import User, UserMfa, PayrollPeriod, PayrollDetail, PayrollConcept, PayrollMovement, CustomerSupplier, Proyect, Bank, BankAccount, Invoice, InvoiceMaterialService, ProductFamily, IncidentType, Incident, IncidentDetail, Brand, Unit, Material, MaterialComponent, Movement, LocationType, Location, Product, NmIncidentProduct, Task, TaskNote, Ticket, FiscalAccount, FiscalStamp, FiscalRecord, Service, Status, Theme, Department, Subdepartment, Level, Field, Permission, NmFieldPermission, EventLog, TaskType, Template, NmTemplateTask, SurveyQuestion, SurveyMultipleAnswer, NmSurveyUser, EntityPermission, InventoryStatus, ProductSaleConfig, PublicApiKey

class UserPage(graphene.ObjectType):
    items = graphene.List(UserType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class UserMfaPage(graphene.ObjectType):
    items = graphene.List(UserMfaType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class PayrollPeriodPage(graphene.ObjectType):
    items = graphene.List(PayrollPeriodType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class PayrollDetailPage(graphene.ObjectType):
    items = graphene.List(PayrollDetailType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class PayrollConceptPage(graphene.ObjectType):
    items = graphene.List(PayrollConceptType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class PayrollMovementPage(graphene.ObjectType):
    items = graphene.List(PayrollMovementType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class CustomerSupplierPage(graphene.ObjectType):
    items = graphene.List(CustomerSupplierType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class ProyectPage(graphene.ObjectType):
    items = graphene.List(ProyectType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class BankPage(graphene.ObjectType):
    items = graphene.List(BankType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class BankAccountPage(graphene.ObjectType):
    items = graphene.List(BankAccountType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class InvoicePage(graphene.ObjectType):
    items = graphene.List(InvoiceType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class InvoiceMaterialServicePage(graphene.ObjectType):
    items = graphene.List(InvoiceMaterialServiceType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class ProductFamilyPage(graphene.ObjectType):
    items = graphene.List(ProductFamilyType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class IncidentTypePage(graphene.ObjectType):
    items = graphene.List(IncidentTypeType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class IncidentPage(graphene.ObjectType):
    items = graphene.List(IncidentType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class IncidentDetailPage(graphene.ObjectType):
    items = graphene.List(IncidentDetailType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class BrandPage(graphene.ObjectType):
    items = graphene.List(BrandType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class UnitPage(graphene.ObjectType):
    items = graphene.List(UnitType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class MaterialPage(graphene.ObjectType):
    items = graphene.List(MaterialType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class MaterialComponentPage(graphene.ObjectType):
    items = graphene.List(MaterialComponentType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class MovementPage(graphene.ObjectType):
    items = graphene.List(MovementType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class LocationTypePage(graphene.ObjectType):
    items = graphene.List(LocationTypeType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class LocationPage(graphene.ObjectType):
    items = graphene.List(LocationType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class ProductPage(graphene.ObjectType):
    items = graphene.List(ProductType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class NmIncidentProductPage(graphene.ObjectType):
    items = graphene.List(NmIncidentProductType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class TaskPage(graphene.ObjectType):
    items = graphene.List(TaskType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class TaskNotePage(graphene.ObjectType):
    items = graphene.List(TaskNoteType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class TicketPage(graphene.ObjectType):
    items = graphene.List(TicketType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class FiscalAccountPage(graphene.ObjectType):
    items = graphene.List(FiscalAccountType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class FiscalStampPage(graphene.ObjectType):
    items = graphene.List(FiscalStampType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class FiscalRecordPage(graphene.ObjectType):
    items = graphene.List(FiscalRecordType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class ServicePage(graphene.ObjectType):
    items = graphene.List(ServiceType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class StatusPage(graphene.ObjectType):
    items = graphene.List(StatusType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class ThemePage(graphene.ObjectType):
    items = graphene.List(ThemeType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class DepartmentPage(graphene.ObjectType):
    items = graphene.List(DepartmentType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class SubdepartmentPage(graphene.ObjectType):
    items = graphene.List(SubdepartmentType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class LevelPage(graphene.ObjectType):
    items = graphene.List(LevelType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class FieldPage(graphene.ObjectType):
    items = graphene.List(FieldType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class PermissionPage(graphene.ObjectType):
    items = graphene.List(PermissionType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class NmFieldPermissionPage(graphene.ObjectType):
    items = graphene.List(NmFieldPermissionType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class EventLogPage(graphene.ObjectType):
    items = graphene.List(EventLogType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class TaskTypePage(graphene.ObjectType):
    items = graphene.List(TaskTypeType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class TemplatePage(graphene.ObjectType):
    items = graphene.List(TemplateType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class NmTemplateTaskPage(graphene.ObjectType):
    items = graphene.List(NmTemplateTaskType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class SurveyQuestionPage(graphene.ObjectType):
    items = graphene.List(SurveyQuestionType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class SurveyMultipleAnswerPage(graphene.ObjectType):
    items = graphene.List(SurveyMultipleAnswerType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class NmSurveyUserPage(graphene.ObjectType):
    items = graphene.List(NmSurveyUserType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class EntityPermissionPage(graphene.ObjectType):
    items = graphene.List(EntityPermissionType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class InventoryStatusPage(graphene.ObjectType):
    items = graphene.List(InventoryStatusType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class ProductSaleConfigPage(graphene.ObjectType):
    items = graphene.List(ProductSaleConfigType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class PublicApiKeyPage(graphene.ObjectType):
    items = graphene.List(PublicApiKeyType, required=True)
    page_info = graphene.Field(PageInfo, required=True)

class Query(graphene.ObjectType):
    get_user = graphene.Field(UserType, id_user=graphene.Int(required=True))
    list_users = graphene.Field(UserPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_userMfa = graphene.Field(UserMfaType, id_user_mfa=graphene.Int(required=True))
    list_userMfas = graphene.Field(UserMfaPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_payrollPeriod = graphene.Field(PayrollPeriodType, id_payroll_period=graphene.Int(required=True))
    list_payrollPeriods = graphene.Field(PayrollPeriodPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_payrollDetail = graphene.Field(PayrollDetailType, id_payroll_detail=graphene.Int(required=True))
    list_payrollDetails = graphene.Field(PayrollDetailPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_payrollConcept = graphene.Field(PayrollConceptType, id_payroll_concept=graphene.Int(required=True))
    list_payrollConcepts = graphene.Field(PayrollConceptPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_payrollMovement = graphene.Field(PayrollMovementType, id_payroll_movement=graphene.Int(required=True))
    list_payrollMovements = graphene.Field(PayrollMovementPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_customerSupplier = graphene.Field(CustomerSupplierType, id_customer_supplier=graphene.Int(required=True))
    list_customerSuppliers = graphene.Field(CustomerSupplierPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_proyect = graphene.Field(ProyectType, id_proyect=graphene.Int(required=True))
    list_proyects = graphene.Field(ProyectPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_bank = graphene.Field(BankType, id_bank=graphene.Int(required=True))
    list_banks = graphene.Field(BankPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_bankAccount = graphene.Field(BankAccountType, id_bank_account=graphene.Int(required=True))
    list_bankAccounts = graphene.Field(BankAccountPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_invoice = graphene.Field(InvoiceType, id_invoice=graphene.Int(required=True))
    list_invoices = graphene.Field(InvoicePage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_invoiceMaterialService = graphene.Field(InvoiceMaterialServiceType, id_invoice_material_service=graphene.Int(required=True))
    list_invoiceMaterialServices = graphene.Field(InvoiceMaterialServicePage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_productFamily = graphene.Field(ProductFamilyType, id_product_family=graphene.Int(required=True))
    list_productFamilies = graphene.Field(ProductFamilyPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_incidentType = graphene.Field(IncidentTypeType, id_incident_type=graphene.Int(required=True))
    list_incidentTypes = graphene.Field(IncidentTypePage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_incident = graphene.Field(IncidentType, id_incident=graphene.Int(required=True))
    list_incidents = graphene.Field(IncidentPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_incidentDetail = graphene.Field(IncidentDetailType, id_incident_detail=graphene.Int(required=True))
    list_incidentDetails = graphene.Field(IncidentDetailPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_brand = graphene.Field(BrandType, id_brand=graphene.Int(required=True))
    list_brands = graphene.Field(BrandPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_unit = graphene.Field(UnitType, id_unit=graphene.Int(required=True))
    list_units = graphene.Field(UnitPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_material = graphene.Field(MaterialType, id_material=graphene.Int(required=True))
    list_materials = graphene.Field(MaterialPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_materialComponent = graphene.Field(MaterialComponentType, id_material_component=graphene.Int(required=True))
    list_materialComponents = graphene.Field(MaterialComponentPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_movement = graphene.Field(MovementType, id_movement=graphene.Int(required=True))
    list_movements = graphene.Field(MovementPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_locationType = graphene.Field(LocationTypeType, id_location_type=graphene.Int(required=True))
    list_locationTypes = graphene.Field(LocationTypePage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_location = graphene.Field(LocationType, id_location=graphene.Int(required=True))
    list_locations = graphene.Field(LocationPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_product = graphene.Field(ProductType, id_product=graphene.Int(required=True))
    list_products = graphene.Field(ProductPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_nmIncidentProduct = graphene.Field(NmIncidentProductType, id_nm_incident_product=graphene.Int(required=True))
    list_nmIncidentProducts = graphene.Field(NmIncidentProductPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_task = graphene.Field(TaskType, id_task=graphene.Int(required=True))
    list_tasks = graphene.Field(TaskPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_taskNote = graphene.Field(TaskNoteType, id_task_note=graphene.Int(required=True))
    list_taskNotes = graphene.Field(TaskNotePage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_ticket = graphene.Field(TicketType, id_ticket=graphene.Int(required=True))
    list_tickets = graphene.Field(TicketPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_fiscalAccount = graphene.Field(FiscalAccountType, id_fiscal_account=graphene.Int(required=True))
    list_fiscalAccounts = graphene.Field(FiscalAccountPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_fiscalStamp = graphene.Field(FiscalStampType, id_fiscal_stamp=graphene.Int(required=True))
    list_fiscalStamps = graphene.Field(FiscalStampPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_fiscalRecord = graphene.Field(FiscalRecordType, id_fiscal_record=graphene.Int(required=True))
    list_fiscalRecords = graphene.Field(FiscalRecordPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_service = graphene.Field(ServiceType, id_service=graphene.Int(required=True))
    list_services = graphene.Field(ServicePage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_status = graphene.Field(StatusType, id_status=graphene.Int(required=True))
    list_statuses = graphene.Field(StatusPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_theme = graphene.Field(ThemeType, id_theme=graphene.Int(required=True))
    list_themes = graphene.Field(ThemePage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_department = graphene.Field(DepartmentType, id_department=graphene.Int(required=True))
    list_departments = graphene.Field(DepartmentPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_subdepartment = graphene.Field(SubdepartmentType, id_subdepartment=graphene.Int(required=True))
    list_subdepartments = graphene.Field(SubdepartmentPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_level = graphene.Field(LevelType, id_level=graphene.Int(required=True))
    list_levels = graphene.Field(LevelPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_field = graphene.Field(FieldType, id_field=graphene.Int(required=True))
    list_fields = graphene.Field(FieldPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_permission = graphene.Field(PermissionType, id_permission=graphene.Int(required=True))
    list_permissions = graphene.Field(PermissionPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_nmFieldPermission = graphene.Field(NmFieldPermissionType, id_nm_field_permission=graphene.Int(required=True))
    list_nmFieldPermissions = graphene.Field(NmFieldPermissionPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_eventLog = graphene.Field(EventLogType, id_event_log=graphene.Int(required=True))
    list_eventLogs = graphene.Field(EventLogPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_taskType = graphene.Field(TaskTypeType, id_task_type=graphene.Int(required=True))
    list_taskTypes = graphene.Field(TaskTypePage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_template = graphene.Field(TemplateType, id_template=graphene.Int(required=True))
    list_templates = graphene.Field(TemplatePage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_nmTemplateTask = graphene.Field(NmTemplateTaskType, id_nm_template_task=graphene.Int(required=True))
    list_nmTemplateTasks = graphene.Field(NmTemplateTaskPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_surveyQuestion = graphene.Field(SurveyQuestionType, id_survey_question=graphene.Int(required=True))
    list_surveyQuestions = graphene.Field(SurveyQuestionPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_surveyMultipleAnswer = graphene.Field(SurveyMultipleAnswerType, id_survey_multiple_answer=graphene.Int(required=True))
    list_surveyMultipleAnswers = graphene.Field(SurveyMultipleAnswerPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_nmSurveyUser = graphene.Field(NmSurveyUserType, id_nm_survey_user=graphene.Int(required=True))
    list_nmSurveyUsers = graphene.Field(NmSurveyUserPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_entityPermission = graphene.Field(EntityPermissionType, id_entity_permission=graphene.Int(required=True))
    list_entityPermissions = graphene.Field(EntityPermissionPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_inventoryStatus = graphene.Field(InventoryStatusType, id_inventory_status=graphene.Int(required=True))
    list_inventoryStatuses = graphene.Field(InventoryStatusPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_productSaleConfig = graphene.Field(ProductSaleConfigType, id_product_sale_config=graphene.Int(required=True))
    list_productSaleConfigs = graphene.Field(ProductSaleConfigPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())
    get_publicApiKey = graphene.Field(PublicApiKeyType, id_public_api_key=graphene.Int(required=True))
    list_publicApiKeys = graphene.Field(PublicApiKeyPage, page=graphene.Int(default_value=1), per_page=graphene.Int(default_value=20), filters=JSONString())

    def resolve_get_user(self, info, id_user):
        with transaction_context() as db_session:
            return db_session.get(User, id_user)

    def resolve_list_users(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(User)
            query = apply_filters(query, User, filters)
            items, page_info = paginate_query(query, page, per_page)
            return UserPage(items=items, page_info=page_info)

    def resolve_get_userMfa(self, info, id_user_mfa):
        with transaction_context() as db_session:
            return db_session.get(UserMfa, id_user_mfa)

    def resolve_list_userMfas(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(UserMfa)
            query = apply_filters(query, UserMfa, filters)
            items, page_info = paginate_query(query, page, per_page)
            return UserMfaPage(items=items, page_info=page_info)

    def resolve_get_payrollPeriod(self, info, id_payroll_period):
        with transaction_context() as db_session:
            return db_session.get(PayrollPeriod, id_payroll_period)

    def resolve_list_payrollPeriods(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(PayrollPeriod)
            query = apply_filters(query, PayrollPeriod, filters)
            items, page_info = paginate_query(query, page, per_page)
            return PayrollPeriodPage(items=items, page_info=page_info)

    def resolve_get_payrollDetail(self, info, id_payroll_detail):
        with transaction_context() as db_session:
            return db_session.get(PayrollDetail, id_payroll_detail)

    def resolve_list_payrollDetails(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(PayrollDetail)
            query = apply_filters(query, PayrollDetail, filters)
            items, page_info = paginate_query(query, page, per_page)
            return PayrollDetailPage(items=items, page_info=page_info)

    def resolve_get_payrollConcept(self, info, id_payroll_concept):
        with transaction_context() as db_session:
            return db_session.get(PayrollConcept, id_payroll_concept)

    def resolve_list_payrollConcepts(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(PayrollConcept)
            query = apply_filters(query, PayrollConcept, filters)
            items, page_info = paginate_query(query, page, per_page)
            return PayrollConceptPage(items=items, page_info=page_info)

    def resolve_get_payrollMovement(self, info, id_payroll_movement):
        with transaction_context() as db_session:
            return db_session.get(PayrollMovement, id_payroll_movement)

    def resolve_list_payrollMovements(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(PayrollMovement)
            query = apply_filters(query, PayrollMovement, filters)
            items, page_info = paginate_query(query, page, per_page)
            return PayrollMovementPage(items=items, page_info=page_info)

    def resolve_get_customerSupplier(self, info, id_customer_supplier):
        with transaction_context() as db_session:
            return db_session.get(CustomerSupplier, id_customer_supplier)

    def resolve_list_customerSuppliers(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(CustomerSupplier)
            query = apply_filters(query, CustomerSupplier, filters)
            items, page_info = paginate_query(query, page, per_page)
            return CustomerSupplierPage(items=items, page_info=page_info)

    def resolve_get_proyect(self, info, id_proyect):
        with transaction_context() as db_session:
            return db_session.get(Proyect, id_proyect)

    def resolve_list_proyects(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Proyect)
            query = apply_filters(query, Proyect, filters)
            items, page_info = paginate_query(query, page, per_page)
            return ProyectPage(items=items, page_info=page_info)

    def resolve_get_bank(self, info, id_bank):
        with transaction_context() as db_session:
            return db_session.get(Bank, id_bank)

    def resolve_list_banks(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Bank)
            query = apply_filters(query, Bank, filters)
            items, page_info = paginate_query(query, page, per_page)
            return BankPage(items=items, page_info=page_info)

    def resolve_get_bankAccount(self, info, id_bank_account):
        with transaction_context() as db_session:
            return db_session.get(BankAccount, id_bank_account)

    def resolve_list_bankAccounts(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(BankAccount)
            query = apply_filters(query, BankAccount, filters)
            items, page_info = paginate_query(query, page, per_page)
            return BankAccountPage(items=items, page_info=page_info)

    def resolve_get_invoice(self, info, id_invoice):
        with transaction_context() as db_session:
            return db_session.get(Invoice, id_invoice)

    def resolve_list_invoices(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Invoice)
            query = apply_filters(query, Invoice, filters)
            items, page_info = paginate_query(query, page, per_page)
            return InvoicePage(items=items, page_info=page_info)

    def resolve_get_invoiceMaterialService(self, info, id_invoice_material_service):
        with transaction_context() as db_session:
            return db_session.get(InvoiceMaterialService, id_invoice_material_service)

    def resolve_list_invoiceMaterialServices(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(InvoiceMaterialService)
            query = apply_filters(query, InvoiceMaterialService, filters)
            items, page_info = paginate_query(query, page, per_page)
            return InvoiceMaterialServicePage(items=items, page_info=page_info)

    def resolve_get_productFamily(self, info, id_product_family):
        with transaction_context() as db_session:
            return db_session.get(ProductFamily, id_product_family)

    def resolve_list_productFamilies(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(ProductFamily)
            query = apply_filters(query, ProductFamily, filters)
            items, page_info = paginate_query(query, page, per_page)
            return ProductFamilyPage(items=items, page_info=page_info)

    def resolve_get_incidentType(self, info, id_incident_type):
        with transaction_context() as db_session:
            return db_session.get(IncidentType, id_incident_type)

    def resolve_list_incidentTypes(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(IncidentType)
            query = apply_filters(query, IncidentType, filters)
            items, page_info = paginate_query(query, page, per_page)
            return IncidentTypePage(items=items, page_info=page_info)

    def resolve_get_incident(self, info, id_incident):
        with transaction_context() as db_session:
            return db_session.get(Incident, id_incident)

    def resolve_list_incidents(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Incident)
            query = apply_filters(query, Incident, filters)
            items, page_info = paginate_query(query, page, per_page)
            return IncidentPage(items=items, page_info=page_info)

    def resolve_get_incidentDetail(self, info, id_incident_detail):
        with transaction_context() as db_session:
            return db_session.get(IncidentDetail, id_incident_detail)

    def resolve_list_incidentDetails(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(IncidentDetail)
            query = apply_filters(query, IncidentDetail, filters)
            items, page_info = paginate_query(query, page, per_page)
            return IncidentDetailPage(items=items, page_info=page_info)

    def resolve_get_brand(self, info, id_brand):
        with transaction_context() as db_session:
            return db_session.get(Brand, id_brand)

    def resolve_list_brands(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Brand)
            query = apply_filters(query, Brand, filters)
            items, page_info = paginate_query(query, page, per_page)
            return BrandPage(items=items, page_info=page_info)

    def resolve_get_unit(self, info, id_unit):
        with transaction_context() as db_session:
            return db_session.get(Unit, id_unit)

    def resolve_list_units(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Unit)
            query = apply_filters(query, Unit, filters)
            items, page_info = paginate_query(query, page, per_page)
            return UnitPage(items=items, page_info=page_info)

    def resolve_get_material(self, info, id_material):
        with transaction_context() as db_session:
            return db_session.get(Material, id_material)

    def resolve_list_materials(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Material)
            query = apply_filters(query, Material, filters)
            items, page_info = paginate_query(query, page, per_page)
            return MaterialPage(items=items, page_info=page_info)

    def resolve_get_materialComponent(self, info, id_material_component):
        with transaction_context() as db_session:
            return db_session.get(MaterialComponent, id_material_component)

    def resolve_list_materialComponents(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(MaterialComponent)
            query = apply_filters(query, MaterialComponent, filters)
            items, page_info = paginate_query(query, page, per_page)
            return MaterialComponentPage(items=items, page_info=page_info)

    def resolve_get_movement(self, info, id_movement):
        with transaction_context() as db_session:
            return db_session.get(Movement, id_movement)

    def resolve_list_movements(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Movement)
            query = apply_filters(query, Movement, filters)
            items, page_info = paginate_query(query, page, per_page)
            return MovementPage(items=items, page_info=page_info)

    def resolve_get_locationType(self, info, id_location_type):
        with transaction_context() as db_session:
            return db_session.get(LocationType, id_location_type)

    def resolve_list_locationTypes(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(LocationType)
            query = apply_filters(query, LocationType, filters)
            items, page_info = paginate_query(query, page, per_page)
            return LocationTypePage(items=items, page_info=page_info)

    def resolve_get_location(self, info, id_location):
        with transaction_context() as db_session:
            return db_session.get(Location, id_location)

    def resolve_list_locations(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Location)
            query = apply_filters(query, Location, filters)
            items, page_info = paginate_query(query, page, per_page)
            return LocationPage(items=items, page_info=page_info)

    def resolve_get_product(self, info, id_product):
        with transaction_context() as db_session:
            return db_session.get(Product, id_product)

    def resolve_list_products(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Product)
            query = apply_filters(query, Product, filters)
            items, page_info = paginate_query(query, page, per_page)
            return ProductPage(items=items, page_info=page_info)

    def resolve_get_nmIncidentProduct(self, info, id_nm_incident_product):
        with transaction_context() as db_session:
            return db_session.get(NmIncidentProduct, id_nm_incident_product)

    def resolve_list_nmIncidentProducts(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(NmIncidentProduct)
            query = apply_filters(query, NmIncidentProduct, filters)
            items, page_info = paginate_query(query, page, per_page)
            return NmIncidentProductPage(items=items, page_info=page_info)

    def resolve_get_task(self, info, id_task):
        with transaction_context() as db_session:
            return db_session.get(Task, id_task)

    def resolve_list_tasks(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Task)
            query = apply_filters(query, Task, filters)
            items, page_info = paginate_query(query, page, per_page)
            return TaskPage(items=items, page_info=page_info)

    def resolve_get_taskNote(self, info, id_task_note):
        with transaction_context() as db_session:
            return db_session.get(TaskNote, id_task_note)

    def resolve_list_taskNotes(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(TaskNote)
            query = apply_filters(query, TaskNote, filters)
            items, page_info = paginate_query(query, page, per_page)
            return TaskNotePage(items=items, page_info=page_info)

    def resolve_get_ticket(self, info, id_ticket):
        with transaction_context() as db_session:
            return db_session.get(Ticket, id_ticket)

    def resolve_list_tickets(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Ticket)
            query = apply_filters(query, Ticket, filters)
            items, page_info = paginate_query(query, page, per_page)
            return TicketPage(items=items, page_info=page_info)

    def resolve_get_fiscalAccount(self, info, id_fiscal_account):
        with transaction_context() as db_session:
            return db_session.get(FiscalAccount, id_fiscal_account)

    def resolve_list_fiscalAccounts(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(FiscalAccount)
            query = apply_filters(query, FiscalAccount, filters)
            items, page_info = paginate_query(query, page, per_page)
            return FiscalAccountPage(items=items, page_info=page_info)

    def resolve_get_fiscalStamp(self, info, id_fiscal_stamp):
        with transaction_context() as db_session:
            return db_session.get(FiscalStamp, id_fiscal_stamp)

    def resolve_list_fiscalStamps(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(FiscalStamp)
            query = apply_filters(query, FiscalStamp, filters)
            items, page_info = paginate_query(query, page, per_page)
            return FiscalStampPage(items=items, page_info=page_info)

    def resolve_get_fiscalRecord(self, info, id_fiscal_record):
        with transaction_context() as db_session:
            return db_session.get(FiscalRecord, id_fiscal_record)

    def resolve_list_fiscalRecords(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(FiscalRecord)
            query = apply_filters(query, FiscalRecord, filters)
            items, page_info = paginate_query(query, page, per_page)
            return FiscalRecordPage(items=items, page_info=page_info)

    def resolve_get_service(self, info, id_service):
        with transaction_context() as db_session:
            return db_session.get(Service, id_service)

    def resolve_list_services(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Service)
            query = apply_filters(query, Service, filters)
            items, page_info = paginate_query(query, page, per_page)
            return ServicePage(items=items, page_info=page_info)

    def resolve_get_status(self, info, id_status):
        with transaction_context() as db_session:
            return db_session.get(Status, id_status)

    def resolve_list_statuses(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Status)
            query = apply_filters(query, Status, filters)
            items, page_info = paginate_query(query, page, per_page)
            return StatusPage(items=items, page_info=page_info)

    def resolve_get_theme(self, info, id_theme):
        with transaction_context() as db_session:
            return db_session.get(Theme, id_theme)

    def resolve_list_themes(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Theme)
            query = apply_filters(query, Theme, filters)
            items, page_info = paginate_query(query, page, per_page)
            return ThemePage(items=items, page_info=page_info)

    def resolve_get_department(self, info, id_department):
        with transaction_context() as db_session:
            return db_session.get(Department, id_department)

    def resolve_list_departments(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Department)
            query = apply_filters(query, Department, filters)
            items, page_info = paginate_query(query, page, per_page)
            return DepartmentPage(items=items, page_info=page_info)

    def resolve_get_subdepartment(self, info, id_subdepartment):
        with transaction_context() as db_session:
            return db_session.get(Subdepartment, id_subdepartment)

    def resolve_list_subdepartments(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Subdepartment)
            query = apply_filters(query, Subdepartment, filters)
            items, page_info = paginate_query(query, page, per_page)
            return SubdepartmentPage(items=items, page_info=page_info)

    def resolve_get_level(self, info, id_level):
        with transaction_context() as db_session:
            return db_session.get(Level, id_level)

    def resolve_list_levels(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Level)
            query = apply_filters(query, Level, filters)
            items, page_info = paginate_query(query, page, per_page)
            return LevelPage(items=items, page_info=page_info)

    def resolve_get_field(self, info, id_field):
        with transaction_context() as db_session:
            return db_session.get(Field, id_field)

    def resolve_list_fields(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Field)
            query = apply_filters(query, Field, filters)
            items, page_info = paginate_query(query, page, per_page)
            return FieldPage(items=items, page_info=page_info)

    def resolve_get_permission(self, info, id_permission):
        with transaction_context() as db_session:
            return db_session.get(Permission, id_permission)

    def resolve_list_permissions(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Permission)
            query = apply_filters(query, Permission, filters)
            items, page_info = paginate_query(query, page, per_page)
            return PermissionPage(items=items, page_info=page_info)

    def resolve_get_nmFieldPermission(self, info, id_nm_field_permission):
        with transaction_context() as db_session:
            return db_session.get(NmFieldPermission, id_nm_field_permission)

    def resolve_list_nmFieldPermissions(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(NmFieldPermission)
            query = apply_filters(query, NmFieldPermission, filters)
            items, page_info = paginate_query(query, page, per_page)
            return NmFieldPermissionPage(items=items, page_info=page_info)

    def resolve_get_eventLog(self, info, id_event_log):
        with transaction_context() as db_session:
            return db_session.get(EventLog, id_event_log)

    def resolve_list_eventLogs(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(EventLog)
            query = apply_filters(query, EventLog, filters)
            items, page_info = paginate_query(query, page, per_page)
            return EventLogPage(items=items, page_info=page_info)

    def resolve_get_taskType(self, info, id_task_type):
        with transaction_context() as db_session:
            return db_session.get(TaskType, id_task_type)

    def resolve_list_taskTypes(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(TaskType)
            query = apply_filters(query, TaskType, filters)
            items, page_info = paginate_query(query, page, per_page)
            return TaskTypePage(items=items, page_info=page_info)

    def resolve_get_template(self, info, id_template):
        with transaction_context() as db_session:
            return db_session.get(Template, id_template)

    def resolve_list_templates(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(Template)
            query = apply_filters(query, Template, filters)
            items, page_info = paginate_query(query, page, per_page)
            return TemplatePage(items=items, page_info=page_info)

    def resolve_get_nmTemplateTask(self, info, id_nm_template_task):
        with transaction_context() as db_session:
            return db_session.get(NmTemplateTask, id_nm_template_task)

    def resolve_list_nmTemplateTasks(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(NmTemplateTask)
            query = apply_filters(query, NmTemplateTask, filters)
            items, page_info = paginate_query(query, page, per_page)
            return NmTemplateTaskPage(items=items, page_info=page_info)

    def resolve_get_surveyQuestion(self, info, id_survey_question):
        with transaction_context() as db_session:
            return db_session.get(SurveyQuestion, id_survey_question)

    def resolve_list_surveyQuestions(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(SurveyQuestion)
            query = apply_filters(query, SurveyQuestion, filters)
            items, page_info = paginate_query(query, page, per_page)
            return SurveyQuestionPage(items=items, page_info=page_info)

    def resolve_get_surveyMultipleAnswer(self, info, id_survey_multiple_answer):
        with transaction_context() as db_session:
            return db_session.get(SurveyMultipleAnswer, id_survey_multiple_answer)

    def resolve_list_surveyMultipleAnswers(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(SurveyMultipleAnswer)
            query = apply_filters(query, SurveyMultipleAnswer, filters)
            items, page_info = paginate_query(query, page, per_page)
            return SurveyMultipleAnswerPage(items=items, page_info=page_info)

    def resolve_get_nmSurveyUser(self, info, id_nm_survey_user):
        with transaction_context() as db_session:
            return db_session.get(NmSurveyUser, id_nm_survey_user)

    def resolve_list_nmSurveyUsers(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(NmSurveyUser)
            query = apply_filters(query, NmSurveyUser, filters)
            items, page_info = paginate_query(query, page, per_page)
            return NmSurveyUserPage(items=items, page_info=page_info)

    def resolve_get_entityPermission(self, info, id_entity_permission):
        with transaction_context() as db_session:
            return db_session.get(EntityPermission, id_entity_permission)

    def resolve_list_entityPermissions(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(EntityPermission)
            query = apply_filters(query, EntityPermission, filters)
            items, page_info = paginate_query(query, page, per_page)
            return EntityPermissionPage(items=items, page_info=page_info)

    def resolve_get_inventoryStatus(self, info, id_inventory_status):
        with transaction_context() as db_session:
            return db_session.get(InventoryStatus, id_inventory_status)

    def resolve_list_inventoryStatuses(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(InventoryStatus)
            query = apply_filters(query, InventoryStatus, filters)
            items, page_info = paginate_query(query, page, per_page)
            return InventoryStatusPage(items=items, page_info=page_info)

    def resolve_get_productSaleConfig(self, info, id_product_sale_config):
        with transaction_context() as db_session:
            return db_session.get(ProductSaleConfig, id_product_sale_config)

    def resolve_list_productSaleConfigs(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(ProductSaleConfig)
            query = apply_filters(query, ProductSaleConfig, filters)
            items, page_info = paginate_query(query, page, per_page)
            return ProductSaleConfigPage(items=items, page_info=page_info)

    def resolve_get_publicApiKey(self, info, id_public_api_key):
        with transaction_context() as db_session:
            return db_session.get(PublicApiKey, id_public_api_key)

    def resolve_list_publicApiKeys(self, info, page=1, per_page=20, filters=None):
        with transaction_context() as db_session:
            query = db_session.query(PublicApiKey)
            query = apply_filters(query, PublicApiKey, filters)
            items, page_info = paginate_query(query, page, per_page)
            return PublicApiKeyPage(items=items, page_info=page_info)
