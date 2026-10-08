# Notificaciones con destino (2026-10-06)

Cierra el pendiente #1 de `CLAUDE.md`: un clic en un aviso de la campana abre el
registro que lo originó.

## Decisiones (las dos que estaban abiertas)

1. **Abrir un aviso NO lo marca como leído.** "Enterado" sigue siendo un acto
   explícito y aparte, a propósito: nadie puede decir "no la vi". Distinguir
   "vista" de "enterado" exigiría una columna `seen_date`; no se hizo.
2. **Qué módulos notifican hoy:** proyectos (`_notificar_proyecto`) y vales
   (custodia, recoger, vencido y el nuevo "entregado"). Tareas, incidencias y
   citas no producen avisos todavía; cuando lo hagan, agregar una línea al mapa.

## Qué cambia

- **Migración `20261006100000`** (idempotente): `notification.target_entity` +
  `target_id`, con relleno de lo existente (proyectos desde `id_proyect`, vales
  desde `metadata->>'id_incident'`, solo filas con `target_entity IS NULL`), índice,
  y el CHECK de `notification_type` ampliado con `warehouse_voucher_delivered`.
- **`create_notification`** acepta `target_entity`/`target_id`. Sin destino pero con
  `id_proyect`, el destino es ese proyecto (los productores viejos siguen llevando
  a algún lado). Medio destino se descarta: o es un par completo o no hay destino.
- **Productores con destino explícito:** proyectos, custodia asignada, recoger,
  vencido (job) y el aviso nuevo `warehouse_voucher_delivered`: al responsable,
  cuando almacén marca la entrega (`POST /vouchers/<id>/deliver`), para que
  confirme el recibido. No avisa si quien entrega es el propio responsable.
- **Frontend:** `src/notifications/destino.js` es el ÚNICO mapa entidad → ruta
  (`proyect` → `/proyect?abrir=ID`, `voucher` → `/vouchers?abrir=ID`); un destino
  desconocido o con id inválido no lleva a ningún lado (el aviso se ve, sin clic).
  `NotificationBell` navega con clic o Enter y cierra el panel; "Enterado" usa
  `stopPropagation`. `/proyect` y `/vouchers` leen `?abrir=`, abren el registro y
  limpian el parámetro (recargar no lo reabre).
- **403/404:** si el registro ya no existe o el usuario no lo puede ver, se muestra
  un mensaje (`errors.not_found`, ahora traducido) en vez de dejar la pantalla en
  blanco. El mensaje vive en su propio estado: `listar()`/`loadData()` limpian
  `error` al arrancar y lo borraban según quién ganara la carrera.

## Seguridad

El destino es solo una ruta del front. Quien abre `?abrir=ID` pasa por los mismos
endpoints (`GET /vouchers/<id>`, `GET /proyect/<id>`) y su alcance de rol: un aviso
no da acceso a nada que el usuario no pudiera abrir a mano.

## Pruebas

Backend: 9 casos nuevos en `test_vale_de_almacen.py` (destino explícito, por
omisión, medio destino, custodia, job de vencidos, aviso de entrega, no avisarse a
uno mismo, un fallo al notificar no revierte). Frontend: 6 casos en
`src/notifications/destino.test.js` (corren con `npm test`).

## Fuera de esta entrega

Navegar a una pestaña concreta dentro del registro; avisos de tareas, incidencias
y citas; marcar "vista" distinto de "enterado".
