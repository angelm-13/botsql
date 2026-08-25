"""
Extensiones Flask compartidas.

`db` es la instancia de Flask-SQLAlchemy que usa el modulo de restaurante
(app/restaurante/models). El core de tyakxa usa SQLAlchemy directo via
app/models/session.py; ambas capas apuntan a la misma base de datos por
DATABASE_URL, pero mantienen sesiones independientes.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
