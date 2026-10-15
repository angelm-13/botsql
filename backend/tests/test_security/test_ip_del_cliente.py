import os
from unittest import mock

from flask import Flask

from app.utils.client_ip import client_ip


def _ip(cabecera, **env):
    app = Flask(__name__)
    with mock.patch.dict(os.environ, env), app.test_request_context(
            "/", headers={"X-Forwarded-For": cabecera}, environ_base={"REMOTE_ADDR": "10.0.0.9"}):
        return client_ip()


def test_without_the_variable_it_keeps_the_first_entry():
    assert _ip("1.1.1.1, 2.2.2.2") == "1.1.1.1"


def test_with_one_trusted_hop_it_takes_the_entry_our_proxy_added():
    assert _ip("6.6.6.6, 2.2.2.2", TRUSTED_PROXY_HOPS="1") == "2.2.2.2"


def test_a_spoofed_leading_entry_is_ignored_when_hops_are_configured():
    assert _ip("9.9.9.9, 8.8.8.8, 2.2.2.2", TRUSTED_PROXY_HOPS="1") == "2.2.2.2"


def test_with_no_header_it_falls_back_to_the_socket():
    assert _ip("") == "10.0.0.9"
