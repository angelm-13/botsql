# Auditoría técnica del proyecto

## 1. Resumen ejecutivo

Auditoría ejecutada el 16 de agosto de 2026 sobre el estado local de `tyakxa_tny`. Tras la primera remediación, el cálculo ponderado es **50.7/100** y la calificación efectiva es **49.9/100, Riesgo alto**. Aplica el límite máximo de **49.9** por aislamiento de proyecto/tenant incompleto y datos personales o fiscales almacenados sin cifrado de columna.

Se incorporaron controles concretos para ledger de inventario, CFDI XML, ciclo de cotización, vínculo con tareas, portal cliente, importación CSV de estados de cuenta y un puerto de timbrado con fake. La suite backend completa pasa 285/285. No se declara integración total: faltan aislamiento transversal, conciliación bancaria completa, cancelación/descarga Facturama, UI operativa para varias capacidades, Redis, Alembic, Kubernetes y CI.

## 2. Alcance y limitaciones

- Alcance: código, configuración y pruebas locales de `tyakxa_tny`; fuentes ADSER y Cotizador solo para comparación de comportamiento.
- No se conectó a producción ni a Facturama real. `STAMPING_PROVIDER=fake` es el modo seguro previsto para pruebas.
- No se encontraron licencias de proyecto verificables en las fuentes; se reimplementó comportamiento.
- No se instalaron herramientas globales ni dependencias de red.
- `pytest`, Ruff, Black y mypy no están disponibles en el contenedor runtime. Se usó `unittest` para pruebas focales.
- El lint frontend no pudo ejecutarse porque falta `eslint-plugin-react-refresh` en las dependencias del proyecto.
- El downgrade de migraciones no está soportado: el proyecto usa SQL incremental y `create_all`, no Alembic.

## 3. Tablero general

| Grupo | Peso | Calificación | Aporte ponderado | Estado |
|---|---:|---:|---:|---|
| Arquitectura y organización | 10% | 50% | 5.0 | Parcial |
| Backend Flask/Python | 10% | 65% | 6.5 | Parcial |
| Frontend React/Vite | 8% | 50% | 4.0 | Parcial |
| PostgreSQL y persistencia | 10% | 60% | 6.0 | Parcial |
| Autenticación, roles y autorización | 12% | 60% | 7.2 | Parcial |
| Seguridad y cifrado | 15% | 45% | 6.8 | Parcial |
| Pruebas y calidad | 10% | 62.5% | 6.3 | Parcial |
| CI/CD y cadena de suministro | 8% | 25% | 2.0 | Parcial |
| Docker, Kubernetes y despliegue | 7% | 50% | 3.5 | Parcial |
| Observabilidad, Event Log y operación | 5% | 30% | 1.5 | Parcial |
| Documentación, privacidad y recuperación | 5% | 40% | 2.0 | Parcial |
| **Global efectivo** | **100%** | **49.9%** | **49.9** | **Riesgo alto** |

El cálculo es `suma(calificación de grupo × peso) = 50.70`. El límite crítico reduce el resultado efectivo a **49.9**.

## 4. Hallazgos críticos y altos

1. **Crítico: aislamiento tenant no transversal.** Product REST y el JWT interno ya aplican proyecto, pero invoice, task, banca, GraphQL y otros CRUD no fuerzan scope de forma central. Evidencia: `backend/app/utils/auth.py`, `backend/app/routes/product.py`, `backend/app/routes/invoice.py`.
2. **Crítico: PII y datos fiscales sin cifrado de columna.** RFC, SSN, correo y teléfonos se persisten como `String`. Evidencia: `backend/app/models/user.py` y `customer_supplier.py`.
3. **Alto: bootstrap conserva alcance global.** Los administradores de empresa ya consultan ACL; `is_bootstrap_admin` sigue siendo superusuario y requiere restricción operativa y auditoría reforzada. Evidencia: `backend/app/utils/auth.py::_has_entity_permission`.
5. **Alto: TLS, Redis, Kubernetes y CI ausentes.** Compose ofrece NGINX y RabbitMQ, pero no hay Redis, manifiestos Kubernetes ni workflow CI.
6. **Alto: integración Facturama incompleta.** Hay interfaz, fake, sandbox POST, timeout e idempotencia; faltan payload CFDI 4.0 completo, cancelación, descarga XML/PDF y reconciliación persistente.
7. **Alto: estados de cuenta incompletos.** Se importa CSV con hash y movimientos; faltan parsers PDF por banco, matching, conciliación manual/automática y UI.
8. **Alto: inventario sin cobertura vertical suficiente.** El servicio usa bloqueo de fila, idempotencia y evita negativos, pero no pudo validarse con datos locales por ausencia de producto asociado a proyecto; faltan reportes y UI de ledger.

## 5. Resultados detallados por grupo

### Arquitectura y organización

| ID | Control | Estado | Peso interno | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---:|---:|---|---|---|
| ARC-01 | Dominios y application factory | Implementado | 15 | 15 | `backend/app/__init__.py::create_app`; Blueprints por entidad | Medio | Separar dominios en paquetes funcionales |
| ARC-02 | Despliegue independiente de microservicios | No implementado | 15 | 0 | Un solo backend Flask posee todos los datos | Alto | Extraer servicios solo donde exista propiedad de datos clara |
| ARC-03 | Configuración por ambiente | Parcial | 10 | 5 | `docker-compose.yml`, `docker-compose.prod.yml`, variables de entorno | Medio | Añadir configuración test/staging validada |
| ARC-04 | Contratos API/eventos versionados | No implementado | 10 | 0 | No se encontró evidencia en el repositorio | Alto | Introducir `/api/v1` y schemas de eventos |
| ARC-05 | Timeouts, reintentos e idempotencia | Parcial | 15 | 7.5 | `services/stamping.py`, `inventory_service.py` | Alto | Backoff/jitter y circuit breaker |
| ARC-06 | Correlation/causation ID | No implementado | 10 | 0 | No se encontró evidencia en el repositorio | Alto | Middleware de correlación |
| ARC-07 | Health/readiness/liveness | Parcial | 10 | 5 | `routes/health.py`; no revisa dependencias | Medio | Separar probes y comprobar DB/broker |
| ARC-08 | Dockerfile por proceso | Implementado | 15 | 15 | `infra/docker/backend.Dockerfile`, `frontend.Dockerfile`, `worker.Dockerfile` | Bajo | Fijar imágenes por digest |

### Backend Flask/Python

| ID | Control | Estado | Peso interno | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---:|---:|---|---|---|
| BE-01 | Flask, factory y Blueprints | Implementado | 20 | 20 | `backend/app/__init__.py`; `backend/app/routes/` | Bajo | Mantener patrón |
| BE-02 | Servicios y validación | Parcial | 20 | 10 | `services/base_service.py`, `validations/validator.py`, servicios de dominio nuevos | Medio | Schemas explícitos por endpoint |
| BE-03 | Errores globales uniformes | Parcial | 10 | 5 | `utils/errors.py`; respuestas legacy mezcladas | Medio | Unificar contrato error |
| BE-04 | Dependencias fijadas | Implementado | 10 | 10 | `backend/requirements.txt` | Medio | Añadir lock con hashes |
| BE-05 | Logging JSON | No implementado | 10 | 0 | No se encontró evidencia en el repositorio | Alto | Logging estructurado y redacción |
| BE-06 | Gunicorn y debug producción | Implementado | 10 | 10 | `backend/entrypoint.sh` selecciona Gunicorn fuera de development | Medio | Validar `APP_ENV` y workers |
| BE-07 | CORS/rate limit/headers | Parcial | 10 | 5 | CORS configurable y límites in-memory en auth público | Alto | Rate limiter distribuido y headers |
| BE-08 | Tipos/lint/formato ejecutables | Parcial | 10 | 5 | Configuración en `pyproject.toml`; herramientas ausentes del runtime | Medio | Imagen CI dedicada |

### Frontend React/Vite

| ID | Control | Estado | Peso interno | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---:|---:|---|---|---|
| FE-01 | React/Vite y router | Implementado | 15 | 15 | `frontend/package.json`, `src/App.jsx` | Bajo | Mantener versiones soportadas |
| FE-02 | TypeScript | No implementado | 10 | 0 | Frontend JSX | Medio | Migración incremental |
| FE-03 | Rutas protegidas/permisos | Parcial | 15 | 7.5 | `ProtectedRoute`, `RoleAccessRoute`; controles visuales no sustituyen backend | Alto | Compartir catálogo de capacidades |
| FE-04 | HTTP/errores centralizados | Parcial | 10 | 5 | `src/api/client.js`; portal tiene cliente local | Medio | Unificar cliente público/privado |
| FE-05 | Sesión segura | Parcial | 10 | 5 | Tokens en localStorage | Alto | Cookies HttpOnly/SameSite o mitigación XSS |
| FE-06 | Estados loading/empty/error e i18n | Parcial | 10 | 5 | Páginas e i18n existentes; cobertura inconsistente | Medio | Componentes compartidos |
| FE-07 | Pruebas/WCAG | No implementado | 15 | 0 | No se encontró evidencia automatizada suficiente | Alto | Vitest, RTL, axe y E2E |
| FE-08 | Build, lazy loading, code splitting | Parcial | 15 | 7.5 | Build exitoso; chunk principal 1.3 MB | Medio | `lazy()` y separación por módulo |

### PostgreSQL y persistencia

| ID | Control | Estado | Peso interno | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---:|---:|---|---|---|
| DB-01 | PostgreSQL/SQLAlchemy real | Implementado | 15 | 15 | `models/session.py`, Compose PostgreSQL 16 | Bajo | Mantener pool explícito |
| DB-02 | Alembic incremental | No implementado | 15 | 0 | SQL bajo `database/migrations/`; no Alembic operativo | Alto | Adoptar Alembic y tabla de versión |
| DB-03 | Restricciones e índices | Parcial | 15 | 7.5 | FKs/unique/check; cobertura desigual | Medio | Auditar índices por consulta |
| DB-04 | Transacciones/bloqueos | Parcial | 15 | 7.5 | `transaction_context`; `with_for_update` en inventario | Alto | Pruebas PostgreSQL concurrentes |
| DB-05 | Importes Decimal | Parcial | 10 | 5 | Nuevos servicios usan Decimal; serializadores legacy convierten a float | Alto | Eliminar conversiones float |
| DB-06 | Vistas PostgreSQL versionadas | No implementado | 10 | 0 | No se encontró evidencia en el repositorio | Medio | Vistas de balance/kardex |
| DB-07 | Backup/restauración | Parcial | 10 | 5 | `infra/ops/backup-db.sh`, `restore-db.sh` | Alto | Cifrado y prueba de restauración |
| DB-08 | Separación test/prod y mínimo privilegio | Parcial | 10 | 5 | SQLite tests y usuario Compose | Alto | PostgreSQL test desechable y roles mínimos |

### Autenticación, roles y autorización

| ID | Control | Estado | Peso interno | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---:|---:|---|---|---|
| AUTH-01 | Login y hash bcrypt | Implementado | 15 | 15 | `routes/auth.py::_verify_password`; `base_service.py` | Medio | Retirar fallback plaintext |
| AUTH-02 | MFA | Parcial | 10 | 5 | TOTP, backup y bloqueo disponibles; política opcional | Medio | MFA obligatorio por rol |
| AUTH-03 | JWT corto, revocación y refresh rotation | Parcial | 10 | 5 | JWT con exp; sin revocación/refresh rotation | Alto | Sesiones revocables |
| AUTH-04 | RBAC persistido granular | Parcial | 20 | 10 | Entity/field permissions CRUD; acciones de dominio reutilizan bits | Alto | Capacidades de dominio explícitas |
| AUTH-05 | Denegación por defecto | Implementado | 10 | 10 | Falta de permiso deniega; bypass admin retirado; bootstrap explícito | Medio | Auditar uso bootstrap |
| AUTH-06 | Tenant/propiedad/IDOR | Parcial | 20 | 10 | Portal y nuevas rutas comprueban propiedad; CRUD legacy no | Crítico | Scope obligatorio central |
| AUTH-07 | Auditoría y pruebas negativas | Parcial | 15 | 7.5 | Suite verde y cinco pruebas tenant; falta matriz HTTP con dos proyectos | Alto | Matriz IDOR automatizada |

### Seguridad y cifrado

| ID | Control | Estado | Peso interno | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---:|---:|---|---|---|
| SEC-01 | HTTPS/HSTS/CSP/headers | Parcial | 15 | 7.5 | NGINX existe; no se verificó enforcement completo | Crítico | TLS real, HSTS y CSP |
| SEC-02 | Inyección/XSS/CSRF/SSRF | Parcial | 15 | 7.5 | ORM; JWT header; sin política CSRF/cookies | Alto | CSP, validación URL y pruebas |
| SEC-03 | Carga segura XML/archivos | Implementado | 15 | 15 | `services/cfdi_xml.py`, límites de imagen/CSV | Medio | MIME/magic bytes y AV |
| SEC-04 | Secretos | Parcial | 10 | 5 | Variables de entorno; defaults de desarrollo y sin vault | Alto | Secret manager y fail-closed |
| SEC-05 | Cifrado sensible en aplicación | Parcial | 15 | 7.5 | MFA AES-GCM; PII/RFC/SSN plaintext | Crítico | Cifrado de columna con rotación |
| SEC-06 | Cifrado reposo/backups/mensajes | No verificable | 10 | 0 | No se encontró evidencia en el repositorio | Crítico | KMS, TLS DB/broker, backup cifrado |
| SEC-07 | SAST/DAST/SCA/containers | No implementado | 10 | 0 | No se encontró pipeline | Alto | Bandit, pip-audit, npm audit, Trivy |
| SEC-08 | Errores y redacción de logs | Parcial | 10 | 5 | AppError; algunos `str(exc)` se devuelven o imprimen | Alto | Mapeo seguro y redacción |

### Pruebas y calidad

| ID | Control | Estado | Peso interno | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---:|---:|---|---|---|
| TEST-01 | Unitarias y servicios nuevos | Implementado | 20 | 20 | Modelos 51/51, servicios 65/65 y pruebas focales pasan | Medio | Añadir integración PostgreSQL |
| TEST-02 | Suite backend completa | Implementado | 20 | 20 | 285/285 correctas | Bajo | Ejecutar en CI |
| TEST-03 | Autorización/tenant/IDOR | Parcial | 20 | 10 | Security tests existentes; sin cobertura vertical nueva | Crítico | Dos proyectos y actores por flujo |
| TEST-04 | Concurrencia/idempotencia | Parcial | 15 | 7.5 | Lógica/constraints; smoke DB sin producto elegible | Alto | Test concurrente PostgreSQL |
| TEST-05 | Frontend/E2E/WCAG | No implementado | 15 | 0 | Build pasa; no pruebas ejecutables | Alto | Vitest/Playwright/axe |
| TEST-06 | Cobertura y quality gates | Parcial | 10 | 5 | Umbral 60 configurado; lint bloqueado | Alto | CI bloqueante y cobertura crítica 90% |

### CI/CD y cadena de suministro

| ID | Control | Estado | Peso interno | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---:|---:|---|---|---|
| CI-01 | Scripts locales de checks | Parcial | 20 | 10 | `backend/ci/` | Medio | Imagen CI reproducible |
| CI-02 | Pipeline PR automatizado | No implementado | 20 | 0 | No se encontró `.github/workflows` | Alto | Workflow lint/test/build |
| CI-03 | Lockfiles y dependencias fijadas | Parcial | 15 | 7.5 | Python fijado; frontend sin lockfile encontrado | Alto | Lockfiles con hashes |
| CI-04 | Escaneo y SBOM | No implementado | 20 | 0 | No se encontró evidencia | Alto | SCA, SBOM y firma |
| CI-05 | Artefactos/imágenes/versionado | No implementado | 15 | 0 | No SemVer/CHANGELOG/pipeline | Medio | Registry, tags inmutables |
| CI-06 | Rollback/despliegue progresivo | Parcial | 10 | 5 | Scripts manuales; no canary/blue-green | Alto | Automatizar rollback |

### Docker, Kubernetes y despliegue

| ID | Control | Estado | Peso interno | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---:|---:|---|---|---|
| OPS-01 | Docker/Compose y health | Implementado | 20 | 20 | Compose dev/prod validado; health backend | Bajo | Fijar digests |
| OPS-02 | Multi-stage/no-root/read-only | Parcial | 15 | 7.5 | Frontend multi-stage; backend no endurecido | Alto | Usuario no-root y FS readonly |
| OPS-03 | Redes/DB no pública | Parcial | 10 | 5 | Red privada, pero DB publica puerto local | Alto | Sin puerto DB en producción |
| OPS-04 | Kubernetes/Ingress/probes | No implementado | 20 | 0 | No se encontró evidencia en el repositorio | Alto | Manifiestos o Helm |
| OPS-05 | Recursos/HPA/PDB | No implementado | 15 | 0 | No se encontró evidencia | Alto | Requests/limits/HPA/PDB |
| OPS-06 | Secretos externos/IaC | No implementado | 10 | 0 | `.env`; sin secret manager/IaC | Alto | External Secrets y Terraform |
| OPS-07 | Ambientes y recuperación | Parcial | 10 | 5 | Dev/prod y scripts backup; staging ausente | Alto | Staging y simulacro |

### Observabilidad, Event Log y operación

| ID | Control | Estado | Peso interno | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---:|---:|---|---|---|
| OBS-01 | Log técnico estructurado | No implementado | 15 | 0 | No se encontró evidencia en el repositorio | Alto | JSON logging |
| OBS-02 | Audit/Event Log central | Parcial | 20 | 10 | `models/audit_log.py`, `event_log.py`, `security/audit.py` | Alto | Append-only, retención y acceso |
| OBS-03 | IDs UTC/correlation/causation | No implementado | 15 | 0 | No se encontró evidencia completa | Alto | Esquema versionado |
| OBS-04 | Redacción/integridad/retención | No verificable | 15 | 0 | No se encontró evidencia en el repositorio | Alto | Política y firmas/WORM |
| OBS-05 | Métricas/trazas/dashboards | No implementado | 20 | 0 | No se encontró evidencia | Alto | OpenTelemetry/Prometheus |
| OBS-06 | SLO/runbooks/alertas | No implementado | 15 | 0 | No se encontró evidencia | Alto | SLO y alertas accionables |

### Documentación, privacidad y recuperación

| ID | Control | Estado | Peso interno | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---:|---:|---|---|---|
| DOC-01 | README/instalación/arquitectura | Parcial | 15 | 7.5 | README mínimo; `docs/INTEGRACION_FUNCIONAL.md`, `infra/README.md` | Medio | README operativo unificado |
| DOC-02 | API/datos/roles | Parcial | 15 | 7.5 | GraphQL docs y security-permissions; REST incompleto | Medio | OpenAPI versionado |
| DOC-03 | Despliegue/rollback | Parcial | 10 | 5 | Scripts e infra README | Alto | Runbook probado |
| DOC-04 | Backup/restauración | Parcial | 15 | 7.5 | Scripts disponibles; prueba no verificada | Alto | Registro de restore/RPO/RTO |
| DOC-05 | ADR/CHANGELOG/SemVer | No implementado | 10 | 0 | No se encontró evidencia suficiente | Medio | ADR y CHANGELOG |
| DOC-06 | Privacidad/consentimiento/derechos | No implementado | 20 | 0 | No se encontró evidencia | Crítico | Política, retención, DSAR |
| DOC-07 | Incidentes/responsable seguridad | No implementado | 15 | 0 | No se encontró evidencia | Alto | Plan IR y ownership |

## 6. Validaciones ejecutadas

| Validación | Resultado |
|---|---|
| Backend health local | Correcto: `status=ok`, contenedor healthy |
| Pruebas focales backend | 14/14 correctas: CFDI, inventario, cotización, stamping fake, CSV bancario |
| Suite backend completa | Correcta: 285/285 |
| Build React/Vite | Correcto; advertencia de chunk principal de 1.3 MB |
| ESLint frontend | No ejecutable: falta `eslint-plugin-react-refresh` |
| Migraciones incrementales | Seis scripts aplicados correctamente a PostgreSQL local |
| Downgrade de migraciones | No ejecutado: no existe Alembic ni downgrade SQL |
| Compose desarrollo | Correcto |
| Compose producción | Correcto al combinar base + override |
| Kubernetes | No ejecutado: manifiestos ausentes |
| Referencias runtime a fuentes | Cero coincidencias |
| Facturama real | No ejecutado por seguridad; fake únicamente |
| Smoke inventario DB | Bloqueado: no había producto local asociado a factura con proyecto |

## 7. Riesgos priorizados

| Prioridad | Riesgo | Consecuencia |
|---|---|---|
| P0 | Acceso cruzado por scope inconsistente | Exposición o modificación de datos entre empresas |
| P0 | PII/fiscal en texto plano | Impacto legal y de confidencialidad |
| P1 | Suite no automatizada en CI | Regresiones si el chequeo local no se ejecuta |
| P1 | Bootstrap/admin bypass | Privilegios excesivos persistentes |
| P1 | Facturama incompleto | Doble timbrado o estado fiscal incierto |
| P1 | Sin TLS/secret manager | Robo de credenciales/datos |
| P1 | Sin CI/SCA | Vulnerabilidades y builds no reproducibles |
| P2 | Sin observabilidad | Incidentes difíciles de detectar y reconstruir |

## 8. Plan de remediación

1. Incorporar `id_proyect` obligatorio al JWT interno y un query scope central; negar recursos sin scope y eliminar bypass por `user_type`.
2. Crear pruebas PostgreSQL de IDOR, dos proyectos, inventario concurrente, portal, timbrado idempotente y conciliación.
3. Reparar los 85 resultados rojos de la suite sin relajar aserciones.
4. Adoptar Alembic, migrar los seis SQL nuevos y validar upgrade/downgrade en DB desechable.
5. Completar Facturama: builder CFDI 4.0, cancelación, descarga, reconciliación y persistencia cifrada.
6. Completar estados de cuenta: parsers bancarios, matching, conciliación y frontend.
7. Cifrar PII seleccionada, rotar claves y cifrar backups/tránsito.
8. Agregar CI con lint, tipos, tests, build, SCA, secret scan, SBOM y Trivy.
9. Incorporar Redis seguro si continúa como requisito arquitectónico y definir su función no crítica.
10. Añadir Kubernetes/Helm, probes, recursos, secretos externos y staging.

## 9. Mejoras rápidas

- Declarar `eslint-plugin-react-refresh` y generar lockfile frontend.
- Eliminar defaults inseguros de DB/JWT y fallar al arrancar fuera de test.
- Retirar comparación de contraseñas legacy plaintext.
- Añadir límite/rate limit al portal de comentarios.
- Añadir índice/scope a listados principales y endpoint de consulta del ledger.
- Dividir el bundle frontend con lazy loading.

## 10. Controles no verificables

- Cifrado real de discos, PostgreSQL, RabbitMQ y backups.
- Restauración probada, PITR, RPO y RTO.
- Certificados TLS de producción y configuración HSTS efectiva.
- Secret manager externo y rotación operativa.
- Cobertura porcentual real: la suite termina verde, pero no se generó reporte de cobertura.
- Comportamiento real de Facturama: no se realizaron llamadas externas.

## 11. Controles no aplicables

No se marcaron tecnologías obligatorias como `⚪ No aplica`. DAST contra producción, despliegue progresivo real y pruebas de servicios externos no se ejecutaron por las reglas de seguridad, pero permanecen como controles pendientes, no como no aplicables.

## 12. Conclusión

El proyecto tiene una base funcional y las integraciones nuevas reducen brechas concretas. La suite backend está verde, pero el estado continúa en **Riesgo alto (49.9/100 efectivo)** por aislamiento tenant incompleto, PII sin cifrado, flujos parciales de Facturama/estados de cuenta/inventario y ausencia de infraestructura obligatoria. La prioridad sigue siendo autorización transversal y protección de datos.

## 13. Seguimiento de remediación

Primera iteración posterior a la auditoría:

- JWT interno enriquecido con `id_proyect`.
- Bypass de permisos para administradores no bootstrap retirado.
- Product REST scoped por el proyecto de Invoice; recursos ajenos responden 404.
- Contrato de error de login reparado sin retirar `error_key`.
- Cinco pruebas tenant agregadas; 9/9 pruebas combinadas de auth/MFA/tenant correctas.
- Factories compartidas reparan fixtures de modelos y servicios sin relajar validaciones.
- Reset SQLite aislado e inicialización temprana del entorno de pruebas.
- Blueprint de documentos idempotente entre múltiples application factories.
- Suite completa actual: 285/285 pruebas correctas.

El cálculo ponderado sube a 50.7; la calificación efectiva queda en 49.9 por el tope tenant/PII hasta completar scope en Invoice, Task, banca y GraphQL, cifrar datos sensibles y ejecutar pruebas HTTP IDOR con dos proyectos reales.