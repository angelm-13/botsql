-- Vinculo entre el numero del checador y el empleado del sistema.
--
-- De que se parte
-- ---------------
-- `attendance_record` (20261016100000) guarda cada checada con el numero de
-- empleado tal como lo trae el checador (`employee_no`), pero `user` no tiene
-- ningun campo con ese numero: no habia forma de saber de quien es cada checada,
-- y la nomina necesita contarlas por empleado.
--
-- Que se agrega
-- -------------
-- `attendance_employee_link`: una fila por numero de checador ligado a un
-- usuario. Vive en el modulo `rh` en lugar de agregar una columna a `user`, que
-- es tabla del nucleo y la usan todos los modulos: asi este cambio no toca nada
-- fuera de Recursos humanos.
--
--   source       de que origen es el numero ('kronos' hoy). Dos checadores de
--                distinta marca pueden repetir numeros.
--   employee_no  el numero tal como lo trae el checador.
--   id_user      el empleado del sistema.
--
-- Un numero vivo se liga a un solo empleado (indice unico parcial sobre las
-- filas sin `deletion_date`). Desligar es borrado logico, para que quede rastro
-- de quien estaba ligado antes.
--
-- Reaplicable: solo CREATE ... IF NOT EXISTS. No toca entity_permission; los
-- permisos llegan por la resiembra 20261016110100.
BEGIN;

CREATE TABLE IF NOT EXISTS attendance_employee_link (
    id_attendance_employee_link SERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL DEFAULT 'kronos'
        CONSTRAINT ck_attendance_employee_link_source CHECK (source IN ('kronos', 'whatsapp', 'manual')),
    employee_no VARCHAR(32) NOT NULL,
    id_user INTEGER NOT NULL REFERENCES "user"(id_user) DEFERRABLE INITIALLY DEFERRED,
    created_by INTEGER NOT NULL,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_attendance_employee_link_vivo
    ON attendance_employee_link (source, employee_no)
    WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_attendance_employee_link_user
    ON attendance_employee_link (id_user);

COMMIT;
