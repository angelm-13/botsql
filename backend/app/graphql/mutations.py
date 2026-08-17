from __future__ import annotations
import graphene
from app.utils.errors import AppError
from app.graphql.inputs import UserInput, UserMfaInput, PayrollPeriodInput, PayrollDetailInput, PayrollConceptInput, PayrollMovementInput, CustomerSupplierInput, ProyectInput, BankInput, BankAccountInput, InvoiceInput, InvoiceMaterialServiceInput, ProductFamilyInput, IncidentTypeInput, IncidentInput, IncidentDetailInput, BrandInput, UnitInput, MaterialInput, MaterialComponentInput, MovementInput, LocationTypeInput, LocationInput, ProductInput, NmIncidentProductInput, TaskInput, TaskNoteInput, TicketInput, FiscalAccountInput, FiscalStampInput, FiscalRecordInput, ServiceInput, StatusInput, ThemeInput, DepartmentInput, SubdepartmentInput, LevelInput, FieldInput, PermissionInput, NmFieldPermissionInput, EventLogInput, TaskTypeInput, TemplateInput, NmTemplateTaskInput, SurveyQuestionInput, SurveyMultipleAnswerInput, NmSurveyUserInput, EntityPermissionInput, InventoryStatusInput, ProductSaleConfigInput, PublicApiKeyInput
from app.graphql.types import UserType, UserMfaType, PayrollPeriodType, PayrollDetailType, PayrollConceptType, PayrollMovementType, CustomerSupplierType, ProyectType, BankType, BankAccountType, InvoiceType, InvoiceMaterialServiceType, ProductFamilyType, IncidentTypeType, IncidentType, IncidentDetailType, BrandType, UnitType, MaterialType, MaterialComponentType, MovementType, LocationTypeType, LocationType, ProductType, NmIncidentProductType, TaskType, TaskNoteType, TicketType, FiscalAccountType, FiscalStampType, FiscalRecordType, ServiceType, StatusType, ThemeType, DepartmentType, SubdepartmentType, LevelType, FieldType, PermissionType, NmFieldPermissionType, EventLogType, TaskTypeType, TemplateType, NmTemplateTaskType, SurveyQuestionType, SurveyMultipleAnswerType, NmSurveyUserType, EntityPermissionType, InventoryStatusType, ProductSaleConfigType, PublicApiKeyType
from app.services import UserService, UserMfaService, PayrollPeriodService, PayrollDetailService, PayrollConceptService, PayrollMovementService, CustomerSupplierService, ProyectService, BankService, BankAccountService, InvoiceService, InvoiceMaterialServiceService, ProductFamilyService, IncidentTypeService, IncidentService, IncidentDetailService, BrandService, UnitService, MaterialService, MaterialComponentService, MovementService, LocationTypeService, LocationService, ProductService, NmIncidentProductService, TaskService, TaskNoteService, TicketService, FiscalAccountService, FiscalStampService, FiscalRecordService, ServiceService, StatusService, ThemeService, DepartmentService, SubdepartmentService, LevelService, FieldService, PermissionService, NmFieldPermissionService, EventLogService, TaskTypeService, TemplateService, NmTemplateTaskService, SurveyQuestionService, SurveyMultipleAnswerService, NmSurveyUserService, EntityPermissionService, InventoryStatusService, ProductSaleConfigService, PublicApiKeyService

class CreateUser(graphene.Mutation):
    class Arguments:
        input = UserInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(UserType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = UserService.create(payload)
            return CreateUser(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateUser(ok=False, message_key=error.message_key, item=None)

class UpdateUser(graphene.Mutation):
    class Arguments:
        id_user = graphene.Int(required=True)
        input = UserInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(UserType)
    @staticmethod
    def mutate(root, info, id_user, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = UserService.update(id_user, payload)
            return UpdateUser(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateUser(ok=False, message_key=error.message_key, item=None)

class DeleteUser(graphene.Mutation):
    class Arguments:
        id_user = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_user):
        try:
            result = UserService.delete(id_user)
            return DeleteUser(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteUser(ok=False, message_key=error.message_key)

class CreateUserMfa(graphene.Mutation):
    class Arguments:
        input = UserMfaInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(UserMfaType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = UserMfaService.create(payload)
            return CreateUserMfa(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateUserMfa(ok=False, message_key=error.message_key, item=None)

class UpdateUserMfa(graphene.Mutation):
    class Arguments:
        id_user_mfa = graphene.Int(required=True)
        input = UserMfaInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(UserMfaType)
    @staticmethod
    def mutate(root, info, id_user_mfa, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = UserMfaService.update(id_user_mfa, payload)
            return UpdateUserMfa(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateUserMfa(ok=False, message_key=error.message_key, item=None)

class DeleteUserMfa(graphene.Mutation):
    class Arguments:
        id_user_mfa = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_user_mfa):
        try:
            result = UserMfaService.delete(id_user_mfa)
            return DeleteUserMfa(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteUserMfa(ok=False, message_key=error.message_key)

class CreatePayrollPeriod(graphene.Mutation):
    class Arguments:
        input = PayrollPeriodInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(PayrollPeriodType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = PayrollPeriodService.create(payload)
            return CreatePayrollPeriod(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreatePayrollPeriod(ok=False, message_key=error.message_key, item=None)

class UpdatePayrollPeriod(graphene.Mutation):
    class Arguments:
        id_payroll_period = graphene.Int(required=True)
        input = PayrollPeriodInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(PayrollPeriodType)
    @staticmethod
    def mutate(root, info, id_payroll_period, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = PayrollPeriodService.update(id_payroll_period, payload)
            return UpdatePayrollPeriod(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdatePayrollPeriod(ok=False, message_key=error.message_key, item=None)

class DeletePayrollPeriod(graphene.Mutation):
    class Arguments:
        id_payroll_period = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_payroll_period):
        try:
            result = PayrollPeriodService.delete(id_payroll_period)
            return DeletePayrollPeriod(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeletePayrollPeriod(ok=False, message_key=error.message_key)

class CreatePayrollDetail(graphene.Mutation):
    class Arguments:
        input = PayrollDetailInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(PayrollDetailType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = PayrollDetailService.create(payload)
            return CreatePayrollDetail(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreatePayrollDetail(ok=False, message_key=error.message_key, item=None)

class UpdatePayrollDetail(graphene.Mutation):
    class Arguments:
        id_payroll_detail = graphene.Int(required=True)
        input = PayrollDetailInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(PayrollDetailType)
    @staticmethod
    def mutate(root, info, id_payroll_detail, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = PayrollDetailService.update(id_payroll_detail, payload)
            return UpdatePayrollDetail(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdatePayrollDetail(ok=False, message_key=error.message_key, item=None)

class DeletePayrollDetail(graphene.Mutation):
    class Arguments:
        id_payroll_detail = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_payroll_detail):
        try:
            result = PayrollDetailService.delete(id_payroll_detail)
            return DeletePayrollDetail(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeletePayrollDetail(ok=False, message_key=error.message_key)

class CreatePayrollConcept(graphene.Mutation):
    class Arguments:
        input = PayrollConceptInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(PayrollConceptType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = PayrollConceptService.create(payload)
            return CreatePayrollConcept(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreatePayrollConcept(ok=False, message_key=error.message_key, item=None)

class UpdatePayrollConcept(graphene.Mutation):
    class Arguments:
        id_payroll_concept = graphene.Int(required=True)
        input = PayrollConceptInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(PayrollConceptType)
    @staticmethod
    def mutate(root, info, id_payroll_concept, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = PayrollConceptService.update(id_payroll_concept, payload)
            return UpdatePayrollConcept(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdatePayrollConcept(ok=False, message_key=error.message_key, item=None)

class DeletePayrollConcept(graphene.Mutation):
    class Arguments:
        id_payroll_concept = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_payroll_concept):
        try:
            result = PayrollConceptService.delete(id_payroll_concept)
            return DeletePayrollConcept(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeletePayrollConcept(ok=False, message_key=error.message_key)

class CreatePayrollMovement(graphene.Mutation):
    class Arguments:
        input = PayrollMovementInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(PayrollMovementType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = PayrollMovementService.create(payload)
            return CreatePayrollMovement(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreatePayrollMovement(ok=False, message_key=error.message_key, item=None)

class UpdatePayrollMovement(graphene.Mutation):
    class Arguments:
        id_payroll_movement = graphene.Int(required=True)
        input = PayrollMovementInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(PayrollMovementType)
    @staticmethod
    def mutate(root, info, id_payroll_movement, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = PayrollMovementService.update(id_payroll_movement, payload)
            return UpdatePayrollMovement(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdatePayrollMovement(ok=False, message_key=error.message_key, item=None)

class DeletePayrollMovement(graphene.Mutation):
    class Arguments:
        id_payroll_movement = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_payroll_movement):
        try:
            result = PayrollMovementService.delete(id_payroll_movement)
            return DeletePayrollMovement(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeletePayrollMovement(ok=False, message_key=error.message_key)

class CreateCustomerSupplier(graphene.Mutation):
    class Arguments:
        input = CustomerSupplierInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(CustomerSupplierType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = CustomerSupplierService.create(payload)
            return CreateCustomerSupplier(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateCustomerSupplier(ok=False, message_key=error.message_key, item=None)

class UpdateCustomerSupplier(graphene.Mutation):
    class Arguments:
        id_customer_supplier = graphene.Int(required=True)
        input = CustomerSupplierInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(CustomerSupplierType)
    @staticmethod
    def mutate(root, info, id_customer_supplier, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = CustomerSupplierService.update(id_customer_supplier, payload)
            return UpdateCustomerSupplier(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateCustomerSupplier(ok=False, message_key=error.message_key, item=None)

class DeleteCustomerSupplier(graphene.Mutation):
    class Arguments:
        id_customer_supplier = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_customer_supplier):
        try:
            result = CustomerSupplierService.delete(id_customer_supplier)
            return DeleteCustomerSupplier(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteCustomerSupplier(ok=False, message_key=error.message_key)

class CreateProyect(graphene.Mutation):
    class Arguments:
        input = ProyectInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(ProyectType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = ProyectService.create(payload)
            return CreateProyect(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateProyect(ok=False, message_key=error.message_key, item=None)

class UpdateProyect(graphene.Mutation):
    class Arguments:
        id_proyect = graphene.Int(required=True)
        input = ProyectInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(ProyectType)
    @staticmethod
    def mutate(root, info, id_proyect, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = ProyectService.update(id_proyect, payload)
            return UpdateProyect(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateProyect(ok=False, message_key=error.message_key, item=None)

class DeleteProyect(graphene.Mutation):
    class Arguments:
        id_proyect = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_proyect):
        try:
            result = ProyectService.delete(id_proyect)
            return DeleteProyect(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteProyect(ok=False, message_key=error.message_key)

class CreateBank(graphene.Mutation):
    class Arguments:
        input = BankInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(BankType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = BankService.create(payload)
            return CreateBank(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateBank(ok=False, message_key=error.message_key, item=None)

class UpdateBank(graphene.Mutation):
    class Arguments:
        id_bank = graphene.Int(required=True)
        input = BankInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(BankType)
    @staticmethod
    def mutate(root, info, id_bank, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = BankService.update(id_bank, payload)
            return UpdateBank(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateBank(ok=False, message_key=error.message_key, item=None)

class DeleteBank(graphene.Mutation):
    class Arguments:
        id_bank = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_bank):
        try:
            result = BankService.delete(id_bank)
            return DeleteBank(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteBank(ok=False, message_key=error.message_key)

class CreateBankAccount(graphene.Mutation):
    class Arguments:
        input = BankAccountInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(BankAccountType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = BankAccountService.create(payload)
            return CreateBankAccount(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateBankAccount(ok=False, message_key=error.message_key, item=None)

class UpdateBankAccount(graphene.Mutation):
    class Arguments:
        id_bank_account = graphene.Int(required=True)
        input = BankAccountInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(BankAccountType)
    @staticmethod
    def mutate(root, info, id_bank_account, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = BankAccountService.update(id_bank_account, payload)
            return UpdateBankAccount(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateBankAccount(ok=False, message_key=error.message_key, item=None)

class DeleteBankAccount(graphene.Mutation):
    class Arguments:
        id_bank_account = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_bank_account):
        try:
            result = BankAccountService.delete(id_bank_account)
            return DeleteBankAccount(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteBankAccount(ok=False, message_key=error.message_key)

class CreateInvoice(graphene.Mutation):
    class Arguments:
        input = InvoiceInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(InvoiceType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = InvoiceService.create(payload)
            return CreateInvoice(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateInvoice(ok=False, message_key=error.message_key, item=None)

class UpdateInvoice(graphene.Mutation):
    class Arguments:
        id_invoice = graphene.Int(required=True)
        input = InvoiceInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(InvoiceType)
    @staticmethod
    def mutate(root, info, id_invoice, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = InvoiceService.update(id_invoice, payload)
            return UpdateInvoice(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateInvoice(ok=False, message_key=error.message_key, item=None)

class DeleteInvoice(graphene.Mutation):
    class Arguments:
        id_invoice = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_invoice):
        try:
            result = InvoiceService.delete(id_invoice)
            return DeleteInvoice(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteInvoice(ok=False, message_key=error.message_key)

class CreateInvoiceMaterialService(graphene.Mutation):
    class Arguments:
        input = InvoiceMaterialServiceInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(InvoiceMaterialServiceType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = InvoiceMaterialServiceService.create(payload)
            return CreateInvoiceMaterialService(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateInvoiceMaterialService(ok=False, message_key=error.message_key, item=None)

class UpdateInvoiceMaterialService(graphene.Mutation):
    class Arguments:
        id_invoice_material_service = graphene.Int(required=True)
        input = InvoiceMaterialServiceInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(InvoiceMaterialServiceType)
    @staticmethod
    def mutate(root, info, id_invoice_material_service, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = InvoiceMaterialServiceService.update(id_invoice_material_service, payload)
            return UpdateInvoiceMaterialService(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateInvoiceMaterialService(ok=False, message_key=error.message_key, item=None)

class DeleteInvoiceMaterialService(graphene.Mutation):
    class Arguments:
        id_invoice_material_service = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_invoice_material_service):
        try:
            result = InvoiceMaterialServiceService.delete(id_invoice_material_service)
            return DeleteInvoiceMaterialService(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteInvoiceMaterialService(ok=False, message_key=error.message_key)

class CreateProductFamily(graphene.Mutation):
    class Arguments:
        input = ProductFamilyInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(ProductFamilyType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = ProductFamilyService.create(payload)
            return CreateProductFamily(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateProductFamily(ok=False, message_key=error.message_key, item=None)

class UpdateProductFamily(graphene.Mutation):
    class Arguments:
        id_product_family = graphene.Int(required=True)
        input = ProductFamilyInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(ProductFamilyType)
    @staticmethod
    def mutate(root, info, id_product_family, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = ProductFamilyService.update(id_product_family, payload)
            return UpdateProductFamily(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateProductFamily(ok=False, message_key=error.message_key, item=None)

class DeleteProductFamily(graphene.Mutation):
    class Arguments:
        id_product_family = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_product_family):
        try:
            result = ProductFamilyService.delete(id_product_family)
            return DeleteProductFamily(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteProductFamily(ok=False, message_key=error.message_key)

class CreateIncidentType(graphene.Mutation):
    class Arguments:
        input = IncidentTypeInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(IncidentTypeType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = IncidentTypeService.create(payload)
            return CreateIncidentType(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateIncidentType(ok=False, message_key=error.message_key, item=None)

class UpdateIncidentType(graphene.Mutation):
    class Arguments:
        id_incident_type = graphene.Int(required=True)
        input = IncidentTypeInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(IncidentTypeType)
    @staticmethod
    def mutate(root, info, id_incident_type, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = IncidentTypeService.update(id_incident_type, payload)
            return UpdateIncidentType(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateIncidentType(ok=False, message_key=error.message_key, item=None)

class DeleteIncidentType(graphene.Mutation):
    class Arguments:
        id_incident_type = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_incident_type):
        try:
            result = IncidentTypeService.delete(id_incident_type)
            return DeleteIncidentType(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteIncidentType(ok=False, message_key=error.message_key)

class CreateIncident(graphene.Mutation):
    class Arguments:
        input = IncidentInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(IncidentType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = IncidentService.create(payload)
            return CreateIncident(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateIncident(ok=False, message_key=error.message_key, item=None)

class UpdateIncident(graphene.Mutation):
    class Arguments:
        id_incident = graphene.Int(required=True)
        input = IncidentInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(IncidentType)
    @staticmethod
    def mutate(root, info, id_incident, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = IncidentService.update(id_incident, payload)
            return UpdateIncident(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateIncident(ok=False, message_key=error.message_key, item=None)

class DeleteIncident(graphene.Mutation):
    class Arguments:
        id_incident = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_incident):
        try:
            result = IncidentService.delete(id_incident)
            return DeleteIncident(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteIncident(ok=False, message_key=error.message_key)

class CreateIncidentDetail(graphene.Mutation):
    class Arguments:
        input = IncidentDetailInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(IncidentDetailType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = IncidentDetailService.create(payload)
            return CreateIncidentDetail(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateIncidentDetail(ok=False, message_key=error.message_key, item=None)

class UpdateIncidentDetail(graphene.Mutation):
    class Arguments:
        id_incident_detail = graphene.Int(required=True)
        input = IncidentDetailInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(IncidentDetailType)
    @staticmethod
    def mutate(root, info, id_incident_detail, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = IncidentDetailService.update(id_incident_detail, payload)
            return UpdateIncidentDetail(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateIncidentDetail(ok=False, message_key=error.message_key, item=None)

class DeleteIncidentDetail(graphene.Mutation):
    class Arguments:
        id_incident_detail = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_incident_detail):
        try:
            result = IncidentDetailService.delete(id_incident_detail)
            return DeleteIncidentDetail(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteIncidentDetail(ok=False, message_key=error.message_key)

class CreateBrand(graphene.Mutation):
    class Arguments:
        input = BrandInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(BrandType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = BrandService.create(payload)
            return CreateBrand(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateBrand(ok=False, message_key=error.message_key, item=None)

class UpdateBrand(graphene.Mutation):
    class Arguments:
        id_brand = graphene.Int(required=True)
        input = BrandInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(BrandType)
    @staticmethod
    def mutate(root, info, id_brand, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = BrandService.update(id_brand, payload)
            return UpdateBrand(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateBrand(ok=False, message_key=error.message_key, item=None)

class DeleteBrand(graphene.Mutation):
    class Arguments:
        id_brand = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_brand):
        try:
            result = BrandService.delete(id_brand)
            return DeleteBrand(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteBrand(ok=False, message_key=error.message_key)

class CreateUnit(graphene.Mutation):
    class Arguments:
        input = UnitInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(UnitType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = UnitService.create(payload)
            return CreateUnit(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateUnit(ok=False, message_key=error.message_key, item=None)

class UpdateUnit(graphene.Mutation):
    class Arguments:
        id_unit = graphene.Int(required=True)
        input = UnitInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(UnitType)
    @staticmethod
    def mutate(root, info, id_unit, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = UnitService.update(id_unit, payload)
            return UpdateUnit(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateUnit(ok=False, message_key=error.message_key, item=None)

class DeleteUnit(graphene.Mutation):
    class Arguments:
        id_unit = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_unit):
        try:
            result = UnitService.delete(id_unit)
            return DeleteUnit(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteUnit(ok=False, message_key=error.message_key)

class CreateMaterial(graphene.Mutation):
    class Arguments:
        input = MaterialInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(MaterialType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = MaterialService.create(payload)
            return CreateMaterial(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateMaterial(ok=False, message_key=error.message_key, item=None)

class UpdateMaterial(graphene.Mutation):
    class Arguments:
        id_material = graphene.Int(required=True)
        input = MaterialInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(MaterialType)
    @staticmethod
    def mutate(root, info, id_material, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = MaterialService.update(id_material, payload)
            return UpdateMaterial(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateMaterial(ok=False, message_key=error.message_key, item=None)

class DeleteMaterial(graphene.Mutation):
    class Arguments:
        id_material = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_material):
        try:
            result = MaterialService.delete(id_material)
            return DeleteMaterial(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteMaterial(ok=False, message_key=error.message_key)

class CreateMaterialComponent(graphene.Mutation):
    class Arguments:
        input = MaterialComponentInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(MaterialComponentType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = MaterialComponentService.create(payload)
            return CreateMaterialComponent(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateMaterialComponent(ok=False, message_key=error.message_key, item=None)

class UpdateMaterialComponent(graphene.Mutation):
    class Arguments:
        id_material_component = graphene.Int(required=True)
        input = MaterialComponentInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(MaterialComponentType)
    @staticmethod
    def mutate(root, info, id_material_component, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = MaterialComponentService.update(id_material_component, payload)
            return UpdateMaterialComponent(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateMaterialComponent(ok=False, message_key=error.message_key, item=None)

class DeleteMaterialComponent(graphene.Mutation):
    class Arguments:
        id_material_component = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_material_component):
        try:
            result = MaterialComponentService.delete(id_material_component)
            return DeleteMaterialComponent(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteMaterialComponent(ok=False, message_key=error.message_key)

class CreateMovement(graphene.Mutation):
    class Arguments:
        input = MovementInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(MovementType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = MovementService.create(payload)
            return CreateMovement(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateMovement(ok=False, message_key=error.message_key, item=None)

class UpdateMovement(graphene.Mutation):
    class Arguments:
        id_movement = graphene.Int(required=True)
        input = MovementInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(MovementType)
    @staticmethod
    def mutate(root, info, id_movement, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = MovementService.update(id_movement, payload)
            return UpdateMovement(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateMovement(ok=False, message_key=error.message_key, item=None)

class DeleteMovement(graphene.Mutation):
    class Arguments:
        id_movement = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_movement):
        try:
            result = MovementService.delete(id_movement)
            return DeleteMovement(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteMovement(ok=False, message_key=error.message_key)

class CreateLocationType(graphene.Mutation):
    class Arguments:
        input = LocationTypeInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(LocationTypeType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = LocationTypeService.create(payload)
            return CreateLocationType(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateLocationType(ok=False, message_key=error.message_key, item=None)

class UpdateLocationType(graphene.Mutation):
    class Arguments:
        id_location_type = graphene.Int(required=True)
        input = LocationTypeInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(LocationTypeType)
    @staticmethod
    def mutate(root, info, id_location_type, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = LocationTypeService.update(id_location_type, payload)
            return UpdateLocationType(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateLocationType(ok=False, message_key=error.message_key, item=None)

class DeleteLocationType(graphene.Mutation):
    class Arguments:
        id_location_type = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_location_type):
        try:
            result = LocationTypeService.delete(id_location_type)
            return DeleteLocationType(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteLocationType(ok=False, message_key=error.message_key)

class CreateLocation(graphene.Mutation):
    class Arguments:
        input = LocationInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(LocationType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = LocationService.create(payload)
            return CreateLocation(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateLocation(ok=False, message_key=error.message_key, item=None)

class UpdateLocation(graphene.Mutation):
    class Arguments:
        id_location = graphene.Int(required=True)
        input = LocationInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(LocationType)
    @staticmethod
    def mutate(root, info, id_location, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = LocationService.update(id_location, payload)
            return UpdateLocation(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateLocation(ok=False, message_key=error.message_key, item=None)

class DeleteLocation(graphene.Mutation):
    class Arguments:
        id_location = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_location):
        try:
            result = LocationService.delete(id_location)
            return DeleteLocation(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteLocation(ok=False, message_key=error.message_key)

class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(ProductType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = ProductService.create(payload)
            return CreateProduct(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateProduct(ok=False, message_key=error.message_key, item=None)

class UpdateProduct(graphene.Mutation):
    class Arguments:
        id_product = graphene.Int(required=True)
        input = ProductInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(ProductType)
    @staticmethod
    def mutate(root, info, id_product, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = ProductService.update(id_product, payload)
            return UpdateProduct(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateProduct(ok=False, message_key=error.message_key, item=None)

class DeleteProduct(graphene.Mutation):
    class Arguments:
        id_product = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_product):
        try:
            result = ProductService.delete(id_product)
            return DeleteProduct(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteProduct(ok=False, message_key=error.message_key)

class CreateNmIncidentProduct(graphene.Mutation):
    class Arguments:
        input = NmIncidentProductInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(NmIncidentProductType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = NmIncidentProductService.create(payload)
            return CreateNmIncidentProduct(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateNmIncidentProduct(ok=False, message_key=error.message_key, item=None)

class UpdateNmIncidentProduct(graphene.Mutation):
    class Arguments:
        id_nm_incident_product = graphene.Int(required=True)
        input = NmIncidentProductInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(NmIncidentProductType)
    @staticmethod
    def mutate(root, info, id_nm_incident_product, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = NmIncidentProductService.update(id_nm_incident_product, payload)
            return UpdateNmIncidentProduct(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateNmIncidentProduct(ok=False, message_key=error.message_key, item=None)

class DeleteNmIncidentProduct(graphene.Mutation):
    class Arguments:
        id_nm_incident_product = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_nm_incident_product):
        try:
            result = NmIncidentProductService.delete(id_nm_incident_product)
            return DeleteNmIncidentProduct(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteNmIncidentProduct(ok=False, message_key=error.message_key)

class CreateTask(graphene.Mutation):
    class Arguments:
        input = TaskInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(TaskType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = TaskService.create(payload)
            return CreateTask(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateTask(ok=False, message_key=error.message_key, item=None)

class UpdateTask(graphene.Mutation):
    class Arguments:
        id_task = graphene.Int(required=True)
        input = TaskInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(TaskType)
    @staticmethod
    def mutate(root, info, id_task, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = TaskService.update(id_task, payload)
            return UpdateTask(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateTask(ok=False, message_key=error.message_key, item=None)

class DeleteTask(graphene.Mutation):
    class Arguments:
        id_task = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_task):
        try:
            result = TaskService.delete(id_task)
            return DeleteTask(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteTask(ok=False, message_key=error.message_key)

class CreateTaskNote(graphene.Mutation):
    class Arguments:
        input = TaskNoteInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(TaskNoteType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = TaskNoteService.create(payload)
            return CreateTaskNote(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateTaskNote(ok=False, message_key=error.message_key, item=None)

class UpdateTaskNote(graphene.Mutation):
    class Arguments:
        id_task_note = graphene.Int(required=True)
        input = TaskNoteInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(TaskNoteType)
    @staticmethod
    def mutate(root, info, id_task_note, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = TaskNoteService.update(id_task_note, payload)
            return UpdateTaskNote(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateTaskNote(ok=False, message_key=error.message_key, item=None)

class DeleteTaskNote(graphene.Mutation):
    class Arguments:
        id_task_note = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_task_note):
        try:
            result = TaskNoteService.delete(id_task_note)
            return DeleteTaskNote(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteTaskNote(ok=False, message_key=error.message_key)

class CreateTicket(graphene.Mutation):
    class Arguments:
        input = TicketInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(TicketType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = TicketService.create(payload)
            return CreateTicket(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateTicket(ok=False, message_key=error.message_key, item=None)

class UpdateTicket(graphene.Mutation):
    class Arguments:
        id_ticket = graphene.Int(required=True)
        input = TicketInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(TicketType)
    @staticmethod
    def mutate(root, info, id_ticket, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = TicketService.update(id_ticket, payload)
            return UpdateTicket(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateTicket(ok=False, message_key=error.message_key, item=None)

class DeleteTicket(graphene.Mutation):
    class Arguments:
        id_ticket = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_ticket):
        try:
            result = TicketService.delete(id_ticket)
            return DeleteTicket(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteTicket(ok=False, message_key=error.message_key)

class CreateFiscalAccount(graphene.Mutation):
    class Arguments:
        input = FiscalAccountInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(FiscalAccountType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = FiscalAccountService.create(payload)
            return CreateFiscalAccount(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateFiscalAccount(ok=False, message_key=error.message_key, item=None)

class UpdateFiscalAccount(graphene.Mutation):
    class Arguments:
        id_fiscal_account = graphene.Int(required=True)
        input = FiscalAccountInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(FiscalAccountType)
    @staticmethod
    def mutate(root, info, id_fiscal_account, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = FiscalAccountService.update(id_fiscal_account, payload)
            return UpdateFiscalAccount(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateFiscalAccount(ok=False, message_key=error.message_key, item=None)

class DeleteFiscalAccount(graphene.Mutation):
    class Arguments:
        id_fiscal_account = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_fiscal_account):
        try:
            result = FiscalAccountService.delete(id_fiscal_account)
            return DeleteFiscalAccount(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteFiscalAccount(ok=False, message_key=error.message_key)

class CreateFiscalStamp(graphene.Mutation):
    class Arguments:
        input = FiscalStampInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(FiscalStampType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = FiscalStampService.create(payload)
            return CreateFiscalStamp(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateFiscalStamp(ok=False, message_key=error.message_key, item=None)

class UpdateFiscalStamp(graphene.Mutation):
    class Arguments:
        id_fiscal_stamp = graphene.Int(required=True)
        input = FiscalStampInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(FiscalStampType)
    @staticmethod
    def mutate(root, info, id_fiscal_stamp, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = FiscalStampService.update(id_fiscal_stamp, payload)
            return UpdateFiscalStamp(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateFiscalStamp(ok=False, message_key=error.message_key, item=None)

class DeleteFiscalStamp(graphene.Mutation):
    class Arguments:
        id_fiscal_stamp = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_fiscal_stamp):
        try:
            result = FiscalStampService.delete(id_fiscal_stamp)
            return DeleteFiscalStamp(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteFiscalStamp(ok=False, message_key=error.message_key)

class CreateFiscalRecord(graphene.Mutation):
    class Arguments:
        input = FiscalRecordInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(FiscalRecordType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = FiscalRecordService.create(payload)
            return CreateFiscalRecord(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateFiscalRecord(ok=False, message_key=error.message_key, item=None)

class UpdateFiscalRecord(graphene.Mutation):
    class Arguments:
        id_fiscal_record = graphene.Int(required=True)
        input = FiscalRecordInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(FiscalRecordType)
    @staticmethod
    def mutate(root, info, id_fiscal_record, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = FiscalRecordService.update(id_fiscal_record, payload)
            return UpdateFiscalRecord(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateFiscalRecord(ok=False, message_key=error.message_key, item=None)

class DeleteFiscalRecord(graphene.Mutation):
    class Arguments:
        id_fiscal_record = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_fiscal_record):
        try:
            result = FiscalRecordService.delete(id_fiscal_record)
            return DeleteFiscalRecord(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteFiscalRecord(ok=False, message_key=error.message_key)

class CreateService(graphene.Mutation):
    class Arguments:
        input = ServiceInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(ServiceType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = ServiceService.create(payload)
            return CreateService(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateService(ok=False, message_key=error.message_key, item=None)

class UpdateService(graphene.Mutation):
    class Arguments:
        id_service = graphene.Int(required=True)
        input = ServiceInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(ServiceType)
    @staticmethod
    def mutate(root, info, id_service, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = ServiceService.update(id_service, payload)
            return UpdateService(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateService(ok=False, message_key=error.message_key, item=None)

class DeleteService(graphene.Mutation):
    class Arguments:
        id_service = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_service):
        try:
            result = ServiceService.delete(id_service)
            return DeleteService(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteService(ok=False, message_key=error.message_key)

class CreateStatus(graphene.Mutation):
    class Arguments:
        input = StatusInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(StatusType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = StatusService.create(payload)
            return CreateStatus(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateStatus(ok=False, message_key=error.message_key, item=None)

class UpdateStatus(graphene.Mutation):
    class Arguments:
        id_status = graphene.Int(required=True)
        input = StatusInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(StatusType)
    @staticmethod
    def mutate(root, info, id_status, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = StatusService.update(id_status, payload)
            return UpdateStatus(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateStatus(ok=False, message_key=error.message_key, item=None)

class DeleteStatus(graphene.Mutation):
    class Arguments:
        id_status = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_status):
        try:
            result = StatusService.delete(id_status)
            return DeleteStatus(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteStatus(ok=False, message_key=error.message_key)

class CreateTheme(graphene.Mutation):
    class Arguments:
        input = ThemeInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(ThemeType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = ThemeService.create(payload)
            return CreateTheme(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateTheme(ok=False, message_key=error.message_key, item=None)

class UpdateTheme(graphene.Mutation):
    class Arguments:
        id_theme = graphene.Int(required=True)
        input = ThemeInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(ThemeType)
    @staticmethod
    def mutate(root, info, id_theme, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = ThemeService.update(id_theme, payload)
            return UpdateTheme(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateTheme(ok=False, message_key=error.message_key, item=None)

class DeleteTheme(graphene.Mutation):
    class Arguments:
        id_theme = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_theme):
        try:
            result = ThemeService.delete(id_theme)
            return DeleteTheme(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteTheme(ok=False, message_key=error.message_key)

class CreateDepartment(graphene.Mutation):
    class Arguments:
        input = DepartmentInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(DepartmentType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = DepartmentService.create(payload)
            return CreateDepartment(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateDepartment(ok=False, message_key=error.message_key, item=None)

class UpdateDepartment(graphene.Mutation):
    class Arguments:
        id_department = graphene.Int(required=True)
        input = DepartmentInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(DepartmentType)
    @staticmethod
    def mutate(root, info, id_department, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = DepartmentService.update(id_department, payload)
            return UpdateDepartment(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateDepartment(ok=False, message_key=error.message_key, item=None)

class DeleteDepartment(graphene.Mutation):
    class Arguments:
        id_department = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_department):
        try:
            result = DepartmentService.delete(id_department)
            return DeleteDepartment(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteDepartment(ok=False, message_key=error.message_key)

class CreateSubdepartment(graphene.Mutation):
    class Arguments:
        input = SubdepartmentInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(SubdepartmentType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = SubdepartmentService.create(payload)
            return CreateSubdepartment(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateSubdepartment(ok=False, message_key=error.message_key, item=None)

class UpdateSubdepartment(graphene.Mutation):
    class Arguments:
        id_subdepartment = graphene.Int(required=True)
        input = SubdepartmentInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(SubdepartmentType)
    @staticmethod
    def mutate(root, info, id_subdepartment, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = SubdepartmentService.update(id_subdepartment, payload)
            return UpdateSubdepartment(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateSubdepartment(ok=False, message_key=error.message_key, item=None)

class DeleteSubdepartment(graphene.Mutation):
    class Arguments:
        id_subdepartment = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_subdepartment):
        try:
            result = SubdepartmentService.delete(id_subdepartment)
            return DeleteSubdepartment(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteSubdepartment(ok=False, message_key=error.message_key)

class CreateLevel(graphene.Mutation):
    class Arguments:
        input = LevelInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(LevelType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = LevelService.create(payload)
            return CreateLevel(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateLevel(ok=False, message_key=error.message_key, item=None)

class UpdateLevel(graphene.Mutation):
    class Arguments:
        id_level = graphene.Int(required=True)
        input = LevelInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(LevelType)
    @staticmethod
    def mutate(root, info, id_level, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = LevelService.update(id_level, payload)
            return UpdateLevel(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateLevel(ok=False, message_key=error.message_key, item=None)

class DeleteLevel(graphene.Mutation):
    class Arguments:
        id_level = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_level):
        try:
            result = LevelService.delete(id_level)
            return DeleteLevel(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteLevel(ok=False, message_key=error.message_key)

class CreateField(graphene.Mutation):
    class Arguments:
        input = FieldInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(FieldType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = FieldService.create(payload)
            return CreateField(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateField(ok=False, message_key=error.message_key, item=None)

class UpdateField(graphene.Mutation):
    class Arguments:
        id_field = graphene.Int(required=True)
        input = FieldInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(FieldType)
    @staticmethod
    def mutate(root, info, id_field, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = FieldService.update(id_field, payload)
            return UpdateField(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateField(ok=False, message_key=error.message_key, item=None)

class DeleteField(graphene.Mutation):
    class Arguments:
        id_field = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_field):
        try:
            result = FieldService.delete(id_field)
            return DeleteField(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteField(ok=False, message_key=error.message_key)

class CreatePermission(graphene.Mutation):
    class Arguments:
        input = PermissionInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(PermissionType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = PermissionService.create(payload)
            return CreatePermission(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreatePermission(ok=False, message_key=error.message_key, item=None)

class UpdatePermission(graphene.Mutation):
    class Arguments:
        id_permission = graphene.Int(required=True)
        input = PermissionInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(PermissionType)
    @staticmethod
    def mutate(root, info, id_permission, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = PermissionService.update(id_permission, payload)
            return UpdatePermission(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdatePermission(ok=False, message_key=error.message_key, item=None)

class DeletePermission(graphene.Mutation):
    class Arguments:
        id_permission = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_permission):
        try:
            result = PermissionService.delete(id_permission)
            return DeletePermission(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeletePermission(ok=False, message_key=error.message_key)

class CreateNmFieldPermission(graphene.Mutation):
    class Arguments:
        input = NmFieldPermissionInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(NmFieldPermissionType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = NmFieldPermissionService.create(payload)
            return CreateNmFieldPermission(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateNmFieldPermission(ok=False, message_key=error.message_key, item=None)

class UpdateNmFieldPermission(graphene.Mutation):
    class Arguments:
        id_nm_field_permission = graphene.Int(required=True)
        input = NmFieldPermissionInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(NmFieldPermissionType)
    @staticmethod
    def mutate(root, info, id_nm_field_permission, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = NmFieldPermissionService.update(id_nm_field_permission, payload)
            return UpdateNmFieldPermission(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateNmFieldPermission(ok=False, message_key=error.message_key, item=None)

class DeleteNmFieldPermission(graphene.Mutation):
    class Arguments:
        id_nm_field_permission = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_nm_field_permission):
        try:
            result = NmFieldPermissionService.delete(id_nm_field_permission)
            return DeleteNmFieldPermission(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteNmFieldPermission(ok=False, message_key=error.message_key)

class CreateEventLog(graphene.Mutation):
    class Arguments:
        input = EventLogInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(EventLogType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = EventLogService.create(payload)
            return CreateEventLog(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateEventLog(ok=False, message_key=error.message_key, item=None)

class UpdateEventLog(graphene.Mutation):
    class Arguments:
        id_event_log = graphene.Int(required=True)
        input = EventLogInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(EventLogType)
    @staticmethod
    def mutate(root, info, id_event_log, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = EventLogService.update(id_event_log, payload)
            return UpdateEventLog(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateEventLog(ok=False, message_key=error.message_key, item=None)

class DeleteEventLog(graphene.Mutation):
    class Arguments:
        id_event_log = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_event_log):
        try:
            result = EventLogService.delete(id_event_log)
            return DeleteEventLog(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteEventLog(ok=False, message_key=error.message_key)

class CreateTaskType(graphene.Mutation):
    class Arguments:
        input = TaskTypeInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(TaskTypeType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = TaskTypeService.create(payload)
            return CreateTaskType(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateTaskType(ok=False, message_key=error.message_key, item=None)

class UpdateTaskType(graphene.Mutation):
    class Arguments:
        id_task_type = graphene.Int(required=True)
        input = TaskTypeInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(TaskTypeType)
    @staticmethod
    def mutate(root, info, id_task_type, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = TaskTypeService.update(id_task_type, payload)
            return UpdateTaskType(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateTaskType(ok=False, message_key=error.message_key, item=None)

class DeleteTaskType(graphene.Mutation):
    class Arguments:
        id_task_type = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_task_type):
        try:
            result = TaskTypeService.delete(id_task_type)
            return DeleteTaskType(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteTaskType(ok=False, message_key=error.message_key)

class CreateTemplate(graphene.Mutation):
    class Arguments:
        input = TemplateInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(TemplateType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = TemplateService.create(payload)
            return CreateTemplate(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateTemplate(ok=False, message_key=error.message_key, item=None)

class UpdateTemplate(graphene.Mutation):
    class Arguments:
        id_template = graphene.Int(required=True)
        input = TemplateInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(TemplateType)
    @staticmethod
    def mutate(root, info, id_template, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = TemplateService.update(id_template, payload)
            return UpdateTemplate(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateTemplate(ok=False, message_key=error.message_key, item=None)

class DeleteTemplate(graphene.Mutation):
    class Arguments:
        id_template = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_template):
        try:
            result = TemplateService.delete(id_template)
            return DeleteTemplate(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteTemplate(ok=False, message_key=error.message_key)

class CreateNmTemplateTask(graphene.Mutation):
    class Arguments:
        input = NmTemplateTaskInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(NmTemplateTaskType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = NmTemplateTaskService.create(payload)
            return CreateNmTemplateTask(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateNmTemplateTask(ok=False, message_key=error.message_key, item=None)

class UpdateNmTemplateTask(graphene.Mutation):
    class Arguments:
        id_nm_template_task = graphene.Int(required=True)
        input = NmTemplateTaskInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(NmTemplateTaskType)
    @staticmethod
    def mutate(root, info, id_nm_template_task, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = NmTemplateTaskService.update(id_nm_template_task, payload)
            return UpdateNmTemplateTask(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateNmTemplateTask(ok=False, message_key=error.message_key, item=None)

class DeleteNmTemplateTask(graphene.Mutation):
    class Arguments:
        id_nm_template_task = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_nm_template_task):
        try:
            result = NmTemplateTaskService.delete(id_nm_template_task)
            return DeleteNmTemplateTask(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteNmTemplateTask(ok=False, message_key=error.message_key)

class CreateSurveyQuestion(graphene.Mutation):
    class Arguments:
        input = SurveyQuestionInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(SurveyQuestionType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = SurveyQuestionService.create(payload)
            return CreateSurveyQuestion(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateSurveyQuestion(ok=False, message_key=error.message_key, item=None)

class UpdateSurveyQuestion(graphene.Mutation):
    class Arguments:
        id_survey_question = graphene.Int(required=True)
        input = SurveyQuestionInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(SurveyQuestionType)
    @staticmethod
    def mutate(root, info, id_survey_question, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = SurveyQuestionService.update(id_survey_question, payload)
            return UpdateSurveyQuestion(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateSurveyQuestion(ok=False, message_key=error.message_key, item=None)

class DeleteSurveyQuestion(graphene.Mutation):
    class Arguments:
        id_survey_question = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_survey_question):
        try:
            result = SurveyQuestionService.delete(id_survey_question)
            return DeleteSurveyQuestion(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteSurveyQuestion(ok=False, message_key=error.message_key)

class CreateSurveyMultipleAnswer(graphene.Mutation):
    class Arguments:
        input = SurveyMultipleAnswerInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(SurveyMultipleAnswerType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = SurveyMultipleAnswerService.create(payload)
            return CreateSurveyMultipleAnswer(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateSurveyMultipleAnswer(ok=False, message_key=error.message_key, item=None)

class UpdateSurveyMultipleAnswer(graphene.Mutation):
    class Arguments:
        id_survey_multiple_answer = graphene.Int(required=True)
        input = SurveyMultipleAnswerInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(SurveyMultipleAnswerType)
    @staticmethod
    def mutate(root, info, id_survey_multiple_answer, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = SurveyMultipleAnswerService.update(id_survey_multiple_answer, payload)
            return UpdateSurveyMultipleAnswer(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateSurveyMultipleAnswer(ok=False, message_key=error.message_key, item=None)

class DeleteSurveyMultipleAnswer(graphene.Mutation):
    class Arguments:
        id_survey_multiple_answer = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_survey_multiple_answer):
        try:
            result = SurveyMultipleAnswerService.delete(id_survey_multiple_answer)
            return DeleteSurveyMultipleAnswer(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteSurveyMultipleAnswer(ok=False, message_key=error.message_key)

class CreateNmSurveyUser(graphene.Mutation):
    class Arguments:
        input = NmSurveyUserInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(NmSurveyUserType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = NmSurveyUserService.create(payload)
            return CreateNmSurveyUser(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateNmSurveyUser(ok=False, message_key=error.message_key, item=None)

class UpdateNmSurveyUser(graphene.Mutation):
    class Arguments:
        id_nm_survey_user = graphene.Int(required=True)
        input = NmSurveyUserInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(NmSurveyUserType)
    @staticmethod
    def mutate(root, info, id_nm_survey_user, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = NmSurveyUserService.update(id_nm_survey_user, payload)
            return UpdateNmSurveyUser(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateNmSurveyUser(ok=False, message_key=error.message_key, item=None)

class DeleteNmSurveyUser(graphene.Mutation):
    class Arguments:
        id_nm_survey_user = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_nm_survey_user):
        try:
            result = NmSurveyUserService.delete(id_nm_survey_user)
            return DeleteNmSurveyUser(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteNmSurveyUser(ok=False, message_key=error.message_key)

class CreateEntityPermission(graphene.Mutation):
    class Arguments:
        input = EntityPermissionInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(EntityPermissionType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = EntityPermissionService.create(payload)
            return CreateEntityPermission(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateEntityPermission(ok=False, message_key=error.message_key, item=None)

class UpdateEntityPermission(graphene.Mutation):
    class Arguments:
        id_entity_permission = graphene.Int(required=True)
        input = EntityPermissionInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(EntityPermissionType)
    @staticmethod
    def mutate(root, info, id_entity_permission, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = EntityPermissionService.update(id_entity_permission, payload)
            return UpdateEntityPermission(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateEntityPermission(ok=False, message_key=error.message_key, item=None)

class DeleteEntityPermission(graphene.Mutation):
    class Arguments:
        id_entity_permission = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_entity_permission):
        try:
            result = EntityPermissionService.delete(id_entity_permission)
            return DeleteEntityPermission(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteEntityPermission(ok=False, message_key=error.message_key)

class CreateInventoryStatus(graphene.Mutation):
    class Arguments:
        input = InventoryStatusInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(InventoryStatusType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = InventoryStatusService.create(payload)
            return CreateInventoryStatus(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateInventoryStatus(ok=False, message_key=error.message_key, item=None)

class UpdateInventoryStatus(graphene.Mutation):
    class Arguments:
        id_inventory_status = graphene.Int(required=True)
        input = InventoryStatusInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(InventoryStatusType)
    @staticmethod
    def mutate(root, info, id_inventory_status, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = InventoryStatusService.update(id_inventory_status, payload)
            return UpdateInventoryStatus(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateInventoryStatus(ok=False, message_key=error.message_key, item=None)

class DeleteInventoryStatus(graphene.Mutation):
    class Arguments:
        id_inventory_status = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_inventory_status):
        try:
            result = InventoryStatusService.delete(id_inventory_status)
            return DeleteInventoryStatus(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteInventoryStatus(ok=False, message_key=error.message_key)

class CreateProductSaleConfig(graphene.Mutation):
    class Arguments:
        input = ProductSaleConfigInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(ProductSaleConfigType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = ProductSaleConfigService.create(payload)
            return CreateProductSaleConfig(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreateProductSaleConfig(ok=False, message_key=error.message_key, item=None)

class UpdateProductSaleConfig(graphene.Mutation):
    class Arguments:
        id_product_sale_config = graphene.Int(required=True)
        input = ProductSaleConfigInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(ProductSaleConfigType)
    @staticmethod
    def mutate(root, info, id_product_sale_config, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = ProductSaleConfigService.update(id_product_sale_config, payload)
            return UpdateProductSaleConfig(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdateProductSaleConfig(ok=False, message_key=error.message_key, item=None)

class DeleteProductSaleConfig(graphene.Mutation):
    class Arguments:
        id_product_sale_config = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_product_sale_config):
        try:
            result = ProductSaleConfigService.delete(id_product_sale_config)
            return DeleteProductSaleConfig(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeleteProductSaleConfig(ok=False, message_key=error.message_key)

class CreatePublicApiKey(graphene.Mutation):
    class Arguments:
        input = PublicApiKeyInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(PublicApiKeyType)
    @staticmethod
    def mutate(root, info, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = PublicApiKeyService.create(payload)
            return CreatePublicApiKey(ok=True, message_key="graphql.create_success", item=item)
        except AppError as error:
            return CreatePublicApiKey(ok=False, message_key=error.message_key, item=None)

class UpdatePublicApiKey(graphene.Mutation):
    class Arguments:
        id_public_api_key = graphene.Int(required=True)
        input = PublicApiKeyInput(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    item = graphene.Field(PublicApiKeyType)
    @staticmethod
    def mutate(root, info, id_public_api_key, input):
        payload = {k: v for k, v in dict(input).items() if v is not None}
        try:
            item = PublicApiKeyService.update(id_public_api_key, payload)
            return UpdatePublicApiKey(ok=True, message_key="graphql.update_success", item=item)
        except AppError as error:
            return UpdatePublicApiKey(ok=False, message_key=error.message_key, item=None)

class DeletePublicApiKey(graphene.Mutation):
    class Arguments:
        id_public_api_key = graphene.Int(required=True)
    ok = graphene.Boolean(required=True)
    message_key = graphene.String(required=True)
    @staticmethod
    def mutate(root, info, id_public_api_key):
        try:
            result = PublicApiKeyService.delete(id_public_api_key)
            return DeletePublicApiKey(ok=True, message_key=result.get("message_key", "graphql.delete_success"))
        except AppError as error:
            return DeletePublicApiKey(ok=False, message_key=error.message_key)

class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()
    update_user = UpdateUser.Field()
    delete_user = DeleteUser.Field()
    create_userMfa = CreateUserMfa.Field()
    update_userMfa = UpdateUserMfa.Field()
    delete_userMfa = DeleteUserMfa.Field()
    create_payrollPeriod = CreatePayrollPeriod.Field()
    update_payrollPeriod = UpdatePayrollPeriod.Field()
    delete_payrollPeriod = DeletePayrollPeriod.Field()
    create_payrollDetail = CreatePayrollDetail.Field()
    update_payrollDetail = UpdatePayrollDetail.Field()
    delete_payrollDetail = DeletePayrollDetail.Field()
    create_payrollConcept = CreatePayrollConcept.Field()
    update_payrollConcept = UpdatePayrollConcept.Field()
    delete_payrollConcept = DeletePayrollConcept.Field()
    create_payrollMovement = CreatePayrollMovement.Field()
    update_payrollMovement = UpdatePayrollMovement.Field()
    delete_payrollMovement = DeletePayrollMovement.Field()
    create_customerSupplier = CreateCustomerSupplier.Field()
    update_customerSupplier = UpdateCustomerSupplier.Field()
    delete_customerSupplier = DeleteCustomerSupplier.Field()
    create_proyect = CreateProyect.Field()
    update_proyect = UpdateProyect.Field()
    delete_proyect = DeleteProyect.Field()
    create_bank = CreateBank.Field()
    update_bank = UpdateBank.Field()
    delete_bank = DeleteBank.Field()
    create_bankAccount = CreateBankAccount.Field()
    update_bankAccount = UpdateBankAccount.Field()
    delete_bankAccount = DeleteBankAccount.Field()
    create_invoice = CreateInvoice.Field()
    update_invoice = UpdateInvoice.Field()
    delete_invoice = DeleteInvoice.Field()
    create_invoiceMaterialService = CreateInvoiceMaterialService.Field()
    update_invoiceMaterialService = UpdateInvoiceMaterialService.Field()
    delete_invoiceMaterialService = DeleteInvoiceMaterialService.Field()
    create_productFamily = CreateProductFamily.Field()
    update_productFamily = UpdateProductFamily.Field()
    delete_productFamily = DeleteProductFamily.Field()
    create_incidentType = CreateIncidentType.Field()
    update_incidentType = UpdateIncidentType.Field()
    delete_incidentType = DeleteIncidentType.Field()
    create_incident = CreateIncident.Field()
    update_incident = UpdateIncident.Field()
    delete_incident = DeleteIncident.Field()
    create_incidentDetail = CreateIncidentDetail.Field()
    update_incidentDetail = UpdateIncidentDetail.Field()
    delete_incidentDetail = DeleteIncidentDetail.Field()
    create_brand = CreateBrand.Field()
    update_brand = UpdateBrand.Field()
    delete_brand = DeleteBrand.Field()
    create_unit = CreateUnit.Field()
    update_unit = UpdateUnit.Field()
    delete_unit = DeleteUnit.Field()
    create_material = CreateMaterial.Field()
    update_material = UpdateMaterial.Field()
    delete_material = DeleteMaterial.Field()
    create_materialComponent = CreateMaterialComponent.Field()
    update_materialComponent = UpdateMaterialComponent.Field()
    delete_materialComponent = DeleteMaterialComponent.Field()
    create_movement = CreateMovement.Field()
    update_movement = UpdateMovement.Field()
    delete_movement = DeleteMovement.Field()
    create_locationType = CreateLocationType.Field()
    update_locationType = UpdateLocationType.Field()
    delete_locationType = DeleteLocationType.Field()
    create_location = CreateLocation.Field()
    update_location = UpdateLocation.Field()
    delete_location = DeleteLocation.Field()
    create_product = CreateProduct.Field()
    update_product = UpdateProduct.Field()
    delete_product = DeleteProduct.Field()
    create_nmIncidentProduct = CreateNmIncidentProduct.Field()
    update_nmIncidentProduct = UpdateNmIncidentProduct.Field()
    delete_nmIncidentProduct = DeleteNmIncidentProduct.Field()
    create_task = CreateTask.Field()
    update_task = UpdateTask.Field()
    delete_task = DeleteTask.Field()
    create_taskNote = CreateTaskNote.Field()
    update_taskNote = UpdateTaskNote.Field()
    delete_taskNote = DeleteTaskNote.Field()
    create_ticket = CreateTicket.Field()
    update_ticket = UpdateTicket.Field()
    delete_ticket = DeleteTicket.Field()
    create_fiscalAccount = CreateFiscalAccount.Field()
    update_fiscalAccount = UpdateFiscalAccount.Field()
    delete_fiscalAccount = DeleteFiscalAccount.Field()
    create_fiscalStamp = CreateFiscalStamp.Field()
    update_fiscalStamp = UpdateFiscalStamp.Field()
    delete_fiscalStamp = DeleteFiscalStamp.Field()
    create_fiscalRecord = CreateFiscalRecord.Field()
    update_fiscalRecord = UpdateFiscalRecord.Field()
    delete_fiscalRecord = DeleteFiscalRecord.Field()
    create_service = CreateService.Field()
    update_service = UpdateService.Field()
    delete_service = DeleteService.Field()
    create_status = CreateStatus.Field()
    update_status = UpdateStatus.Field()
    delete_status = DeleteStatus.Field()
    create_theme = CreateTheme.Field()
    update_theme = UpdateTheme.Field()
    delete_theme = DeleteTheme.Field()
    create_department = CreateDepartment.Field()
    update_department = UpdateDepartment.Field()
    delete_department = DeleteDepartment.Field()
    create_subdepartment = CreateSubdepartment.Field()
    update_subdepartment = UpdateSubdepartment.Field()
    delete_subdepartment = DeleteSubdepartment.Field()
    create_level = CreateLevel.Field()
    update_level = UpdateLevel.Field()
    delete_level = DeleteLevel.Field()
    create_field = CreateField.Field()
    update_field = UpdateField.Field()
    delete_field = DeleteField.Field()
    create_permission = CreatePermission.Field()
    update_permission = UpdatePermission.Field()
    delete_permission = DeletePermission.Field()
    create_nmFieldPermission = CreateNmFieldPermission.Field()
    update_nmFieldPermission = UpdateNmFieldPermission.Field()
    delete_nmFieldPermission = DeleteNmFieldPermission.Field()
    create_eventLog = CreateEventLog.Field()
    update_eventLog = UpdateEventLog.Field()
    delete_eventLog = DeleteEventLog.Field()
    create_taskType = CreateTaskType.Field()
    update_taskType = UpdateTaskType.Field()
    delete_taskType = DeleteTaskType.Field()
    create_template = CreateTemplate.Field()
    update_template = UpdateTemplate.Field()
    delete_template = DeleteTemplate.Field()
    create_nmTemplateTask = CreateNmTemplateTask.Field()
    update_nmTemplateTask = UpdateNmTemplateTask.Field()
    delete_nmTemplateTask = DeleteNmTemplateTask.Field()
    create_surveyQuestion = CreateSurveyQuestion.Field()
    update_surveyQuestion = UpdateSurveyQuestion.Field()
    delete_surveyQuestion = DeleteSurveyQuestion.Field()
    create_surveyMultipleAnswer = CreateSurveyMultipleAnswer.Field()
    update_surveyMultipleAnswer = UpdateSurveyMultipleAnswer.Field()
    delete_surveyMultipleAnswer = DeleteSurveyMultipleAnswer.Field()
    create_nmSurveyUser = CreateNmSurveyUser.Field()
    update_nmSurveyUser = UpdateNmSurveyUser.Field()
    delete_nmSurveyUser = DeleteNmSurveyUser.Field()
    create_entityPermission = CreateEntityPermission.Field()
    update_entityPermission = UpdateEntityPermission.Field()
    delete_entityPermission = DeleteEntityPermission.Field()
    create_inventoryStatus = CreateInventoryStatus.Field()
    update_inventoryStatus = UpdateInventoryStatus.Field()
    delete_inventoryStatus = DeleteInventoryStatus.Field()
    create_productSaleConfig = CreateProductSaleConfig.Field()
    update_productSaleConfig = UpdateProductSaleConfig.Field()
    delete_productSaleConfig = DeleteProductSaleConfig.Field()
    create_publicApiKey = CreatePublicApiKey.Field()
    update_publicApiKey = UpdatePublicApiKey.Field()
    delete_publicApiKey = DeletePublicApiKey.Field()
