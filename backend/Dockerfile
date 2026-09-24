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
COPY app.py demo.py wsgi.py ./

# Usuario sin privilegios: el proceso no tiene por que poder escribir su
# propio codigo.
RUN useradd --create-home --uid 10001 bi && chown -R bi:bi /app
USER bi

EXPOSE 5001

# El tiempo de espera va alto a proposito: una respuesta de un modelo local
# puede tardar decenas de segundos, y el valor por omision de gunicorn (30s)
# cortaria la peticion justo antes de que el modelo conteste.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "--timeout", "180", \
     "--access-logfile", "-", "wsgi:application"]
