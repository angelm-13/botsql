"""
Configuracion de la app por ambiente (Config/DevelopmentConfig/
ProductionConfig/TestingConfig), en vez de leer os.getenv() disperso por
create_app(). create_app(config_name) elige la clase segun el argumento
explicito, o segun FLASK_ENV si no se pasa nada (default 'production': la
opcion mas segura si alguien olvida definir el ambiente).

La validacion de SECRET_KEY/JWT_SECRET_KEY (fail-fast si faltan, son un
literal de ejemplo, o son demasiado cortas) se queda en app/__init__.py y
no aqui: son secretos que dependen del entorno de ejecucion real, no
"configuracion" en el sentido de esta clase -- mezclar ambos haria mas
dificil probar create_app() con TestingConfig sin secretos reales.

Atributos como clase plana (no @property): Flask's app.config.from_object()
recibe la CLASE (no una instancia), y un @property definido en una clase no
se evalua al acceder via la clase misma (devuelve el descriptor, no el
valor) -- solo funciona en instancias. Como estos valores no cambian
durante la vida del proceso, un atributo de clase evaluado una sola vez al
importar el modulo es identico en la practica y evita esa trampa.
"""
import os
from datetime import timedelta


class Config:
    """Configuracion base: valores compartidos por los 3 ambientes.
    Las subclases solo sobreescriben lo que de verdad cambia entre ellos."""
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # El token de ACCESO ahora dura minutos, no un turno completo: con el
    # token de refresco de abajo, el usuario no nota nada (se renueva solo
    # en segundo plano), pero si alguien roba la cookie de sesion la ventana
    # para reusarla baja de 12 horas a 30 minutos. JWT_ACCESS_HOURS se sigue
    # respetando si alguien ya lo tenia definido en su .env, para no cambiarle
    # el comportamiento a un despliegue existente sin avisar.
    JWT_ACCESS_TOKEN_EXPIRES = (
        timedelta(hours=int(os.environ['JWT_ACCESS_HOURS']))
        if os.getenv('JWT_ACCESS_HOURS')
        else timedelta(minutes=int(os.getenv('JWT_ACCESS_MINUTES', 30)))
    )
    # El token de REFRESCO es el que mantiene la sesion viva durante el
    # turno (y varios dias despues, para no obligar a re-teclear la
    # contrasena cada manana en una tablet compartida).
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', 30)))
    # Fase 3.4 de la remediacion de auditoria: el JWT ya no vive en
    # localStorage (legible por cualquier script inyectado via XSS), sino en
    # una cookie httpOnly (invisible para JS) + su cookie CSRF companera de
    # doble-submit, que Flask-JWT-Extended maneja solo. Se dejan 'headers' Y
    # 'cookies' como ubicaciones validas: el navegador (frontend/api.ts) ya
    # solo usa la cookie, pero el header Authorization sigue funcionando para
    # clientes que no son el navegador (la suite de pytest, un futuro cliente
    # movil/API) sin tener que reescribir esa suite completa. El ORDEN
    # importa: Flask-JWT-Extended prueba cada ubicacion en secuencia y usa la
    # PRIMERA que traiga un token, sin seguir probando las demas. 'headers'
    # va primero para que una peticion con Authorization explicito (como las
    # de pytest) autentique por ahi sin pasar por la validacion CSRF -- esa
    # solo aplica al camino de cookies (ver _decode_jwt_from_cookies). Si
    # 'cookies' fuera primero, una peticion de prueba que trajera POR
    # CASUALIDAD la cookie de un login anterior del mismo cliente HTTP (ej.
    # login() siempre deja la cookie, incluso si la prueba solo queria probar
    # el header) terminaria exigiendo CSRF aunque nunca fue esa la intencion.
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_COOKIE_CSRF_PROTECT = True
    # La cookie del JWT (httpOnly) solo se manda en peticiones a /api/, nunca
    # hacia los assets estaticos de la SPA que sirve el mismo dominio. OJO:
    # esto NO aplica a la cookie CSRF (csrf_access_token) -- esa se deja en
    # su path default '/' a proposito, porque el frontend necesita poder
    # leerla via document.cookie desde CUALQUIER pantalla (/mesero, /admin,
    # /cocina...), no solo desde /api/.
    JWT_ACCESS_COOKIE_PATH = '/api/'
    # La cookie de refresco se manda UNICAMENTE a /api/auth/refresh, no en
    # cada peticion como la de acceso. Es la diferencia de seguridad que
    # justifica el esquema: el token de larga vida (30 dias) casi nunca
    # viaja por la red, asi que hay muchisimas menos oportunidades de
    # interceptarlo que si acompanara a cada consulta de mesas o del tablero
    # de cocina (que hacen polling cada pocos segundos).
    JWT_REFRESH_COOKIE_PATH = '/api/auth/refresh'
    # False (no efimera): la cookie dura lo mismo que el token
    # (JWT_ACCESS_TOKEN_EXPIRES) en vez de borrarse al cerrar el navegador --
    # mismo comportamiento que tenia el token en localStorage (sobrevive un
    # reinicio del navegador dentro de esas 12h).
    JWT_SESSION_COOKIE = False
    # True por default: produccion siempre corre detras de TLS (ver
    # PRODUCTION_CHECKLIST.md, seccion HTTPS/TLS) y una cookie Secure jamas
    # se manda sobre HTTP plano. DevelopmentConfig/TestingConfig la relajan
    # porque ahi el backend corre en HTTP plano.
    JWT_COOKIE_SECURE = True
    # Modo replica real de cliente (ver backend/seed.py): en vez de sembrar
    # el personal de ejemplo (mesero-luis, cajero, admin, cocina...) con
    # contrasenas conocidas, solo siembra el superadmin -- el dueno real de
    # ese restaurante recibe su propia cuenta de admin por separado y desde
    # ahi da de alta a su propio personal. Apagado por default (siembra todo
    # el personal de ejemplo), util para desarrollo local y para la demo
    # publica de ventas donde SI conviene poder entrar con un clic. No tiene
    # relacion con FREEMIUM_LIMITS_ENABLED (ver app/demo.py), que controla
    # los limites del PRODUCTO (expiracion, tope de facturas, etc.) en vez
    # de como se siembra una replica -- las dos banderas son independientes
    # y se pueden combinar segun el despliegue.
    DEMO_MODE = os.getenv('DEMO_MODE', '0') == '1'
    DEBUG = False
    TESTING = False
    # Logs como JSON (ver utils/logging_setup.py) -- mas facil de mandar a
    # un agregador, pero mas incomodo de leer directo en la terminal.
    LOG_JSON = True


class DevelopmentConfig(Config):
    DEBUG = True
    # Texto legible en desarrollo: nadie esta mandando estos logs a un
    # agregador todavia, y JSON es mas dificil de leer a simple vista.
    LOG_JSON = False
    # HTTP plano en desarrollo (Vite en :3000, Flask en :5000): una cookie
    # Secure no se manda nunca sobre HTTP, asi que aqui se desactiva para no
    # romper el login. (Los navegadores modernos hacen una excepcion para
    # "localhost" exacto, pero no conviene depender de ese detalle.)
    JWT_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    """Usada por backend/tests/ (ver conftest.py). DATABASE_URL para
    pruebas apunta a una base de datos separada (nunca la de desarrollo/
    produccion) via TEST_DATABASE_URL -- los locks pg_advisory_xact_lock
    que usa este proyecto son especificos de Postgres, asi que las
    pruebas SI necesitan un Postgres real, no un SQLite en memoria."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL') or os.getenv('DATABASE_URL')
    # El cliente de pruebas de Flask/Werkzeug tambien corre "sobre HTTP"; ver
    # el mismo razonamiento que en DevelopmentConfig.
    JWT_COOKIE_SECURE = False


CONFIG_BY_NAME = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}


def get_config_class(name=None):
    name = name or os.getenv('FLASK_ENV') or 'production'
    return CONFIG_BY_NAME.get(name, ProductionConfig)
