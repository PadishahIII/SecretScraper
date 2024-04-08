"""Test config"""

import pytest
from click.testing import CliRunner


@pytest.fixture()
def clicker():
    """clicker fixture"""
    yield CliRunner()
