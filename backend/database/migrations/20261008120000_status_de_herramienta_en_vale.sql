-- Estado de la herramienta en el vale: disponible, apartada, entregada, en_transito, devuelta, dañada, extraviada, destruida.
-- Permite rastrear si una herramienta está comprometida en otro vale y gestionar prestamos eficientemente.

ALTER TABLE nm_incident_product
ADD COLUMN status VARCHAR(20) DEFAULT 'disponible',
ADD CONSTRAINT ck_nm_incident_product_status
  CHECK (status IN ('disponible', 'apartada', 'entregada', 'en_transito', 'devuelta', 'dañada', 'extraviada', 'destruida'));
