#!/usr/bin/env bash
#
# Levanta TYAKXA.
#
# Por que ya no levanta nada mas
# ------------------------------
# Este script arrancaba dos proyectos: TYAKXA y el punto de venta, que corria su
# propio backend contra su propia base (`pos_enterprise`). Explicaba con detalle
# por que no se podian fundir en un solo `docker-compose`: los nombres de
# servicio chocaban -- los dos tenian `db`, `backend` y `frontend` -- y los
# volumenes eran del otro proyecto, asi que redeclararlos aqui habria arrancado
# el POS con la base VACIA.
#
# Todo eso dejo de aplicar cuando el punto de venta entro a esta base
# (migracion 20260911100000). Ya no hay un segundo backend que arrancar ni un
# segundo volumen que respetar: el POS es un modulo mas, sus rutas las sirve
# este backend y su catalogo es `product`.
#
# Con `docker compose up -d` habria bastado. El script se queda porque hace lo
# que un `up -d` no hace: comprobar que los servicios RESPONDEN. Un contenedor
# en estado 'Up' no significa que su API conteste, y esa diferencia ya costo un
# rato de busqueda una vez.
#
set -euo pipefail

TYAKXA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> TYAKXA  ($TYAKXA)"
docker compose -f "$TYAKXA/docker-compose.yml" up -d

echo
echo "==> Comprobando"

esperar() {
  local nombre="$1" url="$2" puerto="$3"
  for intento in $(seq 1 30); do
    if curl -fsS -o /dev/null "$url" 2>/dev/null; then
      printf "   %-14s ok  %s\n" "$nombre" "$url"
      return 0
    fi
    sleep 2
  done
  printf "   %-14s NO responde en el %s\n" "$nombre" "$puerto"
  return 1
}

fallo=0
esperar "Backend"  "http://localhost:5001/health" 5001 || fallo=1
esperar "Interfaz" "http://localhost:3001/"       3001 || fallo=1

echo
if [[ $fallo -eq 0 ]]; then
  echo "   El punto de venta entra por la interfaz, en Caja: ya no es un"
  echo "   servicio aparte que haya que arrancar."
fi
exit $fallo
