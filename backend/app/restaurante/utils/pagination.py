"""Helper de paginacion reutilizado por varias rutas de solo-lectura (listas largas)."""
from .errors import ApiError


def paginate(query, request):
    """Pagina un query de SQLAlchemy usando los parametros ?page= y ?per_page= de la URL."""
    # int() sin try/except tronaba con un ValueError no capturado (500
    # generico, con traceback solo en logs pero un mensaje generico "Unexpected
    # server error" para el cliente) si ?page= o ?per_page= no eran numericos
    # -- un 422 claro es mas util tanto para el frontend como para cualquier
    # cliente de la API que mande un valor invalido por error.
    try:
        page = max(int(request.args.get('page', 1)), 1)
        per_page = min(max(int(request.args.get('per_page', 10)), 1), 100)
    except (TypeError, ValueError):
        raise ApiError('page y per_page deben ser numericos', 422, 'validation_error') from None
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        'items': [item.to_dict() for item in result.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': result.total,
            'pages': result.pages,
            'has_next': result.has_next,
            'has_prev': result.has_prev,
        }
    }
