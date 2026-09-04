from app import create_app
app = create_app()
from app.services.stamping import preflight_invoice
from app.models.session import transaction_context
from app.models import Invoice
ACTOR = {"id_user": 1, "id_proyect": 8, "is_superuser": True}
with app.app_context():
    with transaction_context() as db:
        notas = db.query(Invoice).filter(Invoice.tipo_de_comprobante == "E").order_by(
            Invoice.id_invoice.desc()).limit(2).all()
        ids = [n.id_invoice for n in notas]
    for i in ids:
        r = preflight_invoice(i, ACTOR)
        print(f"nota {i}:")
        for e in (r.get("errors") or []):
            print(f"   ERROR  {e}")
        for w in (r.get("warnings") or []):
            print(f"   aviso  {w}")
