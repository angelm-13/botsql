from __future__ import annotations

from urllib.parse import urljoin

import pytest
import requests
from bs4 import BeautifulSoup


@pytest.mark.smoke
def test_frontend_links_are_reachable(settings):
    response = requests.get(settings.frontend_url, timeout=10)
    assert response.status_code < 500
    soup = BeautifulSoup(response.text, 'html.parser')
    links = [a.get('href') for a in soup.find_all('a') if a.get('href')]
    for href in links[:50]:
        if href.startswith(('mailto:', 'tel:', '#', 'javascript:')):
            continue
        url = urljoin(settings.frontend_url, href)
        result = requests.get(url, timeout=10, allow_redirects=True)
        assert result.status_code < 500, url
