"""Siembra la base de demostracion generica en un Postgres real.

    python seed_demo_postgres.py postgresql+psycopg2://postgres:postgres@db:5432/erp_demo

Es lo que usa `docker-compose.demo.yml` para darle al stack completo de
Docker (nginx + backend + Postgres) el mismo dataset generico que
`demo.py` usa para el camino sin Docker -- clientes, productos, empleados,
ventas, con la misma tendencia y estacionalidad, la misma semilla fija -- en
vez de una base vacia o un placeholder sin configurar.

Dos cosas hace este script y no solo una, a proposito
------------------------------------------------------
1. Siembra los datos (reusando `demo.sembrar()`, no una copia).
2. Crea el rol `bi_lector` de solo lectura y le da GRANT SELECT.

La segunda no es un adorno: es la barrera que de verdad importa (ver
docs/DESPLIEGUE.md seccion 1), y una demostracion que la salta -- conectando
como el superusuario -- enseñaria el habito equivocado justo en el momento en
que alguien se está formando la idea de como se despliega esto en serio. Si
se va a mostrar un flujo de punta a punta, que sea el flujo correcto.

Es idempotente: se puede correr mas de una vez contra la misma base (un
contenedor que se reinicia) sin fallar.
"""

from __future__ import annotations

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

from demo import sembrar

# Solo para la demostracion. En un despliegue real, la clave se genera y se
# guarda como cualquier otra credencial -- nunca queda fija en un script.
CLAVE_DE_DEMO = "bi_lector_demo"


def _url_administrador() -> str:
    if len(sys.argv) < 2:
        print("uso: python seed_demo_postgres.py <URL-de-postgres-con-permiso-de-crear>",
              file=sys.stderr)
        raise SystemExit(2)
    return sys.argv[1]


def crear_rol_de_solo_lectura(url_administrador: str) -> None:
    """El rol `bi_lector`, con GRANT SELECT y nada mas.

    Se conecta como administrador (quien SI puede crear roles y otorgar
    permisos) solo para este paso. La aplicacion nunca usa esta conexion --
    usa `bi_lector`, que es la que de verdad no puede escribir.
    """
    motor = create_engine(url_administrador, future=True)
    with motor.begin() as con:
        existe = con.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = 'bi_lector'")
        ).scalar()
        if not existe:
            # No se puede parametrizar un nombre de rol ni una clave dentro
            # de CREATE ROLE -- va literal, y por eso la clave no sale de
            # este archivo ni se toma de fuera.
            con.execute(text(f"CREATE ROLE bi_lector LOGIN PASSWORD '{CLAVE_DE_DEMO}'"))

        # GRANT ... ON DATABASE tampoco acepta una subconsulta como nombre;
        # hace falta el nombre literal, asi que se pregunta primero.
        base = con.execute(text("SELECT current_database()")).scalar()
        con.execute(text(f'GRANT CONNECT ON DATABASE "{base}" TO bi_lector'))
        con.execute(text("GRANT USAGE ON SCHEMA public TO bi_lector"))
        con.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_lector"))
        con.execute(text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO bi_lector"
        ))
    motor.dispose()


def main() -> None:
    url_administrador = _url_administrador()

    print("Sembrando la base de demostracion...", file=sys.stderr)
    sembrar(database_url=url_administrador)

    print("Creando el rol de solo lectura 'bi_lector'...", file=sys.stderr)
    try:
        crear_rol_de_solo_lectura(url_administrador)
    except ProgrammingError as exc:
        # Un rol que ya existe de una corrida anterior no es un error --
        # es exactamente lo que se espera al reiniciar el contenedor.
        if "already exists" not in str(exc):
            raise

    print("Listo: datos sembrados y 'bi_lector' con permiso de solo lectura.",
          file=sys.stderr)


if __name__ == "__main__":
    main()
