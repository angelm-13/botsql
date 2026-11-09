-- Bajas de empleados para el finiquito y la liquidacion (Etapa E; diseño
-- aprobado por RH el 2026-11-02).
--
-- De que se parte
-- ---------------
-- No habia forma de registrar que alguien deja la empresa ni de calcular lo que
-- se le debe.
--
-- Que se agrega
-- -------------
-- employee_termination   la baja: empleado, fecha (ultimo dia trabajado), motivo
--                     (resignation, mutual_agreement, justified_dismissal,
--                     unjustified_dismissal), si se pagan los 20 dias por año
--                     en despido injustificado y notas. El calculo no se guarda:
--                     services/termination_service.py lo hace con los datos del dia.
-- Desactivar al usuario sigue siendo aparte (la baja de usuarios del equipo).
--
-- Reaplicable: CREATE ... IF NOT EXISTS. Los permisos llegan por la resiembra
-- 20261102190000.
BEGIN;

CREATE TABLE IF NOT EXISTS employee_termination (
    id_employee_termination SERIAL PRIMARY KEY,
    id_user INTEGER NOT NULL REFERENCES "user"(id_user) DEFERRABLE INITIALLY DEFERRED,
    termination_date DATE NOT NULL,
    reason VARCHAR(30) NOT NULL CONSTRAINT ck_employee_termination_reason
        CHECK (reason IN ('resignation', 'mutual_agreement', 'justified_dismissal', 'unjustified_dismissal')),
    pay_twenty_days BOOLEAN NOT NULL DEFAULT false,
    notes VARCHAR(300) NULL,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL
);
CREATE INDEX IF NOT EXISTS ix_employee_termination_user ON employee_termination (id_user);

COMMIT;
