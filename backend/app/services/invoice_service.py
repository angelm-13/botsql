"""Facturas, acotadas al proyecto de la factura.

El hueco
--------
El CRUD de facturas llamaba a los metodos base sin filtro, mientras el resto del
modulo si exigia proyecto. Medido con dos usuarios reales, uno en cada proyecto:
la descarga del XML respondia 404 al ajeno y el registro que lo respalda
respondia 200, tanto al leerlo como al modificarlo. El documento estaba
protegido y la factura no, aunque el registro lleva el RFC del receptor, los
importes y el folio fiscal.

Que regla se aplica y por que esta
----------------------------------
Igualdad estricta: se opera una factura solo si pertenece al proyecto del actor.
No es un criterio nuevo, es el que el modulo ya aplicaba en cinco caminos -la
descarga del XML y del PDF, la cancelacion, el complemento de pago, las notas de
credito y la aplicacion al almacen-. Faltaba en el CRUD, que es justo la puerta
mas ancha.

Se eligio este y no la visibilidad por facultad que rige proyectos y tareas -donde
quien autoriza ve todos los proyectos- por tres razones: es lo que este modulo ya
hacia en la mayoria de sus rutas; un comprobante fiscal es atribuible ante la
autoridad y no hay necesidad operativa de tocarlo desde otro proyecto; y ante la
duda, en un arreglo de acceso conviene la opcion mas cerrada.

Si el negocio decide que un gerente con facultad de autorizar debe ver las
facturas de todos los proyectos, ahora es un cambio en un solo lugar -este- en
vez de en once rutas.
"""

from __future__ import annotations

from sqlalchemy import String, func, select

from app.models import Invoice
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class InvoiceService(CrudService):
    model = Invoice
    primary_key = 'id_invoice'
    entity_name = 'invoice'

    @staticmethod
    def actor_project(user_data: dict) -> int | None:
        """Proyecto del actor, o None si no tiene limite.

        Solo la cuenta de arranque queda sin limite. Un actor sin proyecto no
        pasa: sin el no hay forma de acotar, y dejarlo pasar convertiria el
        filtro en un adorno.
        """
        if user_data.get('is_superuser') or user_data.get('is_bootstrap_admin'):
            return None
        raw = user_data.get('id_proyect') or user_data.get('project_id')
        try:
            project_id = int(raw)
        except (TypeError, ValueError):
            raise AppError('errors.project_scope_required', 403)
        if not project_id:
            raise AppError('errors.project_scope_required', 403)
        return project_id

    @classmethod
    def list_scoped(cls, user_data: dict, page: int = 1, per_page: int = 20,
                    filters: dict | None = None, sort: str | None = None,
                    q: str | None = None):
        project_id = cls.actor_project(user_data)
        if project_id is None:
            return cls.list(page=page, per_page=per_page, filters=filters, sort=sort, q=q)

        filters = filters or {}
        with transaction_context() as session:
            stmt = select(Invoice).where(
                Invoice.id_proyect == project_id,
                Invoice.deletion_date.is_(None),
            )
            # La misma busqueda libre que la lista sin alcance. Va DESPUES del
            # filtro de proyecto y como una condicion mas, no en su lugar: si
            # sustituyera al alcance, buscar seria una forma de ver las facturas
            # de otro proyecto.
            busqueda = cls._busqueda_libre(q)
            if busqueda is not None:
                stmt = stmt.where(busqueda)
            for key, value in filters.items():
                tipo = cls._columns().get(key)
                if tipo is None or value in (None, ''):
                    continue
                column = getattr(Invoice, key)
                # Coincidencia parcial solo en texto; en numeros revienta en Postgres.
                stmt = stmt.where(
                    column.ilike(f'%{value}%') if isinstance(value, str) and isinstance(tipo.type, String)
                    else column == value
                )
            if sort and sort.lstrip('-') in cls._columns():
                column = getattr(Invoice, sort.lstrip('-'))
                stmt = stmt.order_by(column.desc() if sort.startswith('-') else column.asc())
            else:
                stmt = stmt.order_by(Invoice.id_invoice.desc())

            total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            items = session.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()
            return {
                'items': [item.serialize() for item in items],
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page,
            }

    @classmethod
    def require_scope(cls, invoice_id, user_data: dict) -> None:
        """Exige que la factura sea del proyecto del actor.

        Responde 404 y no 403 cuando queda fuera: quien no participa en el
        proyecto tampoco debe enterarse de que la factura existe. Es el mismo
        criterio que ya usaban la descarga de documentos y las incidencias.
        """
        try:
            invoice_id = int(invoice_id)
        except (TypeError, ValueError) as exc:
            raise AppError('errors.invalid_field', 400, {'field': 'id_invoice'}) from exc

        project_id = cls.actor_project(user_data)

        with transaction_context() as session:
            invoice_project = session.scalar(
                select(Invoice.id_proyect).where(
                    Invoice.id_invoice == invoice_id,
                    Invoice.deletion_date.is_(None),
                )
            )

        if invoice_project is None:
            # Cubre las dos cosas a la vez: la factura no existe, o existe sin
            # proyecto. Una factura sin proyecto no se puede acotar, asi que
            # tampoco se entrega; dejarla pasar seria un hueco permanente.
            raise AppError('errors.resource_not_found', 404)

        if project_id is not None and int(invoice_project) != project_id:
            raise AppError('errors.resource_not_found', 404)

    @classmethod
    def require_project_for_write(cls, project_id, user_data: dict) -> None:
        """El proyecto que llega en el cuerpo de un alta o de un traslado.

        Sin esto se podria crear una factura dentro de un proyecto ajeno, o
        mover una existente a otro proyecto: la misma fuga por la puerta de
        atras, y esta ademas cambia datos.
        """
        actor_project = cls.actor_project(user_data)
        if actor_project is None:
            return
        if project_id in (None, ''):
            raise AppError('errors.required_field', 400, {'field': 'id_proyect'})
        try:
            target = int(project_id)
        except (TypeError, ValueError) as exc:
            raise AppError('errors.invalid_field', 400, {'field': 'id_proyect'}) from exc
        if target != actor_project:
            raise AppError('errors.permission_denied', 403,
                           {'entity': 'invoice', 'field': 'id_proyect'})
