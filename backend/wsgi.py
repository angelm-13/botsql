"""Punto de entrada para un servidor WSGI de produccion.

    gunicorn -w 4 -b 0.0.0.0:5001 wsgi:application

El servidor de desarrollo de Flask (`python app.py`) es de un solo proceso y
no aguanta carga; ademas, con un modelo local cada peticion ocupa su hilo
varios segundos, asi que aqui los trabajadores importan mas de lo normal.
"""

from app import crear_app

application = crear_app()
