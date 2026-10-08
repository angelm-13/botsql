# Vale de almacén: entrega, recibido, externos y complementario (2026-10-06)

Rama `feature/vale-entrega-recibido`, sobre `initAlan` con `ec40a90` de Ángel
(quién recoge, custodia visible, notificaciones) ya mergeado.

Origen: conversación con Adser. El supervisor no puede salir de planta, así que
pide herramienta adicional dentro del mismo proyecto y designa quién la recoge;
almacén entrega a esa persona y el supervisor confirma que le llegó.

## Qué cambia

- **Entrega separada de la autorización.** `POST /vouchers/<id>/deliver`
  (almacén, `warehouse_voucher` update). Si recibe alguien distinto del designado,
  la nota es obligatoria y la custodia de los renglones sigue a quien recibió.
- **Confirmación de recibido para TODO vale nuevo.**
  `POST /vouchers/<id>/confirm-receipt` `{ok, note}`. Solo el responsable del vale
  (o administrador); con `ok:false` la nota es obligatoria. No bloquea la
  devolución. Confirma de paso la custodia de los renglones entregados a otro.
- **Quien recoge sin usuario (externo).** `pickup_name` en el vale y
  `delivered_to_name` por renglón; excluyente con `id_user_pickup`. El frontend usa
  un combobox (`PersonaCombobox.jsx`): sugiere usuarios y ofrece "Persona externa".
  A un externo no se le notifica (no tiene cuenta).
- **Vale complementario.** `id_incident_parent` opcional: el vale anterior, del
  MISMO proyecto, que debe estar activo (`PROYECTO_ACTIVO` en el servicio:
  `authorized`, `waiting_material`, `in_progress`, `stopped`). Quien solo pide
  material solo puede colgarse de un vale suyo (404, no 403).
- **Estado de entrega derivado** (`estado_de_entrega`): `por_autorizar` →
  `por_entregar` → `entregado` → `recibido` / `recibido_con_observaciones`.
  Dimensión aparte de `incident_status`. Filtros `?delivery=` en `GET /vouchers`.

## Vales anteriores

`incident.tracks_delivery` nace en `false` para todo lo existente (incluidos los
migrados de Adser): sin seguimiento, `delivery_status = null`. NO se rellena
ninguna confirmación. Solo los vales creados desde esta versión llevan `true`.

## Migración

`20261006090000_vale_entrega_recibido_y_complementario.sql`: solo
`ADD COLUMN IF NOT EXISTS`, idempotente (corre en cada arranque). Verificada
aplicándola dos veces seguidas. No toca columnas `scope_*`.

## Bug de paso (de `ec40a90`, corregido aquí)

`Borrador` leía `actorIdUser` sin recibirlo como prop: `ReferenceError` al pintar el
selector de "quién recoge" (eslint `no-undef`). Ahora se pasa el actor.

## Fuera de esta entrega

- PDF con "Recoge: X" y firma de quien recibió (los externos ya salen por nombre
  en la columna de custodia).
- Avisos de "por confirmar" por campanita (el tipo requiere ampliar el CHECK de
  `notification.notification_type`) y el deep-link, pendiente #1 de `CLAUDE.md`.
- Sugerir nombres de externos ya usados (hoy es texto libre; "Juan Perez" y
  "Juan Pérez" serían dos personas).

## Promoción

`tyakxa-dev` se despliega solo al pushear `initAlan`. `adser-prod` es promoción
manual. Nada de esto está promovido.
