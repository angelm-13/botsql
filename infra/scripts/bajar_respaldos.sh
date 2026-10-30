#!/usr/bin/env bash
# Corre en master1 (lo lanza bajar_respaldos.ps1 desde la PC de Alan).
#
# Para cada ambiente: monta el PVC `pg-backups` en un pod temporal (queda en el nodo
# donde vive el volumen, que casi nunca es master1), copia el ULTIMO .sql.gz a
# ~/respaldos_para_bajar/<ambiente>/, lo verifica (gzip -t y conteo de tablas) y borra
# el pod. El original sigue en el clúster; esto solo saca una copia.
#
# Uso:  bash bajar_respaldos.sh [ambiente ...]
#       (sin argumentos: los cuatro ambientes con respaldo)
set -u
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
DEST="$HOME/respaldos_para_bajar"
POD=pg-backups-bajar
if [ "$#" -gt 0 ]; then AMBIENTES=("$@"); else AMBIENTES=(tyakxa-dev torredigital-prod comala-prod adser-prod); fi

rm -rf "$DEST"; mkdir -p "$DEST"
fallas=0
resumen=()

for ns in "${AMBIENTES[@]}"; do
  echo "== $ns"
  img=$(kubectl -n "$ns" get cronjob pg-backup -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}' 2>/dev/null)
  if [ -z "$img" ]; then echo "   sin CronJob pg-backup: se omite"; fallas=$((fallas+1)); resumen+=("$ns: SIN RESPALDO CONFIGURADO"); continue; fi

  kubectl -n "$ns" delete pod "$POD" --ignore-not-found >/dev/null 2>&1
  # Sin priorityClassName a proposito: es un pod de segundos, y activeDeadlineSeconds
  # lo mata solo si algo se cuelga.
  cat <<EOF | kubectl -n "$ns" apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: $POD
spec:
  restartPolicy: Never
  activeDeadlineSeconds: 300
  enableServiceLinks: false
  containers:
    - name: bajar
      image: $img
      command: ["sleep", "280"]
      resources:
        requests: { cpu: 10m, memory: 16Mi }
        limits: { cpu: 100m, memory: 64Mi }
      volumeMounts:
        - { name: backups, mountPath: /backups, readOnly: true }
  volumes:
    - name: backups
      persistentVolumeClaim: { claimName: pg-backups }
EOF

  if ! kubectl -n "$ns" wait --for=condition=Ready "pod/$POD" --timeout=120s >/dev/null 2>&1; then
    echo "   el pod no arranco (revisar: kubectl -n $ns describe pod $POD)"
    kubectl -n "$ns" delete pod "$POD" --ignore-not-found >/dev/null 2>&1
    fallas=$((fallas+1)); resumen+=("$ns: FALLO (pod no arranco)"); continue
  fi

  ultimo=$(kubectl -n "$ns" exec "$POD" -- sh -c 'ls -t /backups/*.sql.gz 2>/dev/null | head -1' </dev/null)
  if [ -z "$ultimo" ]; then
    echo "   no hay respaldos en el volumen"
    kubectl -n "$ns" delete pod "$POD" --ignore-not-found >/dev/null 2>&1
    fallas=$((fallas+1)); resumen+=("$ns: FALLO (volumen sin respaldos)"); continue
  fi

  mkdir -p "$DEST/$ns"
  out="$DEST/$ns/$(basename "$ultimo")"
  # exec + cat (sin kubectl cp) para no depender de tar dentro de la imagen.
  kubectl -n "$ns" exec "$POD" -- cat "$ultimo" </dev/null > "$out"
  kubectl -n "$ns" delete pod "$POD" --ignore-not-found >/dev/null 2>&1

  if gzip -t "$out" 2>/dev/null; then
    tablas=$(zcat "$out" | grep -c '^CREATE TABLE')
    tam=$(du -h "$out" | cut -f1)
    echo "   $(basename "$out"): $tam, $tablas tablas, integridad OK"
    resumen+=("$ns: $(basename "$out") ($tam, $tablas tablas)")
  else
    echo "   $(basename "$out"): ARCHIVO CORRUPTO, se descarta"
    rm -f "$out"; fallas=$((fallas+1)); resumen+=("$ns: FALLO (archivo corrupto)")
  fi
done

echo
echo "== Resumen"
printf '%s\n' "${resumen[@]}"
# exit explicito: PowerShell 5.1 agrega un CR+LF al final del pipe y bash lo
# ejecutaria como comando ("\r: command not found"), falsificando el codigo de salida.
if [ "$fallas" -ne 0 ]; then echo "HUBO $fallas FALLA(S)"; exit 1; fi
exit 0
