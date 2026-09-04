"""El tipo dentro de una familia de materiales.

Un material se define por familia + tipo + marca: desarmadores / plano / Truper.
El tipo cuelga de la familia porque "Plano" no significa nada suelto -es un tipo
de desarmador- y con una tabla plana se podria capturar "Cemento de tipo De
cruz".

Lo que este servicio agrega al CRUD generico
--------------------------------------------
**Comprueba que la familia exista** antes de escribir. En PostgreSQL la llave
ajena ya lo impide, pero el error que sale de ahi es
`errors.database_constraint`, que no dice cual campo esta mal. Comprobandolo
aqui el error nombra `id_product_family`.

**Impide el tipo repetido dentro de la familia.** Hay un indice unico en la base
sobre (familia, descripcion) entre los vivos, y aqui se traduce a un error que
dice cual es el tipo que ya existe. Dos "Plano" en desarmadores son el mismo
tipo capturado dos veces, y con los dos vigentes la mitad de los materiales
apunta a uno y la mitad al otro.
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import MaterialType, ProductFamily
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class MaterialTypeService(CrudService):
    model = MaterialType
    primary_key = 'id_material_type'
    entity_name = 'material_type'

    @classmethod
    def _validar(cls, payload: dict, *, id_actual=None) -> None:
        familia = payload.get('id_product_family')
        descripcion = str(payload.get('material_type_description') or '').strip()

        with transaction_context() as db:
            if familia not in (None, ''):
                try:
                    familia = int(familia)
                except (TypeError, ValueError) as exc:
                    raise AppError('errors.invalid_field', 400,
                                   {'field': 'id_product_family'}) from exc
                existe = db.scalars(
                    select(ProductFamily).where(
                        ProductFamily.id_product_family == familia,
                        ProductFamily.deletion_date.is_(None),
                    )
                ).first()
                if existe is None:
                    raise AppError('errors.not_found', 404,
                                   {'entity': 'product_family',
                                    'field': 'id_product_family'})

            if familia and descripcion:
                # El par tiene que ser unico entre los vivos. Se compara sin
                # distinguir mayusculas: "Plano" y "plano" son el mismo tipo, y
                # dejar los dos hace que el desplegable ofrezca dos opciones
                # identicas.
                consulta = select(MaterialType).where(
                    MaterialType.id_product_family == familia,
                    func.lower(MaterialType.material_type_description)
                    == descripcion.lower(),
                    MaterialType.deletion_date.is_(None),
                )
                if id_actual is not None:
                    consulta = consulta.where(
                        MaterialType.id_material_type != int(id_actual))
                repetido = db.scalars(consulta).first()
                if repetido is not None:
                    raise AppError(
                        'errors.material_type_already_exists', 409,
                        {'id_material_type': repetido.id_material_type,
                         'id_product_family': familia,
                         'material_type_description':
                             repetido.material_type_description},
                    )

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        cls._validar(dict(payload or {}))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        datos = dict(payload or {})
        if 'id_product_family' not in datos or 'material_type_description' not in datos:
            # Una actualizacion parcial no trae los dos campos, y el par se
            # valida como par: se completa con lo que ya esta guardado.
            with transaction_context() as db:
                actual = db.get(MaterialType, int(item_id))
            if actual is not None:
                datos.setdefault('id_product_family', actual.id_product_family)
                datos.setdefault('material_type_description',
                                 actual.material_type_description)
        cls._validar(datos, id_actual=item_id)
        return super().update(item_id, payload, user_id=user_id)


def tipos_de_la_familia(id_product_family, user_data: dict | None = None) -> dict:
    """Los tipos de una familia, para el desplegable del alta de material.

    Existe aparte del listado general porque el alta de un material ya sabe su
    familia: ofrecer los tipos de todas las familias es lo que permite capturar
    "Cemento de tipo De cruz".
    """
    try:
        familia = int(id_product_family)
    except (TypeError, ValueError) as exc:
        raise AppError('errors.invalid_field', 400,
                       {'field': 'id_product_family'}) from exc

    with transaction_context() as db:
        filas = db.scalars(
            select(MaterialType)
            .where(MaterialType.id_product_family == familia,
                   MaterialType.deletion_date.is_(None))
            .order_by(MaterialType.material_type_description)
        ).all()
        return {'id_product_family': familia,
                'items': [f.serialize() for f in filas],
                'total': len(filas)}
