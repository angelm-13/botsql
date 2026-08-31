-- Indices que faltaban en llaves foraneas.
--
-- PostgreSQL indexa sola la columna referenciada, no la que referencia. Sin
-- indice del lado que apunta, dos cosas se degradan de golpe cuando las tablas
-- crecen: cualquier consulta que una por esa columna recorre la tabla entera,
-- y -mas serio- borrar o actualizar una fila del lado padre obliga a
-- PostgreSQL a recorrer la tabla hija completa para comprobar que no queden
-- huerfanos, tomando un candado mientras lo hace. Con pocas filas no se nota;
-- con volumen de produccion se convierte en bloqueos.
--
-- Se encontraron 63 llaves foraneas sin indice propio. Se crean aqui.
--
-- Nota para mas adelante: sobre tablas ya grandes y en caliente conviene
-- CREATE INDEX CONCURRENTLY, que no bloquea escrituras pero no puede ir dentro
-- de una transaccion. Aqui las tablas todavia son chicas, asi que se hace en
-- una sola transaccion, que es mas facil de revertir si algo sale mal.

BEGIN;

CREATE INDEX IF NOT EXISTS idx_appointment_created_by
    ON appointment (created_by);

CREATE INDEX IF NOT EXISTS idx_appointment_id_appointment_type
    ON appointment (id_appointment_type);

CREATE INDEX IF NOT EXISTS idx_appointment_id_calendar_profile
    ON appointment (id_calendar_profile);

CREATE INDEX IF NOT EXISTS idx_appointment_id_proyect
    ON appointment (id_proyect);

CREATE INDEX IF NOT EXISTS idx_appointment_type_created_by
    ON appointment_type (created_by);

CREATE INDEX IF NOT EXISTS idx_appointment_type_id_calendar_profile
    ON appointment_type (id_calendar_profile);

CREATE INDEX IF NOT EXISTS idx_availability_override_created_by
    ON availability_override (created_by);

CREATE INDEX IF NOT EXISTS idx_availability_override_id_calendar_profile
    ON availability_override (id_calendar_profile);

CREATE INDEX IF NOT EXISTS idx_availability_rule_created_by
    ON availability_rule (created_by);

CREATE INDEX IF NOT EXISTS idx_availability_rule_id_calendar_profile
    ON availability_rule (id_calendar_profile);

CREATE INDEX IF NOT EXISTS idx_bank_account_id_proyect
    ON bank_account (id_proyect);

CREATE INDEX IF NOT EXISTS idx_bank_statement_id_bank_account
    ON bank_statement (id_bank_account);

CREATE INDEX IF NOT EXISTS idx_bank_statement_id_proyect
    ON bank_statement (id_proyect);

CREATE INDEX IF NOT EXISTS idx_bank_statement_movement_id_invoice
    ON bank_statement_movement (id_invoice);

CREATE INDEX IF NOT EXISTS idx_calendar_profile_created_by
    ON calendar_profile (created_by);

CREATE INDEX IF NOT EXISTS idx_calendar_profile_id_proyect
    ON calendar_profile (id_proyect);

CREATE INDEX IF NOT EXISTS idx_calendar_profile_id_user
    ON calendar_profile (id_user);

CREATE INDEX IF NOT EXISTS idx_inventory_ledger_id_location_target
    ON inventory_ledger (id_location_target);

CREATE INDEX IF NOT EXISTS idx_invoice_cancellation_id_proyect
    ON invoice_cancellation (id_proyect);

CREATE INDEX IF NOT EXISTS idx_invoice_material_service_id_task
    ON invoice_material_service (id_task);

CREATE INDEX IF NOT EXISTS idx_invoice_payment_id_payment_invoice
    ON invoice_payment (id_payment_invoice);

CREATE INDEX IF NOT EXISTS idx_invoice_payment_id_proyect
    ON invoice_payment (id_proyect);

CREATE INDEX IF NOT EXISTS idx_logistics_branch_created_by
    ON logistics_branch (created_by);

CREATE INDEX IF NOT EXISTS idx_logistics_contact_id_customer_supplier
    ON logistics_contact (id_customer_supplier);

CREATE INDEX IF NOT EXISTS idx_logistics_evidence_captured_by
    ON logistics_evidence (captured_by);

CREATE INDEX IF NOT EXISTS idx_logistics_evidence_created_by
    ON logistics_evidence (created_by);

CREATE INDEX IF NOT EXISTS idx_logistics_file_created_by
    ON logistics_file (created_by);

CREATE INDEX IF NOT EXISTS idx_logistics_incident_created_by
    ON logistics_incident (created_by);

CREATE INDEX IF NOT EXISTS idx_logistics_incident_responsible_user_id
    ON logistics_incident (responsible_user_id);

CREATE INDEX IF NOT EXISTS idx_logistics_quotation_created_by
    ON logistics_quotation (created_by);

CREATE INDEX IF NOT EXISTS idx_logistics_receivable_created_by
    ON logistics_receivable (created_by);

CREATE INDEX IF NOT EXISTS idx_logistics_service_request_created_by
    ON logistics_service_request (created_by);

CREATE INDEX IF NOT EXISTS idx_logistics_shipment_created_by
    ON logistics_shipment (created_by);

CREATE INDEX IF NOT EXISTS idx_logistics_trip_created_by
    ON logistics_trip (created_by);

CREATE INDEX IF NOT EXISTS idx_logistics_trip_id_logistics_operator
    ON logistics_trip (id_logistics_operator);

CREATE INDEX IF NOT EXISTS idx_logistics_trip_id_logistics_trailer
    ON logistics_trip (id_logistics_trailer);

CREATE INDEX IF NOT EXISTS idx_quotation_comment_id_user
    ON quotation_comment (id_user);

CREATE INDEX IF NOT EXISTS idx_restaurant_cash_session_closed_by_id
    ON restaurant_cash_session (closed_by_id);

CREATE INDEX IF NOT EXISTS idx_restaurant_cash_session_created_by
    ON restaurant_cash_session (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_cash_session_opened_by_id
    ON restaurant_cash_session (opened_by_id);

CREATE INDEX IF NOT EXISTS idx_restaurant_category_created_by
    ON restaurant_category (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_dish_created_by
    ON restaurant_dish (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_guisado_created_by
    ON restaurant_guisado (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_inventory_item_created_by
    ON restaurant_inventory_item (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_inventory_movement_created_by
    ON restaurant_inventory_movement (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_order_created_by
    ON restaurant_order (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_order_id_restaurant_waiter
    ON restaurant_order (id_restaurant_waiter);

CREATE INDEX IF NOT EXISTS idx_restaurant_order_item_created_by
    ON restaurant_order_item (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_order_item_id_guisado_1
    ON restaurant_order_item (id_guisado_1);

CREATE INDEX IF NOT EXISTS idx_restaurant_order_item_id_guisado_2
    ON restaurant_order_item (id_guisado_2);

CREATE INDEX IF NOT EXISTS idx_restaurant_order_item_id_restaurant_dish
    ON restaurant_order_item (id_restaurant_dish);

CREATE INDEX IF NOT EXISTS idx_restaurant_recipe_item_created_by
    ON restaurant_recipe_item (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_recipe_item_id_restaurant_dish
    ON restaurant_recipe_item (id_restaurant_dish);

CREATE INDEX IF NOT EXISTS idx_restaurant_recipe_item_id_restaurant_inventory_item
    ON restaurant_recipe_item (id_restaurant_inventory_item);

CREATE INDEX IF NOT EXISTS idx_restaurant_reservation_created_by
    ON restaurant_reservation (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_reservation_id_restaurant_table
    ON restaurant_reservation (id_restaurant_table);

CREATE INDEX IF NOT EXISTS idx_restaurant_table_created_by
    ON restaurant_table (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_visit_created_by
    ON restaurant_visit (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_visit_id_restaurant_table
    ON restaurant_visit (id_restaurant_table);

CREATE INDEX IF NOT EXISTS idx_restaurant_visit_id_restaurant_waiter
    ON restaurant_visit (id_restaurant_waiter);

CREATE INDEX IF NOT EXISTS idx_restaurant_waiter_created_by
    ON restaurant_waiter (created_by);

CREATE INDEX IF NOT EXISTS idx_restaurant_waiter_id_user
    ON restaurant_waiter (id_user);

CREATE INDEX IF NOT EXISTS idx_stamping_operation_id_proyect
    ON stamping_operation (id_proyect);

COMMIT;
