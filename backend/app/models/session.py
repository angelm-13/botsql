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
        return 'sqlite:///:memory:'
    return f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


engine = create_engine(
    database_url(),
    connect_args={'check_same_thread': False} if TESTING else {},
    poolclass=StaticPool if TESTING else None,
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
