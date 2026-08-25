"""
Cifrado simetrico para secretos de configuracion guardados en la base de
datos (credenciales del PAC de facturacion). Mismo enfoque que un proyecto
hermano de esta empresa (cotizador_demo): Fernet con una llave derivada de
CONFIG_ENCRYPTION_KEY o, si no esta definida, de SECRET_KEY.

El tipo de columna EncryptedString cifra al guardar y descifra al leer de
forma transparente: las rutas siguen leyendo/escribiendo el atributo como
texto plano. Tolerante a datos legados: si un valor no descifra (se guardo
en texto plano antes de activar el cifrado), decrypt() lo devuelve tal cual
en vez de tronar.
"""
import os
import base64
import hashlib

import sqlalchemy.types as types
from cryptography.fernet import Fernet, InvalidToken


def _derive_key():
    # Sin fallback a un valor por default: create_app() (app/__init__.py) ya
    # exige que SECRET_KEY exista antes de arrancar, asi que si esta funcion
    # se llama es porque la app ya arranco y por lo tanto la variable existe.
    # Un fallback aqui hubiera sido una segunda puerta trasera con la misma
    # llave publicamente conocida, aunque se hubiera cerrado la de arranque.
    secret = os.getenv('CONFIG_ENCRYPTION_KEY') or os.environ['SECRET_KEY']
    digest = hashlib.sha256(secret.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_derive_key())
    return _fernet


def encrypt(plaintext):
    if plaintext is None:
        return None
    if plaintext == '':
        return ''
    token = _get_fernet().encrypt(plaintext.encode('utf-8'))
    return token.decode('utf-8')


def decrypt(token):
    if token is None:
        return None
    if token == '':
        return ''
    try:
        return _get_fernet().decrypt(token.encode('utf-8')).decode('utf-8')
    except (InvalidToken, ValueError, TypeError):
        return token


class EncryptedString(types.TypeDecorator):
    """Columna de texto que se cifra al guardar y se descifra al leer.

    Uso: password = db.Column(EncryptedString(512))
    """
    impl = types.String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        return decrypt(value)
