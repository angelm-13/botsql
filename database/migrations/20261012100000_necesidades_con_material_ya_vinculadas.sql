-- Las necesidades creadas con un material del catalogo nacian con review_result
-- NULL: ni se podian ordenar (need_not_purchasable) ni confirmar la compra
-- (need_already_linked). Ahora nacen 'linked'; esto arregla las que ya existian.
-- Idempotente: solo toca lo que sigue sin revisar.
UPDATE proyect_material_need
   SET review_result = 'linked'
 WHERE id_material IS NOT NULL
   AND review_result IS NULL
   AND deletion_date IS NULL;
