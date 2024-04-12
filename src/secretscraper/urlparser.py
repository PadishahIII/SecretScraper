"""Extract URL nodes in HTML page."""
from typing import Set
from urllib.parse import ParseResult, urlparse

from bs4 import BeautifulSoup

from .entity import URL, URLNode


class URLParser:
    """Extract URL nodes in HTML"""

    def __init__(self):
        pass

    def extract_urls(self, base_url: URLNode, text: str) -> Set[URLNode]:
        """Extract URL nodes"""
        found_urls: Set[URLNode] = set()
        soup = BeautifulSoup(text, "html.parser")
        current_depth = base_url.depth + 1
        links = soup.find_all("a")

        for link in links:
            href = str(link['href'])
            if href is not None:
                url_obj = urlparse(href)
                if url_obj.netloc is not None and len(url_obj.netloc) > 0:
                    # a full url
                    node = URLNode(depth=current_depth, parent=base_url, url=url_obj.geturl(), url_object=url_obj)
                    found_urls.add(node)
                else:
                    # only a path on base_url
                    url_obj = URL(scheme=base_url.url_object.scheme,
                                  netloc=base_url.url_object.netloc,
                                  path=url_obj.path,
                                  params=url_obj.params,
                                  query=url_obj.query,
                                  fragment=url_obj.fragment
                                  )
                    node = URLNode(depth=current_depth, parent=base_url, url=url_obj.geturl(), url_object=url_obj)
                    found_urls.add(node)
        return found_urls
