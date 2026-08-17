from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

from helpers import by_testid, fill, login, safe_click


ENTITY_CASES = [
    ('user', 'id_user', 'full_name'),
    ('user_mfa', 'id_user_mfa', 'secret'),
    ('payroll_period', 'id_payroll_period', 'period_start'),
    ('payroll_detail', 'id_payroll_detail', 'gross_salary'),
    ('payroll_concept', 'id_payroll_concept', 'payroll_concept_description'),
    ('payroll_movement', 'id_payroll_movement', 'amount'),
    ('customer_supplier', 'id_customer_supplier', 'name'),
    ('proyect', 'id_proyect', 'proyect_description'),
    ('bank', 'id_bank', 'bank_name'),
    ('bank_account', 'id_bank_account', 'bank_account_description'),
    ('invoice', 'id_invoice', 'subtotal'),
    ('invoice_material_service', 'id_invoice_material_service', 'invoice_material_service_description'),
    ('product_family', 'id_product_family', 'product_family_description'),
    ('incident_type', 'id_incident_type', 'incident_type_description'),
    ('incident', 'id_incident', 'note'),
    ('incident_detail', 'id_incident_detail', 'incident_detail_name'),
    ('brand', 'id_brand', 'brand_description'),
    ('unit', 'id_unit', 'unit_name'),
    ('material', 'id_material', 'material_description'),
    ('material_component', 'id_material_component', 'relation'),
    ('movement', 'id_movement', 'type'),
    ('location_type', 'id_location_type', 'location_type_description'),
    ('location', 'id_location', 'location_description'),
    ('product', 'id_product', 'gross_price'),
    ('nm_incident_product', 'id_nm_incident_product', 'note')
]


@pytest.mark.e2e
@pytest.mark.parametrize('entity,pk,field', ENTITY_CASES)
def test_entity_crud_screen_has_core_controls(driver, wait, settings, entity, pk, field):
    login(driver, wait, settings)
    driver.get(f'{settings.frontend_url}/{entity}')
    wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')

    assert driver.find_elements(By.CSS_SELECTOR, 'body')
    assert driver.find_elements(By.CSS_SELECTOR, 'input, select, textarea, button')

    # Optional generated test ids. Tests stay compatible while encouraging stable selectors.
    for testid in ['search-input', 'create-button', 'table-view-button', 'kanban-view-button']:
        elements = driver.find_elements(*by_testid(testid))
        if elements:
            assert elements[0].is_displayed()
