#!/usr/bin/env bash
# Comando forzado de la llave de PROMOCIONES a clientes (workflow promover.yml).
#
# Se instala en master1 y se ata a UNA llave SSH con `command=` en authorized_keys:
#   command="/home/alanp/promover.sh",restrict,no-pty ssh-ed25519 AAAA... promover-clientes
# La llave NO da shell: solo ejecuta este script, y lo que el cliente pide viaja en
# $SSH_ORIGINAL_COMMAND con el formato  "<modo> <namespace>"  y nada mas.
#
#   respaldo    <ns>   pg_dump de postgres-0 y comprobacion de que quedo completo
#   sincronizar <ns>   recibe por stdin un tar.gz con k8s/base, k8s/components y
#                      k8s/overlays/<ns>, lo VALIDA y reemplaza la copia del servidor
#   aplicar     <ns>   kubectl apply -k del overlay y espera el rollout
#   verificar   <ns>   pods, esquema de la base y sitios; falla si algo esta mal
#
# POR QUE TANTA VALIDACION: `sincronizar` hace que lo que llegue por SSH se aplique al
# cluster con permisos de administrador. Quien controle la llave podria intentar aplicar
# manifiestos arbitrarios. Por eso, antes de tocar nada, el script renderiza el overlay y
# rechaza: tipos de recurso fuera de la lista, recursos de otro namespace, imagenes que no
# sean las de ghcr.io/tyakxa o rabbitmq, hostPath fuera de la carpeta de fotos y contenedores
# privilegiados o con red del nodo. Cualquier cambio a estas listas pasa por PR (esta ruta
# esta en CODEOWNERS) y se vuelve a instalar a mano en el servidor.
#
# Archivo de namespaces permitidos (uno por linea, lo mantiene quien administra el servidor):
#   /home/alanp/promover.permitidos
set -euo pipefail

K8S=/home/alanp/tyakxa_tny/k8s
PERMITIDOS=/home/alanp/promover.permitidos
RESPALDOS=/home/alanp/respaldos_promover
PREVIOS=/home/alanp/promover_k8s_previo
BITACORA=/home/alanp/promover.log
LOCK=/home/alanp/.promover.lock
MAX_BYTES=$((20 * 1024 * 1024))

KINDS_OK=" CronJob Deployment Ingress Namespace PersistentVolumeClaim Service StatefulSet "
IMAGENES_OK='^(ghcr\.io/tyakxa/tyakxa-tny-(backend|db-init|frontend|worker)|rabbitmq):'
HOSTPATH_OK='^/home/infra-k8s/imagenes/'

export KUBECONFIG="$HOME/.kube/config"
export PATH="$HOME/bin:$PATH"

die() { echo "ERROR: $*" >&2; exit 1; }

# --- 1. que se pidio ----------------------------------------------------------
pedido="${SSH_ORIGINAL_COMMAND:-}"
modo=""; ns=""; resto=""
read -r modo ns resto <<<"$pedido" || true
[ -z "$resto" ] || die "argumentos de mas"
case "$modo" in
  respaldo|sincronizar|aplicar|verificar) ;;
  *) die "modo no permitido: '$modo'" ;;
esac
[[ "$ns" =~ ^[a-z0-9]([a-z0-9-]{0,40}[a-z0-9])?$ ]] || die "namespace invalido: '$ns'"
[ -f "$PERMITIDOS" ] || die "falta $PERMITIDOS"
grep -qxF -- "$ns" "$PERMITIDOS" || die "namespace no permitido: '$ns'"

# Una promocion a la vez en todo el servidor.
exec 9>"$LOCK"
flock -n 9 || die "hay otra promocion en curso"

echo "$(date -u +%FT%TZ) $modo $ns desde ${SSH_CONNECTION%% *}" >> "$BITACORA" || true
echo "== $modo $ns ($(date -u +%FT%TZ))"

# --- 2. modos -----------------------------------------------------------------
respaldo() {
  mkdir -p "$RESPALDOS"; chmod 700 "$RESPALDOS"
  local dump sello
  sello="$(date -u +%Y%m%d_%H%M%S)"
  dump="$RESPALDOS/${ns}_${sello}.sql"
  # Las variables se expanden DENTRO del pod (comillas simples a proposito).
  # shellcheck disable=SC2016
  if ! kubectl -n "$ns" exec postgres-0 -- sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$dump"; then
    rm -f "$dump"; die "fallo el pg_dump"
  fi
  tail -n 8 "$dump" | grep -q "PostgreSQL database dump complete" \
    || { rm -f "$dump"; die "respaldo incompleto (sin la linea final de pg_dump)"; }
  [ "$(stat -c %s "$dump")" -gt 1024 ] || { rm -f "$dump"; die "respaldo sospechosamente chico"; }
  echo "respaldo ok: $dump ($(du -h "$dump" | cut -f1), $(wc -l < "$dump") lineas)"
}

sincronizar() {
  local stage; stage="$(mktemp -d /home/alanp/promover_stage.XXXXXX)"
  # shellcheck disable=SC2064
  trap "rm -rf '$stage'" EXIT
  mkdir -p "$stage/x"

  # Tamano: se lee un byte de mas para saber si se pasa.
  head -c $((MAX_BYTES + 1)) > "$stage/in.tgz"
  [ "$(stat -c %s "$stage/in.tgz")" -le "$MAX_BYTES" ] || die "el paquete excede $MAX_BYTES bytes"
  [ -s "$stage/in.tgz" ] || die "paquete vacio"

  # Rutas: solo las tres permitidas, sin absolutas ni '..'.
  local p
  while IFS= read -r p; do
    [[ "$p" != /* && "$p" != *..* ]] || die "ruta no permitida en el paquete: $p"
    [[ "$p" =~ ^k8s/(base|components|overlays/$ns)(/|$) ]] || die "ruta fuera de lo permitido: $p"
  done < <(tar -tzf "$stage/in.tgz")
  # Tipos: solo archivos y carpetas (nada de enlaces, dispositivos ni fifos).
  local tipos
  tipos="$(tar -tvzf "$stage/in.tgz" | cut -c1 | sort -u | tr -d '\n')"
  [[ "$tipos" =~ ^[-d]+$ ]] || die "el paquete trae enlaces u otros tipos de archivo: '$tipos'"

  tar -xzf "$stage/in.tgz" -C "$stage/x" --no-same-owner --no-same-permissions
  local overlay="$stage/x/k8s/overlays/$ns"
  [ -f "$overlay/kustomization.yaml" ] || die "el paquete no trae overlays/$ns/kustomization.yaml"

  # Render y revision del contenido ANTES de tocar la copia del servidor.
  local render; render="$(kubectl kustomize "$overlay")" || die "kustomize no pudo renderizar el overlay"
  local malos=""
  local kind rns rname
  while IFS='|' read -r kind rns rname; do
    [ -n "$kind" ] || continue
    if [[ "$KINDS_OK" != *" $kind "* ]]; then malos+=$'\n'"  tipo no permitido: $kind $rname"; continue; fi
    if [ "$kind" = Namespace ]; then
      [ "$rname" = "$ns" ] || malos+=$'\n'"  Namespace distinto del permitido: $rname"
    else
      [ "$rns" = "$ns" ] || malos+=$'\n'"  $kind/$rname en namespace '$rns' (debe ser '$ns')"
    fi
  done < <(printf '%s\n' "$render" | yq -N '.kind + "|" + (.metadata.namespace // "-") + "|" + .metadata.name')

  local img
  while IFS= read -r img; do
    [[ "$img" =~ $IMAGENES_OK ]] || malos+=$'\n'"  imagen no permitida: $img"
  done < <(printf '%s\n' "$render" | grep -E '^[[:space:]]*(-[[:space:]]+)?image:' | sed -E 's/^[[:space:]]*(-[[:space:]]+)?image:[[:space:]]*//; s/["'"'"']//g')

  local hp
  while IFS= read -r hp; do
    [[ "$hp" =~ $HOSTPATH_OK ]] || malos+=$'\n'"  hostPath no permitido: $hp"
  done < <(printf '%s\n' "$render" | grep -A2 'hostPath:' | awk '/path:/{print $2}')

  if printf '%s\n' "$render" | grep -Eq '(privileged|hostNetwork|hostPID|hostIPC):[[:space:]]*true'; then
    malos+=$'\n'"  contenedor privilegiado o con red/PID del nodo"
  fi
  [ -z "$malos" ] || die "el overlay no pasa la validacion:$malos"
  echo "validacion ok: $(printf '%s\n' "$render" | yq -N '.kind' | grep -c .) recursos, namespace $ns"

  # Comparacion con la copia del servidor. Un archivo que SOLO existe alli se perderia al
  # reemplazar: se aborta y se pide resolverlo (commitearlo al repo o retirarlo).
  local d actual nuevo solo
  for d in base components "overlays/$ns"; do
    actual="$K8S/$d"; nuevo="$stage/x/k8s/$d"
    [ -d "$nuevo" ] || die "el paquete no trae $d"
    if [ -d "$actual" ]; then
      solo="$(diff -rq "$actual" "$nuevo" | grep -F "Only in $actual" || true)"
      [ -z "$solo" ] || die "hay archivos que solo existen en el servidor (se perderian):
$solo"
      echo "diferencias en $d: $(diff -rq "$actual" "$nuevo" | grep -c . || true) archivo(s)"
    else
      echo "diferencias en $d: carpeta nueva"
    fi
  done

  # Respaldo de lo que se va a reemplazar, y reemplazo.
  local sello dest; sello="$(date -u +%Y%m%d_%H%M%S)"; dest="$PREVIOS/${ns}_$sello"
  for d in base components "overlays/$ns"; do
    actual="$K8S/$d"; nuevo="$stage/x/k8s/$d"
    if [ -d "$actual" ]; then
      mkdir -p "$dest/$(dirname "$d")"; cp -a "$actual" "$dest/$d"
      mv "$actual" "$actual.viejo"
    fi
    mkdir -p "$(dirname "$actual")"
    cp -a "$nuevo" "$actual"
    rm -rf "$actual.viejo"
  done
  echo "sincronizado. copia previa en $dest"
}

aplicar() {
  [ -d "$K8S/overlays/$ns" ] || die "no existe $K8S/overlays/$ns"
  kubectl apply -k "$K8S/overlays/$ns" | grep -v unchanged || true
  local d
  for d in backend celery-worker celery-beat frontend; do
    if kubectl -n "$ns" get deploy "$d" >/dev/null 2>&1; then
      kubectl -n "$ns" rollout status "deploy/$d" --timeout=420s || die "fallo el rollout de $d"
    fi
  done
  kubectl -n "$ns" rollout status statefulset/postgres --timeout=300s 2>/dev/null || true
  echo "aplicado"
}

verificar() {
  local fallo=0
  echo "-- imagenes"
  kubectl -n "$ns" get deploy -o custom-columns=NAME:.metadata.name,IMG:.spec.template.spec.containers[0].image,LISTOS:.status.readyReplicas,DESEADOS:.spec.replicas --no-headers
  local nolisto
  nolisto="$(kubectl -n "$ns" get deploy -o yaml | yq -N '.items[] | select((.status.readyReplicas // 0) != .spec.replicas) | .metadata.name')"
  if [ -n "$nolisto" ]; then echo "  deployments no listos: $nolisto"; fallo=1; fi

  echo "-- pods"
  kubectl -n "$ns" get pods --no-headers | grep -v Completed || true
  # Los pods de los jobs de respaldo (pg-backup-*) se ignoran: uno viejo en Error no es de esta promocion.
  if kubectl -n "$ns" get pods --no-headers | grep -v '^pg-backup' | grep -E 'CrashLoopBackOff|Error|ImagePullBackOff|ErrImagePull|CreateContainerConfigError'; then
    echo "  hay pods en mal estado"; fallo=1
  fi

  echo "-- migraciones (db-migrate)"
  local pod; pod="$(kubectl -n "$ns" get pods --no-headers | awk '/^backend-/{print $1; exit}')"
  if [ -n "$pod" ]; then
    local m; m="$(kubectl -n "$ns" logs "$pod" -c db-migrate 2>&1 | grep -E 'ERROR|FATAL|esquema' | tail -n 5 || true)"
    echo "$m"
    echo "$m" | grep -q 'esquema al dia' || { echo "  no aparece 'esquema al dia'"; fallo=1; }
    if echo "$m" | grep -qE 'ERROR|FATAL'; then fallo=1; fi
  else
    echo "  no hay pod backend"; fallo=1
  fi

  echo "-- sitios"
  local h c1 c2
  while read -r h; do
    [ -n "$h" ] || continue
    c1="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "https://$h/" || true)"
    c2="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "https://$h/api/health" || true)"
    echo "$h  /=$c1  /api/health=$c2"
    case "$c1" in 2??|3??) ;; *) fallo=1 ;; esac
    case "$c2" in 2??|3??) ;; *) fallo=1 ;; esac
  done < <(kubectl -n "$ns" get ingress -o jsonpath='{range .items[*]}{range .spec.rules[*]}{.host}{"\n"}{end}{end}' | sort -u)

  [ "$fallo" -eq 0 ] || die "la verificacion encontro problemas"
  echo "verificacion ok"
}

"$modo"
echo "== RESULTADO: OK ($modo $ns)"
