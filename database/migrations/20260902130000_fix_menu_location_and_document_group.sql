-- Dos correcciones de datos que salieron al verificar la idempotencia.
--
-- Como se encontraron
-- -------------------
-- El initContainer de k8s reaplica TODAS las migraciones en cada arranque del
-- pod. Se reprodujo eso a mano contra la base: de las 58, tres fallaron. Las
-- dos que arregla esta migracion son de datos; la tercera se corrigio en el
-- archivo que la causaba.
--
--
-- 1. menu_location = 'none' no existe
-- -----------------------------------
-- `ck_entity_permission_menu_location` -que crea 20260816234500- solo acepta
-- 'sidebar', 'settings' y 'hidden'. Habia 13 filas con 'none', sembradas por
-- una version del registro que emitia ese valor antes de que af44687 lo
-- cambiara a 'hidden'.
--
-- El efecto no se veia: el menu del frente solo pinta lo que dice 'sidebar',
-- asi que 'none' se comportaba como oculto. Lo que rompia era la restriccion:
-- al reaplicarse 20260816234500 el ALTER TABLE no podia recrearla, y con
-- ON_ERROR_STOP=1 eso detiene el arranque del pod. Un valor invalido que no
-- molesta hasta el dia del despliegue.
--
--
-- 2. Documentos estaba archivado dentro de Laboratorio
-- ----------------------------------------------------
-- 20260901090000 fijaba menu_group = 'Laboratorio' para sus siete entidades,
-- incluidas las cuatro de documentos. Dos modulos distintos bajo un solo
-- encabezado. El archivo ya quedo corregido para las instalaciones nuevas;
-- esto arregla las filas ya sembradas.

BEGIN;

UPDATE entity_permission
   SET menu_location = 'hidden',
       last_update_date = now()
 WHERE menu_location = 'none';

UPDATE entity_permission
   SET menu_group = 'Documentos',
       menu_group_icon = 'file-text',
       last_update_date = now()
 WHERE deletion_date IS NULL
   AND entity_name IN ('document', 'document_category',
                       'document_version', 'document_relation')
   AND menu_group = 'Laboratorio';

COMMIT;
