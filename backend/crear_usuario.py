"""Un usuario en el proyecto 8 para poder probar el aislamiento en ambos sentidos.

Sin el, un 404 no distingue entre "correctamente aislado" y "roto para todos".
"""
from app import create_app
app = create_app()
from app.models.session import transaction_context
from app.models import User
import bcrypt

with app.app_context():
    with transaction_context() as db:
        ya = db.query(User).filter_by(username="gerente8").first()
        if ya:
            print(f"ya existe: gerente8 proyecto {ya.id_proyect}")
        else:
            modelo = db.query(User).filter_by(username="gerente1").first()
            nuevo = User(
                username="gerente8",
                password=bcrypt.hashpw(b"Prueba2026!", bcrypt.gensalt()).decode(),
                email="gerente8@prueba.local",
                id_proyect=8,
                id_permission=modelo.id_permission,
                id_status=modelo.id_status,
                user_type=modelo.user_type,
                full_name="Gerente Proyecto 8",
                supervisor=modelo.supervisor or modelo.id_user,
                first_name="Gerente", last_name_father="Proyecto", last_name_mother="Ocho",
                created_by=1,
            )
            db.add(nuevo)
            db.flush()
            print(f"creado: gerente8 proyecto 8 perfil {nuevo.id_permission}")
