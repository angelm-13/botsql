#!/usr/bin/env python3
"""Script para inicializar datos de prueba y usuarios para testear el flujo de vales.

Uso:
    docker compose exec -T backend python scripts/init_test_data.py
"""

import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from werkzeug.security import generate_password_hash
from sqlalchemy import select, func
from app.models.session import transaction_context
from app.models.user import User
from app.models.product import Product
from app.models.location import Location
from app.models.incident_type import IncidentType
from app.models.entity_permission import EntityPermission
from app.models.nm_field_permission import NmFieldPermission


def hash_password(password: str) -> str:
    """Genera hash de contraseña compatible con werkzeug."""
    return generate_password_hash(password, method='pbkdf2:sha256')


def create_test_users(db):
    """Crea usuarios de prueba con roles definidos."""
    print("🧑 Creando usuarios de prueba...")

    usuarios = [
        {
            "username": "supervisor1",
            "full_name": "Supervisor Uno",
            "email": "supervisor1@test.com",
            "user_type": "employee",
            "password": "supervisor1",
        },
        {
            "username": "almacen1",
            "full_name": "Almacenista Uno",
            "email": "almacen1@test.com",
            "user_type": "employee",
            "password": "almacen1",
        },
        {
            "username": "gerencia1",
            "full_name": "Gerente Uno",
            "email": "gerencia1@test.com",
            "user_type": "employee",
            "password": "gerencia1",
        },
    ]

    created_users = {}
    for usuario in usuarios:
        # Verificar si ya existe
        existente = db.scalars(
            select(User).where(User.username == usuario["username"])
        ).first()

        if existente:
            print(f"  ⚠️  {usuario['username']} ya existe (ID: {existente.id_user})")
            created_users[usuario["username"]] = existente.id_user
            continue

        # Crear usuario (con todos los campos NOT NULL)
        nuevo_user = User(
            username=usuario["username"],
            full_name=usuario["full_name"],
            email=usuario["email"],
            user_type=usuario["user_type"],
            password=hash_password(usuario["password"]),
            created_by=1,        # bootstrap admin
            is_employee=True,
            id_permission=1,     # rol por defecto
            id_proyect=1,        # proyecto por defecto
            id_status=1,         # estado activo
            supervisor=1,        # supervisor por defecto (bootstrap admin)
        )
        db.add(nuevo_user)
        db.flush()
        print(f"  ✅ Creado: {usuario['username']} (ID: {nuevo_user.id_user}, contraseña: {usuario['password']})")
        created_users[usuario["username"]] = nuevo_user.id_user

    return created_users


def assign_permissions(db, users):
    """Asigna permisos a los usuarios de prueba."""
    print("\n🔐 Asignando permisos...")

    permisos = {
        "supervisor1": ["warehouse_prevoucher"],
        "almacen1": ["warehouse_voucher", "warehouse_voucher_authorize"],
        "gerencia1": ["warehouse_voucher", "warehouse_voucher_authorize"],
    }

    for username, capacidades in permisos.items():
        user_id = users.get(username)
        if not user_id:
            print(f"  ⚠️  Usuario {username} no encontrado")
            continue

        for capacidad in capacidades:
            # Encontrar la entidad de permiso para esta capacidad
            ep = db.scalars(
                select(EntityPermission).where(
                    EntityPermission.capacidad == capacidad
                )
            ).first()

            if not ep:
                print(f"  ⚠️  Capacidad {capacidad} no encontrada")
                continue

            # Verificar si el usuario ya tiene este permiso
            existente = db.scalars(
                select(NmFieldPermission).where(
                    NmFieldPermission.id_user == user_id,
                    NmFieldPermission.id_entity_permission == ep.id_entity_permission,
                )
            ).first()

            if existente:
                print(f"  ⚠️  {username} ya tiene {capacidad}")
                continue

            # Crear permiso
            np = NmFieldPermission(
                id_user=user_id,
                id_entity_permission=ep.id_entity_permission,
                created_by=1,
            )
            db.add(np)
            print(f"  ✅ {username} → {capacidad}")

    db.flush()


def create_test_products(db):
    """Crea productos de prueba para los vales."""
    print("\n📦 Creando productos de prueba...")

    productos = [
        {
            "product_name": "Desarmador Plano",
            "product_code": "DESA-01",
            "tracking_mode": "serialized",
        },
        {
            "product_name": "Desarmador Phillips",
            "product_code": "DESA-02",
            "tracking_mode": "serialized",
        },
        {
            "product_name": "Taladro Inalámbrico",
            "product_code": "TALD-01",
            "tracking_mode": "serialized",
        },
        {
            "product_name": "Cable Eléctrico",
            "product_code": "CABLE-01",
            "tracking_mode": "fungible",
        },
    ]

    for prod in productos:
        # Verificar si ya existe
        existente = db.scalars(
            select(Product).where(Product.product_code == prod["product_code"])
        ).first()

        if existente:
            print(f"  ⚠️  {prod['product_code']} ya existe")
            continue

        # Crear producto
        nuevo_prod = Product(
            product_name=prod["product_name"],
            product_code=prod["product_code"],
            tracking_mode=prod["tracking_mode"],
            created_by=1,
        )
        db.add(nuevo_prod)
        db.flush()
        print(f"  ✅ Creado: {prod['product_code']} ({prod['product_name']})")


def main():
    """Ejecuta la inicialización de datos de prueba."""
    print("\n" + "="*60)
    print("🚀 Inicializando datos de prueba para vales")
    print("="*60 + "\n")

    try:
        with transaction_context() as db:
            # Crear usuarios
            usuarios = create_test_users(db)

            print("\n" + "="*60)
            print("✅ Datos de prueba creados exitosamente")
            print("="*60)
            print("\n📝 Credenciales de prueba:")
            print("  Supervisor:  supervisor1 / supervisor1")
            print("  Almacén:     almacen1 / almacen1")
            print("  Gerencia:    gerencia1 / gerencia1")
            print("\n💡 Accede a http://localhost:3000 y prueba el flujo:")
            print("  1. Inicia sesión como 'supervisor1'")
            print("  2. Crea un prevale de préstamo")
            print("  3. Inicia sesión como 'almacen1'")
            print("  4. Autoriza el prevale")
            print("  5. Vuelve a 'supervisor1' y devuelve la herramienta\n")

            return 0
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
