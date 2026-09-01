from app.models.base import Base
from app.models.bank import Bank
from app.models.bank_account import BankAccount
from app.models.bank_statement import BankStatement, BankStatementMovement
from app.models.appointment import Appointment, AppointmentType, AvailabilityOverride, AvailabilityRule, CalendarProfile
from app.models.brand import Brand
from app.models.customer_supplier import CustomerSupplier
from app.models.department import Department
from app.models.entity_permission import EntityPermission
from app.models.event_log import EventLog
from app.models.field import Field
from app.models.fiscal_account import FiscalAccount
from app.models.fiscal_record import FiscalRecord
from app.models.fiscal_stamp import FiscalStamp
from app.models.incident import Incident
from app.models.incident_detail import IncidentDetail
from app.models.incident_type import IncidentType
from app.models.inventory_status import InventoryStatus
from app.models.inventory_asset import InventoryAsset
from app.models.inventory_asset_event import InventoryAssetEvent
from app.models.inventory_ledger import InventoryLedger
from app.models.inventory_stock import InventoryStock
from app.models.invoice import Invoice
from app.models.invoice_material_service import InvoiceMaterialService
from app.models.cfdi_relation import CfdiRelation
from app.models.invoice_cancellation import InvoiceCancellation
from app.models.invoice_payment import InvoicePayment
from app.models.level import Level
from app.models.location import Location
from app.models.location_type import LocationType
from app.models.logistics_address import LogisticsAddress
from app.models.logistics_branch import LogisticsBranch
from app.models.logistics_contact import LogisticsContact
from app.models.logistics_contract import LogisticsContract
from app.models.logistics_evidence import LogisticsEvidence
from app.models.logistics_file import LogisticsFile
from app.models.logistics_incident import LogisticsIncident
from app.models.logistics_inventory import LogisticsInventory
from app.models.logistics_location import LogisticsLocation
from app.models.logistics_maintenance import LogisticsMaintenance
from app.models.logistics_operator import LogisticsOperator
from app.models.logistics_quotation import LogisticsQuotation
from app.models.logistics_rack import LogisticsRack
from app.models.logistics_rate import LogisticsRate
from app.models.logistics_receivable import LogisticsReceivable
from app.models.logistics_shipment import LogisticsShipment
from app.models.logistics_trailer import LogisticsTrailer
from app.models.logistics_trip import LogisticsTrip
from app.models.logistics_unit import LogisticsUnit
from app.models.logistics_service_request import LogisticsServiceRequest
from app.models.logistics_warehouse import LogisticsWarehouse
from app.models.material import Material
from app.models.material_component import MaterialComponent
from app.models.movement import Movement
from app.models.nm_field_permission import NmFieldPermission
from app.models.nm_incident_product import NmIncidentProduct
from app.models.nm_survey_user import NmSurveyUser
from app.models.nm_template_task import NmTemplateTask
from app.models.pac_config import PacConfig
from app.models.password_reset_token import PasswordResetToken
from app.models.payroll_concept import PayrollConcept
from app.models.payroll_detail import PayrollDetail
from app.models.payroll_movement import PayrollMovement
from app.models.payroll_period import PayrollPeriod
from app.models.permission import Permission
from app.models.pos_product_link import PosProductLink
from app.models.product import Product
from app.models.product_family import ProductFamily
from app.models.product_sale_config import ProductSaleConfig
from app.models.proyect import Proyect
from app.models.proyect_event import ProyectEvent
from app.models.quotation_comment import QuotationComment
from app.models.restaurant import (
	RestaurantCashSession,
	RestaurantCategory,
	RestaurantDish,
	RestaurantGuisado,
	RestaurantInventoryItem,
	RestaurantInventoryMovement,
	RestaurantOrder,
	RestaurantOrderItem,
	RestaurantRecipeItem,
	RestaurantReservation,
	RestaurantTable,
	RestaurantVisit,
	RestaurantWaiter,
)
from app.models.public_api_key import PublicApiKey
from app.models.service import Service
from app.models.status import Status
from app.models.sat_product_key import SatProductKey
from app.models.stamping_operation import StampingOperation
from app.models.subdepartment import Subdepartment
from app.models.survey_multiple_answer import SurveyMultipleAnswer
from app.models.survey_question import SurveyQuestion
from app.models.task import Task
from app.models.task_note import TaskNote
from app.models.task_type import TaskType
from app.models.template import Template
from app.models.theme import Theme
from app.models.ticket import Ticket
from app.models.unit import Unit
from app.models.user import User
from app.models.user_mfa import UserMfa

__all__ = ['Base', 'Appointment', 'AppointmentType', 'AvailabilityOverride', 'AvailabilityRule', 'CalendarProfile', 'Bank', 'BankAccount', 'BankStatement', 'BankStatementMovement', 'Brand', 'CfdiRelation', 'CustomerSupplier', 'Department', 'EntityPermission', 'EventLog', 'Field', 'FiscalAccount', 'FiscalRecord', 'FiscalStamp', 'Incident', 'IncidentDetail', 'IncidentType', 'InventoryAsset', 'InventoryAssetEvent', 'InventoryLedger', 'InventoryStatus', 'InventoryStock', 'Invoice', 'InvoiceCancellation', 'InvoiceMaterialService', 'InvoicePayment', 'Level', 'Location', 'LocationType', 'LogisticsAddress', 'LogisticsBranch', 'LogisticsContact', 'LogisticsContract', 'LogisticsEvidence', 'LogisticsFile', 'LogisticsIncident', 'LogisticsInventory', 'LogisticsLocation', 'LogisticsMaintenance', 'LogisticsOperator', 'LogisticsQuotation', 'LogisticsRack', 'LogisticsRate', 'LogisticsReceivable', 'LogisticsServiceRequest', 'LogisticsShipment', 'LogisticsTrailer', 'LogisticsTrip', 'LogisticsUnit', 'LogisticsWarehouse', 'Material', 'MaterialComponent', 'Movement', 'NmFieldPermission', 'NmIncidentProduct', 'NmSurveyUser', 'NmTemplateTask', 'PacConfig', 'PasswordResetToken', 'PayrollConcept', 'PayrollDetail', 'PayrollMovement', 'PayrollPeriod', 'Permission', 'Product', 'ProductFamily', 'ProductSaleConfig', 'Proyect', 'ProyectEvent', 'PublicApiKey', 'QuotationComment', 'RestaurantCashSession', 'RestaurantCategory', 'RestaurantDish', 'RestaurantGuisado', 'RestaurantInventoryItem', 'RestaurantInventoryMovement', 'RestaurantOrder', 'RestaurantOrderItem', 'RestaurantRecipeItem', 'RestaurantReservation', 'RestaurantTable', 'RestaurantVisit', 'RestaurantWaiter', 'Service', 'SatProductKey', 'StampingOperation', 'Status', 'Subdepartment', 'SurveyMultipleAnswer', 'SurveyQuestion', 'Task', 'TaskNote', 'TaskType', 'Template', 'Theme', 'Ticket', 'Unit', 'User', 'UserMfa']

def _make_foreign_keys_deferrable() -> int:
    """Marca todas las llaves foraneas como diferibles, comprobadas de inmediato.

    Por que hace falta: las tablas de user, permission, proyect y
    customer_supplier se referencian en circulo, y dos de esas columnas son
    obligatorias (`permission.authorized_by` y `user.id_permission`). Ninguna
    puede insertarse primero, asi que NINGUN orden de sentencias puede sembrar
    una base nueva. A eso se suma que el orden del archivo de semillas no
    respeta las dependencias en 694 pares.

    `DEFERRABLE INITIALLY IMMEDIATE` no cambia el comportamiento normal: la
    llave se sigue comprobando en cada sentencia. Lo unico que habilita es que
    una transaccion pida explicitamente aplazar la comprobacion al COMMIT, que
    es lo que hace la siembra. Se prefiere sobre INITIALLY DEFERRED justamente
    para que los errores de la aplicacion sigan saliendo donde ocurren.

    Se aplica aqui, sobre el metadata, porque el arranque crea el esquema desde
    los modelos: declararlo solo en una migracion no alcanzaria para una
    instalacion nueva.
    """
    ajustadas = 0
    for tabla in Base.metadata.tables.values():
        for restriccion in tabla.foreign_key_constraints:
            if not restriccion.deferrable:
                restriccion.deferrable = True
                restriccion.initially = "IMMEDIATE"
                ajustadas += 1
    return ajustadas


_make_foreign_keys_deferrable()
