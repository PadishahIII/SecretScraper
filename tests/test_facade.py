import logging
import pathlib
import traceback
import typing
import unittest
from collections import namedtuple
from urllib.parse import urlparse

import click
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


Validator_Type = typing.Tuple[
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
                "-x http://127.0.0.1:7890",
                "-F",
                "--debug"
            ],
            [
                (lambda setting: setting["headers"]["User-Agent"], "MyUA"),
                (lambda setting: setting["headers"]["Cookie"], "MyCookie"),
                (lambda setting: setting["max_depth"], 3),
                (lambda setting: setting["max_page_num"], 100),
                (lambda setting: setting["proxy"], "http://127.0.0.1:7890"),
                (lambda setting: setting["follow_redirects"], True),
                (lambda setting: setting["debug"], True),
                (lambda setting: setting["loglevel"], "DEBUG"),
            ],
        ),
    ],
)
def test_crawler_facade_update_settings(
    clicker: CliRunner, invoke_args: typing.List[str], validators: typing.List[Validator_Type]
):
    """Test updating settings via option"""
    result = clicker.invoke(main, invoke_args)
    if result.exception is not None:
        logger.exception(result.exception)
        raise result.exception
    from secretscraper.cmdline import facade_obj, facade_settings

    for i, validator in enumerate(validators):
        validator = Validator(*validator)
        try:
            assert True is validate_setting(
                facade_settings, validator.get_attr_func, validator.expected_value
            )
        except AssertionError as e:
            logger.error(f"Expected: {validator.expected_value}")
            raise Exception(
                f"Excepted: {validator.expected_value}, Got: {validator.get_attr_func(facade_settings)} index: {i}, Invoke-args: {invoke_args}")

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
                "-x http://127.0.0.1:7890",
            ],
            [
                (lambda crawler: crawler.headers["User-Agent"], "MyUA"),
                (lambda crawler: crawler.headers["Cookie"], "MyCookie"),
                (lambda crawler: crawler.max_depth, 3),
                (lambda crawler: crawler.max_page_num, 100),
                (lambda crawler: crawler.proxy, "http://127.0.0.1:7890"),
                (lambda crawler: len(crawler.start_urls), 1),
                # (lambda crawler: crawler.follow_redirects, False), # settings is modified via other tests
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
        # ( TODO: cannot copy file in github actions
        #     [
        #         "-u",
        #         "http://127.0.0.1:8888",
        #         "-i",
        #         pathlib.Path(__file__).parent / "local_tests" / "settings.yml",
        #     ],
        #     [(lambda crawler: crawler.headers["User-Agent"], "Test-UA")],
        # ),
        (
            ["-u", "http://127.0.0.1:8888", "-F"],
            [(lambda crawler: crawler.follow_redirects, True)],
        ),
        (
            ["-u", "http://127.0.0.1:8888", "-H"],
            [(lambda crawler: True, True)],
        ),
        (
            ["-u", "http://127.0.0.1:8888", "--detail"],
            [(lambda crawler: True, True)],
        ),
    ],
)
def test_crawler_facade_update_crawler(
    clicker: CliRunner, invoke_args: typing.List[str], validators: typing.List[Validator_Type]
):
    """Test updating crawler config via option"""
    result = clicker.invoke(main, invoke_args)
    if result.exception is not None:
        logger.exception(result.exception)
        raise result.exception
    from secretscraper.cmdline import facade_obj, facade_settings

    for i, validator in enumerate(validators):
        validator = Validator(*validator)
        try:
            assert True is validate_setting(
                facade_obj.crawler, validator.get_attr_func, validator.expected_value
            )
        except AssertionError as e:
            logger.error(f"Expected: {validator.expected_value}")
            raise Exception(
                f"Excepted: {validator.expected_value}, Got: {validator.get_attr_func(facade_obj.crawler)} index: {i}, Invoke-args: {invoke_args}")


@pytest.mark.parametrize(
    ["invoke_args"],
    [(["-u", "http://127.0.0.1:8888", "--max-depth=0"],)],

    # [(["-u", "https://www.baidu.com/", "--max-page=10","-F"],)],  # "-x", "http://127.0.0.1:8080",
    # [(["-u", "http://qyyx.dqwjj.cn:29200/IDCAS_dq/Scripts/lib/layui/layui.all.js", "--detail"],)],
    # [(["-u", "http://qyyx.dqwjj.cn:29200/IDCAS_dq"],)],
    # [(["-l", "/Users/padishah/Downloads/layui.js", "--detail"],)],
    # [(["--version"],)],
    # [(["-u", "https://gthnb.zjzwfw.gov.cn ", "-x", "http://127.0.0.1:8080", "-H"],)],
    # secretscraper -u https://meeting.nawaa.com:4433/zh-CN/home -H  -x http://127.0.0.1:8080
    # secretscraper -u http://127.0.0.1:8888

)
def test_normal_run(clicker: CliRunner, invoke_args: typing.List[str]):
    result = clicker.invoke(main, invoke_args)
    if result.exception is not None:
        logger.exception(result.exception)
        raise result.exception
    with click.open_file("1.log","w") as f:
        click.echo(result.output, file=f)
    print(result)


# @pytest.mark.parametrize( # TODO: cannot copy file in github actions
#     ["invoke_args"],
#     [
#         (["--local", "tests/local_tests/local_scan"],),
#         (["--local", "tests/local_tests/local_scan/empty_dir"],),
#         (["--local", "tests/local_tests/local_scan/source_text.txt"],),
#
#     ],
#
# )
# def test_local_scan(clicker: CliRunner, invoke_args: typing.List[str]):
#     """Test local file scanner"""
#     result = clicker.invoke(main, invoke_args)
#     if result.exception is not None:
#         logger.exception(result.exception)
#         raise result.exception
#     logger.info(result.output)
#     logger.info(result)
def test_local_scan(clicker: CliRunner, tmp_path: pathlib.Path, resource_text: str):
    """Test local file scanner"""
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "dir2").mkdir()
    (tmp_path / "dir1" / "dir2" / "resource1.txt").write_text(resource_text)
    (tmp_path / "empty_dir").mkdir()
    (tmp_path / "source_text.txt").write_text(resource_text)

    result = clicker.invoke(main, ['--local', str(tmp_path.absolute())])
    if result.exception is not None:
        logger.exception(result.exception)
        raise result.exception
    logger.info(result.output)
    logger.info(result)
