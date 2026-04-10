"""Test config"""

import functools
import os
import typing
from pathlib import Path

import pytest
from click.testing import CliRunner

from secretscraper.util import read_rules_from_setting, start_local_test_http_server

from . import settings


# Python 3.13's tmp_path handling can reach getpass.getuser() on Windows.
# Some CI runners do not provide USERNAME, so seed a stable fallback for tests.
os.environ.setdefault("USERNAME", os.environ.get("USER", "pytest"))


@pytest.fixture()
def clicker():
    """clicker fixture"""
    yield CliRunner()


@pytest.fixture
@functools.cache
def resource_text() -> str:
    with open(Path(__file__).parent / "resources" / "source_text.txt") as f:
        s = f.read()
    return s


@pytest.fixture
@functools.cache
def html_text() -> str:
    with open(Path(__file__).parent / "resources" / "HackerNews.html") as f:
        s = f.read()
    return s


@pytest.fixture
@functools.cache
def local_html_text() -> str:
    with open(Path(__file__).parent / "resources" / "local_server" / "index.html") as f:
        s = f.read()
    return s


@pytest.fixture
@functools.cache
def regex_dict() -> typing.Dict[str, str]:
    return read_rules_from_setting(settings)


@pytest.fixture
def local_http_server_base_url() -> typing.Generator[str, None, None]:
    thread, httpd = start_local_test_http_server("127.0.0.1", 0)
    assert httpd is not None
    try:
        port = httpd.server_address[1]
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        if thread is not None:
            thread.join(timeout=1)
