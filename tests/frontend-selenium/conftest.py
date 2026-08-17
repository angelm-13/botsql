from __future__ import annotations

import os
import time
from dataclasses import dataclass

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait


@dataclass(frozen=True)
class Settings:
    frontend_url: str = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    backend_url: str = os.getenv('BACKEND_URL', 'http://localhost:5001')
    browser: str = os.getenv('SELENIUM_BROWSER', 'chrome')
    headless: bool = os.getenv('SELENIUM_HEADLESS', '1') == '1'
    timeout: int = int(os.getenv('SELENIUM_TIMEOUT', '15'))
    username: str = os.getenv('E2E_USERNAME', 'admin1')
    password: str = os.getenv('E2E_PASSWORD', 'Admin1234')
    mfa_code: str = os.getenv('E2E_MFA_CODE', '123456')


@pytest.fixture(scope='session')
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope='session', autouse=True)
def wait_for_frontend(settings: Settings):
    deadline = time.time() + 60
    last_error = None
    while time.time() < deadline:
        try:
            response = requests.get(settings.frontend_url, timeout=3)
            if response.status_code < 500:
                return
        except Exception as exc:  # pragma: no cover - environment dependent
            last_error = exc
        time.sleep(2)
    raise RuntimeError(f'Frontend not reachable at {settings.frontend_url}: {last_error}')


@pytest.fixture
def driver(settings: Settings):
    browser = settings.browser.lower()
    if browser == 'firefox':
        options = FirefoxOptions()
        if settings.headless:
            options.add_argument('-headless')
        instance = webdriver.Firefox(options=options)
    else:
        options = ChromeOptions()
        if settings.headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1440,1000')
        instance = webdriver.Chrome(options=options)

    instance.set_page_load_timeout(settings.timeout)
    yield instance
    instance.quit()


@pytest.fixture
def wait(driver, settings: Settings):
    return WebDriverWait(driver, settings.timeout)
