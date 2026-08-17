from __future__ import annotations

import pytest

from helpers import login


VIEWPORTS = [(390, 844), (768, 1024), (1440, 1000)]


@pytest.mark.e2e
@pytest.mark.responsive
@pytest.mark.parametrize('width,height', VIEWPORTS)
def test_dashboard_responsive_viewports(driver, wait, settings, width, height):
    driver.set_window_size(width, height)
    login(driver, wait, settings)
    driver.get(settings.frontend_url)
    wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
    assert driver.execute_script('return document.body.scrollWidth') <= max(width + 40, 430)
