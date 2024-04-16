"""Test crawler on local server and other test websites. This file will not be executed automatically."""

import functools
import logging

import aiohttp
import pytest

from secretscraper.crawler import Crawler
from secretscraper.filter import (
    ChainedURLFilter,
    DomainBlackListURLFilter,
    DomainWhiteListURLFilter,
)
from secretscraper.handler import HyperscanRegexHandler
from secretscraper.output_formatter import Formatter
from secretscraper.urlparser import URLParser
from tests.conftest import regex_dict

logger = logging.getLogger(__name__)


@pytest.fixture
@functools.cache
def start_urls() -> list[str]:
    return [
        # "https://news.ycombinator.com/",
        # "https://scrapeme.live/shop/",
        "https://scrape.center/",
        # "invalid.url"
    ]


@pytest.fixture
def aiohttp_client() -> aiohttp.ClientSession:
    return aiohttp.ClientSession()


def test_crawler_scrapeme(regex_dict):
    """
    Test max depth and normal work
    """
    handler = HyperscanRegexHandler(regex_dict)
    max_depth = 1
    urlfilter = ChainedURLFilter(
        [
            DomainWhiteListURLFilter(
                # {"*ycombinator.com", }
                {
                    "*scrapeme*",
                }
            )
        ]
    )
    max_page_num = 0
    crawler = Crawler(
        start_urls=[
            "https://scrapeme.live/shop/",
        ],
        # client=aiohttp_client,
        url_filter=urlfilter,
        parser=URLParser(),
        handler=handler,
        max_page_num=max_page_num,
        max_depth=max_depth,
        num_workers=100,
        proxy="socks://127.0.0.1:7890",
        verbose=False,
        timeout=10,
        debug=False,
    )
    formatter = Formatter()
    crawler.start()
    for url in crawler.visited_urls:
        assert max_depth <= 0 or url.depth <= max_depth
        assert urlfilter.doFilter(url.url_object) is True
    if max_page_num > 0:
        assert crawler.total_page <= max_page_num
    logger.info(f"Total page: {crawler.total_page}")
    logger.info(
        f"found urls: {formatter.output_found_domains(list(crawler.found_urls))}"
    )
    logger.info(f"Hierarchy: {formatter.output_url_hierarchy(crawler.url_dict)}")
    logger.info(f"Secrets: {formatter.output_secrets(crawler.url_secrets)}")
    logger.info(f"{formatter.output_js(crawler.js_dict)}")


def test_crawler_local(regex_dict, start_urls):
    """
    Test max depth and normal work, run `python -m http.server 8888` in resources/local_server folder first.
    max_page: passed
    max_depth: passed
    extract secrets: passed
    """
    handler = HyperscanRegexHandler(regex_dict)
    max_depth = 2
    urlfilter = ChainedURLFilter(
        [
            DomainBlackListURLFilter(
                # {"*ycombinator.com", }
                # {"*scrapeme*", }
                set()
            )
        ]
    )
    max_page_num = 100
    crawler = Crawler(
        # start_urls=["https://scrapeme.live/shop/", ],
        start_urls=[
            "http://localhost:8888",
        ],
        # client=aiohttp_client,
        url_filter=urlfilter,
        parser=URLParser(),
        handler=handler,
        max_page_num=max_page_num,
        max_depth=max_depth,
        num_workers=100,
        # proxy="socks://127.0.0.1:7890",
        verbose=False,
        timeout=10,
    )
    formatter = Formatter()
    crawler.start()
    for url in crawler.visited_urls:
        assert max_depth <= 0 or url.depth <= max_depth
        assert urlfilter.doFilter(url.url_object) is True
    if max_page_num > 0:
        assert crawler.total_page <= max_page_num
    logger.info(f"Total page: {crawler.total_page}")
    logger.info(
        f"found urls: {formatter.output_found_domains(list(crawler.found_urls))}"
    )
    # visited_urls_str = "\n".join(str(url) for url in crawler.visited_urls)
    # logger.info(f"visited_urls: {visited_urls_str}")
    logger.info(f"Hierarchy: {formatter.output_url_hierarchy(crawler.url_dict)}")
    logger.info(f"Secrets: {formatter.output_secrets(crawler.url_secrets)}")
    logger.info(f"{formatter.output_js(crawler.js_dict)}")


# @pytest.mark.asyncio
# async def test_fetch(regex_dict, start_urls, aiohttp_client, event_loop):
#     async with aiohttp.ClientSession() as session:
#         res = await session.get("https://www.baidu.com", proxy=None)
#         res_text = await res.text()
#         logger.debug(f"res: {res_text}")
