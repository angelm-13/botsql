# Avisos de revisión de datos para Adser (campana del sistema)

- **Script:** `backend/scripts/notify_adser_revision_datos.py` (`--dry-run`, `--destinatario`, idempotente).
- **Pruebas:** `backend/tests/test_services/test_avisos_revision_datos_adser.py`.
- **Frontend:** `NotificationBell.css` (`white-space: pre-line`) para que las listas se lean.

Decisión de Alan (2026-09-30): los avisos los ve **solo `yesgo`** (Yessica González, rol
Gerente). No cambian ningún dato ni permiso: solo dicen qué revisar.

## Qué avisa (una notificación por tema, más un resumen)

| Aviso | Casos en adser-prod (medido 2026-09-30) | Qué se le pide |
|---|---|---|
| Préstamos abiertos de herramientas que figuran en el almacén | 29 renglones, 13 responsables | Confirmar dónde está; si ya volvió, «Marcar devuelto» en el vale |
| Préstamos del sistema anterior sin herramienta en el catálogo | 5 (vales 1 ×2, 3, 36, 96) | Si alguna sigue fuera, registrarla en un vale nuevo |
| Incidencia 90: el responsable cambió de nombre | 1 | Corregir el responsable si no es la misma persona |
| Vales abiertos sin ningún material | 6 (44, 120, 133, 134, 138, 139) | Cerrarlos o cancelarlos |
| Resumen | — | Explica lo anterior y dice que, si necesitan acceso o permiso, avisen a Alan Pérez |

Cada aviso se quita de la lista solo con el botón **«Enterado»**: sirve de recordatorio
hasta que lo confirman. El resumen se crea último para que, con el orden de la campana
(más reciente primero), quede arriba. Un tema sin casos no se avisa, y uno ya avisado (aunque
esté leído) no se repite.

## Pasos

Después de promover y de correr los scripts de datos (los avisos se calculan sobre los datos
ya corregidos):

```bash
kubectl -n <ns> exec deploy/backend -- python scripts/notify_adser_revision_datos.py --dry-run
kubectl -n <ns> exec deploy/backend -- python scripts/notify_adser_revision_datos.py
kubectl -n <ns> exec deploy/backend -- python scripts/notify_adser_revision_datos.py   # debe dar 0 creados
```

**No correr en `adser-prod` sin el OK de Alan:** son mensajes para personal de Adser. En dev,
para verlos tú mismo en la campana: `--destinatario admin1`.

## Lo que se aprendió al probarlo

- La tabla `notification` tiene una restricción CHECK con una lista **cerrada** de tipos
  (`project_status_change`, `project_modified`, `activity_log_created`, `task_assigned`,
  `material_confirmed`, `custom`). Un primer intento con un tipo propio habría fallado al
  crear el primer aviso; se usa `custom` y los avisos se distinguen por `metadata->>'clave'`.
  Una prueba vigila que el tipo sea uno admitido.
- La campana pintaba el mensaje sin respetar saltos de línea; una lista se veía como un
  párrafo corrido. Con `white-space: pre-line` se lee en viñetas (verificado en el navegador
  con la app local).
- Los 5 préstamos sin herramienta **no están en la base** (la migración los excluyó porque su
  producto no existe en el origen): sus datos están en el script, tomados del respaldo.
  Las otras tres consultas se calculan en vivo.
- Con el rol Gerente, `yesgo` recibe la campana sin más permisos: las rutas solo piden sesión
  (`@token_required`), no una fila de `entity_permission`.
