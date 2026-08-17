from __future__ import annotations

import pytest

from helpers import login


ENTITIES = [
        'user',
        'user_mfa',
        'payroll_period',
        'payroll_detail',
        'payroll_concept',
        'payroll_movement',
        'customer_supplier',
        'proyect',
        'bank',
        'bank_account',
        'invoice',
        'invoice_material_service',
        'product_family',
        'incident_type',
        'incident',
        'incident_detail',
        'brand',
        'unit',
        'material',
        'material_component',
        'movement',
        'location_type',
        'location',
        'product',
        'nm_incident_product',
        'task',
        'task_note',
        'ticket',
        'fiscal_account',
        'fiscal_stamp',
]


@pytest.mark.e2e
@pytest.mark.smoke
def test_main_navigation_loads(driver, wait, settings):
    login(driver, wait, settings)
    driver.get(settings.frontend_url)
    assert driver.title is not None


@pytest.mark.e2e
@pytest.mark.parametrize('entity', ENTITIES)
def test_entity_routes_do_not_crash(driver, wait, settings, entity):
    login(driver, wait, settings)
    driver.get(f'{settings.frontend_url}/{entity}')
    wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
    body = driver.find_element('tag name', 'body').text.lower()
    assert 'uncaught runtime errors' not in body
    assert 'application error' not in body
