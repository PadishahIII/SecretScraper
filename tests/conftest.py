"""Test config"""

import functools
from pathlib import Path

import pytest
from click.testing import CliRunner

from secretscraper.util import read_rules_from_setting

from . import settings


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
def regex_dict() -> dict[str, str]:
    return read_rules_from_setting(settings)
