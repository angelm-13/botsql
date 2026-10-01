from sqlalchemy import func, select

from app.models import Material, Product
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError

# Los campos que forman la identidad de un material. Si una edicion no toca
# ninguno, no hay nada que comprobar.
CAMPOS_DE_IDENTIDAD = (
    'material_description', 'id_unit', 'id_brand', 'id_product_family', 'id_material_type',
)
INDICE_DE_IDENTIDAD = 'uq_material_identidad'


class MaterialService(CrudService):
    model = Material
    primary_key = 'id_material'
    entity_name = 'material'

    @staticmethod
    def _descripcion_normalizada(texto) -> str:
        return str(texto or '').strip().lower()

    @classmethod
    def _verificar_que_no_se_repite(cls, datos: dict, *, excepto: int | None = None) -> None:
        """Rechaza un material que ya existe vivo con la misma identidad.

        Es la misma regla que el indice `uq_material_identidad`, dicha antes de
        llegar a el: el indice solo sabe reventar, y aqui se puede decir cual
        es el material que ya esta. Ademas cubre SQLite, donde no hay indice.
        """
        consulta = select(Material.id_material).where(
            Material.deletion_date.is_(None),
            func.lower(func.trim(Material.material_description))
            == cls._descripcion_normalizada(datos.get('material_description')),
            Material.id_unit == datos.get('id_unit'),
            Material.id_brand == datos.get('id_brand'),
            Material.id_product_family == datos.get('id_product_family'),
            func.coalesce(Material.id_material_type, 0) == (datos.get('id_material_type') or 0),
        )
        if excepto is not None:
            consulta = consulta.where(Material.id_material != excepto)
        with transaction_context() as session:
            existente = session.scalars(consulta.limit(1)).first()
        if existente is not None:
            raise AppError(
                'errors.material_already_exists', 409,
                {'entity': 'material', 'id_material': existente},
            )

    @staticmethod
    def heredar_foto_de_producto(items: list[dict]) -> list[dict]:
        """A un material sin foto propia le presta la de uno de sus productos.

        Casi todo el catalogo trae sus fotos en los PRODUCTOS (las del sistema
        anterior), asi que un material sin foto propia mostraria un hueco aunque
        su herramienta se vea en Almacen, Localizar y Productos. Se toma la del
        producto vivo con foto de menor id, para que sea estable. Solo lectura:
        no escribe `material.path_imagen`.
        """
        pendientes = {int(i['id_material']) for i in items
                      if not i.get('path_imagen') and i.get('id_material')}
        if not pendientes:
            return items
        with transaction_context() as session:
            filas = session.execute(
                select(Product.id_material, Product.path_imagen).where(
                    Product.id_material.in_(list(pendientes)),
                    Product.deletion_date.is_(None),
                    Product.path_imagen.isnot(None),
                    Product.path_imagen != '',
                ).order_by(Product.id_product.desc())
            ).all()
        # Desc + sobrescribir deja la de menor id al final.
        fotos = {int(id_material): ruta for id_material, ruta in filas}
        for item in items:
            if not item.get('path_imagen') and item.get('id_material'):
                item['path_imagen'] = fotos.get(int(item['id_material'])) or item.get('path_imagen')
        return items

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        datos = dict(payload or {})
        if user_id and 'created_by' not in datos:
            datos['created_by'] = user_id
        cls._verificar_que_no_se_repite(cls._coerce_payload(datos))
        return super().create(payload, user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        cambios = cls._coerce_payload(dict(payload or {}), partial=True)
        if any(campo in cambios for campo in CAMPOS_DE_IDENTIDAD):
            with transaction_context() as session:
                actual = session.get(Material, item_id)
                if actual is None:
                    raise AppError('errors.resource_not_found', status_code=404)
                resultante = {campo: getattr(actual, campo) for campo in CAMPOS_DE_IDENTIDAD}
            resultante.update({c: v for c, v in cambios.items() if c in CAMPOS_DE_IDENTIDAD})
            cls._verificar_que_no_se_repite(resultante, excepto=int(item_id))
        return super().update(item_id, payload, user_id)

    @classmethod
    def _raise_database_constraint_error(cls, error, *, action: str):
        # Carrera entre dos capturas iguales: las dos pasaron la comprobacion y
        # la segunda en escribir la para el indice.
        if INDICE_DE_IDENTIDAD in cls._database_constraint_detail(error).lower():
            raise AppError('errors.material_already_exists', 409, {'entity': 'material'})
        return super()._raise_database_constraint_error(error, action=action)
