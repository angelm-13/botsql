"""
Sincronizacion aditiva de esquema (auto-migracion segura).

Cada vez que se agrega una columna nueva a un modelo (por ejemplo
Order.payment_method o Waiter.max_tables en cambios anteriores), una base
de datos que ya tenia datos de una version previa del codigo se queda con
un esquema desactualizado, porque db.create_all() solo crea tablas que no
existen: nunca modifica una tabla que ya existe.

Esta funcion revisa, para cada tabla que ya existe en la base de datos,
si le faltan columnas que el modelo actual si define, y si es asi las
agrega con ALTER TABLE ADD COLUMN. Nunca borra ni modifica columnas o
filas existentes, por lo que es seguro correrla en cada arranque del
backend (se ejecuta automaticamente desde init_db.py).
"""
from sqlalchemy import inspect, text


def sync_missing_columns(db):
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    added = []
    for table in db.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        existing_cols = {c['name'] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing_cols:
                continue
            col_type = column.type.compile(dialect=db.engine.dialect)
            ddl = f'ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}'
            if not column.nullable:
                default_value = 0
                if column.default is not None and not callable(column.default.arg):
                    default_value = column.default.arg
                if isinstance(default_value, str):
                    ddl += f" NOT NULL DEFAULT '{default_value}'"
                elif isinstance(default_value, bool):
                    ddl += f" NOT NULL DEFAULT {str(default_value).upper()}"
                else:
                    ddl += f" NOT NULL DEFAULT {default_value}"
            db.session.execute(text(ddl))
            added.append(f'{table.name}.{column.name}')
    if added:
        db.session.commit()
    return added
