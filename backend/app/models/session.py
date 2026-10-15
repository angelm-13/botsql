from __future__ import annotations
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

TESTING = os.getenv('TESTING', '0') == '1'
DB_USER = os.getenv('DB_USER', 'tyakxa_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'tyakxa_password')
DB_HOST = os.getenv('DB_HOST', 'db')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'tyakxa_erp')


def database_url() -> str:
    if TESTING:
        # SQLite en memoria es rapido y no necesita nada montado, asi que sigue
        # siendo lo que corre por omision. Pero hay comportamiento que no puede
        # medirse ahi: SQLite serializa las escrituras, de modo que dos hilos
        # nunca compiten por la misma fila y una prueba de concurrencia daria
        # verde sin haber probado nada. Tampoco valida los tipos y restricciones
        # propios de PostgreSQL: un `server_default` invalido pasaba aqui y
        # rompia la instalacion real.
        #
        # Con TEST_DATABASE_URL la misma suite corre contra una base PostgreSQL
        # desechable, que es donde esas pruebas si miden algo.
        return os.getenv('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    return f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


_URL = database_url()
_ES_SQLITE = _URL.startswith('sqlite')


def _connect_args() -> dict:
    if _ES_SQLITE:
        # Este ajuste y el StaticPool de abajo existen para compartir una sola
        # base en memoria entre hilos; con PostgreSQL estorban, porque impiden el pool real que
        # hace falta justo para probar concurrencia.
        return {'check_same_thread': False}
    if _URL.startswith('postgresql'):
        # La sesion corre en UTC sin importar como este configurado el servidor
        # (el contenedor local usaba la hora de Mexico, el cluster UTC): asi
        # `now()` -creation_date, last_update_date- es la misma hora en todos
        # lados y la API la entrega como UTC. Ver app/utils/tiempo.py.
        return {'options': '-c timezone=UTC'}
    return {}


engine = create_engine(
    _URL,
    connect_args=_connect_args(),
    poolclass=StaticPool if _ES_SQLITE else None,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=True, autocommit=False, expire_on_commit=False)


@contextmanager
def transaction_context():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
