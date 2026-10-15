#!/usr/bin/env python3
"""Usuario de prueba con el rol Compras (id_permission=8), solo para desarrollo.

Uso: docker compose exec -T backend python scripts/seed_usuario_compras.py
Usuario: compras1 / contrasena: Compras4682.  Idempotente. No correr en produccion.
"""
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy import select
import bcrypt

from app.models.session import transaction_context
from app.models.user import User
from app.utils.startup_guard import is_production

if is_production():
    sys.exit("Usuario de prueba con contrasena de ejemplo: no se corre en produccion.")

ROL_COMPRAS = 8

with transaction_context() as db:
    existente = db.scalars(select(User).where(User.username == "compras1")).first()
    modelo = db.scalars(select(User).where(User.username == "almacen")).first()
    if existente:
        existente.password = bcrypt.hashpw(b"Compras4682.", bcrypt.gensalt()).decode()
        print("compras1 ya existe (id %s): contrasena restablecida" % existente.id_user)
    else:
        # `user.id_proyect` es NOT NULL (campo heredado): se toma el de un usuario existente.
        db.add(User(id_proyect=modelo.id_proyect, id_status=modelo.id_status, supervisor=modelo.supervisor or 1,
            username="compras1", full_name="Compras Uno", email="compras1@test.com",
            user_type="employee", password=bcrypt.hashpw(b"Compras4682.", bcrypt.gensalt()).decode(),
            created_by=1, is_employee=True, id_permission=ROL_COMPRAS))
        db.flush()
        print("compras1 creado")
