"""Test cmdline"""

from __future__ import annotations  # PEP 585

import pytest
from click.testing import CliRunner

from secretscraper import __version__
from secretscraper.cmdline import main


@pytest.mark.parametrize(
    ["invoke_args", "exit_code", "output_keyword"],
    [
        ([], 0, "help"),
        (["--help"], 0, "help"),
        (["--version"], 0, __version__),
        (["-V"], 0, __version__),
        (["--debug", "--verbose", "run"], 0, "run"),
    ],
)
def test_main(
    clicker: CliRunner,
    invoke_args: list[str],
    exit_code: int,
    output_keyword: str,
):
    """Test main cmdline"""
    result = clicker.invoke(main, invoke_args)
    assert result.exit_code == exit_code
    assert output_keyword in result.output
