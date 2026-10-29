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
7. **Cuando Alan lo haya integrado**, trae `origin/initAlan` a tu rama, copia tu
   `k8s/` a tu home en el VPS con `scp` y aplica:
   `kubectl apply -k k8s/overlays/<cliente>-<env>`. Confirma
   con `kubectl -n <cliente>-<env> rollout status` de `backend`, `celery-worker`,
   `celery-beat` y `frontend`.
8. **Activa la contraseña real del admin, antes de exponer el dominio.**
   `init.sql` siembra `admin1` con un hash temporal público y `init_db.py` lo
   reemplaza por `BOOTSTRAP_ADMIN_PASSWORD` del Secret:
   `kubectl -n <cliente>-<env> exec -it deploy/backend -- python init_db.py`.
   Confirma en los logs del primer arranque que se aplicó (en imágenes
   anteriores al 20 oct el hash público se quedaba tal cual).
9. **Certificado**: empieza con `letsencrypt-staging` (ya viene así en la
   plantilla); cuando el certificado salga `READY=True`, cambia a
   `letsencrypt-prod`, commitea y vuelve a aplicar.

### Dónde cae el cliente

La plantilla trae un parche `nodeSelector: tier: big`. Producción y servicios
pesados van en `big` (master1 o master4). Nunca volúmenes nuevos en master2 ni
master3. El `base/` no fija nodo y los pods no se rebalancean solos: sin ese
parche un volumen `local-path` queda atado al nodo donde nazca. Los overlays
anteriores a esta plantilla no lo traen todavía (`adser-prod` fija su propio
nodo por sus fotos).

### Secrets (no viven en el repo)

- `ghcr-pull-secret`: lo crea cada quien con **su** token clásico de GitHub
  (`read:packages`), de una cuenta que vea los paquetes `tyakxa-tny-*`; con una
  cuenta que no los ve da 403. Los tokens vencen: anota la fecha.
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
  superior; si no se pone, no hay badge) y `STAMPING_PROVIDER`. Esta última
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
