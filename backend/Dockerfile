# syntax=docker/dockerfile:1
FROM python:3.13-slim

# psycopg2-binary y pymysql no necesitan compilador; pyodbc si, y por eso el
# controlador de SQL Server no viene en esta imagen: se agrega en un derivado
# solo si el despliegue lo usa, en vez de engordar la imagen de todos.
WORKDIR /app

# Red de seguridad: si algun dia no hay rueda precompilada para la
# plataforma o version de Python del build, pip cae a compilar desde
# fuente y necesita esto. Ya paso una vez -- psycopg2-binary 2.9.9 no
# traia rueda para Python 3.13 y el build tronaba con "pg_config
# executable not found" -- por eso queda instalado, aunque hoy no se
# necesite con la version fijada abajo. Se purga en la misma capa.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir psycopg2-binary==2.9.13 PyMySQL==1.1.1 \
    && apt-get purge -y --auto-remove gcc libpq-dev

COPY bi/ ./bi/
COPY app.py demo.py wsgi.py seed_demo_postgres.py ./

# Usuario sin privilegios: el proceso no tiene por que poder escribir su
# propio codigo.
RUN useradd --create-home --uid 10001 bi && chown -R bi:bi /app
USER bi

EXPOSE 5001

# El tiempo de espera va alto a proposito: una respuesta de un modelo local
# puede tardar decenas de segundos, y el valor por omision de gunicorn (30s)
# cortaria la peticion justo antes de que el modelo conteste.
#
# 300 y no 180: medido en la practica dentro de Docker (con otros
# contenedores compitiendo por CPU), una pregunta real tardo 166s de punta a
# punta -- mas de lo que BI_LLM_TIMEOUT (240s) por si solo hacia pensar, y
# gunicorn mataba al trabajador por "silencioso" ANTES de que la aplicacion
# llegara a decidir que el modelo tardaba demasiado. El timeout de esta capa
# tiene que quedar por ENCIMA de BI_LLM_TIMEOUT, nunca por debajo -- si no,
# el sintoma no es un error claro, es una respuesta vacia sin explicacion.
# "gthread" con 1 proceso y 4 hilos, y no "-w 4" (4 procesos): verificado en
# la practica que con 4 procesos el cache de preguntas (bi/service.py) y el
# de esquema (bi/schema_extractor.py) casi no acertaban -- cada worker es un
# proceso de Python con su propia memoria, asi que una pregunta repetida
# tenia solo 1 de 4 chances de caer en el mismo proceso que la guardo. Con
# hilos comparten memoria de verdad, y el cache si sirve. No se pierde
# concurrencia real: la espera al modelo es de red (Ollama por HTTP), asi
# que el hilo suelta el GIL mientras espera, igual que lo haria un proceso
# aparte -- y el Engine de SQLAlchemy ya se creo pensado para esto
# (pool_size=5 en app.py::crear_engine).
CMD ["gunicorn", "-k", "gthread", "-w", "1", "--threads", "4", \
     "-b", "0.0.0.0:5001", "--timeout", "300", \
     "--access-logfile", "-", "wsgi:application"]
