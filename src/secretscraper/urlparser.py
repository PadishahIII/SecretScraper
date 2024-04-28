"""Extract URL nodes in HTML page."""

from typing import Set
from urllib.parse import ParseResult, urlparse

from bs4 import BeautifulSoup

from .handler import Handler
from .entity import URL, URLNode, Secret
from .util import is_static_resource, sanitize_url


class URLParser:
    """Extract URL nodes in HTML"""

    def __init__(self):
        pass

    def extract_urls(self, base_url: URLNode, text: str) -> Set[URLNode]:
        """Extract URL nodes"""
        found_urls: Set[URLNode] = set()
        soup = BeautifulSoup(text, "html.parser")
        current_depth = base_url.depth + 1
        links_a = soup.find_all("a")
        links_link = soup.find_all("link")
        links_script = soup.find_all("script")
        hrefs: Set[str] = set()

        for link in links_link:
            try:
                href = str(link["href"])
                hrefs.add(href)
            except KeyError:
                pass
                # try:
                #     href = str(link["href"])
                #     hrefs.add(href)
                # except KeyError:
                #     pass

        for link in links_a:
            try:
                href = str(link["href"])
                hrefs.add(href)
            except KeyError:
                pass

        for link in links_script:
            try:
                href = str(link["src"])
                if href.endswith(".js"):
                    hrefs.add(href)
            except KeyError:
                pass

        for href in hrefs:
            if href is not None:
                url_obj = urlparse(href)

                if is_static_resource(url_obj.path):
                    continue
                href = sanitize_url(href)
                if len(href) == 0:
                    continue
                if (
                    len(url_obj.scheme) > 0
                    and url_obj.netloc is not None
                    and len(url_obj.netloc) > 0
                ):
                    # a full url
                    node = URLNode(
                        depth=current_depth,
                        parent=base_url,
                        url=url_obj.geturl(),
                        url_object=url_obj,
                    )
                    found_urls.add(node)
                else:
                    # only a path on base_url
                    url_obj = URL(
                        scheme=base_url.url_object.scheme,
                        netloc=base_url.url_object.netloc,
                        path=url_obj.path,
                        params=url_obj.params,
                        query=url_obj.query,
                        fragment=url_obj.fragment,
                    )
                    node = URLNode(
                        depth=current_depth,
                        parent=base_url,
                        url=url_obj.geturl(),
                        url_object=url_obj,
                    )
                    found_urls.add(node)
        return found_urls


class RegexURLParser(URLParser):
    """Extract URLs via regex and HTML node"""

    def __init__(self, handler: Handler):
        self.handler: Handler = handler
        super().__init__()

    def extract_urls(self, base_url: URLNode, text: str) -> Set[URLNode]:
        """Extract URLs via regex and HTML node"""
        found_urls: Set[URLNode] = set()
        current_depth = base_url.depth + 1

        links: set[Secret] = set(self.handler.handle(text))
        for link in links:
            link = link.data
            if len(link) == 0:
                continue
            obj = urlparse(link)
            # ignore static resource
            if is_static_resource(obj.path):
                continue
            link = sanitize_url(link)
            if len(link) == 0:
                continue
            url_obj = URL(
                scheme=base_url.url_object.scheme if obj.scheme == "" or obj.scheme not in (
                    "http", "https") else obj.scheme,
                netloc=base_url.url_object.netloc if obj.netloc == "" else obj.netloc,
                path=obj.path,
                params=obj.params,
                query=obj.query,
                fragment=obj.fragment,
            )
            node = URLNode(
                depth=current_depth,
                parent=base_url,
                url=url_obj.geturl(),
                url_object=url_obj,
            )
            found_urls.add(node)

        found_urls.update(super().extract_urls(base_url, text))
        return found_urls
