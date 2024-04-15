"""Entity classes and factory methods."""

import typing
from dataclasses import dataclass, field
from urllib.parse import ParseResult, urlparse

URL: typing.TypeAlias = ParseResult


@dataclass(unsafe_hash=True, eq=True)
class URLNode:
    """URL node used in site map.
    Compare based on url_object.
    """

    url: str = field(hash=False, compare=False)
    url_object: ParseResult = field(hash=True, compare=True)
    response_status: str = field(default="Unknown", hash=False, compare=False)
    depth: int = field(default=0, hash=False, compare=False)
    parent: typing.Optional["URLNode"] = field(default=None, hash=False, compare=False)

    def __post_init__(self):
        if self.parent is not None and self.depth <= self.parent.depth:
            raise ValueError(
                f"URLNode: depth({self.depth}) must be greater than that of parent({self.parent.depth})"
            )


@dataclass(eq=True, frozen=True)
class Secret:
    """Describes a unit of secret data
    Hashable.
    """

    type: str = field(compare=True, hash=True)
    data: typing.Any = field(compare=True, hash=True)


def create_url(url_str: str, depth: int = -1, parent: URLNode = None) -> URLNode:
    """Factory method for creating URL objects."""
    urlparsed = urlparse(url_str)
    return URLNode(depth=depth, parent=parent, url=url_str, url_object=urlparsed)
