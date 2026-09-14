from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.models import CustomerSupplier, Invoice, LogisticsBranch, LogisticsOperator, LogisticsTrailer, LogisticsUnit, User
from app.models.logistics_evidence import LogisticsEvidence
from app.models.logistics_file import LogisticsFile
from app.models.logistics_incident import LogisticsIncident
from app.models.logistics_quotation import LogisticsQuotation
from app.models.logistics_receivable import LogisticsReceivable
from app.models.logistics_service_request import LogisticsServiceRequest
from app.models.logistics_shipment import LogisticsShipment
from app.models.logistics_trip import LogisticsTrip
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class LogisticsWorkflowService(CrudService):
    @classmethod
    def _domain(cls, payload: dict, field: str, allowed: set[str]) -> None:
        if field in payload and payload[field] not in allowed:
            raise AppError(f'validations.{cls.entity_name}.{field}.invalid', status_code=400, meta={'field': field})

    @classmethod
    def _nonnegative(cls, payload: dict, fields: tuple[str, ...]) -> None:
        for field in fields:
            if field not in payload or payload[field] in (None, ''):
                continue
            try:
                if Decimal(str(payload[field])) < 0:
                    raise AppError(f'validations.{cls.entity_name}.{field}.invalid', status_code=400, meta={'field': field})
            except (InvalidOperation, TypeError, ValueError):
                raise AppError('errors.invalid_field', status_code=400, meta={'field': field})

    @classmethod
    def _fk(cls, payload: dict, field: str, model, label: str, *, required: bool = False):
        value = payload.get(field)
        if value in (None, ''):
            if required:
                raise AppError(f'validations.{cls.entity_name}.{label}.required', status_code=400, meta={'field': field})
            if field in payload:
                payload[field] = None
            return None
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise AppError(f'validations.{cls.entity_name}.{label}.invalid', status_code=400, meta={'field': field})
        with transaction_context() as session:
            item = session.get(model, value)
            if not item or getattr(item, 'deletion_date', None) is not None:
                raise AppError(f'validations.{cls.entity_name}.{label}.invalid', status_code=400, meta={'field': field})
            if model is CustomerSupplier and item.type != 'client':
                raise AppError(f'validations.{cls.entity_name}.{label}.invalid', status_code=400, meta={'field': field})
            serialized = item.serialize()
        payload[field] = value
        return serialized

    @classmethod
    def _matching_client(cls, client: dict | None, record: dict | None, field: str) -> None:
        if client and record and record.get('id_customer_supplier') != client.get('id_customer_supplier'):
            raise AppError(f'validations.{cls.entity_name}.{field}.invalid', status_code=400, meta={'field': field})

    @classmethod
    def _date_order(cls, payload: dict, start_field: str, end_field: str) -> None:
        start = payload.get(start_field)
        end = payload.get(end_field)
        if not start or not end:
            return
        try:
            start_value = start if isinstance(start, datetime) else datetime.fromisoformat(str(start).replace('Z', '+00:00'))
            end_value = end if isinstance(end, datetime) else datetime.fromisoformat(str(end).replace('Z', '+00:00'))
        except (TypeError, ValueError):
            raise AppError('errors.invalid_field', status_code=400, meta={'field': end_field})
        if end_value < start_value:
            raise AppError(f'validations.{cls.entity_name}.dates.invalid', status_code=400, meta={'field': end_field})


class LogisticsQuotationService(LogisticsWorkflowService):
    model = LogisticsQuotation
    primary_key = 'id_logistics_quotation'
    entity_name = 'logistics_quotation'

    @classmethod
    def _validate(cls, payload: dict, creating: bool = False) -> dict:
        payload = dict(payload or {})
        cls._fk(payload, 'id_customer_supplier', CustomerSupplier, 'client', required=creating)
        cls._nonnegative(payload, ('kilometers', 'maneuvers', 'storage', 'total'))
        cls._domain(payload, 'status', {'borrador', 'enviada', 'aceptada', 'rechazada', 'vencida', 'cancelada'})
        if 'additional_services' in payload and not isinstance(payload['additional_services'], dict):
            raise AppError('validations.logistics_quotation.additional_services.invalid', status_code=400, meta={'field': 'additional_services'})
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload, True), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)


class LogisticsServiceRequestService(LogisticsWorkflowService):
    model = LogisticsServiceRequest
    primary_key = 'id_logistics_service_request'
    entity_name = 'logistics_service_request'

    @classmethod
    def _validate(cls, payload: dict, creating: bool = False) -> dict:
        payload = dict(payload or {})
        client = cls._fk(payload, 'id_customer_supplier', CustomerSupplier, 'client', required=creating)
        quotation = cls._fk(payload, 'id_logistics_quotation', LogisticsQuotation, 'quotation')
        if client and quotation and quotation['id_customer_supplier'] != client['id_customer_supplier']:
            raise AppError('validations.logistics_service_request.quotation.invalid', status_code=400, meta={'field': 'id_logistics_quotation'})
        cls._domain(payload, 'status', {'solicitado', 'aprobado', 'programado', 'cancelado'})
        cls._domain(payload, 'priority', {'baja', 'normal', 'alta', 'urgente'})
        cls._date_order(payload, 'requested_pickup_at', 'requested_delivery_at')
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload, True), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)


class LogisticsTripService(LogisticsWorkflowService):
    model = LogisticsTrip
    primary_key = 'id_logistics_trip'
    entity_name = 'logistics_trip'

    @classmethod
    def _validate(cls, payload: dict, creating: bool = False) -> dict:
        payload = dict(payload or {})
        client = cls._fk(payload, 'id_customer_supplier', CustomerSupplier, 'client', required=creating)
        request = cls._fk(payload, 'id_logistics_service_request', LogisticsServiceRequest, 'request', required=creating)
        if client and request and request['id_customer_supplier'] != client['id_customer_supplier']:
            raise AppError('validations.logistics_trip.request.invalid', status_code=400, meta={'field': 'id_logistics_service_request'})
        cls._fk(payload, 'id_logistics_unit', LogisticsUnit, 'unit')
        cls._fk(payload, 'id_logistics_trailer', LogisticsTrailer, 'trailer')
        cls._fk(payload, 'id_logistics_operator', LogisticsOperator, 'operator')
        logistics_file = cls._fk(payload, 'id_logistics_file', LogisticsFile, 'file')
        cls._matching_client(client, logistics_file, 'id_logistics_file')
        cls._nonnegative(payload, ('planned_cost', 'actual_cost', 'revenue', 'kilometers'))
        cls._domain(payload, 'status', {'solicitado', 'planeado', 'asignado', 'cargado', 'en tránsito', 'en ruta', 'retrasado', 'entregado', 'cerrado', 'facturado', 'cancelado'})
        cls._date_order(payload, 'planned_pickup_at', 'planned_delivery_at')
        cls._date_order(payload, 'actual_pickup_at', 'actual_delivery_at')
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload, True), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)


class LogisticsShipmentService(LogisticsWorkflowService):
    model = LogisticsShipment
    primary_key = 'id_logistics_shipment'
    entity_name = 'logistics_shipment'

    @classmethod
    def _validate(cls, payload: dict, creating: bool = False) -> dict:
        payload = dict(payload or {})
        cls._fk(payload, 'id_customer_supplier', CustomerSupplier, 'client', required=creating)
        cls._domain(payload, 'status', {'registrado', 'en tránsito', 'en aduana', 'liberado', 'entregado'})
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload, True), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)


class LogisticsBranchService(LogisticsWorkflowService):
    model = LogisticsBranch
    primary_key = 'id_logistics_branch'
    entity_name = 'logistics_branch'

    @classmethod
    def _validate(cls, payload: dict) -> dict:
        payload = dict(payload or {})
        cls._domain(payload, 'status', {'activo', 'inactivo'})
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)


class LogisticsReceivableService(LogisticsWorkflowService):
    model = LogisticsReceivable
    primary_key = 'id_logistics_receivable'
    entity_name = 'logistics_receivable'

    @classmethod
    def _validate(cls, payload: dict, creating: bool = False) -> dict:
        payload = dict(payload or {})
        client = cls._fk(payload, 'id_customer_supplier', CustomerSupplier, 'client', required=creating)
        invoice = cls._fk(payload, 'id_invoice', Invoice, 'invoice', required=creating)
        cls._matching_client(client, invoice, 'id_invoice')
        cls._nonnegative(payload, ('amount',))
        cls._domain(payload, 'status', {'pendiente', 'pagado', 'vencido'})
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload, True), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)


class LogisticsFileService(LogisticsWorkflowService):
    model = LogisticsFile
    primary_key = 'id_logistics_file'
    entity_name = 'logistics_file'

    @classmethod
    def _validate(cls, payload: dict, creating: bool = False) -> dict:
        payload = dict(payload or {})
        client = cls._fk(payload, 'id_customer_supplier', CustomerSupplier, 'client', required=creating)
        cls._fk(payload, 'id_logistics_branch', LogisticsBranch, 'branch')
        invoice = cls._fk(payload, 'id_invoice', Invoice, 'invoice')
        cls._matching_client(client, invoice, 'id_invoice')
        cls._domain(payload, 'status', {'abierto', 'facturando', 'facturado'})
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload, True), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)


class LogisticsEvidenceService(LogisticsWorkflowService):
    model = LogisticsEvidence
    primary_key = 'id_logistics_evidence'
    entity_name = 'logistics_evidence'

    @classmethod
    def _validate(cls, payload: dict, creating: bool = False) -> dict:
        payload = dict(payload or {})
        cls._fk(payload, 'id_logistics_trip', LogisticsTrip, 'trip', required=creating)
        cls._fk(payload, 'captured_by', User, 'captured_by')
        for field, minimum, maximum in (('latitude', -90, 90), ('longitude', -180, 180)):
            if field in payload and payload[field] not in (None, ''):
                try:
                    value = Decimal(str(payload[field]))
                except (InvalidOperation, TypeError, ValueError):
                    raise AppError('errors.invalid_field', status_code=400, meta={'field': field})
                if value < minimum or value > maximum:
                    raise AppError(f'validations.logistics_evidence.{field}.invalid', status_code=400, meta={'field': field})
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload, True), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)


class LogisticsIncidentService(LogisticsWorkflowService):
    model = LogisticsIncident
    primary_key = 'id_logistics_incident'
    entity_name = 'logistics_incident'

    @classmethod
    def _validate(cls, payload: dict, creating: bool = False) -> dict:
        payload = dict(payload or {})
        cls._fk(payload, 'id_logistics_trip', LogisticsTrip, 'trip', required=creating)
        cls._fk(payload, 'responsible_user_id', User, 'responsible_user')
        cls._domain(payload, 'severity', {'baja', 'media', 'alta', 'critica'})
        cls._domain(payload, 'status', {'abierta', 'en_proceso', 'resuelta', 'cerrada', 'cancelada'})
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._validate(payload, True), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._validate(payload), user_id=user_id)