from app import create_app
app = create_app()
from app.models.session import transaction_context
from app.models import Product
from app.services import inventory_asset_service as piezas
from datetime import date, timedelta

ACTOR = {"id_user": 1, "id_proyect": 1, "is_superuser": True}
with app.app_context():
    with transaction_context() as db:
        p = db.get(Product, 101)
        p.tracking_mode = "serializado"
        p.stock_purpose = "uso_interno"
        pid, loc = p.id_product, p.id_location
    print(f"producto {pid} -> serializado / uso_interno, ubicacion {loc}")

    creadas = []
    for i, etiqueta in enumerate(["TAL-001", "TAL-002", "TAL-003", "ESM-010"]):
        try:
            a = piezas.register_asset({
                "id_product": pid, "asset_tag": etiqueta, "id_location": loc,
                "serial_number": f"SN-{1000+i}", "acquisition_cost": "3200.00",
            }, ACTOR)["asset"]
            creadas.append(a["id_inventory_asset"])
        except Exception as e:
            print(f"  {etiqueta}: {getattr(e,'message_key',e)}")
    print(f"piezas creadas: {creadas}")

    if len(creadas) >= 3:
        piezas.lend_asset(creadas[0], {"id_holder": 77,
            "due_date": (date.today()+timedelta(days=6)).isoformat()}, ACTOR)
        piezas.assign_asset(creadas[1], {"id_holder": 88}, ACTOR)
        piezas.send_to_repair(creadas[2], {"reason": "No enciende"}, ACTOR)
        print("estados sembrados: prestada, en uso, en reparacion")
