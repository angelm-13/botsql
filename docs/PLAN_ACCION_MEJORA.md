# Plan de accion para mejora funcional y tecnica

## Objetivo

Subir la calificacion auditada desde 47.9/100 sin ocultar riesgos ni ampliar funciones sobre una base insegura. El orden prioriza aislamiento tenant, pruebas y datos sensibles antes de infraestructura y nuevas pantallas.

## Fases

| Fase | Prioridad | Acciones | Criterio de aceptacion | Impacto estimado |
|---|---|---|---|---:|
| 1. Tenant y autorizacion | P0 | Incluir proyecto en JWT; eliminar bypass admin; scope central en REST/GraphQL; pruebas IDOR con dos proyectos | Ningun actor consulta, muta, descarga o enlaza recursos ajenos; bootstrap auditado por separado | +8 a +12 puntos |
| 2. Suite y contratos | P0 | Reparar fixtures, enums, fechas y contrato auth; PostgreSQL desechable | Suite backend verde y quality gate reproducible | +5 a +8 puntos |
| 3. PII y secretos | P0 | Inventario de datos, cifrado de columna, rotacion, retirar fallbacks inseguros | PII seleccionada cifrada; claves fuera de Compose; migracion reversible | +5 a +8 puntos |
| 4. Flujos verticales | P1 | Inventario UI/kardex; Facturama completo; conciliacion bancaria; portal documental | E2E feliz/negativo/idempotente por flujo | +6 a +10 puntos |
| 5. Persistencia y calidad | P1 | Alembic, Decimal transversal, indices, concurrencia | Upgrade/downgrade y pruebas PostgreSQL pasan | +3 a +5 puntos |
| 6. CI y suministro | P1 | Lint, tipos, tests, build, SCA, secretos, SBOM, imagen | PR bloqueada ante fallo; artefactos inmutables | +4 a +7 puntos |
| 7. Operacion | P2 | Logs JSON, correlacion, metricas, trazas, alertas, backups probados | SLO, restore y runbooks verificados | +3 a +6 puntos |
| 8. Despliegue | P2 | Kubernetes/Helm, probes, recursos, secretos externos, staging | Despliegue y rollback automatizados | +3 a +5 puntos |

Los impactos no son aditivos de forma directa: la auditoria pondera grupos y mantiene topes por fallos criticos.

## Primera iteracion completada

- [x] Añadir `id_proyect` al payload de acceso interno, incluido login con MFA.
- [x] Retirar el bypass global de ACL para administradores no bootstrap.
- [x] Aplicar scope tenant a Product REST mediante Invoice.
- [x] Ocultar recursos de otro proyecto con 404 para reducir enumeracion.
- [x] Agregar pruebas unitarias de identidad, denegacion por defecto y scope.
- [x] Corregir el contrato de error del login sin retirar `error_key`.
- [x] Reemplazar fechas literales y normalizar fixtures generados.
- [x] Crear factories compartidas para modelos y servicios con FKs obligatorias.
- [x] Corregir el aislamiento SQLite y la inicializacion temprana de `TESTING`.
- [x] Hacer idempotente el Blueprint de documentos.
- [ ] Migrar Invoice REST al mismo patron.
- [ ] Aplicar scope a Task, BankAccount, BankStatement y rutas GraphQL.
- [ ] Crear fixtures PostgreSQL de dos proyectos y pruebas HTTP IDOR.

## Paridad funcional con Cotizador `initAlan`

Comparacion verificada contra `cotizador_demo:initAlan` (`473b5cfe`). La meta es reimplementar el comportamiento sobre los limites tenant y modelos de TYAKXA, sin copiar codigo ni debilitar autorizacion.

| Modulo | Estado TYAKXA | Brecha contra `initAlan` | Proxima entrega verificable |
|---|---|---|---|
| Facturacion manual | Preview Decimal, descuentos, IVA, retenciones, claves SAT, captura atomica y pantalla dedicada | Timbrado inmediato, catalogos SAT, CSD/PAC, cancelacion, nota de credito y descargas XML/PDF/ZIP | Adaptador Facturama sandbox con idempotencia; descarga y cancelacion con pruebas de timeout |
| Gastos XML | Parser CFDI seguro integrado al flujo generico de Invoice | No hay dominio ExpenseInvoice/ExpenseItem, direccion emisor/receptor, matching, cancelacion, estadisticas ni conciliacion | Modelos y migracion; upload preview sin persistencia; import atomico e idempotente por UUID |
| Estados de cuenta | Importacion CSV segura, hash duplicado y scope de cuenta/proyecto | No hay PDF BBVA, confianza de extraccion, detalle de movimientos, matching manual ni conciliacion | StatementMovement; preview PDF; parser BBVA aislado; matching con Invoice/ExpenseInvoice |
| Cotizador | Invoice-backed, calculo Decimal, transiciones, comentarios, tarea y portal cliente | Faltan versiones, subtareas, trabajo de ingenieria, estadisticas, adjuntos y distribucion PDF/email/WhatsApp | Conservar Invoice-backed; agregar versiones/subtareas y PDF compartible antes de evaluar tablas nuevas |

### Facturacion manual entregada

- [x] `POST /invoice/manual/preview` totaliza sin persistir.
- [x] `POST /invoice/manual` crea cabecera y partidas en una transaccion.
- [x] Scope de proyecto y existencia de cliente/emisor antes de calcular o guardar.
- [x] Descuento, IVA trasladado, retenciones ISR/IVA, objeto de impuesto y claves SAT por concepto.
- [x] Migracion incremental e idempotente para campos fiscales.
- [x] Pantalla `/invoice/manual` con preview obligatorio antes de guardar.
- [x] Pruebas de calculo, claves SAT y rollback sin filas parciales.

## Siguiente bloque ejecutable

1. Crear ExpenseInvoice/ExpenseItem y flujo de preview/import XML idempotente.
2. Agregar movimientos de estado de cuenta y conciliacion gasto/factura.
3. Completar Facturama: timbrado, estado incierto, cancelacion y artefactos.
4. Cerrar scope tenant transversal de Invoice, Task, BankAccount, BankStatement y GraphQL.
5. Extender Cotizador con versiones, subtareas y distribucion documental.

Evidencia de la iteracion:

- 9/9 pruebas de auth/MFA y tenant scope correctas.
- Login local correcto con `id_proyect=1` en la identidad emitida.
- 52 placeholders `datetime.now()` reemplazados por un valor ISO determinista.
- 51/51 pruebas de modelo y 65/65 pruebas de servicios correctas.
- Suite backend completa: 289/289 pruebas correctas.
- Build Vite de produccion correcto; permanece advertencia preexistente por bundle mayor a 500 kB.
- Migracion `20260816233000_manual_invoicing.sql` aplicada al PostgreSQL local.
- Smoke test autenticado confirma 404 ante referencia de cliente inexistente; la base local tiene un proyecto con FK de cliente huerfana y requiere saneamiento de datos.
- Calculo ponderado provisional: 50.7; calificacion efectiva 49.9 por el tope tenant/PII.

## Responsables sugeridos

| Area | Responsable | Revision obligatoria |
|---|---|---|
| Tenant/RBAC | Backend + seguridad | Pruebas negativas y threat model |
| PII/secretos | Seguridad + DBA | Plan de rotacion y rollback |
| Facturama/CFDI | Backend fiscal | Sandbox y validacion fiscal |
| Portal/frontend | Frontend | Accesibilidad y E2E |
| CI/infra | DevOps | Supply chain y recuperacion |

## Regla de cierre

Una casilla funcional solo se cierra cuando existen implementacion backend, autorizacion por propiedad, migracion, prueba positiva, prueba negativa, prueba de idempotencia cuando corresponda y documentacion operativa.