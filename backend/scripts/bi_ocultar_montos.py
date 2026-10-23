"""Quita a un rol la lectura de las columnas de dinero (para el modulo BI y,
como efecto, para los campos de la aplicacion: es el mismo permiso de campo).

Ejemplo: que el encargado de Operaciones no vea los importes de Finanzas.

    python scripts/bi_ocultar_montos.py --rol "Jefe de taller"            # solo muestra
    python scripts/bi_ocultar_montos.py --rol "Jefe de taller" --aplicar  # lo hace
    python scripts/bi_ocultar_montos.py --rol "Jefe de taller" --restaurar --aplicar

Actua sobre nm_field_permission quitando el bit de lectura (2) a los campos cuyo
nombre parece un importe. Es reversible con --restaurar. Se puede ajustar mas
fino despues desde el gestor de roles y permisos.
"""

import argparse
import re

from sqlalchemy import text

from app import create_app
from app.models.field import Field
from app.models.nm_field_permission import NmFieldPermission
from app.models.permission import Permission
from app.models.session import transaction_context

FIELD_READ_BIT = 2
PATRON = re.compile(
    r"(amount|total|price|precio|cost|costo|importe|monto|balance|saldo|salary|salario|"
    r"tax|iva|subtotal|paid|pago|ingreso|income|discount|descuento)", re.IGNORECASE)
# Identificadores y fechas no son dinero aunque lleven la palabra.
EXCLUIR = re.compile(r"^(id_|.*_id$|.*_date$|.*_by$|.*description.*|.*status.*|.*type.*)", re.IGNORECASE)


def _ajustar(s, rol, id_field, control_type=None, retirar=False, reactivar=False):
    """UPDATE por rol+campo (hay filas duplicadas por campo en bases viejas).

    Se escribe `ajustado_por_gestor`: asi el trigger que protege lo hecho desde
    el Gestor (migracion 20260816) lo trata como un cambio del Gestor y no lo
    descarta. Es lo correcto: esto ES un ajuste de permisos hecho a mano.
    """
    tiene = s.execute(text("select 1 from information_schema.columns where table_name="
                           "'nm_field_permission' and column_name='ajustado_por_gestor'")).first()
    sets = []
    if control_type is not None:
        sets.append("control_type = :ct")
    if retirar:
        sets.append("deletion_date = now()")
    if reactivar:
        sets.append("deletion_date = NULL")
    if tiene:
        sets.append("ajustado_por_gestor = now()")
    s.execute(text(f"update nm_field_permission set {', '.join(sets)} "
                   "where id_permission = :p and id_field = :f"),
              {"ct": control_type, "p": rol.id_permission, "f": id_field})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rol", required=True, help="permission_description del rol")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--restaurar", action="store_true")
    args = ap.parse_args()

    app = create_app()
    with app.app_context(), transaction_context() as s:
        rol = s.query(Permission).filter(Permission.permission_description == args.rol).first()
        if not rol:
            raise SystemExit(f"No existe el rol {args.rol!r}")
        campos = {f.id_field: f for f in s.query(Field).filter(Field.deletion_date.is_(None)).all()
                  if PATRON.search(f.field_name) and not EXCLUIR.search(f.field_name)}
        filas = (s.query(NmFieldPermission)
                 .filter(NmFieldPermission.id_permission == rol.id_permission)
                 .filter(NmFieldPermission.id_field.in_(list(campos)))
                 .filter(NmFieldPermission.deletion_date.is_(None)).all())
        cambios = 0
        if args.restaurar:
            # Vuelve a dar lectura: reactiva filas retiradas y crea las que falten.
            todas = {p.id_field: p for p in (
                s.query(NmFieldPermission)
                .filter(NmFieldPermission.id_permission == rol.id_permission)
                .filter(NmFieldPermission.id_field.in_(list(campos))).all())}
            for id_field, f in campos.items():
                p = todas.get(id_field)
                if p is not None and p.deletion_date is None and int(p.control_type) & FIELD_READ_BIT:
                    continue
                cambios += 1
                print(f"{f.table_name}.{f.field_name}: se restaura la lectura")
                if args.aplicar:
                    if p is None:
                        s.add(NmFieldPermission(id_field=id_field, id_permission=rol.id_permission,
                                                control_type="2", created_by=1))
                    else:
                        _ajustar(s, rol, id_field, control_type=str(int(p.control_type) | FIELD_READ_BIT), reactivar=True)
        else:
            for p in filas:
                ct = int(p.control_type)
                f = campos[p.id_field]
                cambios += 1
                nuevo = ct & ~FIELD_READ_BIT
                if nuevo >= 1:
                    print(f"{f.table_name}.{f.field_name}: {ct} -> {nuevo}")
                    if args.aplicar:
                        _ajustar(s, rol, p.id_field, control_type=str(nuevo))
                else:   # el enum no admite 0: sin permisos = fila retirada
                    print(f"{f.table_name}.{f.field_name}: {ct} -> fila retirada")
                    if args.aplicar:
                        _ajustar(s, rol, p.id_field, retirar=True)
        print(f"\n{cambios} campos {'actualizados' if args.aplicar else 'se actualizarian (usa --aplicar)'}")
        if not args.aplicar:
            s.rollback()


if __name__ == "__main__":
    main()
