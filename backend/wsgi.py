"""Punto de entrada para un servidor WSGI de produccion.

    gunicorn -k gthread -w 1 --threads 4 -b 0.0.0.0:5001 wsgi:application

El servidor de desarrollo de Flask (`python app.py`) es de un solo proceso y
no aguanta carga; ademas, con un modelo local cada peticion ocupa su hilo
varios segundos, asi que aqui los trabajadores importan mas de lo normal.

Un solo PROCESO con varios HILOS, no varios procesos ("-w N" con workers
sync): los caches en memoria de `bi/service.py` (preguntas) y
`bi/schema_extractor.py` (esquema) viven en `application`, este objeto de
aqui -- con procesos separados cada uno tendria su propia copia y una
pregunta repetida solo acertaria por suerte. Con hilos comparten memoria de
verdad, y la espera al modelo es de red (HTTP a Ollama), asi que el hilo
suelta el GIL mientras espera -- no se pierde concurrencia por no usar
procesos.
"""

from app import crear_app

application = crear_app()
