"""
Manejo centralizado de errores.

ApiError es la excepcion que usan las rutas para devolver errores de
negocio con un codigo HTTP y un `code` de maquina claro (por ejemplo
'register_closed', 'table_occupied'), en vez de dejar que Flask devuelva
un error generico. register_error_handlers() atrapa cualquier excepcion
no prevista tambien, para que la API nunca devuelva un HTML de error sino
siempre JSON con la misma forma: {"error": {"message", "code", "status"}}.
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError


class ApiError(Exception):
    def __init__(self, message, status_code=400, code='api_error'):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)

def error_response(message, status_code=400, code='api_error'):
    return jsonify({'error': {'message': message, 'code': code, 'status': status_code}}), status_code

def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return error_response(err.message, err.status_code, err.code)

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return error_response(err.description, err.code, err.name.lower().replace(' ', '_'))

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(err):
        app.logger.exception(err)
        return error_response('Database error', 500, 'database_error')

    @app.errorhandler(Exception)
    def handle_error(err):
        app.logger.exception(err)
        return error_response('Unexpected server error', 500, 'internal_error')
