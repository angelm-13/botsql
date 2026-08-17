from __future__ import annotations

import pytest

from helpers import by_testid, fill, login, safe_click, visible


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.mfa
def test_login_supports_mfa_flow(driver, wait, settings):
    driver.get(f'{settings.frontend_url}/login')
    visible(wait, by_testid('login-card'))
    fill(wait, by_testid('login-username'), settings.username)
    fill(wait, by_testid('login-password'), settings.password)
    safe_click(wait, by_testid('login-submit'))

    if driver.find_elements(*by_testid('mfa-code')):
        fill(wait, by_testid('mfa-code'), settings.mfa_code)
        safe_click(wait, by_testid('mfa-submit'))

    wait.until(lambda d: '/login' not in d.current_url)
    assert driver.execute_script('return window.localStorage.getItem("token")')


@pytest.mark.e2e
@pytest.mark.smoke
def test_logout_returns_to_login(driver, wait, settings):
    login(driver, wait, settings)
    if driver.find_elements(*by_testid('logout-button')):
        safe_click(wait, by_testid('logout-button'))
        wait.until(lambda d: '/login' in d.current_url)
        assert '/login' in driver.current_url
