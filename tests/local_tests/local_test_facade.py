import logging
import pathlib
import traceback
import typing
import unittest
from collections import namedtuple
from urllib.parse import urlparse

import dynaconf
import pytest
from click.testing import CliRunner

from secretscraper.cmdline import main
from secretscraper.facade import CrawlerFacade
from secretscraper.log import init_log

init_log()
logger = logging.getLogger(__file__)


def validate_setting(
    obj: typing.Any,
    get_attr_func: typing.Callable[
        [
            typing.Any,
        ],
        typing.Any,
    ],
    expected_value: typing.Any,
) -> bool:
    """Validate setting attribute is expected"""
    try:
        value = get_attr_func(obj)
        ret = value == expected_value
        return ret
    except AttributeError as e:
        logger.error(traceback.format_exc())
        return False


Validator_Type = tuple[
    typing.Callable[
        [
            typing.Any,
        ],
        typing.Any,
    ],
    typing.Any,
]
Validator = namedtuple("Validator", ["get_attr_func", "expected_value"])


@pytest.mark.parametrize(
    ["invoke_args", "validators"],
    [
        (
            [
                "-u http://127.0.0.1:8888",
                "-a MyUA",
                "--cookie=MyCookie",
                "--max-page=100",
                "--max-depth=3",
                "-x socks://127.0.0.1:7890",
                "-F",
            ],
            [
                (lambda setting: setting["headers"]["User-Agent"], "MyUA"),
                (lambda setting: setting["headers"]["Cookie"], "MyCookie"),
                (lambda setting: setting["max_depth"], 3),
                (lambda setting: setting["max_page_num"], 100),
                (lambda setting: setting["proxy"], "socks://127.0.0.1:7890"),
                (lambda setting: setting["follow_redirects"], True),
            ],
        ),
    ],
)
def test_crawler_facade_update_settings(
    clicker: CliRunner, invoke_args: list[str], validators: list[Validator_Type]
):
    """Test updating settings via option"""
    result = clicker.invoke(main, invoke_args)
    if result.exception is not None:
        logger.exception(result.exception)
        raise result.exception
    from secretscraper.cmdline import facade_obj, facade_settings

    for validator in validators:
        validator = Validator(*validator)
        assert True is validate_setting(
            facade_settings, validator.get_attr_func, validator.expected_value
        )

    # logger.info(f"Result: {result}\nOutput: {result.output}")


@pytest.mark.parametrize(
    ["invoke_args", "validators"],
    [
        (
            [
                "-u http://127.0.0.1:8888",
                "-a MyUA",
                "--cookie=MyCookie",
                "--max-page=100",
                "--max-depth=3",
                "-x socks://127.0.0.1:7890",
            ],
            [
                (lambda crawler: crawler.headers["User-Agent"], "MyUA"),
                (lambda crawler: crawler.headers["Cookie"], "MyCookie"),
                (lambda crawler: crawler.max_depth, 3),
                (lambda crawler: crawler.max_page_num, 100),
                (lambda crawler: crawler.proxy, "socks://127.0.0.1:7890"),
                (lambda crawler: len(crawler.start_urls), 1),
                (lambda crawler: crawler.follow_redirects, False),
            ],
        ),
        (
            ["--url-file", f"{pathlib.Path(__file__).parent / 'urls.txt'}"],
            [(lambda crawler: len(crawler.start_urls), 4)],
        ),
        (
            ["-u http://127.0.0.1:8888", "-m", "1"],
            [(lambda crawler: crawler.max_depth, 1)],
        ),
        (
            ["-u http://127.0.0.1:8888", "-m", "2"],
            [(lambda crawler: crawler.max_depth, 2)],
        ),
        (
            ["-u", "http://127.0.0.1:8888", "-d", "127.0.0.1"],
            [
                (
                    lambda crawler: crawler.filter.doFilter(
                        urlparse("http://127.0.0.1")
                    ),
                    True,
                ),
                (
                    lambda crawler: crawler.filter.doFilter(
                        urlparse("http://baidu.com")
                    ),
                    False,
                ),
            ],
        ),
        (
            ["-u", "http://127.0.0.1:8888", "-D", "127.0.0.1"],
            [
                (
                    lambda crawler: crawler.filter.doFilter(
                        urlparse("http://127.0.0.1")
                    ),
                    False,
                ),
                (
                    lambda crawler: crawler.filter.doFilter(
                        urlparse("http://baidu.com")
                    ),
                    True,
                ),
            ],
        ),
        (
            [
                "-u",
                "http://127.0.0.1:8888",
                "-i",
                pathlib.Path(__file__).parent / "settings.yml",
            ],
            [(lambda crawler: crawler.headers["User-Agent"], "Test-UA")],
        ),
        (
            ["-u", "http://127.0.0.1:8888", "-F"],
            [(lambda crawler: crawler.follow_redirects, True)],
        ),
    ],
)
def test_crawler_facade_update_crawler(
    clicker: CliRunner, invoke_args: list[str], validators: list[Validator_Type]
):
    """Test updating crawler config via option"""
    result = clicker.invoke(main, invoke_args)
    if result.exception is not None:
        logger.exception(result.exception)
        raise result.exception
    from secretscraper.cmdline import facade_obj, facade_settings

    for validator in validators:
        validator = Validator(*validator)
        assert True is validate_setting(
            facade_obj.crawler, validator.get_attr_func, validator.expected_value
        )


@pytest.mark.parametrize(
    ["invoke_args"],
    [(["-u", "http://www.baidu.com/1", "-x", "http://127.0.0.1:8080"],)],
)
def test_normal_run(clicker: CliRunner, invoke_args: list[str]):
    result = clicker.invoke(main, invoke_args)
    logger.info(result.output)
    logger.info(result)
