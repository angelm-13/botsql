<#
.SYNOPSIS
  Baja a esta PC el ultimo respaldo de Postgres de cada ambiente (respaldo "offline").

.DESCRIPTION
  Ejecuta bajar_respaldos.sh en master1 (pods temporales que montan cada PVC
  `pg-backups`), verifica cada archivo y lo copia a $Destino\<ambiente>\.
  Los originales siguen en el cluster; esto solo saca una copia fuera de el.
  Hace falta la llave SSH cargada (ssh-add), igual que para cualquier scp al VPS.

.EXAMPLE
  .\bajar_respaldos.ps1                          # los cuatro ambientes
  .\bajar_respaldos.ps1 -Ambientes tyakxa-dev    # solo uno (para probar)
#>
param(
  [string[]]$Ambientes = @("tyakxa-dev", "torredigital-prod", "comala-prod", "adser-prod"),
  [string]$Servidor = "168.231.67.33",
  [string]$Destino = "C:\Users\TDW2\respaldos_cluster"
)

$sh = Join-Path $PSScriptRoot "bajar_respaldos.sh"
if (-not (Test-Path $sh)) { Write-Error "No encuentro $sh"; exit 1 }

Write-Host "1/3 Sacando copias en master1..."
# Se quitan los CR (Windows) para que bash no truene; el script viaja por stdin.
(Get-Content -Raw $sh) -replace "`r", "" | ssh $Servidor "bash -s -- $($Ambientes -join ' ')"
$resultado = $LASTEXITCODE

Write-Host "2/3 Copiando a $Destino ..."
New-Item -ItemType Directory -Force $Destino | Out-Null
scp -r "${Servidor}:respaldos_para_bajar/*" "$Destino\"
if ($LASTEXITCODE -ne 0) {
  Write-Error "El scp fallo. Las copias siguen en master1 (~/respaldos_para_bajar); no se borro nada."
  exit 1
}
# Solo son copias de paso: los originales siguen en el cluster.
ssh $Servidor "rm -rf ~/respaldos_para_bajar"

Write-Host "3/3 Ultimo respaldo por ambiente en esta PC:"
foreach ($a in $Ambientes) {
  $d = Join-Path $Destino $a
  if (Test-Path $d) {
    Get-ChildItem $d -Filter *.sql.gz | Sort-Object LastWriteTime -Descending | Select-Object -First 1 |
      ForEach-Object { "{0,-18} {1,-45} {2,6:N2} MB" -f $a, $_.Name, ($_.Length / 1MB) }
  }
}
if ($resultado -ne 0) { Write-Warning "El script de master1 reporto fallas: revisa el resumen de arriba." }
