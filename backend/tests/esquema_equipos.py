"""Lo que `nm_team_user` declara en PostgreSQL, en un solo lugar.

Lo comparten la prueba del esquema que arma el ORM (`esquema_orm`) y la de la base real
(`init.sql` + migraciones): las dos exigen EXACTAMENTE este indice, asi que si una migracion y el
modelo se separan, una de las dos falla.
"""

NOMBRE_INDICE_VIGENTE = "uq_nm_team_user_vigente"
NOMBRE_CONSTRAINT_ANTERIOR = "uq_nm_team_user"
INDEXDEF_VIGENTE = (
    "CREATE UNIQUE INDEX uq_nm_team_user_vigente ON public.nm_team_user "
    "USING btree (id_team, id_user) WHERE (deletion_date IS NULL)"
)


def indices_unicos_de_nm_team_user(conexion) -> dict[str, str]:
    """`{nombre: definicion}` de los indices unicos de `nm_team_user` (un constraint UNIQUE tambien es uno)."""
    from sqlalchemy import text

    filas = conexion.execute(text(
        "SELECT i.relname, pg_get_indexdef(i.oid) "
        "FROM pg_index x JOIN pg_class i ON i.oid = x.indexrelid JOIN pg_class t ON t.oid = x.indrelid "
        "WHERE t.relname = 'nm_team_user' AND x.indisunique AND NOT x.indisprimary"
    )).all()
    return {nombre: definicion for nombre, definicion in filas}
