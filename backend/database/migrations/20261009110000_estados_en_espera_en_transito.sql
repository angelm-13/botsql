-- Estados intermedios en el flujo de vales:
-- borrador -> en_espera (almacén autoriza) -> en_transito (salen) -> abierto (reciben) -> cerrado
-- Permite notificaciones y botones específicos en cada etapa.

ALTER TABLE incident DROP CONSTRAINT IF EXISTS incident_status_check;

ALTER TABLE incident ADD CONSTRAINT incident_status_check
  CHECK (incident_status IN ('borrador', 'en_espera', 'en_transito', 'abierto', 'cerrado', 'cancelado'));
