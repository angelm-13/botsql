-- La orden de trabajo: folio propio, responsable real, y supervisor que la toma.
--
-- Que cambia, y por que
-- ---------------------
-- **El folio lo genera el sistema.** Era un campo de captura libre, y la
-- pantalla INVENTABA uno -"PRJ-000006"- cuando el proyecto no traia ninguno:
-- el numero que la gente leia en la lista no existia en la base, asi que
-- buscarlo no encontraba nada. Ahora cada proyecto nace con
-- `OT-<anio>-<consecutivo>` guardado de verdad, y esta migracion se lo pone a
-- los que ya existen. El indice unico `uq_proyect_folio` ya estaba.
--
-- **El supervisor TOMA el proyecto.** `id_supervisor` era un desplegable del
-- formulario, o sea que quien capturaba la orden repartia el trabajo del
-- taller desde su escritorio. Ahora el proyecto sale sin supervisor y lo toma
-- quien lo va a sacar adelante -- por capacidad `project_execution`, no por
-- nombre de rol. Eso necesita dos tipos de evento nuevos en el expediente,
-- que es lo unico que esta migracion cambia de esquema.
--
-- **El responsable es quien lo crea.** No hace falta migracion: es
-- `create_project` quien deja de aceptar `leader` del cuerpo. Los proyectos
-- que ya tengan un responsable distinto de su autor se quedan como estan --
-- reasignarlos seria reescribir a nombre de quien esta el trabajo de alguien.
--
-- **La orden de compra del cliente y su partida** salen del formulario por
-- peticion. Las columnas NO se borran: `purchase_order` y
-- `purchase_order_item` guardan el numero del documento del cliente, y tirarlo
-- perderia el unico dato que liga la orden con el papel que la autorizo.

BEGIN;

-- 1. El expediente tiene que poder contar que alguien tomo o solto el proyecto.
ALTER TABLE proyect_event DROP CONSTRAINT IF EXISTS proyect_event_event_type_check;

ALTER TABLE proyect_event ADD CONSTRAINT proyect_event_event_type_check CHECK (
    event_type IN (
        'created', 'status_changed', 'message', 'task_event',
        -- El recorrido comercial, que corre en paralelo al de taller.
        'management_transition',
        -- Lo acordado y lo cobrado, cada uno por su lado.
        'payment_agreed', 'payment_settled',
        -- Quien se hizo cargo del proyecto en el taller, y cuando lo solto.
        -- Van como evento y no como una columna de fecha porque un proyecto
        -- puede cambiar de manos varias veces, y lo que importa es la linea de
        -- tiempo: quien lo tenia cuando paso lo que paso.
        'taken', 'released'
    )
);

-- 2. Folio para los proyectos que no lo tienen.
--
-- Se numera por anio de ALTA, no por el anio de hoy: un proyecto de 2025 tiene
-- que llevar folio de 2025 aunque esta migracion corra en 2026. El orden
-- dentro del anio es el de creacion, que es el unico que reproduce lo que
-- habria pasado si el folio hubiera existido desde el principio.
--
-- `uq_proyect_folio` es unico solo sobre las filas vivas con folio, asi que
-- los proyectos borrados no consumen numero -- y tampoco lo estorban.
-- `creation_date` es NULLABLE en la tabla real -- el modelo la declara
-- obligatoria con `server_default`, pero `database/seed.sql` inserta proyectos
-- sin ella y la columna los acepta. Sin el `coalesce`, `to_char(NULL)` da NULL
-- y el folio salia NULL: la primera corrida de esta migracion no le puso folio
-- a ninguno de esos proyectos, en silencio. Se les cuenta en el anio de hoy,
-- que es lo unico que se sabe de ellos.
WITH numerados AS (
    SELECT id_proyect,
           to_char(coalesce(creation_date, now()), 'YYYY') AS anio,
           row_number() OVER (
               PARTITION BY to_char(coalesce(creation_date, now()), 'YYYY')
               ORDER BY coalesce(creation_date, now()), id_proyect
           ) AS consecutivo
      FROM proyect
     WHERE deletion_date IS NULL
       AND (folio IS NULL OR btrim(folio) = '')
)
UPDATE proyect p
   SET folio = 'OT-' || n.anio || '-' || lpad(n.consecutivo::text, 5, '0'),
       last_update_date = now()
  FROM numerados n
 WHERE p.id_proyect = n.id_proyect
   -- Que no choque con un folio capturado a mano que ya use ese numero.
   AND NOT EXISTS (
       SELECT 1 FROM proyect otro
        WHERE otro.deletion_date IS NULL
          AND otro.folio = 'OT-' || n.anio || '-' || lpad(n.consecutivo::text, 5, '0')
   );

COMMIT;
