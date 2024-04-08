"""Test log"""

import pytest

from secretscraper.log import update_log_level, verbose_formatter


@pytest.mark.parametrize(
    ["debug", "level", "expect_value"],
    [
        (True, "", "DEBUG"),
        (True, "INFO", "DEBUG"),
        (False, "DEBUG", "DEBUG"),
        (False, "INFO", "INFO"),
    ],
)
def test_log_level(debug: bool, level: str, expect_value):
    """Test log level"""
    log_level_name = update_log_level(debug, level)
    assert log_level_name == expect_value


def test_verbose_formatter():
    """Test verbose formatter"""
    assert verbose_formatter(True) == "verbose"
    assert verbose_formatter(False) == "simple"
