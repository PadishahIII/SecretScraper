import logging
from urllib.parse import urlparse

from secretscraper.config import settings
from secretscraper.entity import URLNode
from secretscraper.handler import ReRegexHandler
from secretscraper.urlparser import RegexURLParser, URLParser

from .conftest import html_text

logger = logging.getLogger(__file__)


def test_urlparser(html_text):
    base_url = "https://news.ycombinator.com/"
    base_url = URLNode(
        url=base_url, url_object=urlparse(base_url), depth=0, parent=None
    )
    parser = URLParser()
    urls = parser.extract_urls(base_url, html_text)
    res = "\n".join(str(url) for url in urls)
    # logger.info(f"urls:{len(urls)}: {res}")
    assert len(urls) > 0


def test_urlparser_non_html():
    base_url = "https://news.ycombinator.com/"
    base_url = URLNode(
        url=base_url, url_object=urlparse(base_url), depth=0, parent=None
    )
    parser = URLParser()
    urls = parser.extract_urls(base_url, "xxxxxx")
    # res = '\n'.join(str(url) for url in urls)
    # logger.info(f"urls:{len(urls)}: {res}")
    assert len(urls) == 0


def test_regex_urlparser(html_text):
    base_url = "https://news.ycombinator.com/"
    base_url = URLNode(
        url=base_url, url_object=urlparse(base_url), depth=0, parent=None
    )

    rules: typing.List[str] = settings.get("urlFind")
    rules.extend(settings.get("jsFind"))
    rules_dict = {f"urlFinder_{i}": rule for i, rule in enumerate(rules)}
    parser = RegexURLParser(ReRegexHandler(rules_dict))

    urls = parser.extract_urls(base_url, html_text)
    res = "\n".join(str(url) for url in urls)
    logger.info(f"{res}")
    assert len(urls) > 0
