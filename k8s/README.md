# k8s/ — cómo se despliega un cliente del ERP

Para quien va a dar de alta o actualizar clientes. Si es tu primer despliegue,
lee antes la guía de onboarding del clúster (usuario en el VPS, llaves, secrets,
errores comunes). Esto cubre solo lo propio de este repo.

## Cómo llega el código al clúster

- **Todo push a `initAlan` construye imágenes y despliega solo a `tyakxa-dev`**
  (sistema-test.torredigital.mx). Es el ambiente de pruebas: ahí se valida todo
  primero. El workflow (`.github/workflows/build-images.yml`) corre en cada push,
  aunque solo hayas tocado un overlay; tarda unos minutos y es normal. Un push a
  tu rama personal no construye nada: las imágenes solo salen de `initAlan` (o
  `main`).
- **Los clientes reales se promueven a mano**: se edita el tag en su overlay, se
  commitea y se aplica en el VPS. Ahí está el freno real de producción.
- Después de cada push el bot agrega un commit `deploy(tyakxa-dev): actualizar
  a <sha>`. No es un conflicto: al trabajar en tu rama, trae `origin/initAlan`
  (`git fetch` y `git rebase origin/initAlan`) antes de seguir.
- El clúster solo hace `pull` de imágenes (`ghcr.io/tyakxa`). No hay código
  fuente en el servidor, solo estos manifiestos.

## Estructura

```
k8s/
  base/                  el stack completo (postgres, rabbitmq, backend, frontend, ingress)
  components/
    respaldo-postgres/   CronJob de respaldo diario (03:30); opcional por overlay
  overlays/
    _template/           punto de partida de un cliente nuevo
    <cliente>-<env>/     un overlay por cliente: namespace, tags de imagen, dominio
deploy/clients.yaml      qué clientes activos tienen imagen de frontend propia
```

`base/` y `components/` afectan a **todos** los clientes: no se cambian sin
hablarlo con Alan. Cada quien toca solo su carpeta de overlay.

## Dar de alta un cliente nuevo

1. **Registra el cliente en `deploy/clients.yaml`** (`name`, `env`,
   `api_base_url: ""`) en tu rama y avisa a Alan. Él la integra a `initAlan` y
   hace push (con varios clientes, una sola vez), porque las imágenes solo se
   construyen desde ahí. Se construye una imagen de frontend por cliente
   (`<sha>-<cliente>-<env>`), y solo existe para commits que ya incluyen su
   entrada. Espera a que el Actions termine en verde.
2. **Toma el SHA** del commit del bot `deploy(tyakxa-dev): actualizar a <sha>`
   que aparece después de ese build. El bot solo lo publica cuando terminaron
   todas las imágenes, incluida la de tu frontend.
3. **Crea el overlay**: `cp -r k8s/overlays/_template k8s/overlays/<cliente>-<env>`
   y reemplaza `CLIENTE-ENV`, `DOMINIO` y `REEMPLAZAR_SHA` en sus dos archivos.
   Los clientes del ERP usan un solo dominio, `<cliente>.torredigital.mx` (por
   ejemplo `comala.torredigital.mx`); confírmalo con Alan. Verifica el dominio
   con `nslookup`; el DNS (registro A a master1) lo pide Tanya. Los comentarios
   de la plantilla explican cada bloque.
4. **Valida que compila**: `kubectl kustomize k8s/overlays/<cliente>-<env>`
   (debe terminar sin error; revisa que salga tu namespace y tu dominio).
5. **Commit y push a tu rama** (no a `initAlan`), solo de tu overlay y de
   `deploy/clients.yaml`: `git add k8s/overlays/<cliente>-<env> deploy/clients.yaml`.
   Nunca `git add -A`. Avisa a Alan: revisa el diff (debe ser solo tu overlay) y
   decide si lo integra a `initAlan`.
6. **En el VPS**, antes del primer `apply` (ver "Secrets" más abajo): crea el
   namespace, el `ghcr-pull-secret`, parchea el ServiceAccount `default` y crea
   `app-secrets`.
7. **Cuando Alan lo haya integrado**, trae `origin/initAlan` a tu rama y copia
   al VPS `base/`, `components/` y tu overlay. Copia también `base/` y
   `components/`: el pipeline no los sincroniza, y una copia vieja ahí aplica
   manifiestos desactualizados. Desde PowerShell **en tu máquina** (no en la
   sesión SSH; el destino es tu copia de `k8s/` en el VPS, `tyakxa_tny/k8s/`
   en el home de Alan):
   ```powershell
   scp -r k8s\base k8s\components <usuario>@168.231.67.33:tyakxa_tny/k8s/
   scp -r k8s\overlays\<cliente>-<env> <usuario>@168.231.67.33:tyakxa_tny/k8s/overlays/
   ```
   En el VPS: `kubectl apply -k ~/tyakxa_tny/k8s/overlays/<cliente>-<env>`.
   Confirma con `kubectl -n <cliente>-<env> rollout status` de `backend`,
   `celery-worker`, `celery-beat` y `frontend`. Es normal que `postgres-0` muestre
   **un reinicio** en una base nueva (ver "Comprobaciones finales").
8. **Confirma que la contraseña real del admin se aplicó, antes de exponer el
   dominio.** `init.sql` siembra `admin1` con un hash temporal público y el
   backend lo reemplaza por `BOOTSTRAP_ADMIN_PASSWORD` del Secret en su primer
   arranque; no hace falta correr `init_db.py` a mano. Compruébalo en los logs:
   `kubectl -n <cliente>-<env> logs deploy/backend | grep -i bootstrap` debe
   decir `set from BOOTSTRAP_ADMIN_PASSWORD (admin1)` (en imágenes anteriores
   al 20 oct el hash público se quedaba tal cual).
9. **Certificado**: empieza con `letsencrypt-staging` (ya viene así en la
   plantilla). `kubectl -n <cliente>-<env> get certificate` con `READY=True`
   **solo dice que el de staging se emitió**: no distingue staging de prod. Cambia
   a `letsencrypt-prod` en `ingress-single-origin.yaml`, commitea, copia ese
   archivo con `scp` y vuelve a aplicar. Cert-manager reemite solo en uno o dos
   minutos. Verifica desde Windows, **sin `-k`**:
   `curl.exe -sI https://<dominio>`. Si contesta `200` sin error de certificado,
   ya es el real; si falla por certificado, sigue siendo staging. Solo si tras
   unos 5 minutos sigue así, borra el Secret del certificado
   (`kubectl -n <cliente>-<env> delete secret <cliente>-<env>-tls`) y
   cert-manager lo regenera.

### Dónde cae el cliente

La plantilla trae un parche `nodeSelector: tier: big`. Producción y servicios
pesados van en `big` (master1 o master4). Nunca volúmenes nuevos en master2 ni
master3. El `base/` no fija nodo y los pods no se rebalancean solos: sin ese
parche un volumen `local-path` queda atado al nodo donde nazca. Los overlays
anteriores a esta plantilla no lo traen todavía (`adser-prod` fija su propio
nodo por sus fotos).

**Decide el nodo al dar de alta, no después.** Con `tier: big` el scheduler elige
entre master1 y master4, y suele caer en master1, que ya es la única puerta de
todo el tráfico (ingress) y aloja a otros clientes. La regla del clúster es
repartir la producción entre los dos. Para fijar uno, agrega la línea
`kubernetes.io/hostname: k3s-master4` junto a `tier: big` en **los dos** parches
de nodo del overlay (Deployment y StatefulSet); `aai-prod` es el ejemplo.
Cambiarlo más tarde exige migrar datos (dump y un
PVC nuevo), porque un volumen `local-path` queda atado al nodo donde nació.
Antes de elegir, mira cuánto hay: `kubectl top nodes` (uso real) y
`kubectl describe node k3s-master4 | grep -A8 "Allocated resources"` (reserva).

### Secrets (no viven en el repo)

- `ghcr-pull-secret`: lo crea cada quien con **su** token clásico de GitHub
  (`read:packages`), de una cuenta que vea los paquetes `tyakxa-tny-*`; con una
  cuenta que no los ve da 403. Los tokens vencen: anota la fecha. Alternativa
  más simple, sin tocar ningún token: **cópialo de un namespace que ya lo tenga**
  (necesita `jq` en el VPS; hereda el vencimiento de ese token):
  `kubectl -n comala-prod get secret ghcr-pull-secret -o json | jq 'del(.metadata.namespace,.metadata.resourceVersion,.metadata.uid,.metadata.creationTimestamp,.metadata.ownerReferences,.metadata.annotations)' | kubectl -n <ns> apply -f -`
- `app-secrets`: se escribe en el servidor con `nano`, nunca por chat ni
  copiado desde Windows (los saltos de línea CRLF rompen contraseñas). Claves
  confirmadas en la práctica (según el Runbook): `DB_HOST` (= `postgres`),
  `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `RABBITMQ_DEFAULT_USER`,
  `RABBITMQ_DEFAULT_PASS`, `CELERY_BROKER_URL`, `JWT_SECRET`, `SECRET_KEY`,
  `MFA_ENCRYPTION_KEY`, `PAC_ENCRYPTION_KEY` y `BOOTSTRAP_ADMIN_PASSWORD`. Si
  falta una, el error de conexión es distinto por cada llave. Los secretos se
  generan en el servidor con `openssl rand`.
  Con `APP_ENV=production` (lo fija el base) el backend **no arranca sin
  `CORS_ORIGINS`** (el dominio completo, `https://<dominio>`). Además,
  `JWT_SECRET` y `SECRET_KEY` deben tener 32 o más caracteres, y
  `BOOTSTRAP_ADMIN_PASSWORD`, 12 o más (con `openssl rand -hex 16` y `-hex 32`
  se cumple).
  Opcionales: `DEPLOYMENT_LABEL` (el nombre que sale como badge en la barra
  superior; si no se pone, no hay badge) y `STAMPING_PROVIDER`. El badge se
  agrega con `kubectl -n <ns> patch secret app-secrets -p
  '{"stringData":{"DEPLOYMENT_LABEL":"<Nombre>"}}'` y, si ya había pods,
  `kubectl -n <ns> rollout restart deploy/backend`. `STAMPING_PROVIDER`
  **no la pongas vacía**: una variable definida pero vacía rompe el timbrado con
  `Unsupported STAMPING_PROVIDER` en vez del 503 limpio; si no se va a usar, no
  la incluyas. La cuenta del PAC se puede configurar después desde el sistema,
  y esa configuración manda sobre la variable. Para contrastar con un cliente
  real, copia los **nombres**: `kubectl -n comala-prod describe secret
  app-secrets` (solo nombres y tamaños; nunca `get secret -o yaml`). Detalle y
  trampas en el Runbook, secciones «Secretos» y «Primer despliegue».
- Namespace nuevo: engancha el pull secret al ServiceAccount `default` o los
  pods quedan en `ImagePullBackOff`:
  `kubectl patch serviceaccount default -n <ns> -p '{"imagePullSecrets":[{"name":"ghcr-pull-secret"}]}'`

## Comprobaciones finales de un alta

- `kubectl -n <ns> get pods -o wide`: los seis (`backend`, `celery-beat`,
  `celery-worker`, `frontend`, `postgres-0`, `rabbitmq`) en `1/1 Running` y en el
  nodo que elegiste.
- Volúmenes en el nodo correcto (el filtro por namespace; la columna `CLAIM` solo
  trae el nombre del PVC): `kubectl get pv -o custom-columns=CLAIM:.spec.claimRef.name,NS:.spec.claimRef.namespace,NODO:.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0] | grep -E "NS|<ns>"`.
- Entra al dominio como `admin1` con `BOOTSTRAP_ADMIN_PASSWORD` y confirma el
  badge si pusiste `DEPLOYMENT_LABEL` (Ctrl+F5 si no sale).

**Es normal, no es una falla**:
- `postgres-0` con **1 reinicio** en una base nueva: `02-sync-fields.sql` (de la
  imagen `db-init`) falla con `column "data_type" of relation "field" does not
  exist` y el contenedor sale; al volver, el volumen ya no está vacío y arranca.
  El catálogo `field` lo siembra después el backend (`init_db.py`). Si el reinicio
  se repite o el pod no llega a `Running`, entonces sí hay un problema: revisa
  `kubectl -n <ns> logs postgres-0 --previous`.
- El PVC `pg-backups` en `Pending`: `local-path` no crea el volumen hasta que un
  pod lo usa, y el primer uso es el CronJob de las 03:30. Confirma al día
  siguiente que pasó a `Bound` y que el job terminó. Ese respaldo vive dentro del
  mismo clúster.

## Promover una versión a un cliente que ya existe

**Esto lo hace solo Alan.** Quien da de alta ambientes no cambia ni aplica
versiones en clientes que ya existen; esta sección es referencia del proceso.

1. Elige el SHA que ya probó `tyakxa-dev` (el del último commit del bot en verde).
2. Cambia los 4 `newTag` de tu overlay (el del frontend lleva el sufijo
   `-<cliente>-<env>`).
3. Commit y push a tu rama; Alan lo revisa y lo integra a `initAlan`.
4. Ya integrado, `scp` del `kustomization.yaml` actualizado a tu copia en el
   VPS, `kubectl apply -k` y `rollout status`.

En un cliente **en producción** haz antes un respaldo (`pg_dump`) y avisa a
Alan: el backend usa estrategia `Recreate` y hay unos minutos sin servicio. El
ejemplo completo está en `docs/despliegues/2026-09-30_promocion_adser_prod.md`.
No uses `kubectl set image`: cambia el clúster pero no el archivo, y el
siguiente `apply` revierte la versión.

## Reglas para trabajar en equipo

- **Trabaja en tu propia rama, creada desde `initAlan`**
  (`git switch -c <tu-rama> origin/initAlan`). No pushees a `initAlan`: Alan
  revisa y decide qué integra, como con cualquier otro cambio. Commits chicos y
  solo de despliegue (tu overlay y tu entrada en `deploy/clients.yaml`). Si
  necesitas cambiar código de la app, `base/` o `components/`, no lo mezcles con
  los commits de despliegue y avisa a Alan.
- Antes de aplicar, trae `origin/initAlan` a tu rama (`git fetch` y `git rebase
  origin/initAlan`), para no aplicar manifiestos desactualizados.
- Tu trabajo es dar de alta ambientes nuevos. No cambies ni apliques versiones en
  clientes que ya existen: eso lo hace Alan.
- Aplica solo tu overlay. El clúster no te impide aplicar sobre el de otro
  cliente; es una regla de equipo.
- Un push no revisado va directo a sistema-test. Lo que no esté probado en local
  (Docker Compose) no se sube a `initAlan`.

## La copia del VPS

`/home/alanp/tyakxa_tny/k8s/` es una copia plana, no un repo git, y vive en el
home de Alan (permisos `700`). Los demás usan su propia copia en su home. Los
archivos que se reemplazan por `scp` dejan respaldos `.bak*`: no pertenecen al
repo. Detalle del procedimiento en `ARQUITECTURA_TYAKXA_TNY.md`, sección 7.1.

## Por decidir (Alan)

- **PriorityClass** de cada cliente nuevo: las clases no están en el repo y el
  overlay solo funciona si la clase existe. La plantilla trae esos parches
  comentados.
- **Cómo recibe cada persona su copia de `k8s/`** en el VPS: hoy es `scp`; un
  clon sparse por HTTPS pediría token (las deploy keys están deshabilitadas por
  la organización).
- **Nombre de las ramas de despliegue** por persona (por ejemplo `initAngm` e
  `initAngb`) y qué hacer con las ramas viejas, mientras tengan commits sin
  integrar.
- **Dos subdominios** (app + api-app): el `base/ingress.yaml` lo soporta y la
  versión anterior de la plantilla lo parchaba; está en
  `git log -- k8s/overlays/_template`.
