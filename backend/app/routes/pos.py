"""El punto de venta, servido por TYAKXA en lugar de reenviado a otra base.

Por que las rutas siguen colgando de `/pos/api/...`
---------------------------------------------------
Porque ese era el camino del puente, y las siete pantallas del front ya lo
llaman asi. La integracion cambia QUIEN contesta, no el contrato: `PosScreen`,
`PosTillPage` y las demas no se tocaron. Un cambio de esquema de URLs habria
sido trabajo extra sin nada a cambio, y habria mezclado dos cosas distintas en
la misma revision.

Por el mismo motivo las respuestas conservan los nombres del POS -- `items`,
`id`, `expected`, `declared`, `difference` -- y no los de la base
(`id_pos_cash_session`, `blind_declared_amounts`). Esa traduccion vive aqui, en
la orilla, que es donde debe estar: el servicio y los modelos hablan el idioma
de TYAKXA, y el front sigue hablando el suyo.

Las capacidades no cambian
--------------------------
`pos_terminal` para lo del cajero y `pos_admin` para configuracion y reportes,
comprobadas contra `entity_permission` igual que antes. Lo que desaparecio es la
cuenta de servicio (`POS_SERVICE_USER`/`POS_SERVICE_PASSWORD`): solo hacia falta
para que un sistema se autenticara ante el otro, y ya no hay otro.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from sqlalchemy import func, select

from app.models.pos import (
    REGLAS_DE_PROMOCION,
    PosCashSession, PosExpense, PosExpenseCategory, PosPromotion, PosSale, PosSaleItem,
)
from app.models.product import Product
from app.models.product_family import ProductFamily
from app.models.session import transaction_context
from app.services import pos_service
from app.services.inventory_service import apply_movement_in_session, has_capability
from app.services.pos_service import ubicacion_del_mostrador
from app.utils.auth import token_required
from app.utils.errors import AppError

bp_pos = Blueprint("pos", __name__, url_prefix="/pos")


def _exigir(user_data, capacidad):
    with transaction_context() as db:
        if not has_capability(db, user_data, capacidad):
            raise AppError("errors.permission_denied", 403, {"capability": capacidad})


def _cajero(user_data):
    """El cajero alcanza lo suyo, y el administrador tambien.

    Sin esto un administrador -que tiene `pos_admin` pero no necesariamente
    `pos_terminal`- no podria abrir una caja, que es justo lo que hace cuando
    cubre a alguien.
    """
    with transaction_context() as db:
        if (has_capability(db, user_data, "pos_terminal")
                or has_capability(db, user_data, "pos_admin")):
            return
    raise AppError("errors.permission_denied", 403, {"capability": "pos_terminal"})


# --- presentadores ------------------------------------------------------
# Traducen del idioma de la base al del front. Ver la cabecera.

def _turno(fila) -> dict:
    declarado = fila.blind_declared_amounts or {}
    esperado = fila.system_expected_amounts or {}
    diferencia = fila.discrepancy_amounts or {}
    return {
        "id": fila.id_pos_cash_session,
        "register_name": fila.register_name,
        "opening_amount": float(fila.opening_amount or 0),
        "opened_at": fila.opened_at.isoformat() if fila.opened_at else None,
        # Un corte X revisa la caja y la deja abierta; el front distingue los dos
        # justamente por si viene `closed_at`.
        "closed_at": (fila.closed_at.isoformat()
                      if fila.closed_at and fila.session_status == "closed_z" else None),
        "status": fila.session_status,
        "declared": declarado,
        "expected": esperado,
        "discrepancy": diferencia,
        # Las tres cifras sueltas que la tabla del historial pinta en columnas.
        "closing_amount": sum(float(v or 0) for v in declarado.values()),
        "expected_amount": sum(float(v or 0) for v in esperado.values()),
        "difference": sum(float(v or 0) for v in diferencia.values()),
        "notes": fila.notes,
    }


def _producto(fila, existencia=None) -> dict:
    """El producto del almacen, con los nombres que el POS usaba.

    `gross_price` es el precio de TYAKXA; el POS lo llamaba `price`. No hay
    columna de coste en `product` -- se busco --, asi que el margen sale del
    `unit_cost` que cada renglon de venta copio al cobrar, no de aqui.
    """
    return {
        "id": fila.id_product,
        "name": fila.descripcion,
        "sku": fila.product_code,
        "price": float(fila.gross_price or 0),
        "category_id": fila.id_familia,
        "image": fila.path_imagen,
        "current_stock": existencia,
    }


# --- estado -------------------------------------------------------------

@bp_pos.route("/status", methods=["GET"])
@token_required
def estado_del_punto_de_venta(user_data):
    """Antes decia si el puente alcanzaba al otro sistema; ya no hay otro.

    Se conserva la ruta porque el front la consulta antes de pintar, y quitarla
    habria dejado las pantallas esperando una respuesta que nunca llega.
    """
    _cajero(user_data)
    return jsonify({
        "configured": True,
        "reachable": True,
        "native": True,
        "detail": "El punto de venta corre dentro de TYAKXA, sobre la misma base.",
    })


# --- catalogo, que ya es el del almacen ---------------------------------

@bp_pos.route("/api/products", methods=["GET"])
@token_required
def productos(user_data):
    """El catalogo de la caja ES el catalogo del almacen.

    Aqui esta el resultado visible de toda la integracion: no hay que
    sincronizar nada ni emparejar dos catalogos, porque solo hay uno.
    """
    _cajero(user_data)
    busqueda = (request.args.get("q") or "").strip()

    from app.models.inventory_stock import InventoryStock

    # `product` no lleva `id_proyect` -- se comprobo --, asi que el catalogo no
    # se acota por proyecto aqui. En TYAKXA el producto se acota por su
    # ubicacion, y esa es la regla que ya aplica el modulo de almacen.
    with transaction_context() as db:
        condiciones = [Product.deletion_date.is_(None)]
        if busqueda:
            like = "%%%s%%" % busqueda
            condiciones.append(
                func.lower(Product.descripcion).like(func.lower(like))
                | func.lower(Product.product_code).like(func.lower(like)))
        # La existencia viene en el mismo viaje: es la del almacen, porque ya no
        # hay otra. Antes el POS respondia su propio saldo y podia discrepar.
        filas = db.execute(
            select(Product, func.coalesce(func.sum(InventoryStock.quantity), 0))
            .outerjoin(InventoryStock, InventoryStock.id_product == Product.id_product)
            .where(*condiciones)
            .group_by(Product.id_product)
            .order_by(Product.descripcion).limit(int(request.args.get("limit") or 200))
        ).all()
        return jsonify({"items": [_producto(p, float(s or 0)) for p, s in filas]})


@bp_pos.route("/api/products/categories", methods=["GET"])
@token_required
def categorias(user_data):
    """Las categorias del POS son las familias de producto de TYAKXA."""
    _cajero(user_data)
    with transaction_context() as db:
        filas = db.scalars(
            select(ProductFamily)
            .where(ProductFamily.deletion_date.is_(None))
            .order_by(ProductFamily.product_family_description)
        ).all()
        return jsonify({"items": [
            {"id": f.id_product_family, "name": f.product_family_description}
            for f in filas]})


@bp_pos.route("/api/products", methods=["POST"])
@token_required
def alta_de_producto(user_data):
    """Da de alta un producto DEL ALMACEN desde la pantalla del punto de venta.

    Pide la factura de compra y el material porque `product.id_invoice` y
    `product.id_material` son NOT NULL en el nucleo -- se comprobo --, y eso no
    es un capricho del esquema: en TYAKXA un producto existe porque se compro.
    Se piden en vez de inventarlos; fabricar una factura para cuadrar un
    requisito meteria un documento inexistente en la contabilidad.

    Es el precio de compartir la tabla: antes el POS creaba productos en su
    propia base sin contabilidad detras, y por eso sus altas no aparecian en el
    almacen.
    """
    _exigir(user_data, "pos_admin")
    cuerpo = request.get_json(silent=True) or {}

    nombre = (cuerpo.get("name") or "").strip()
    if not nombre:
        raise AppError("errors.validation", 422, {"field": "name"})
    if not cuerpo.get("id_invoice"):
        raise AppError("errors.validation", 422, {"field": "id_invoice"})
    if not cuerpo.get("id_material"):
        raise AppError("errors.validation", 422, {"field": "id_material"})

    id_user = int(user_data.get("id_user") or user_data.get("user_id") or 1)

    with transaction_context() as db:
        id_location = ubicacion_del_mostrador(db, id_user, cuerpo.get("id_location"))
        producto = Product(
            descripcion=nombre[:250],
            product_code=(cuerpo.get("sku") or "").strip()[:60] or None,
            gross_price=cuerpo.get("sale_price") or 0,
            id_familia=cuerpo.get("category_id") or None,
            id_invoice=int(cuerpo["id_invoice"]),
            id_material=int(cuerpo["id_material"]),
            id_location=id_location,
            created_by=id_user,
        )
        db.add(producto)
        db.flush()

        # La existencia de apertura entra por la puerta de siempre, para que
        # quede asentada en el libro en lugar de aparecer sin explicacion.
        inicial = cuerpo.get("current_stock")
        if inicial:
            apply_movement_in_session(
                db, producto.id_product, user_data,
                movement_type="receive", quantity_delta=int(inicial),
                idempotency_key=("pos-alta-%s" % producto.id_product)[:90],
                id_location=id_location,
                reference_type="product_opening", reference_id=str(producto.id_product),
                reason="Alta desde el punto de venta", source_module="pos",
            )
        return jsonify(_producto(producto, float(inicial or 0))), 201


@bp_pos.route("/api/products/categories", methods=["POST"])
@token_required
def alta_de_categoria(user_data):
    """Crea una familia de producto, que es lo que el POS llamaba categoria.

    `color_hex` que manda el formulario se ignora: `product_family` no tiene
    columna de color. Agregar una para esto seria cambiar el catalogo del
    almacen por una comodidad de una pantalla.
    """
    _exigir(user_data, "pos_admin")
    cuerpo = request.get_json(silent=True) or {}
    nombre = (cuerpo.get("name") or "").strip()
    if not nombre:
        raise AppError("errors.validation", 422, {"field": "name"})

    id_user = int(user_data.get("id_user") or user_data.get("user_id") or 1)
    with transaction_context() as db:
        familia = ProductFamily(
            product_family_description=nombre[:160],
            created_by=id_user,
        )
        db.add(familia)
        db.flush()
        return jsonify({"id": familia.id_product_family,
                        "name": familia.product_family_description}), 201


@bp_pos.route("/api/products/low-stock", methods=["GET"])
@token_required
def bajo_minimo(user_data):
    """Lo que esta por acabarse, segun el libro del nucleo.

    Antes el POS llevaba su propia existencia y esta lista podia contradecir a
    la del almacen. Ahora salen del mismo sitio, asi que no pueden discrepar.

    El umbral es un parametro y no un minimo por producto porque TYAKXA no
    guarda ninguno: se busco en todo el esquema y lo unico parecido es
    `inventory_status.id_minimum_level`, que apunta a `level`, una tabla de
    descripciones ("General") sin cifra. Inventar una columna de minimos aqui
    seria una decision de inventario disfrazada de consulta del POS.
    """
    _cajero(user_data)
    from app.models.inventory_stock import InventoryStock

    try:
        umbral = float(request.args.get("threshold") or 5)
    except (TypeError, ValueError):
        raise AppError("errors.validation", 422, {"field": "threshold"})

    with transaction_context() as db:
        filas = db.execute(
            select(Product, func.coalesce(func.sum(InventoryStock.quantity), 0))
            .outerjoin(InventoryStock, InventoryStock.id_product == Product.id_product)
            .where(Product.deletion_date.is_(None))
            .group_by(Product.id_product)
            .having(func.coalesce(func.sum(InventoryStock.quantity), 0) <= umbral)
            .order_by(func.coalesce(func.sum(InventoryStock.quantity), 0)).limit(100)
        ).all()
        return jsonify({"items": [_producto(p, float(s or 0)) for p, s in filas]})


# --- la caja ------------------------------------------------------------

@bp_pos.route("/api/cash/sessions/open", methods=["GET"])
@token_required
def turno_abierto(user_data):
    """Los turnos abiertos. El front toma el primero.

    Devuelve una lista y no un objeto porque asi lo hacia el POS y la pantalla
    hace `listaDe(datos.abiertos)[0]`.
    """
    _cajero(user_data)
    id_proyect = user_data.get("id_proyect") or user_data.get("project_id")
    with transaction_context() as db:
        filas = db.scalars(
            select(PosCashSession).where(
                PosCashSession.id_proyect == int(id_proyect or 0),
                PosCashSession.session_status == "open",
                PosCashSession.deletion_date.is_(None),
            ).order_by(PosCashSession.id_pos_cash_session.desc())
        ).all()
        return jsonify({"items": [_turno(f) for f in filas]})


@bp_pos.route("/api/cash/sessions/open", methods=["POST"])
@token_required
def abrir_turno(user_data):
    """La pantalla de Turno manda el nombre de la caja; la de Caja, no.

    `PosTillPage` abre turno con solo el fondo, para que el cajero pueda cobrar
    sin pasar antes por otra pantalla. Se le pone un nombre por omision en vez
    de rechazar la peticion: el turno tiene que existir para que el corte tenga
    contra que comparar, y quedarse sin abrir es peor que abrirse sin nombre.
    """
    _cajero(user_data)
    cuerpo = dict(request.get_json(silent=True) or {})
    if not (cuerpo.get("register_name") or "").strip():
        cuerpo["register_name"] = "Caja"

    datos = pos_service.abrir_turno(cuerpo, user_data)
    with transaction_context() as db:
        fila = db.get(PosCashSession, datos["id_pos_cash_session"])
        # `session` porque `PosTillPage` lee `abierta?.session || abierta`.
        return jsonify({"session": _turno(fila)}), 201


@bp_pos.route("/api/cash/sessions/history", methods=["GET"])
@token_required
def historial_de_turnos(user_data):
    _cajero(user_data)
    id_proyect = user_data.get("id_proyect") or user_data.get("project_id")
    with transaction_context() as db:
        filas = db.scalars(
            select(PosCashSession).where(
                PosCashSession.id_proyect == int(id_proyect or 0),
                PosCashSession.deletion_date.is_(None),
            ).order_by(PosCashSession.id_pos_cash_session.desc()).limit(50)
        ).all()
        return jsonify({"items": [_turno(f) for f in filas]})


@bp_pos.route("/api/cash/sessions/<int:id_turno>/close", methods=["POST"])
@token_required
def cerrar_turno(user_data, id_turno):
    _cajero(user_data)
    cuerpo = dict(request.get_json(silent=True) or {})
    # El front manda "x" o "z"; la base guarda "closed_x"/"closed_z".
    tipo = str(cuerpo.get("close_type") or "z").strip().lower()
    cuerpo["close_type"] = "closed_x" if tipo in ("x", "closed_x") else "closed_z"

    datos = pos_service.cerrar_turno(id_turno, cuerpo, user_data)
    with transaction_context() as db:
        fila = db.get(PosCashSession, datos["id_pos_cash_session"])
        return jsonify(_turno(fila))


@bp_pos.route("/api/cash/sessions/<int:id_turno>/withdrawals", methods=["POST"])
@token_required
def retirar(user_data, id_turno):
    _cajero(user_data)
    datos = pos_service.retirar_efectivo(
        id_turno, request.get_json(silent=True) or {}, user_data)
    return jsonify({
        "id": datos["id_pos_cash_withdrawal"],
        "amount": datos["amount"],
        "reason": datos["reason"],
    }), 201


# --- el cobro -----------------------------------------------------------

@bp_pos.route("/api/checkout", methods=["POST"])
@token_required
def cobrar(user_data):
    """Cobra la venta y descuenta del almacen en la misma transaccion.

    Es el cambio de fondo respecto al puente: antes la venta se cobraba en la
    otra base y aqui solo se REFLEJABA, asi que una falta de existencia no podia
    detener nada y quedaba como descuadre. Ahora se detiene el cobro.

    La pantalla de caja manda `product_id` y NO manda precio -- lo toma del
    catalogo para pintar el total, pero confiar en el precio que envia el
    navegador dejaria cobrar lo que el cliente quisiera. Se traduce el nombre y
    el precio se lee del producto, aqui en el servidor.
    """
    _cajero(user_data)
    cuerpo = dict(request.get_json(silent=True) or {})

    renglones = []
    for renglon in (cuerpo.get("items") or []):
        copia = dict(renglon)
        if "id_product" not in copia and "product_id" in copia:
            copia["id_product"] = copia.pop("product_id")
        renglones.append(copia)
    cuerpo["items"] = renglones

    return jsonify(pos_service.cobrar(cuerpo, user_data)), 201


@bp_pos.route("/api/sales", methods=["GET"])
@token_required
def ventas(user_data):
    _cajero(user_data)
    datos = pos_service.ventas(user_data, limite=int(request.args.get("limit") or 100))
    return jsonify({"items": datos["data"]})


@bp_pos.route("/api/sales/<int:id_venta>", methods=["GET"])
@token_required
def una_venta(user_data, id_venta):
    _cajero(user_data)
    return jsonify(pos_service.venta(id_venta, user_data))


# --- promociones --------------------------------------------------------

def _promocion(fila) -> dict:
    """La familia de TYAKXA se presenta como la categoria que el POS nombraba.

    La pantalla lee `applicable_category_ids`; la columna se llama
    `applicable_family_ids` porque aqui una categoria de producto es una familia.
    """
    return {
        "id": fila.id_pos_promotion,
        "name": fila.name,
        "rule_type": fila.rule_type,
        "config": fila.config or {},
        "applicable_product_ids": fila.applicable_product_ids or [],
        "applicable_category_ids": fila.applicable_family_ids or [],
        "starts_at": fila.starts_at.isoformat() if fila.starts_at else None,
        "ends_at": fila.ends_at.isoformat() if fila.ends_at else None,
        "requires_stock": bool(fila.requires_stock),
        "max_uses_total": fila.max_uses_total,
        "max_uses_per_customer": fila.max_uses_per_customer,
        "times_used": fila.times_used,
        "is_stackable": bool(fila.is_stackable),
        "priority": fila.priority,
        "is_active": bool(fila.is_active),
    }


@bp_pos.route("/api/promotions", methods=["GET"])
@token_required
def promociones(user_data):
    _cajero(user_data)
    id_proyect = user_data.get("id_proyect") or user_data.get("project_id")
    with transaction_context() as db:
        filas = db.scalars(
            select(PosPromotion).where(
                PosPromotion.id_proyect == int(id_proyect or 0),
                PosPromotion.deletion_date.is_(None),
            ).order_by(PosPromotion.priority.desc(), PosPromotion.id_pos_promotion)
        ).all()
        return jsonify({"items": [_promocion(f) for f in filas]})


@bp_pos.route("/api/promotions", methods=["POST"])
@token_required
def crear_promocion(user_data):
    _exigir(user_data, "pos_admin")
    cuerpo = request.get_json(silent=True) or {}
    nombre = (cuerpo.get("name") or "").strip()
    regla = (cuerpo.get("rule_type") or "").strip()
    if not nombre:
        raise AppError("errors.validation", 422, {"field": "name"})
    if regla not in REGLAS_DE_PROMOCION:
        raise AppError("errors.validation", 422, {"field": "rule_type"})

    id_user = user_data.get("id_user") or user_data.get("user_id")
    id_proyect = user_data.get("id_proyect") or user_data.get("project_id")
    with transaction_context() as db:
        fila = PosPromotion(
            id_proyect=int(id_proyect or 0),
            name=nombre[:160],
            rule_type=regla,
            config=cuerpo.get("config") or {},
            applicable_product_ids=cuerpo.get("applicable_product_ids") or None,
            applicable_family_ids=cuerpo.get("applicable_category_ids") or None,
            requires_stock=bool(cuerpo.get("requires_stock", True)),
            max_uses_total=cuerpo.get("max_uses_total"),
            max_uses_per_customer=cuerpo.get("max_uses_per_customer"),
            is_stackable=bool(cuerpo.get("is_stackable", False)),
            priority=int(cuerpo.get("priority") or 0),
            is_active=bool(cuerpo.get("is_active", True)),
            created_by=int(id_user or 1),
        )
        db.add(fila)
        db.flush()
        return jsonify(_promocion(fila)), 201


# --- gastos -------------------------------------------------------------

@bp_pos.route("/api/expenses", methods=["GET"])
@token_required
def gastos(user_data):
    _exigir(user_data, "pos_admin")
    id_proyect = user_data.get("id_proyect") or user_data.get("project_id")
    with transaction_context() as db:
        filas = db.scalars(
            select(PosExpense).where(
                PosExpense.id_proyect == int(id_proyect or 0),
                PosExpense.deletion_date.is_(None),
            ).order_by(PosExpense.expense_date.desc()).limit(100)
        ).all()
        return jsonify({"items": [
            {"id": f.id_pos_expense, "description": f.description,
             "amount": float(f.amount or 0), "status": f.expense_status,
             "category_id": f.id_pos_expense_category,
             "expense_date": f.expense_date.isoformat() if f.expense_date else None}
            for f in filas]})


@bp_pos.route("/api/expenses/categories", methods=["GET"])
@token_required
def categorias_de_gasto(user_data):
    _exigir(user_data, "pos_admin")
    id_proyect = user_data.get("id_proyect") or user_data.get("project_id")
    with transaction_context() as db:
        filas = db.scalars(
            select(PosExpenseCategory).where(
                PosExpenseCategory.id_proyect == int(id_proyect or 0),
                PosExpenseCategory.deletion_date.is_(None),
            ).order_by(PosExpenseCategory.name)
        ).all()
        return jsonify({"items": [
            {"id": f.id_pos_expense_category, "name": f.name,
             "is_payroll": bool(f.is_payroll), "is_active": bool(f.is_active)}
            for f in filas]})


# --- tablero ------------------------------------------------------------

@bp_pos.route("/api/dashboard/today-summary", methods=["GET"])
@token_required
def resumen_de_hoy(user_data):
    _exigir(user_data, "pos_admin")
    return jsonify(pos_service.resumen_del_dia(user_data))


@bp_pos.route("/api/dashboard/revenue-by-payment-method", methods=["GET"])
@token_required
def ingreso_por_forma_de_pago(user_data):
    _exigir(user_data, "pos_admin")
    resumen = pos_service.resumen_del_dia(user_data)
    return jsonify({"items": [
        {"method": forma, "total": total}
        for forma, total in sorted(resumen["by_payment_method"].items())]})


@bp_pos.route("/api/dashboard/sales-by-category", methods=["GET"])
@token_required
def venta_por_categoria(user_data):
    """Lo vendido por familia de producto.

    Se puede preguntar porque el renglon de la venta apunta al producto del
    almacen, que a su vez tiene familia. Con dos bases habria hecho falta cruzar
    a mano dos catalogos.
    """
    _exigir(user_data, "pos_admin")
    id_proyect = user_data.get("id_proyect") or user_data.get("project_id")
    with transaction_context() as db:
        filas = db.execute(
            select(ProductFamily.product_family_description,
                   func.coalesce(func.sum(PosSaleItem.line_total), 0))
            .select_from(PosSaleItem)
            .join(PosSale, PosSale.id_pos_sale == PosSaleItem.id_pos_sale)
            .join(Product, Product.id_product == PosSaleItem.id_product)
            .outerjoin(ProductFamily,
                       ProductFamily.id_product_family == Product.id_familia)
            .where(PosSale.id_proyect == int(id_proyect or 0),
                   PosSale.sale_status == "paid",
                   PosSaleItem.deletion_date.is_(None))
            .group_by(ProductFamily.product_family_description)
            .order_by(func.coalesce(func.sum(PosSaleItem.line_total), 0).desc())
        ).all()
        return jsonify({"items": [
            {"category": nombre or "Sin familia", "total": float(total)}
            for nombre, total in filas]})


@bp_pos.route("/api/dashboard/product-margin", methods=["GET"])
@token_required
def margen_por_producto(user_data):
    """Vendido menos coste, con el coste que tenia el dia de la venta.

    `unit_cost` se copio al cobrar justamente para esto: recalcular el margen
    con el coste de hoy mentiria sobre la venta de ayer.
    """
    _exigir(user_data, "pos_admin")
    id_proyect = user_data.get("id_proyect") or user_data.get("project_id")
    with transaction_context() as db:
        filas = db.execute(
            select(Product.descripcion,
                   func.coalesce(func.sum(PosSaleItem.line_total), 0),
                   func.coalesce(func.sum(PosSaleItem.unit_cost * PosSaleItem.quantity), 0))
            .select_from(PosSaleItem)
            .join(PosSale, PosSale.id_pos_sale == PosSaleItem.id_pos_sale)
            .join(Product, Product.id_product == PosSaleItem.id_product)
            .where(PosSale.id_proyect == int(id_proyect or 0),
                   PosSale.sale_status == "paid",
                   PosSaleItem.deletion_date.is_(None))
            .group_by(Product.descripcion)
            .order_by(func.coalesce(func.sum(PosSaleItem.line_total), 0).desc()).limit(50)
        ).all()
        return jsonify({"items": [
            {"product": nombre, "revenue": float(venta_total), "cost": float(coste),
             "margin": float(venta_total) - float(coste)}
            for nombre, venta_total, coste in filas]})
