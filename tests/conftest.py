"""Test config"""
import functools
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture()
def clicker():
    """clicker fixture"""
    yield CliRunner()


@pytest.fixture
@functools.cache
def resource_text() -> str:
    with open(Path(__file__).parent / 'resources' / 'source_text.txt') as f:
        s = f.read()
    return s


@pytest.fixture
@functools.cache
def html_text() -> str:
    with open(Path(__file__).parent / 'resources' / 'HackerNews.html') as f:
        s = f.read()
    return s


@pytest.fixture
@functools.cache
def regex_dict() -> dict[str, str]:
    return {
        "swagger": r"\b((swagger-ui.html)|(\"swagger\":)|(Swagger UI)|(swaggerUi)|(swaggerVersion))\b",
        "id card": r'\b((\d{8}(0\d|10|11|12)([0-2]\d|30|31)\d{3}\$)|(\d{6}(18|19|20)\d{2}(0[1-9]|10|11|12)([0-2]\d|30|31)\d{3}(\d|X|x)))\b',
        "phone number": r'\b((?:(?:\+|00)86)?1(?:(?:3[\d])|(?:4[5-79])|(?:5[0-35-9])|(?:6[5-7])|(?:7[0-8])|(?:8[\d])|(?:9[189]))\d{8})\b',
        "js map": r"(\.js\.map)"
    }
