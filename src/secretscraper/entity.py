"""Entity classes and factory methods."""

import typing
from dataclasses import dataclass, field
from urllib.parse import ParseResult, urlparse

URL: typing.TypeAlias = ParseResult


@dataclass
class URLNode:
    """URL node used in site map."""
    depth: int
    parent: typing.Optional['URLNode']
    url: str
    url_object: typing.NamedTuple


@dataclass
class Secret:
    """Describes a unit of secret data"""
    type: str = field(compare=True)
    data: typing.Any = field(compare=True)


def create_url(url_str: str, depth: int = -1, parent: URLNode = None) -> URLNode:
    """Factory method for creating URL objects."""
    urlparsed = urlparse(url_str)
    return URLNode(depth=depth, parent=parent, url=url_str, url_object=urlparsed)
