-- Agregar campos de prioridad y costo total a proyect
-- Fase 1 de mejora de gestión de proyectos: solo estructura, sin lógica de filtrado aún.

ALTER TABLE proyect
  ADD COLUMN priority VARCHAR(20) DEFAULT 'media' CHECK (priority IN ('baja', 'media', 'alta')),
  ADD COLUMN total_cost NUMERIC(14, 2) DEFAULT 0 CHECK (total_cost >= 0);

-- Para instalaciones existentes, poblar prioridad con valor por defecto 'media'
UPDATE proyect SET priority = 'media' WHERE priority IS NULL;
UPDATE proyect SET total_cost = 0 WHERE total_cost IS NULL;

-- Hacer los campos NOT NULL después de llenarlos
ALTER TABLE proyect
  ALTER COLUMN priority SET NOT NULL,
  ALTER COLUMN total_cost SET NOT NULL;
