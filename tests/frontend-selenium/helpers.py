from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def by_testid(value: str):
    return (By.CSS_SELECTOR, f'[data-testid="{value}"]')


def visible(wait, locator):
    return wait.until(EC.visibility_of_element_located(locator))


def clickable(wait, locator):
    return wait.until(EC.element_to_be_clickable(locator))


def safe_click(wait, locator):
    clickable(wait, locator).click()


def fill(wait, locator, value: str):
    element = visible(wait, locator)
    element.clear()
    element.send_keys(value)
    return element


def login(driver, wait, settings):
    driver.get(f'{settings.frontend_url}/login')
    fill(wait, by_testid('login-username'), settings.username)
    fill(wait, by_testid('login-password'), settings.password)
    safe_click(wait, by_testid('login-submit'))

    # MFA is conditional. If the MFA field exists, complete the second step.
    if driver.find_elements(*by_testid('mfa-code')):
        fill(wait, by_testid('mfa-code'), settings.mfa_code)
        safe_click(wait, by_testid('mfa-submit'))

    wait.until(lambda d: '/login' not in d.current_url)
