from sqlalchemy import func, select

from app.models import Invoice, InventoryStock, Material, Product
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError
from app.utils.product_description import es_valida, sugerir


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
    def _rechazar_codigo_repetido(cls, item_id, payload: dict) -> dict:
        """El codigo identifica a UN producto vivo.

        Nada lo impedia: ESC-06 se capturo dos veces (ids 2132 y 2516) y el
        buscador devolvia dos productos con el mismo codigo. Solo se compara si el
        codigo viene y es distinto del que ya tiene -la base migrada trae codigos
        repetidos y editar otro campo de esos productos tiene que seguir
        funcionando-; un producto dado de baja no cuenta.
        """
        codigo = str(payload.get('product_code') or '').strip()
        if not codigo:
            return payload
        with transaction_context() as session:
            if item_id is not None:
                actual = session.get(Product, int(item_id))
                if actual is not None and str(actual.product_code or '').strip().upper() == codigo.upper():
                    return payload
            repetido = session.scalars(
                select(Product.id_product).where(
                    func.upper(func.trim(Product.product_code)) == codigo.upper(),
                    Product.deletion_date.is_(None),
                ).limit(1)
            ).first()
        if repetido is not None:
            raise AppError('errors.product_code_duplicate', status_code=409,
                           meta={'field': 'product_code', 'id_product': repetido})
        return payload

    @classmethod
    def _exigir_existencia_para_en_almacen(cls, item_id, payload: dict) -> dict:
        """Un producto no se marca "En almacen" (ENTRADA) sin existencia.

        El estado es solo un texto: marcar En almacen una pieza con existencia 0 la deja
        diciendo "esta aqui" sin que el libro lo respalde, y el buscador del vale no la
        ofrece. Se pide primero la entrada de existencia (al menos 1) y despues el
        cambio.

        Solo se mira cuando el estado CAMBIA a En almacen en una edicion: guardar otro
        campo de un producto que ya esta En almacen, o dar de alta uno, sigue igual.
        """
        from app.utils.product_status import clave

        if item_id is None or 'product_status' not in payload:
            return payload
        if clave(payload.get('product_status')) != 'entrada':
            return payload
        with transaction_context() as session:
            fila = session.get(Product, int(item_id))
            if fila is None or clave(fila.product_status) == 'entrada':
                return payload
            por_ubicacion = session.scalar(
                select(func.coalesce(func.sum(InventoryStock.quantity), 0))
                .where(InventoryStock.id_product == int(item_id)))
            existencia = int(por_ubicacion or 0) or int(fila.cantidad or 0)
        if existencia < 1:
            raise AppError('errors.product_status_needs_stock', status_code=409,
                           meta={'field': 'product_status', 'status': 'ENTRADA',
                                 'existencia': existencia})
        return payload

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
    def exigir_descripcion_en_oracion(cls, payload: dict, item_id=None) -> None:
        """Rechaza una descripcion que no viene en formato de oracion.

        Se llama desde las rutas (la captura de una persona), no desde `create`/
        `update`: la migracion, la recepcion de compras y las pruebas dan de alta
        productos con sus propios textos y no deben tropezar con una regla de
        captura. En una EDICION solo se exige si el texto cambio: el formulario
        devuelve el registro completo, y un producto migrado en mayusculas no
        puede quedar imposible de editar por algo que no se toco.
        """
        if 'descripcion' not in (payload or {}):
            return
        nueva = payload.get('descripcion')
        if item_id is not None:
            with transaction_context() as session:
                try:
                    fila = session.get(Product, int(item_id))
                except (TypeError, ValueError):
                    fila = None
                if fila is not None and (fila.descripcion or '') == (nueva or ''):
                    return
        if not es_valida(nueva):
            raise AppError(
                'errors.product_description_format', status_code=400,
                meta={'field': 'descripcion', 'suggestion': sugerir(nueva)},
            )

    @staticmethod
    def _clasificacion_del_material(payload: dict) -> dict:
        """La familia y la marca las define el producto; si no se dan, se parte de las del material.

        Un producto es su material mas su familia y su marca: lo que el producto traiga se
        respeta. Solo cuando falta se completa con la del material, y solo si esa es real (no
        "Sin categoria" / "Sin marca especifica", que significan "no se sabe").
        """
        from app.models.brand import Brand
        from app.models.product_family import ProductFamily
        from app.services.inventory_trace_service import FAMILIA_SIN_DATO, MARCA_SIN_DATO

        id_material = ProductService._entero_o_none(payload.get('id_material'))
        if id_material is None:
            return payload
        with transaction_context() as session:
            fila = session.execute(
                select(Material.id_brand, Brand.brand_description,
                       Material.id_product_family, ProductFamily.product_family_description)
                .join(Brand, Brand.id_brand == Material.id_brand)
                .join(ProductFamily, ProductFamily.id_product_family == Material.id_product_family)
                .where(Material.id_material == id_material)).first()
        if fila is None:
            return payload
        id_marca, marca, id_familia, familia = fila
        if marca != MARCA_SIN_DATO and not str(payload.get('id_marca') or '').strip():
            payload['id_marca'] = id_marca
        if familia != FAMILIA_SIN_DATO and not str(payload.get('id_familia') or '').strip():
            payload['id_familia'] = id_familia
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
        payload = cls._rechazar_codigo_repetido(None, cls._rechazar_lot_control(dict(payload or {})))
        payload = cls._sincronizar_estado(None, payload)
        payload = cls._clasificacion_del_material(payload)

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

    @staticmethod
    def _entero_o_none(valor):
        try:
            return int(float(valor))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _rechazar_cantidad_a_mano(cls, item_id, payload: dict) -> dict:
        """La existencia no se edita escribiendo `cantidad`.

        `product.cantidad` es la suma de la existencia por ubicacion y el libro
        de movimientos la respalda (ver `inventory_service`): escribirla directo
        deja el saldo diciendo una cosa y el libro otra, y sin rastro de quien
        la movio ni por que. Lo que entra va por la entrada de existencia, lo
        que sale por el vale, y un conteo fisico por el ajuste de inventario.

        El formulario de edicion devuelve el registro completo, `cantidad`
        incluida: si viene igual a lo que ya hay no se esta moviendo nada.
        """
        if 'cantidad' not in payload:
            return payload
        with transaction_context() as session:
            try:
                fila = session.get(Product, int(item_id))
            except (TypeError, ValueError):
                fila = None
            actual = fila.cantidad if fila is not None else None
        if cls._entero_o_none(payload['cantidad']) == cls._entero_o_none(actual):
            payload.pop('cantidad')
            return payload
        raise AppError('errors.product_quantity_via_movements', status_code=409,
                       meta={'field': 'cantidad'})

    @classmethod
    def _sincronizar_estado(cls, item_id, payload: dict) -> dict:
        """Escribe `product_status` e `id_inventory_status` juntos.

        Antes cada uno se guardaba por su lado: el formulario cambiaba solo el
        texto y el vale solo el catalogo, y el producto quedaba diciendo dos
        cosas (3 en adser-prod, MARR4 "usado" con el catalogo en "extraviado").

        El formulario manda el registro completo, asi que lo que cuenta es lo que
        CAMBIO frente a lo guardado:
        - cambio el texto -> manda el texto: su codigo de catalogo pasa a
          `id_inventory_status`; si el texto no es un estado (ENTRADA, SALIDA,
          vacio) el catalogo se limpia, porque dejarlo diria otra cosa;
        - cambio el catalogo -> manda el catalogo: el texto pasa a su codigo;
        - cambiaron los dos -> manda el catalogo, que es el dato nuevo.
        """
        if 'product_status' not in payload and 'id_inventory_status' not in payload:
            return payload
        from app.models.inventory_status import InventoryStatus
        from app.utils.product_status import clave, codigo_de_catalogo

        payload = dict(payload)
        with transaction_context() as session:
            fila = None
            if item_id is not None:
                try:
                    fila = session.get(Product, int(item_id))
                except (TypeError, ValueError):
                    fila = None
            texto_actual = fila.product_status if fila is not None else None
            id_actual = fila.id_inventory_status if fila is not None else None

            def _id(valor):
                try:
                    return int(valor) if str(valor).strip() != '' else None
                except (TypeError, ValueError):
                    return None

            cambio_texto = ('product_status' in payload
                            and clave(payload['product_status']) != clave(texto_actual))
            cambio_id = ('id_inventory_status' in payload
                         and _id(payload['id_inventory_status']) != id_actual)

            if cambio_id:
                nuevo_id = _id(payload['id_inventory_status'])
                if nuevo_id is None:
                    # Sin estado de catalogo: un texto que diga uno contradice.
                    texto = payload.get('product_status', texto_actual)
                    if codigo_de_catalogo(texto):
                        payload['product_status'] = None
                    return payload
                estado = session.get(InventoryStatus, nuevo_id)
                if estado is not None and estado.deletion_date is None:
                    # Si el texto ya dice lo mismo (DAÑADO y danado), se respeta
                    # tal cual: no se reescribe una historia que no se contradice.
                    if codigo_de_catalogo(payload.get('product_status')) != estado.inventory_status_code:
                        payload['product_status'] = estado.inventory_status_code
                return payload

            if cambio_texto:
                codigo = codigo_de_catalogo(payload['product_status'])
                if codigo is None:
                    payload['id_inventory_status'] = None
                    return payload
                encontrado = session.scalars(
                    select(InventoryStatus.id_inventory_status).where(
                        InventoryStatus.inventory_status_code == codigo,
                        InventoryStatus.entity_scope == 'product',
                        InventoryStatus.deletion_date.is_(None),
                    ).limit(1)
                ).first()
                # Un catalogo sin sembrar no tumba el guardado: se deja el id como esta.
                if encontrado is not None:
                    payload['id_inventory_status'] = encontrado
        return payload

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        # `_rechazar_cantidad_a_mano` es el mismo guardia que escribio por su
        # cuenta `initAlan` (ver su docstring): `PUT /product/<id>` aceptaba
        # `cantidad` como cualquier otro campo, y quien tuviera el permiso de
        # campo (o fuera superusuario, que se salta esa comprobacion por
        # completo) podia cambiar el saldo sin capacidad de ajuste, sin
        # motivo y sin renglon en el ledger -- mismo hallazgo de la auditoria
        # de seguridad del 2026-10-06 que esta rama encontro por su lado;
        # dos arreglos del mismo bug, se queda el de `initAlan` por ser la
        # rama compartida.
        payload = cls._rechazar_codigo_repetido(item_id, cls._rechazar_cantidad_a_mano(item_id, dict(payload or {})))
        payload = cls._sincronizar_estado(item_id, payload)
        payload = cls._exigir_existencia_para_en_almacen(item_id, payload)
        payload = cls._clasificacion_del_material(payload)
        # Los formularios de edicion devuelven el registro completo, `lot_control`
        # incluido. Si viene igual a lo que ya hay no se esta encendiendo nada, y
        # rechazarlo hacia imposible guardar CUALQUIER edicion de un producto.
        if 'lot_control' in payload:
            actual = None
            with transaction_context() as session:
                try:
                    fila = session.get(Product, int(item_id))
                except (TypeError, ValueError):
                    fila = None
                if fila is not None:
                    actual = bool(fila.lot_control)
            if actual is not None and cls._como_booleano(payload['lot_control']) == actual:
                payload.pop('lot_control')
        return super().update(item_id, cls._rechazar_lot_control(payload),
                              user_id=user_id)

    @staticmethod
    def heredar_foto_del_material(items: list[dict]) -> list[dict]:
        """A un producto sin foto propia le presta la de su material.

        La foto se captura una vez en Materiales y la heredan todos los
        productos que no traen la suya. Es solo de LECTURA: no escribe nada en
        `product.path_imagen`, asi que subirle foto al producto despues la hace
        mandar, y quitarsela devuelve la del material.
        """
        pendientes = {
            int(i['id_material']) for i in items
            if not i.get('path_imagen') and i.get('id_material')
        }
        if not pendientes:
            return items
        with transaction_context() as session:
            fotos = dict(session.execute(
                select(Material.id_material, Material.path_imagen).where(
                    Material.id_material.in_(list(pendientes)),
                    Material.path_imagen.isnot(None),
                )
            ).all())
        for item in items:
            if not item.get('path_imagen') and item.get('id_material'):
                item['path_imagen'] = fotos.get(int(item['id_material'])) or item.get('path_imagen')
        return items

    @staticmethod
    def agregar_estado_efectivo(items: list[dict]) -> list[dict]:
        """Agrega `effective_status` a cada producto: el que se pinta.

        `product_status` es un texto que los vales de prestamo no actualizan, asi
        que un producto prestado seguia diciendo ENTRADA. La regla es la de
        Localizar (`estatus_efectivo`); no se copia. Solo LECTURA.
        """
        # Import local: el servicio de rastreo importa de los de vales e inventario.
        from app.services.inventory_trace_service import estatus_efectivo_en_lote

        ids = {int(i['id_product']): i.get('product_status')
               for i in items if i.get('id_product') is not None}
        if not ids:
            return items
        with transaction_context() as session:
            efectivos = estatus_efectivo_en_lote(session, ids)
        for item in items:
            if item.get('id_product') is not None:
                item['effective_status'] = efectivos.get(
                    int(item['id_product']), item.get('product_status'))
        return items

    @staticmethod
    def _como_booleano(valor) -> bool:
        if isinstance(valor, str):
            return valor.strip().lower() in ('1', 'true', 't', 'yes', 'si', 'on')
        return bool(valor)

    @staticmethod
    def _project_id(user_data: dict) -> int | None:
        if user_data.get('is_superuser') or user_data.get('is_bootstrap_admin'):
            return None
        try:
            return int(user_data.get('id_proyect'))
        except (TypeError, ValueError):
            raise AppError('errors.project_scope_required', status_code=403)

    @classmethod
    def list_scoped(cls, user_data: dict, page: int = 1, per_page: int = 20,
                    filters: dict | None = None, sort: str | None = None,
                    q: str | None = None):
        project_id = cls._project_id(user_data)
        if project_id is None:
            return cls.list(page=page, per_page=per_page, filters=filters, sort=sort, q=q)

        filters = filters or {}
        with transaction_context() as session:
            stmt = select(Product).join(Invoice, Product.id_invoice == Invoice.id_invoice).where(Invoice.id_proyect == project_id)
            # La misma busqueda libre que la lista sin alcance: sin esto, quien
            # ve solo su proyecto tendria un buscador peor que el resto.
            busqueda = cls._busqueda_libre(q)
            if busqueda is not None:
                stmt = stmt.where(busqueda)
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
