#!/usr/bin/env python3
"""Initialize database with all tables and seed admin user."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.models.session import engine
from app.models.base import Base
from app.models import *  # noqa: F401, F403
from sqlalchemy import text, inspect
import bcrypt


def sync_serial_sequences():
    """Align SERIAL sequences with current table max IDs after deterministic seeds."""
    try:
        sql = """
        DO $$
        DECLARE r record;
        BEGIN
          FOR r IN
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND column_default LIKE 'nextval%'
          LOOP
            EXECUTE format(
              'SELECT setval(pg_get_serial_sequence(%L, %L), COALESCE((SELECT MAX(%I) FROM %I), 0) + 1, false)',
              r.table_name, r.column_name, r.column_name, r.table_name
            );
          END LOOP;
        END $$;
        """
        with engine.begin() as conn:
            conn.execute(text(sql))
        print("✅ Serial sequences synchronized")
    except Exception as e:
        print(f"⚠️  Sequence sync warning (non-fatal): {e}")


def execute_sql_file(path: Path, label: str) -> bool:
    """Run a generated SQL file on every backend start when it exists.

    PostgreSQL only executes /docker-entrypoint-initdb.d files when a volume is
    first created. Running the idempotent seed here prevents missing admin1 and
    missing FK seed rows when a Docker volume already exists or was left partial.
    """
    if not path.exists():
        print(f"⚠️  {label} not found at {path}")
        return False
    try:
        sql = path.read_text()
        if sql.strip():
            with engine.begin() as conn:
                conn.execute(text(sql))
        print(f"✅ {label} executed")
        return True
    except Exception as e:
        print(f"⚠️  {label} warning (non-fatal): {e}")
        return False


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "si", "sí", "on"}


def bootstrap_admin_enabled() -> bool:
    return _truthy(os.getenv("BOOTSTRAP_ADMIN_ENABLED", "true"))


def bootstrap_admin_username() -> str:
    return (os.getenv("BOOTSTRAP_ADMIN_USERNAME") or "admin1").strip() or "admin1"


def bootstrap_admin_password() -> str:
    return os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or "test password"


def bootstrap_admin_email() -> str:
    return os.getenv("BOOTSTRAP_ADMIN_EMAIL") or "admin1@tyakxa.local"


def admin_mfa_enabled() -> bool:
    # Explicit opt-in only. This prevents locking a new instance before the
    # bootstrap/admin MFA secret has been configured with /mfa-setup.
    explicit = os.getenv("BOOTSTRAP_ADMIN_MFA_ENABLED")
    if explicit is None:
        explicit = os.getenv("ADMIN_MFA_ENABLED")
    return _truthy(explicit)


def init_database():
    """Create all database tables and seed admin user."""
    print("🚀 Initializing database...")
    
    try:
        # Execute init.sql first (CSV tables: user/product/etc.) on every container start.
        # PostgreSQL only runs docker-entrypoint-initdb.d once, so this keeps regenerated CSV schemas in sync.
        init_sql_path = Path("/database/init.sql")
        if init_sql_path.exists():
            try:
                with engine.begin() as conn:
                    conn.execute(text(init_sql_path.read_text()))
                print("✅ init.sql executed (CSV tables created/verified)")
            except Exception as e:
                print(f"⚠️  init.sql warning (non-fatal): {e}")

        # Create all tables from Base.metadata
        Base.metadata.create_all(engine)
        print("✅ Database tables created")

        # Catalogo de KPIs predefinidos: se resiembra en cada arranque, igual
        # que seed.sql, para que un cambio de etiqueta/unidad en el codigo se
        # refleje sin escribir una migracion.
        try:
            from app.kpis.registry import seed_kpi_definitions
            seed_kpi_definitions(engine)
            print("✅ kpi_definition seeded from KPI_REGISTRY")
        except Exception as e:
            print(f"⚠️  KPI catalog seed warning (non-fatal): {e}")

        # Catalogo `field`: sin una fila por columna publicable, un rol que no
        # sea el admin de arranque no puede recibir permiso de campo -- las
        # pantallas genericas se ven vacias para cualquier usuario real. El
        # `database/sync_fields.sql` que deberia llenarlo apunta a columnas que
        # la tabla no tiene y siempre aborta en silencio (ver
        # scripts/sync_field_catalog.py); esto siembra desde los modelos, que
        # es lo unico que siempre coincide con las tablas reales, y es
        # idempotente para poder correr en cada arranque.
        try:
            from scripts.sync_field_catalog import sincronizar as sync_field_catalog
            resultado = sync_field_catalog(actor_id=1)
            print(f"✅ field catalog synced: +{resultado['agregadas']} campos nuevos ({resultado['existentes']} ya existian)")
        except Exception as e:
            print(f"⚠️  Field catalog sync warning (non-fatal): {e}")

        # El permiso de campo se deriva del permiso de entidad (mismo criterio
        # que ya usan las migraciones generadas por seed_module_permissions.py),
        # pero esa derivacion corre en `db-migrate` ANTES de que el paso de
        # arriba exista siquiera: en el primer arranque de un pod nuevo, el
        # catalogo de campos que acaba de sembrarse todavia no tenia filas
        # cuando la migracion hizo su JOIN, asi que no derivo nada para las
        # tablas que dependian de este sembrado. Se repite aqui la misma
        # consulta para que un solo arranque quede completo, sin esperar a que
        # el pod se reinicie una segunda vez.
        try:
            derivar_field_permission_sql = """
                INSERT INTO nm_field_permission (id_field, id_permission, control_type, created_by)
                SELECT f.id_field, ep.id_permission, LEAST(ep.control_type::integer, 15)::text, 1
                FROM entity_permission ep
                JOIN field f
                  ON f.table_name = ep.entity_name
                 AND f.deletion_date IS NULL
                WHERE ep.deletion_date IS NULL
                  AND f.field_name <> 'created_by'
                  AND NOT EXISTS (
                    SELECT 1 FROM nm_field_permission nfp
                    WHERE nfp.id_field = f.id_field
                      AND nfp.id_permission = ep.id_permission
                      AND nfp.deletion_date IS NULL
                  );
            """
            with engine.begin() as conn:
                resultado_derivado = conn.execute(text(derivar_field_permission_sql))
            print(f"✅ nm_field_permission derivado: +{resultado_derivado.rowcount} filas")
        except Exception as e:
            print(f"⚠️  Field permission derive warning (non-fatal): {e}")

        # Re-apply seed.sql on every start. The file is generated idempotently,
        # so this is safe and fixes persistent Docker volumes that skipped the
        # PostgreSQL first-run seed path.
        execute_sql_file(Path("/database/seed.sql"), "seed.sql")
        sync_serial_sequences()
        
        # Check which tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Try to seed bootstrap admin if enabled and user table exists.
        admin_mfa = admin_mfa_enabled()
        bootstrap_username = bootstrap_admin_username()
        bootstrap_password = bootstrap_admin_password()
        bootstrap_email = bootstrap_admin_email()
        if not bootstrap_admin_enabled():
            print("ℹ️  Bootstrap admin disabled by BOOTSTRAP_ADMIN_ENABLED=false")
        if bootstrap_admin_enabled() and 'user' in tables:
            # Use separate connections for each operation to avoid transaction conflicts
            # This prevents "current transaction is aborted" errors
            
            # Check if bootstrap admin exists. If it was already retired and a real
            # administrator with MFA exists, do not recreate it on container restart.
            user_columns = {col["name"] for col in inspector.get_columns("user")}
            active_condition = ""
            if "active" in user_columns:
                active_condition = " AND u.active = TRUE"
            elif "is_active" in user_columns:
                active_condition = " AND u.is_active = TRUE"
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM \"user\" WHERE username = :username"), {"username": bootstrap_username})
                count = result.scalar()
                real_admin_count = 0
                if 'user_mfa' in tables:
                    real_admin_count = conn.execute(text(
                        "SELECT COUNT(*) FROM \"user\" u "
                        "JOIN user_mfa m ON m.id_user = u.id_user AND m.enabled = TRUE "
                        "WHERE u.username <> :username "
                        "AND lower(COALESCE(u.user_type, '')) = 'admin'" + active_condition
                    ), {"username": bootstrap_username}).scalar() or 0
                conn.close()
            
            if count == 0 and int(real_admin_count) > 0:
                print(f"ℹ️  Bootstrap admin ({bootstrap_username}) is retired; real admin with MFA exists, skipping recreation")
            elif count == 0:
                # Create default status if needed (separate transaction)
                try:
                    with engine.begin() as conn:
                        
                        cols = {col["name"] for col in inspector.get_columns("status")}
                        if {"status_description", "category", "is_terminal", "created_by"}.issubset(cols):
                            conn.execute(text("INSERT INTO status (id_status, status_description, category, is_terminal, created_by) VALUES (1, 'active', 'general', TRUE, 1) ON CONFLICT DO NOTHING"))
                        elif "name" in cols:
                            conn.execute(text("INSERT INTO status (id_status, name) VALUES (1, 'active') ON CONFLICT DO NOTHING"))
                except Exception as e:
                    print(f"⚠️  Status table insert: {e}")
                
                # Create default permission if needed (separate transaction)
                try:
                    with engine.begin() as conn:
                        
                        cols = {col["name"] for col in inspector.get_columns("permission")}
                        if {"permission_description", "created_by", "authorized_by", "id_department", "id_subdepartment", "id_level"}.issubset(cols):
                            conn.execute(text("INSERT INTO permission (id_permission, permission_description, created_by, authorized_by, id_department, id_subdepartment, id_level) VALUES (1, 'Administrator', 1, 1, 1, 1, 1) ON CONFLICT DO NOTHING"))
                        elif "name" in cols:
                            conn.execute(text("INSERT INTO permission (id_permission, name) VALUES (1, 'admin') ON CONFLICT DO NOTHING"))
                except Exception as e:
                    print(f"⚠️  Permission table insert: {e}")
                
                # Create default proyect if needed (separate transaction)
                try:
                    with engine.begin() as conn:
                        
                        cols = {col["name"] for col in inspector.get_columns("proyect")}
                        if {"title", "id_customer_supplier", "leader", "created_by"}.issubset(cols):
                            conn.execute(text("INSERT INTO proyect (id_proyect, title, id_customer_supplier, leader, created_by) VALUES (1, 'Default Project', 1, 1, 1) ON CONFLICT DO NOTHING"))
                        elif "name" in cols:
                            conn.execute(text("INSERT INTO proyect (id_proyect, name) VALUES (1, 'Default Project') ON CONFLICT DO NOTHING"))
                except Exception as e:
                    print(f"⚠️  Proyect table insert: {e}")
                
                # Hash the password - bcrypt hash of "test password"
                # Fixed hash: $2b$12$RxTtZtblFwu6ZsmtfNP9Meg6tYSZOCsVIZQLMe260W9seWcdrUma6
                password = bootstrap_password
                hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
                
                # Insert bootstrap core records with triggers disabled only for this
                # minimal bootstrap cycle. Some generated schemas have circular FK
                # dependencies: user -> permission/status/proyect and those rows
                # also use created_by=1. The bootstrap admin must exist in fresh
                # projects before normal seed rows can be replayed safely.
                try:
                    def _insert_seed_row(conn, table_name, pk_name, payload):
                        if table_name not in tables:
                            return
                        cols = {col["name"] for col in inspector.get_columns(table_name)}
                        insert_cols = [name for name in payload if name in cols]
                        if pk_name not in insert_cols:
                            return
                        columns_clause = ", ".join(f'"{name}"' for name in insert_cols)
                        values_clause = ", ".join(f":{name}" for name in insert_cols)
                        sql = f'INSERT INTO "{table_name}" ({columns_clause}) VALUES ({values_clause}) ON CONFLICT ("{pk_name}") DO NOTHING'
                        conn.execute(text(sql), {name: payload[name] for name in insert_cols})

                    now_value = "2026-01-01 00:00:00"
                    bootstrap_tables = [name for name in ("status", "permission", "proyect", "user") if name in tables]

                    with engine.begin() as conn:
                        for table_name in bootstrap_tables:
                            conn.execute(text(f'ALTER TABLE "{table_name}" DISABLE TRIGGER ALL'))
                        try:
                            bootstrap_rows = [
                                ("status", "id_status", {
                                "id_status": 1,
                                "status_description": "active",
                                "name": "active",
                                "category": "general",
                                "is_terminal": True,
                                "sort_order": 1,
                                "created_by": 1,
                                "creation_date": now_value,
                                "last_update_date": now_value,
                                "deletion_date": None,
                                }),
                                ("permission", "id_permission", {
                                "id_permission": 1,
                                "permission_description": "Administrator",
                                "permission_name": "Administrator",
                                "name": "admin",
                                "description": "Full access",
                                "control_type": "15",
                                "created_by": 1,
                                "authorized_by": 1,
                                "id_department": 1,
                                "id_subdepartment": 1,
                                "id_level": 1,
                                "creation_date": now_value,
                                "last_update_date": now_value,
                                "deletion_date": None,
                                }),
                                ("proyect", "id_proyect", {
                                "id_proyect": 1,
                                "title": "Default Project",
                                "name": "Default Project",
                                "proyect_description": "Default Project",
                                "proyect_status": "active",
                                "id_customer_supplier": 1,
                                "leader": 1,
                                "created_by": 1,
                                "creation_date": now_value,
                                "last_update_date": now_value,
                                "deletion_date": None,
                                }),
                                ("user", "id_user", {
                                "id_user": 1,
                                "username": bootstrap_username,
                                "password": hashed,
                                "password_hash": hashed,
                                "email": bootstrap_email,
                                "first_name": "Admin",
                                "full_name": "Administrador Bootstrap",
                                "last_name": "User",
                                "last_name_father": "Bootstrap",
                                "last_name_mother": "System",
                                "user_type": "admin",
                                "is_active": True,
                                "created_by": 1,
                                "id_permission": 1,
                                "id_proyect": 1,
                                "id_status": 1,
                                "supervisor": 1,
                                "principal_phone": "0000000000",
                                "secundary_phone": "0000000000",
                                "national_id": "BOOTSTRAP",
                                "ssn": "BOOTSTRAP",
                                "tax_id": "BOOTSTRAP",
                                "title": "Bootstrap Admin",
                                "puesto": "Bootstrap Admin",
                                "creation_date": now_value,
                                "last_update_date": now_value,
                                "date_born": now_value,
                                "date_start": now_value,
                                "hire_date": now_value,
                                "deletion_date": None,
                                }),
                            ]
                            for table_name, pk_name, payload in bootstrap_rows:
                                try:
                                    with conn.begin_nested():
                                        _insert_seed_row(conn, table_name, pk_name, payload)
                                except Exception as row_error:
                                    print(f"⚠️  Bootstrap {table_name} row warning (non-fatal): {row_error}")
                        finally:
                            for table_name in reversed(bootstrap_tables):
                                conn.execute(text(f'ALTER TABLE "{table_name}" ENABLE TRIGGER ALL'))

                    print(f"✅ Bootstrap admin created ({bootstrap_username})")

                    # Replay idempotent seed after the bootstrap cycle exists.
                    # This fills the rest of the generated seed rows in fresh DBs.
                    try:
                        execute_sql_file(Path("/database/seed.sql"), "seed.sql post-bootstrap")
                        sync_serial_sequences()
                    except Exception as seed_error:
                        print(f"⚠️  post-bootstrap seed warning (non-fatal): {seed_error}")
                except Exception as e:
                    print(f"❌ Admin user insert error: {e}")
            else:
                # Keep the known development credentials valid even when an old
                # Docker volume already has admin1 without the expected password
                # columns populated. Only update columns that exist.
                try:
                    password = bootstrap_password
                    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
                    user_columns = {col["name"] for col in inspector.get_columns("user")}
                    updates = []
                    params = {"username": bootstrap_username, "password": hashed, "password_hash": hashed}
                    if "password" in user_columns:
                        updates.append("password = :password")
                    if "password_hash" in user_columns:
                        updates.append("password_hash = :password_hash")
                    if "is_active" in user_columns:
                        updates.append("is_active = TRUE")
                    if "user_type" in user_columns:
                        updates.append("user_type = 'admin'")
                    if "email" in user_columns:
                        updates.append("email = :email")
                        params["email"] = bootstrap_email
                    if updates:
                        with engine.begin() as conn:
                            conn.execute(text(f"UPDATE \"user\" SET {', '.join(updates)} WHERE username = :username"), params)
                    print(f"⚠️  Bootstrap admin already exists; credentials verified ({bootstrap_username})")
                except Exception as e:
                    print(f"⚠️  Admin credential update warning (non-fatal): {e}")
        
        # Bootstrap MFA is explicit opt-in. It is enabled only when a valid
        # secret/iv already exists, so a fresh instance cannot lock itself.
        if 'user_mfa' in tables and 'user' in tables:
            try:
                mfa_columns = {col["name"] for col in inspector.get_columns("user_mfa")}
                if {"id_user", "enabled"}.issubset(mfa_columns):
                    with engine.begin() as conn:
                        conn.execute(text(
                            """
                            UPDATE user_mfa
                            SET enabled = :enabled
                            WHERE id_user = (SELECT id_user FROM "user" WHERE username = :username)
                              AND (:enabled = FALSE OR (secret IS NOT NULL AND secret_iv IS NOT NULL))
                            """
                        ), {"enabled": admin_mfa, "username": bootstrap_username})
                print(f"✅ Bootstrap MFA requested={admin_mfa}; enabled only when secret/iv are configured")
            except Exception as e:
                print(f"⚠️  Admin MFA update warning (non-fatal): {e}")

        sync_serial_sequences()
        print("✅ Database initialization complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
