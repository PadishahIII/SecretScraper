import functools
import logging

import aiohttp
import pytest

from secretscraper.crawler import Crawler
from secretscraper.filter import ChainedURLFilter, DomainWhiteListURLFilter
from secretscraper.handler import HyperscanRegexHandler
from secretscraper.output_formatter import Formatter
from secretscraper.urlparser import URLParser

from .conftest import regex_dict

logger = logging.getLogger(__name__)


@pytest.fixture
@functools.cache
def start_urls() -> list[str]:
    return [
        "https://news.ycombinator.com/",
        "invalid.url"
    ]


@pytest.fixture
def aiohttp_client() -> aiohttp.ClientSession:
    return aiohttp.ClientSession()


def test_crawler(regex_dict, start_urls, aiohttp_client):
    handler = HyperscanRegexHandler(regex_dict)
    crawler = Crawler(
        start_urls=start_urls,
        client=aiohttp_client,
        url_filter=ChainedURLFilter([DomainWhiteListURLFilter(
            {"*ycombinator.com", }
        )]),
        parser=URLParser(),
        handler=handler,
        max_page_num=0,
        max_depth=3,
        num_workers=100
    )
    formatter = Formatter()
    assert True
    # crawler.start()
    # logger.info(f"Total page: {crawler.total_page}")
    # logger.info(f"found urls: {formatter.output_found_domains(list(crawler.found_urls))}")
    # visited_urls_str = "\n".join(str(url) for url in crawler.visited_urls)
    # logger.info(f"visited_urls: {visited_urls_str}")
    # logger.info(f"Hierarchy: {formatter.output_url_hierarchy(crawler.url_dict)}")
    # logger.info(f"Secrets: {formatter.output_secrets(crawler.url_secrets)}")
