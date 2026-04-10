import queue
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

from secretscraper.crawler import Crawler
from secretscraper.entity import URLNode


class AcceptAllFilter:
    def doFilter(self, url):
        return True


class SingleChildParser:
    def __init__(self, child_url: str):
        self.child_url = child_url

    def extract_urls(self, base_url: URLNode, text: str):
        return {
            URLNode(
                url=self.child_url,
                url_object=urlparse(self.child_url),
                depth=base_url.depth + 1,
                parent=base_url,
            )
        }


@pytest.mark.asyncio
async def test_validate_updates_unknown_js_children(local_http_server_base_url: str):
    crawler = object.__new__(Crawler)
    base_url = local_http_server_base_url
    child_url = f"{local_http_server_base_url}/app.js"
    base = URLNode(
        url=base_url,
        url_object=urlparse(base_url),
        response_status="Unknown",
        depth=0,
        parent=None,
    )
    child = URLNode(
        url=child_url,
        url_object=urlparse(child_url),
        response_status="Unknown",
        depth=1,
        parent=base,
    )
    crawler.url_dict = {}
    crawler.js_dict = {base: {child}}
    calls = []

    async def fake_fetch(url: str):
        calls.append(url)
        return SimpleNamespace(status_code=204)

    crawler.fetch = fake_fetch

    await Crawler.validate(crawler)

    assert calls.count(base.url) == 1
    assert calls.count(child.url) == 1
    assert base.response_status == "204"
    assert child.response_status == "204"


@pytest.mark.asyncio
async def test_extract_links_records_shared_children_for_each_parent(local_http_server_base_url: str):
    child_url = f"{local_http_server_base_url}/shared"
    crawler = object.__new__(Crawler)
    crawler.max_depth = 2
    crawler.parser = SingleChildParser(child_url)
    crawler.visited_urls = set()
    crawler.found_urls = set()
    crawler.filter = AcceptAllFilter()
    crawler.working_queue = queue.Queue()
    crawler.url_dict = {}
    crawler.js_dict = {}

    response = SimpleNamespace(headers={"content-type": "text/html"})
    base1 = URLNode(
        url=f"{local_http_server_base_url}/a",
        url_object=urlparse(f"{local_http_server_base_url}/a"),
        depth=0,
        parent=None,
    )
    base2 = URLNode(
        url=f"{local_http_server_base_url}/b",
        url_object=urlparse(f"{local_http_server_base_url}/b"),
        depth=0,
        parent=None,
    )

    await Crawler.extract_links_and_extend(crawler, base1, response, "")
    await Crawler.extract_links_and_extend(crawler, base2, response, "")

    assert {child.url for child in crawler.url_dict[base1]} == {child_url}
    assert {child.url for child in crawler.url_dict[base2]} == {child_url}
    assert crawler.working_queue.qsize() == 1


@pytest.mark.parametrize(
    ["content_type", "expected"],
    [
        ("text/html; charset=utf-8", True),
        ("application/json", True),
        ("application/pdf", False),
        ("application/octet-stream", False),
        ("image/png", False),
        ("", False),
    ],
)
def test_is_extend_only_allows_text_like_content(content_type: str, expected: bool):
    crawler = object.__new__(Crawler)
    response = SimpleNamespace(headers={"content-type": content_type})

    assert Crawler.is_extend(crawler, response) is expected
