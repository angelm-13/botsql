import re
import unicodedata

from sqlalchemy import func, or_, select

from app.models import ProductFamily
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError

# Letras con acento y su equivalente sin acento. Se reemplazan con `replace()`
# anidado y no con `unaccent`/`translate`: funciona igual en PostgreSQL y en
# SQLite (donde corren las pruebas), sin instalar ninguna extension. Las
# mayusculas se listan aparte porque `lower()` de SQLite solo baja ASCII y el de
# PostgreSQL, en una base de locale "C", tampoco baja las acentuadas.
_ACENTOS = {
    'á': 'a', 'à': 'a', 'ä': 'a', 'â': 'a',
    'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e',
    'í': 'i', 'ì': 'i', 'ï': 'i', 'î': 'i',
    'ó': 'o', 'ò': 'o', 'ö': 'o', 'ô': 'o',
    'ú': 'u', 'ù': 'u', 'ü': 'u', 'û': 'u',
    'ñ': 'n',
}
_ACENTOS.update({k.upper(): v for k, v in _ACENTOS.items()})


def normalizar_descripcion(texto) -> str:
    """Minusculas, sin acentos y con los espacios colapsados.

    "  Refacción " y "REFACCION" dan lo mismo: es la vara con la que se busca y
    con la que se decide si dos familias son la misma.
    """
    descompuesto = unicodedata.normalize('NFD', str(texto or ''))
    sin_acentos = ''.join(c for c in descompuesto if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', sin_acentos).strip().lower()


def _descripcion_normalizada_sql(columna):
    expresion = func.lower(columna)
    for con_acento, sin_acento in _ACENTOS.items():
        expresion = func.replace(expresion, con_acento, sin_acento)
    return expresion


class ProductFamilyService(CrudService):
    model = ProductFamily
    primary_key = 'id_product_family'
    entity_name = 'product_family'

    @classmethod
    def _busqueda_libre(cls, texto):
        """Busqueda por descripcion sin importar mayusculas ni acentos.

        Solo para esta entidad: la busqueda generica (`CrudService`) sigue
        distinguiendo acentos, y cambiarla afecta a todas las pantallas.
        """
        aguja = normalizar_descripcion(texto)
        if not aguja:
            return None
        condiciones = [_descripcion_normalizada_sql(ProductFamily.product_family_description).like(f'%{aguja}%')]
        if aguja.isdigit():
            condiciones.append(ProductFamily.id_product_family == int(aguja))
        return or_(*condiciones)

    @classmethod
    def list(cls, page: int = 1, per_page: int = 20, filters: dict | None = None,
             sort: str | None = None, q: str | None = None):
        # Sin ORDER BY, OFFSET/LIMIT no tiene orden garantizado: lo recien creado
        # podia caer en cualquier pagina, o una fila repetirse entre paginas.
        return super().list(page=page, per_page=per_page, filters=filters,
                            sort=sort or '-id_product_family', q=q)

    @classmethod
    def _validar_descripcion_unica(cls, descripcion, excluir_id=None) -> None:
        """409 si ya hay otra familia vigente con la misma descripcion normalizada."""
        normalizada = normalizar_descripcion(descripcion)
        if not normalizada:
            return
        with transaction_context() as session:
            consulta = select(ProductFamily.id_product_family).where(
                ProductFamily.deletion_date.is_(None),
                _descripcion_normalizada_sql(ProductFamily.product_family_description) == normalizada,
            )
            if excluir_id is not None:
                consulta = consulta.where(ProductFamily.id_product_family != int(excluir_id))
            existente = session.scalars(consulta.limit(1)).first()
        if existente is not None:
            raise AppError(
                'errors.product_family_already_exists',
                status_code=409,
                meta={'entity': 'product_family', 'field': 'product_family_description', 'id_existing': existente},
            )

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        cls._validar_descripcion_unica((payload or {}).get('product_family_description'))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        if 'product_family_description' in (payload or {}):
            cls._validar_descripcion_unica(payload['product_family_description'], excluir_id=item_id)
        return super().update(item_id, payload, user_id=user_id)
