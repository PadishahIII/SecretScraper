import logging
from urllib.parse import urlparse

from secretscraper.entity import URLNode
from secretscraper.urlparser import URLParser

logger = logging.getLogger(__file__)


def test_urlparser(html_text):
    base_url = "https://news.ycombinator.com/"
    base_url = URLNode(url=base_url, url_object=urlparse(base_url), depth=0, parent=None)
    parser = URLParser()
    urls = parser.extract_urls(base_url, html_text)
    res = '\n'.join(str(url) for url in urls)
    # logger.info(f"urls:{len(urls)}: {res}")
    assert len(urls) > 0
