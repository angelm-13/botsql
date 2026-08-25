"""baseline: esquema ya existente creado via db.create_all(), sin cambios reales

Revision ID: dc4363ab55f3
Revises: 
Create Date: 2026-08-13 15:51:23.134323

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dc4363ab55f3'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Intencionalmente vacio: este proyecto arranco sin Alembic (el esquema
    # se creaba/actualizaba con db.create_all() + schema_sync.py, ver
    # backend/app/utils/schema_sync.py). Esta migracion "baseline" no hace
    # ningun cambio de verdad -- es el punto de partida a partir del cual
    # todo cambio de esquema NUEVO si pasa por una migracion real generada
    # con `flask db migrate`. En una base de datos que ya tiene el esquema
    # actual (cualquier despliegue existente de esta plantilla), esta
    # revision se marca como aplicada con `flask db stamp head` SIN correr
    # upgrade() -- por eso no importa que este vacia.
    pass


def downgrade():
    pass
