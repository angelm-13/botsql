from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

from helpers import login


@pytest.mark.e2e
@pytest.mark.a11y
def test_login_inputs_have_accessible_names(driver, wait, settings):
    driver.get(f'{settings.frontend_url}/login')
    inputs = driver.find_elements(By.CSS_SELECTOR, 'input')
    assert inputs, 'Login page should expose input controls.'
    for element in inputs:
        label = element.get_attribute('aria-label') or element.get_attribute('placeholder') or element.get_attribute('name')
        assert label, 'Each input should expose an accessible name, placeholder, or name.'


@pytest.mark.e2e
@pytest.mark.a11y
def test_buttons_have_text_or_aria_label(driver, wait, settings):
    login(driver, wait, settings)
    buttons = driver.find_elements(By.CSS_SELECTOR, 'button')
    assert buttons
    for button in buttons[:50]:
        label = (button.text or button.get_attribute('aria-label') or '').strip()
        assert label, 'Buttons must have visible text or aria-label.'
