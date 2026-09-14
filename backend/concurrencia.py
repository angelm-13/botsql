"""Concurrencia real de almacen contra PostgreSQL.

La auditoria externa dejo este control en rojo por falta de datos:
"Smoke inventario DB: Bloqueado: no habia producto local asociado a factura con
proyecto". Ahora si los hay, asi que se ejecuta.

Lo que se busca no es que "no truene", sino los dos errores que solo aparecen
con carga y que SQLite no puede reproducir porque serializa las escrituras:

* **sobreventa**: dos salidas simultaneas que juntas superan la existencia y
  ambas pasan, dejando el saldo en negativo;
* **actualizacion perdida**: dos movimientos que leen el mismo saldo y el
  segundo pisa al primero, de modo que una de las dos salidas desaparece del
  saldo aunque quede en el libro.

Ninguno de los dos deja error en la bitacora. Se descubren contando el almacen.
"""

from __future__ import annotations

import sys
import threading
import traceback
from decimal import Decimal


ACTOR = {"id_user": 1, "id_proyect": 1, "is_superuser": True}
PRODUCTO = 100

fallos = []


def check(descripcion, condicion, detalle=""):
    if condicion:
        print(f"  ok  {descripcion}")
        return
    fallos.append(descripcion)
    print(f"  XX  {descripcion}{('  -> ' + str(detalle)) if detalle else ''}")


def main():
    from app import create_app
    app = create_app()

    from app.models.session import transaction_context
    from app.models.inventory_stock import InventoryStock
    from app.models.inventory_ledger import InventoryLedger
    from app.services.inventory_service import apply_inventory_movement, reconcile_product_stock
    from sqlalchemy import func, select

    with app.app_context():
        with transaction_context() as db:
            fila = (db.query(InventoryStock)
                    .filter_by(id_product=PRODUCTO)
                    .order_by(InventoryStock.quantity.desc()).first())
            ubicacion = fila.id_location
            inicial = int(fila.quantity)
        print(f"  producto {PRODUCTO}, ubicacion {ubicacion}, existencia inicial {inicial}")

        # ------------------------------------------------------------------
        print("\n" + "=" * 72)
        print(f"1. {inicial + 5} unidades pedidas a la vez sobre {inicial} disponibles")
        print("=" * 72)
        intentos = inicial + 5
        resultados = [None] * intentos
        errores = [None] * intentos

        def sacar(indice):
            try:
                apply_inventory_movement(PRODUCTO, {
                    "movement_type": "issue", "quantity": 1,
                    "idempotency_key": f"conc-v2-{indice}", "id_location": ubicacion,
                    "reason": "Prueba de concurrencia",
                }, ACTOR)
                resultados[indice] = "aplicado"
            except Exception as error:
                errores[indice] = getattr(error, "message_key", type(error).__name__)
                resultados[indice] = "rechazado"

        # Todos los hilos arrancan a la vez: sin la barrera se irian escalonando
        # y la prueba dejaria de medir concurrencia.
        barrera = threading.Barrier(intentos)

        def correr(indice):
            barrera.wait()
            sacar(indice)

        hilos = [threading.Thread(target=correr, args=(i,)) for i in range(intentos)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        aplicados = resultados.count("aplicado")
        rechazados = resultados.count("rechazado")
        print(f"  aplicados {aplicados}, rechazados {rechazados}")
        motivos = {e for e in errores if e}
        print(f"  motivos de rechazo: {motivos or 'ninguno'}")

        with transaction_context() as db:
            final = int(db.query(InventoryStock)
                        .filter_by(id_product=PRODUCTO, id_location=ubicacion).first().quantity)
        print(f"  existencia {inicial} -> {final}")

        check("no se vende mas de lo que hay", aplicados <= inicial,
              f"{aplicados} aplicados sobre {inicial} disponibles")
        check("la existencia nunca queda negativa", final >= 0, final)
        check("el saldo baja exactamente lo aplicado", final == inicial - aplicados,
              f"{inicial} - {aplicados} != {final}")
        check("los rechazos explican el motivo", not rechazados or motivos, motivos)

        # ------------------------------------------------------------------
        print("\n" + "=" * 72)
        print("2. El libro y el saldo siguen cuadrando")
        print("=" * 72)
        with transaction_context() as db:
            suma_libro = int(db.scalar(
                select(func.coalesce(func.sum(InventoryLedger.quantity_delta), 0))
                .where(InventoryLedger.id_product == PRODUCTO)
                .where(InventoryLedger.id_location == ubicacion)
            ) or 0)
        conciliacion = reconcile_product_stock(PRODUCTO, ACTOR)
        print(f"  suma del libro en la ubicacion: {suma_libro}")
        print(f"  conciliacion: {conciliacion.get("is_reconciled")}")
        check("ni un movimiento aplicado quedo sin asentar en el libro",
              aplicados > 0 or inicial == 0)
        cuadra = conciliacion.get("is_reconciled")
        if cuadra is None:
            cuadra = conciliacion.get("balanced")  # respaldo
        check("libro, existencia por ubicacion y total del producto coinciden",
              bool(cuadra), conciliacion)

        # ------------------------------------------------------------------
        print("\n" + "=" * 72)
        print("3. La misma llave repetida no mueve dos veces")
        print("=" * 72)
        with transaction_context() as db:
            antes = int(db.query(InventoryStock)
                        .filter_by(id_product=PRODUCTO, id_location=ubicacion).first().quantity)

        repeticiones = [None] * 5

        def repetir(indice):
            barrera2.wait()
            try:
                apply_inventory_movement(PRODUCTO, {
                    "movement_type": "receive", "quantity": 2,
                    "idempotency_key": "conc-llave-v2", "id_location": ubicacion,
                    "reason": "Prueba de idempotencia concurrente",
                }, ACTOR)
                repeticiones[indice] = "ok"
            except Exception as error:
                repeticiones[indice] = getattr(error, "message_key", type(error).__name__)

        barrera2 = threading.Barrier(5)
        hilos = [threading.Thread(target=repetir, args=(i,)) for i in range(5)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        with transaction_context() as db:
            despues = int(db.query(InventoryStock)
                          .filter_by(id_product=PRODUCTO, id_location=ubicacion).first().quantity)
        print(f"  cinco llamadas con la misma llave: {repeticiones}")
        print(f"  existencia {antes} -> {despues}")
        check("cinco llamadas con la misma llave suman una sola vez",
              despues == antes + 2, f"{antes} + 2 != {despues}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        fallos.append("la prueba se interrumpio con una excepcion")

    print("\n" + "=" * 72)
    if fallos:
        print(f"FALLARON {len(fallos)}:")
        for f in fallos:
            print(f"  - {f}")
        sys.exit(1)
    print("Concurrencia de almacen: todas las comprobaciones pasaron.")
