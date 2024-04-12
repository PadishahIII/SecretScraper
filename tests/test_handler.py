import logging

import pytest
from bs4 import BeautifulSoup

from secretscraper.entity import Secret
from secretscraper.exception import HandlerException
from secretscraper.handler import (BSHandler, BSResult, HyperscanRegexHandler,
                                   ReRegexHandler)
from tests import duration

logger = logging.getLogger(__name__)


@duration
def test_re_regex_handler(regex_dict, resource_text):
    handler = ReRegexHandler(rules=regex_dict)
    secrets: list[Secret] = list(handler.handle(resource_text))
    # ensure all types of secrets are extracted at least once
    keys = set(map(lambda s: s.type, secrets))
    assert len(keys) == len(regex_dict)


def test_hyperscan_regex_handler(regex_dict, resource_text):
    handler = HyperscanRegexHandler(rules=regex_dict, lazy_init=True)
    with pytest.raises(HandlerException):
        handler.handle("")
    handler.init()

    result = set(list(handler.handle(resource_text)))
    # logger.info("after handle")
    # logger.info(f"result: {result}")

    result_types = list(map(lambda s: s.type, result))

    assert len(result_types) == len(regex_dict)


def test_bs_handler(html_text):
    def filter_login(soup: BeautifulSoup) -> list[BSResult]:
        """Get all link elements that contains login literal"""
        links = soup.find_all("a")
        return [link for link in links if link.getText() == "login"]

    handler = BSHandler(filter_func=filter_login)
    results = handler.handle(html_text)
    res = "\n".join(list(map(lambda s: str(s), results)))
    # logger.info(f"Results: {res}")
    assert len(list(results)) == 1
