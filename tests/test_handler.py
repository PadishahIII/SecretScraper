import asyncio
import concurrent.futures
import logging
import sys
import typing

import pytest
from bs4 import BeautifulSoup

from secretscraper.entity import Secret
from secretscraper.exception import HandlerException
from secretscraper.handler import BSHandler, BSResult, ReRegexHandler
from secretscraper.util import is_hyperscan

from . import settings

# from tests import duration


logger = logging.getLogger(__name__)


# @duration
def test_re_regex_handler(regex_dict, resource_text):
    handler = ReRegexHandler(rules=regex_dict)
    secrets: typing.List[Secret] = list(handler.handle(resource_text))
    # ensure all types of secrets are extracted at least once
    keys = set(map(lambda s: s.type, secrets))
    assert len(keys) == len(regex_dict)


def test_hyperscan_regex_handler(regex_dict, resource_text):
    if not is_hyperscan():
        return
    from secretscraper.handler import HyperscanRegexHandler
    handler = HyperscanRegexHandler(rules=regex_dict, lazy_init=True)
    with pytest.raises(HandlerException):
        handler.handle("")
    handler.init()

    result = set(list(handler.handle(resource_text)))
    # logger.info("after handle")
    result_str = "\n".join(f"{re.type}:{re.data}" for re in result)
    logger.info(f"result:\n {result_str}")

    result_types = set(map(lambda s: s.type, result))

    assert len(result_types) == len(regex_dict)


# @pytest.mark.asyncio
# async def test_hyperscan_handler_async(resource_text, regex_dict, event_loop: asyncio.AbstractEventLoop):
#     handler = HyperscanRegexHandler(rules=regex_dict, lazy_init=False)
#     pool = concurrent.futures.ProcessPoolExecutor(max_workers=4)
#     result = await event_loop.run_in_executor(pool, handler.handle, resource_text)
#     logger.info(f"Result: {result}")
#     result_types = list(map(lambda s: s.type, result))
#
#     assert len(result_types) == len(regex_dict)


def test_bs_handler(html_text):
    def filter_login(soup: BeautifulSoup) -> typing.List[BSResult]:
        """Get all link elements that contains login literal"""
        links = soup.find_all("a")
        return [link for link in links if link.getText() == "login"]

    handler = BSHandler(filter_func=filter_login)
    results = handler.handle(html_text)
    res = "\n".join(list(map(lambda s: str(s), results)))
    # logger.info(f"Results: {res}")
    assert len(list(results)) == 1

# def test_get_rules_from_settings():
# settings.RULES[0].get("regex")
