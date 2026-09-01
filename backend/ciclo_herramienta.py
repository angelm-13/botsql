"""Vida completa de una herramienta contra la base real.

Recorre lo que le pasa a un taladro en una empresa: se compra, se presta, vuelve
tarde, se manda a reparar, regresa, se traslada de almacen y al final se da de
baja. En cada paso se comprueba el efecto en el saldo por cantidad, no solo que
la llamada no reviente.
"""

from __future__ import annotations

import sys
import traceback
from datetime import date, timedelta

ACTOR = {"id_user": 1, "id_proyect": 1, "is_superuser": True}
fallos = []
paso_n = 0


def paso(titulo):
    global paso_n
    paso_n += 1
    print(f"\n{'=' * 70}\n{paso_n}. {titulo}\n{'=' * 70}")


def check(que, condicion, detalle=""):
    if condicion:
        print(f"  ok  {que}")
        return
    fallos.append(que)
    print(f"  XX  {que}{('  -> ' + str(detalle)) if detalle else ''}")


def main():
    from app import create_app
    app = create_app()

    from app.models.session import transaction_context
    from app.models import Product
    from app.models.inventory_stock import InventoryStock
    from app.services import inventory_asset_service as piezas

    with app.app_context():
        paso("Preparar un producto que se rastrea pieza por pieza")
        with transaction_context() as db:
            producto = db.get(Product, 100)
            antes_modo = producto.tracking_mode
            producto.tracking_mode = piezas.SERIALIZADO
            id_product = producto.id_product
            fila = (db.query(InventoryStock).filter_by(id_product=id_product)
                    .order_by(InventoryStock.quantity.desc()).first())
            almacen = fila.id_location
            saldo_inicial = int(fila.quantity)
            otro = (db.query(InventoryStock)
                    .filter(InventoryStock.id_product == id_product,
                            InventoryStock.id_location != almacen).first())
            otro_almacen = otro.id_location if otro else None
        print(f"  producto {id_product}, modo {antes_modo} -> serializado")
        print(f"  almacen {almacen}, saldo inicial {saldo_inicial}")

        def saldo(ubicacion=None):
            with transaction_context() as db:
                fila = db.query(InventoryStock).filter_by(
                    id_product=id_product, id_location=ubicacion or almacen).first()
                return int(fila.quantity) if fila else 0

        etiqueta = f"PRUEBA-{date.today().isoformat()}-{paso_n}"

        paso("Alta de la pieza")
        pieza = piezas.register_asset({
            "id_product": id_product, "asset_tag": etiqueta,
            "id_location": almacen, "serial_number": "SN-99887",
            "acquisition_cost": "4250.00",
        }, ACTOR)["asset"]
        id_asset = pieza["id_inventory_asset"]
        print(f"  pieza {id_asset} etiqueta {pieza['asset_tag']} estado {pieza['status']}")
        check("nace disponible", pieza["status"] == "disponible")
        check("suma al saldo", saldo() == saldo_inicial + 1, f"{saldo_inicial} -> {saldo()}")
        check("el importe viaja como cadena, no como flotante",
              isinstance(pieza["acquisition_cost"], str), pieza["acquisition_cost"])

        paso("Prestamo con responsable y fecha")
        vence = (date.today() + timedelta(days=5)).isoformat()
        r = piezas.lend_asset(id_asset, {"id_holder": 77, "due_date": vence,
                                         "reason": "Obra del norte"}, ACTOR)["asset"]
        print(f"  estado {r['status']}, responsable {r['id_holder']}, vence {r['due_date']}")
        check("queda prestada con responsable", r["status"] == "prestada" and r["id_holder"] == 77)
        check("sin ubicacion: no esta en la empresa", r["id_location"] is None)
        check("sale del saldo", saldo() == saldo_inicial, f"{saldo()}")

        paso("Se atrasa y aparece en vencidos")
        with transaction_context() as db:
            from app.models.inventory_asset import InventoryAsset
            db.get(InventoryAsset, id_asset).due_date = date.today() - timedelta(days=4)
        vencidos = piezas.overdue_loans(ACTOR)
        mio = [f for f in vencidos["items"] if f["id_inventory_asset"] == id_asset]
        print(f"  vencidos en total: {vencidos['total']}")
        check("la pieza atrasada aparece", len(mio) == 1)
        if mio:
            check("dice cuantos dias de atraso", mio[0]["days_overdue"] == 4, mio[0]["days_overdue"])

        paso("Devolucion")
        r = piezas.return_asset(id_asset, {"id_location": almacen}, ACTOR)["asset"]
        check("vuelve disponible", r["status"] == "disponible")
        check("libera al responsable", r["id_holder"] is None)
        check("olvida la fecha de regreso", r["due_date"] is None)
        check("vuelve al saldo", saldo() == saldo_inicial + 1, f"{saldo()}")

        paso("Reparacion")
        piezas.send_to_repair(id_asset, {"reason": "Cable danado"}, ACTOR)
        check("existe pero no cuenta", saldo() == saldo_inicial, f"{saldo()}")
        r = piezas.back_from_repair(id_asset, {"id_location": almacen}, ACTOR)["asset"]
        check("regresa disponible", r["status"] == "disponible")
        check("vuelve a contar", saldo() == saldo_inicial + 1)

        if otro_almacen:
            paso("Traslado entre almacenes")
            antes_aqui, antes_alla = saldo(), saldo(otro_almacen)
            r = piezas.move_asset(id_asset, {"id_location": otro_almacen,
                                             "reason": "Se ocupa alla"}, ACTOR)["asset"]
            print(f"  {almacen}: {antes_aqui} -> {saldo()}   "
                  f"{otro_almacen}: {antes_alla} -> {saldo(otro_almacen)}")
            check("cambia de ubicacion sin cambiar de estado",
                  r["id_location"] == otro_almacen and r["status"] == "disponible")
            check("el saldo sigue a la pieza",
                  saldo() == antes_aqui - 1 and saldo(otro_almacen) == antes_alla + 1)
            piezas.move_asset(id_asset, {"id_location": almacen,
                                         "reason": "Regresa"}, ACTOR)

        paso("Resumen del producto")
        resumen = piezas.product_asset_summary(id_product, ACTOR)
        print(f"  piezas: {resumen['total_assets']}  en existencia: {resumen['assets_in_stock']}"
              f"  saldo: {resumen['stock_balance']}")
        print(f"  por estado: {resumen['by_status']}")
        check("dice si cuadra con el saldo", "is_reconciled" in resumen)
        # Con piezas dadas de alta a mano y saldo previo del producto, el
        # descuadre es esperado: lo que importa es que lo reporte y no lo tape.
        if not resumen["is_reconciled"]:
            print(f"  (descuadre reportado: {resumen['difference']}, esperado porque el "
                  f"producto ya tenia saldo antes de rastrearse pieza por pieza)")

        paso("Historia completa")
        historia = piezas.asset_history(id_asset, ACTOR)
        tipos = [e["event_type"] for e in historia["events"]]
        print(f"  {' -> '.join(tipos)}")
        check("la historia esta completa y en orden", tipos[0] == "alta" and len(tipos) >= 5)
        con_libro = [e for e in historia["events"] if e["id_inventory_ledger"]]
        check("los eventos que mueven saldo apuntan a su renglon del libro",
              len(con_libro) >= 4, f"{len(con_libro)} de {len(tipos)}")

        paso("Busqueda por etiqueta")
        encontrada = piezas.find_asset_by_tag(etiqueta, ACTOR)
        check("se encuentra con la etiqueta en la mano",
              encontrada["asset"]["id_inventory_asset"] == id_asset)

        paso("Baja definitiva")
        piezas.retire_asset(id_asset, {"reason": "Fin de la prueba"}, ACTOR)
        check("queda retirada", piezas.asset_history(id_asset, ACTOR)["asset"]["status"] == "retirada")
        try:
            piezas.assign_asset(id_asset, {"id_holder": 1}, ACTOR)
            check("una pieza retirada no revive", False, "acepto asignarla")
        except Exception as e:
            check("una pieza retirada no revive", True,
                  getattr(e, "message_key", type(e).__name__))

        # Se deja el producto como estaba, para no cambiar el modo de un
        # producto de demostracion por una prueba.
        with transaction_context() as db:
            db.get(Product, id_product).tracking_mode = antes_modo
        print(f"\n  producto {id_product} devuelto a modo {antes_modo}")
        print(f"  pieza de prueba: {id_asset} (etiqueta {etiqueta}), queda retirada")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        fallos.append("se interrumpio con una excepcion")

    print(f"\n{'=' * 70}")
    if fallos:
        print(f"FALLARON {len(fallos)}:")
        for f in fallos:
            print(f"  - {f}")
        sys.exit(1)
    print("Vida completa de la herramienta: todas las comprobaciones pasaron.")
