# Imagen mínima cuyo único trabajo es traer el esquema SQL para que
# Postgres lo ejecute la primera vez que el volumen está vacío.
#
# postgres:16-alpine ya ignora los scripts de /docker-entrypoint-initdb.d
# si el volumen ya tiene datos — es exactamente el mismo comportamiento
# que hoy en docker-compose.yml (donde init.sql/seed.sql se montan como
# volumen), solo que aquí el esquema viaja dentro de una imagen
# versionada por SHA en vez de un archivo montado desde el host. Esto
# respeta el principio de que el clúster nunca tiene código fuente en
# disco, solo imágenes.
#
# init.sql + sync_fields.sql pesan ~724 KB combinados: al límite
# práctico de un ConfigMap de Kubernetes (1 MiB) y son esquema, no
# configuración — por eso van en una imagen y no en un ConfigMap.
FROM postgres:16-alpine
COPY database/init.sql /docker-entrypoint-initdb.d/01-init.sql
# seed.sql NO se copia a propósito: inserta un usuario admin1 con un
# hash bcrypt fijo e idéntico en cada instalación (ver database/seed.sql).
# Sirve para desarrollo local, nunca para un cliente real — el admin
# real se crea con `python init_db.py` después de desplegar (ver el
# runbook, paso "Confirma el certificado y crea el admin real").
COPY database/sync_fields.sql /docker-entrypoint-initdb.d/02-sync-fields.sql

# Las migraciones van FUERA de /docker-entrypoint-initdb.d/ a propósito.
# Ahí solo se ejecutarían la primera vez que el volumen está vacío, y el
# problema que resuelven es justamente el contrario: una base que YA existe
# y se quedó con el esquema de init.sql, sin los ALTER posteriores. Quien
# las aplica es el initContainer del backend (ver k8s/base/backend.yaml),
# que corre en cada arranque contra el Postgres ya levantado.
#
# Esta imagen es postgres:16-alpine, así que ya trae psql y pg_isready —
# no hace falta otra imagen para el initContainer.
COPY database/migrations/ /migrations/
