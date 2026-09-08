from sqlalchemy import func, select

from app.models import Invoice, Product
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class ProductService(CrudService):
    model = Product
    primary_key = 'id_product'
    entity_name = 'product'

    # La nota que identifica la factura de captura directa. No es una factura de
    # verdad: es el documento al que se cuelga lo que el almacen da de alta sin
    # compra detras.
    NOTA_DE_CAPTURA = "Captura directa de almacen"

    @classmethod
    def factura_de_captura(cls, session, user_data: dict | None = None):
        """La factura a la que se cuelga un producto capturado sin documento.

        `product.id_invoice` es NOT NULL con llave ajena, asi que un producto
        SIEMPRE pertenece a un documento. Pero obligar a elegir una factura para
        dar de alta un desarmador es pedir un dato que quien captura no tiene, y
        acaba colgandolo de la primera factura de la lista -que es peor que no
        tener ninguna, porque miente-.

        Asi que hay una por proyecto, con su nota, y se crea la primera vez que
        alguien captura sin factura. Su proyecto importa: el alcance del almacen
        se resuelve por el proyecto de la factura, y sin el el producto no lo
        veria nadie salvo un superusuario.
        """
        from app.models import CustomerSupplier, Proyect, Status

        id_proyecto = None
        try:
            id_proyecto = cls._project_id(user_data or {})
        except AppError:
            id_proyecto = None
        if id_proyecto is None:
            fila = session.scalars(
                select(Proyect).where(Proyect.deletion_date.is_(None))
                .order_by(Proyect.id_proyect).limit(1)
            ).first()
            id_proyecto = fila.id_proyect if fila else None

        consulta = select(Invoice).where(
            Invoice.note == cls.NOTA_DE_CAPTURA,
            Invoice.deletion_date.is_(None),
        )
        if id_proyecto is not None:
            consulta = consulta.where(Invoice.id_proyect == id_proyecto)
        existente = session.scalars(consulta.limit(1)).first()
        if existente is not None:
            return existente.id_invoice

        empresa = session.scalars(
            select(CustomerSupplier)
            .where(CustomerSupplier.deletion_date.is_(None))
            .order_by(CustomerSupplier.id_customer_supplier).limit(1)
        ).first()
        estatus = session.scalars(
            select(Status).order_by(Status.id_status).limit(1)).first()
        if empresa is None or estatus is None:
            # Sin empresa ni estatus no se puede armar el documento, y colgar el
            # producto de cualquier factura seria decir que vino de una compra
            # que no existe.
            raise AppError("errors.invoice_required_for_product", status_code=409,
                           meta={"field": "id_invoice"})

        factura = Invoice(
            id_customer_supplier=empresa.id_customer_supplier,
            id_issuer_customer_supplier=empresa.id_customer_supplier,
            tax_certification_supplier=empresa.id_customer_supplier,
            id_status=estatus.id_status,
            id_proyect=id_proyecto,
            invoice_status="captura",
            note=cls.NOTA_DE_CAPTURA,
            apply_tax=False,
            manual_capture=True,
            created_by=int((user_data or {}).get("id_user") or 1),
        )
        session.add(factura)
        session.flush()
        return factura.id_invoice

    @classmethod
    def _rechazar_lot_control(cls, payload: dict) -> dict:
        """El control por lote no se enciende escribiendo la columna.

        Encenderlo en un producto que YA tiene existencia deja esa existencia
        fuera de todo lote, y como la salida se sirve de los lotes, esas unidades
        no se pueden despachar: el saldo dice que estan y los lotes dicen que no.
        Medido al probar contra Postgres, donde el cuadre salio en falso con
        saldo 1 y 0 en lotes.

        Para eso esta `POST /product/<id>/lot-control`, que enciende y crea el
        lote de apertura con lo que ya habia, en la misma transaccion.
        """
        if 'lot_control' in (payload or {}):
            raise AppError(
                'errors.lot_control_needs_its_own_endpoint',
                400,
                {'field': 'lot_control',
                 'use': 'POST /product/<id_product>/lot-control'},
            )
        return payload

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        """Da de alta el producto y le da SITIO a su existencia desde el minuto uno.

        Sin esto, un producto recien creado con `cantidad` no tenia ninguna fila
        en `inventory_stock` hasta que alguien lo moviera, y mientras tanto la
        pantalla de Localizar lo mostraba sin ubicacion -las ubicaciones de un
        producto se leen de ahi- y desaparecia en cuanto alguien filtraba por
        almacen. Era el bug de "no salen los productos en localizar".

        Cae en la ubicacion general cuando el producto no trae una propia, que es
        como llega casi todo lo del sistema original.
        """
        payload = cls._rechazar_lot_control(dict(payload or {}))

        # Sin factura no se rechaza: se resuelve la de captura directa. Es lo que
        # permite dar de alta un desarmador sin inventarse un documento de
        # compra, respetando la llave ajena.
        if not str(payload.get("id_invoice") or "").strip():
            with transaction_context() as session:
                payload["id_invoice"] = cls.factura_de_captura(
                    session, {"id_user": user_id})

        creado = super().create(payload, user_id=user_id)

        # Import local: el servicio de inventario arrastra media docena de
        # modelos y no hace falta al importar este modulo.
        from app.models import Product as _Product
        from app.services.inventory_service import sembrar_existencia_inicial

        id_producto = (creado or {}).get('id_product')
        if id_producto:
            with transaction_context() as session:
                producto = session.get(_Product, id_producto)
                if producto is not None:
                    sembrar_existencia_inicial(session, producto)
        return creado

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        return super().update(item_id, cls._rechazar_lot_control(payload),
                              user_id=user_id)

    @staticmethod
    def _project_id(user_data: dict) -> int | None:
        if user_data.get('is_superuser') or user_data.get('is_bootstrap_admin'):
            return None
        try:
            return int(user_data.get('id_proyect'))
        except (TypeError, ValueError):
            raise AppError('errors.project_scope_required', status_code=403)

    @classmethod
    def list_scoped(cls, user_data: dict, page: int = 1, per_page: int = 20, filters: dict | None = None, sort: str | None = None):
        project_id = cls._project_id(user_data)
        if project_id is None:
            return cls.list(page=page, per_page=per_page, filters=filters, sort=sort)

        filters = filters or {}
        with transaction_context() as session:
            stmt = select(Product).join(Invoice, Product.id_invoice == Invoice.id_invoice).where(Invoice.id_proyect == project_id)
            for key, value in filters.items():
                if not hasattr(Product, key) or value in (None, ''):
                    continue
                column = getattr(Product, key)
                stmt = stmt.where(column.ilike(f'%{value}%') if isinstance(value, str) else column == value)
            if sort and hasattr(Product, sort.lstrip('-')):
                column = getattr(Product, sort.lstrip('-'))
                stmt = stmt.order_by(column.desc() if sort.startswith('-') else column.asc())
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
    def require_record_scope(cls, item_id, user_data: dict) -> None:
        project_id = cls._project_id(user_data)
        if project_id is None:
            return
        with transaction_context() as session:
            exists = session.scalar(
                select(Product.id_product)
                .join(Invoice, Product.id_invoice == Invoice.id_invoice)
                .where(Product.id_product == item_id, Invoice.id_proyect == project_id)
            )
            if exists is None:
                raise AppError('errors.resource_not_found', status_code=404)

    @classmethod
    def require_invoice_scope(cls, invoice_id, user_data: dict) -> None:
        project_id = cls._project_id(user_data)
        if project_id is None:
            return
        try:
            invoice_id = int(invoice_id)
        except (TypeError, ValueError):
            raise AppError('errors.invalid_field', status_code=400, meta={'field': 'id_invoice'})
        with transaction_context() as session:
            exists = session.scalar(
                select(Invoice.id_invoice).where(
                    Invoice.id_invoice == invoice_id,
                    Invoice.id_proyect == project_id,
                )
            )
            if exists is None:
                raise AppError('errors.resource_not_found', status_code=404)
