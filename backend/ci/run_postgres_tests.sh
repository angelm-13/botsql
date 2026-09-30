#!/usr/bin/env bash
# Corre las pruebas exclusivas de PostgreSQL contra el Postgres del
# docker-compose local, en dos grupos y cada uno en su propia base desechable.
#
# Por que existe: con TESTING=1 y sin TEST_DATABASE_URL la suite corre en
# SQLite, y todo archivo que mira `engine.dialect.name == "postgresql"` (o
# `!=`, como test_inventory_concurrency.py) se SALTA en silencio -- entre ellos todas las pruebas de KPIs. Nada las
# corre de forma automatica (el workflow de GitHub solo construye imagenes).
#
# Por que dos grupos, y no una sola corrida: las pruebas exclusivas de
# Postgres vienen en dos sabores incompatibles en una misma base.
#
#   * base_real -- clases `unittest.TestCase` que NO reinician el esquema:
#     necesitan el esquema real (init.sql + migraciones, con sus FK
#     diferibles) y el bootstrap de siempre (user=1, proyect=1, status=1,
#     customer_supplier=1). Ver el comentario al inicio de
#     tests/test_services/test_kpi_ventas_por_empleado.py.
#   * esquema_orm -- clases `BackendTestCase`: cada prueba hace
#     `DROP SCHEMA public CASCADE` y recrea solo lo que declara el ORM
#     (tests/conftest.py, reset_test_database), sin init.sql ni bootstrap.
#
# Juntas en una base, las de esquema_orm borran lo que las de base_real
# necesitan: medido el 2026-09-25, 33 de 60 fallaban solo por el orden.
#
# Uso (desde cualquier carpeta; requiere el stack local arriba y migrado):
#   backend/ci/run_postgres_tests.sh              # todos los archivos de Postgres
#   backend/ci/run_postgres_tests.sh -k kpi       # filtra por nombre, como pytest -k
#   backend/ci/run_postgres_tests.sh --copiar-base-local   # base_real = copia de tu base local
#   CONSERVAR_BASES=1 backend/ci/run_postgres_tests.sh   # no borra las bases al final
#
# La base "base_real" es LIMPIA por omision: se crea vacia con database/init.sql
# (que trae el bootstrap: user=1, proyect=1, status=1, customer_supplier=1) y todas
# las migraciones, en el mismo orden que el servicio `db-migrate` de docker-compose.
# Asi no depende de lo que tenga tu base local. Con --copiar-base-local se usa en
# cambio una COPIA (pg_dump) de la base del stack (POSTGRES_DB del servicio db,
# normalmente tyakxa_erp), que esta base nunca se modifica: sirve para probar contra
# datos reales, pero puede fallar si tiene datos demo (vales, usuarios de prueba),
# porque las pruebas esperan contar solo lo que ellas mismas crean. Ambas bases de
# prueba se borran al terminar.
set -euo pipefail

# Opciones propias (se quitan antes de pasar el resto a pytest).
COPIAR_BASE_LOCAL=0
args_pytest=()
for arg in "$@"; do
  if [ "$arg" = "--copiar-base-local" ]; then COPIAR_BASE_LOCAL=1; else args_pytest+=("$arg"); fi
done
set -- ${args_pytest[@]+"${args_pytest[@]}"}

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$RAIZ"

dc() { docker compose "$@"; }

DB_USER="$(dc exec -T db printenv POSTGRES_USER)"
DB_PASSWORD="$(dc exec -T db printenv POSTGRES_PASSWORD)"
BASE_ORIGEN="$(dc exec -T db printenv POSTGRES_DB)"
BASE_REAL="tyakxa_pgtest_base_real"
BASE_ORM="tyakxa_pgtest_esquema_orm"

psql_admin() { dc exec -T db psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -q "$@"; }

limpiar() {
  if [ "${CONSERVAR_BASES:-0}" = "1" ]; then
    echo "run_postgres_tests: se conservan $BASE_REAL y $BASE_ORM (CONSERVAR_BASES=1)"
    return
  fi
  psql_admin -c "DROP DATABASE IF EXISTS $BASE_REAL" -c "DROP DATABASE IF EXISTS $BASE_ORM" >/dev/null 2>&1 || true
}
trap limpiar EXIT

# --- clasificacion automatica ----------------------------------------------
# Un archivo nuevo de Postgres cae solo en su grupo segun su clase base; no
# hay lista que mantener a mano. Un archivo con ambos tipos de clase se
# rechaza: no hay base en la que pueda correr completo.
grupo_real=()
grupo_orm=()
while IFS= read -r archivo; do
  usa_backend=$(grep -cE '^class \w+\(BackendTestCase\)' "backend/$archivo" || true)
  usa_simple=$(grep -cE '^class \w+\((unittest\.)?TestCase\)' "backend/$archivo" || true)
  if [ "$usa_backend" -gt 0 ] && [ "$usa_simple" -gt 0 ]; then
    echo "run_postgres_tests: $archivo mezcla BackendTestCase y unittest.TestCase; separalo en dos archivos." >&2
    exit 2
  elif [ "$usa_backend" -gt 0 ]; then
    grupo_orm+=("$archivo")
  else
    grupo_real+=("$archivo")
  fi
done < <(cd backend && grep -rlE 'dialect\.name (==|!=) "postgresql"' tests --include='*.py' | sort)

# --- bases ---------------------------------------------------------------------
limpiar
psql_admin -c "CREATE DATABASE $BASE_REAL" -c "CREATE DATABASE $BASE_ORM"
if [ "$COPIAR_BASE_LOCAL" = "1" ]; then
  echo "run_postgres_tests: base_real = copia de $BASE_ORIGEN (--copiar-base-local)"
  dc exec -T db sh -c "pg_dump -U '$DB_USER' -d '$BASE_ORIGEN' | psql -U '$DB_USER' -d '$BASE_REAL' -q -v ON_ERROR_STOP=1" >/dev/null
else
  echo "run_postgres_tests: base_real limpia (init.sql + migraciones)"
  # Los NOTICE de las migraciones (reaplicables) son ruido: solo se muestra la salida si algo falla.
  salida=$(dc exec -T db psql -U "$DB_USER" -d "$BASE_REAL" -q -v ON_ERROR_STOP=1 < database/init.sql 2>&1 \
    && dc run --rm --no-deps -T -e PGDATABASE="$BASE_REAL" db-migrate 2>&1) \
    || { echo "$salida" >&2; echo "run_postgres_tests: no se pudo crear la base limpia" >&2; exit 1; }
fi

correr_grupo() {
  local nombre="$1" base="$2"; shift 2
  local archivos=()
  while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do archivos+=("$1"); shift; done
  [ "${1:-}" = "--" ] && shift
  echo "== $nombre (${#archivos[@]} archivos, base $base)"
  dc run --rm --no-deps -T --entrypoint bash \
    -e TESTING=1 -e JWT_SECRET=test-secret -e JWT_SS=test-secret -e MFA_ISSUER="TYAKXA Test" \
    -e TEST_DATABASE_URL="postgresql+psycopg2://$DB_USER:$DB_PASSWORD@db:5432/$base" \
    backend -c 'pip install -q -r requirements-ci.txt >/dev/null 2>&1; pytest -q -p no:cacheprovider "$@"' _ "${archivos[@]}" "$@"
}

estado=0
correr_grupo "base_real" "$BASE_REAL" "${grupo_real[@]}" -- "$@" || estado=$?
correr_grupo "esquema_orm" "$BASE_ORM" "${grupo_orm[@]}" -- "$@" || estado=$?
exit "$estado"
