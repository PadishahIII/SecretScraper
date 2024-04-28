"""URL filters that determine whether or not a URL should be crawled"""

import fnmatch
from typing import List, Protocol, Set

from secretscraper.entity import URL, URLNode
from secretscraper.util import to_host_port


class URLFilter(Protocol):
    """Base interface for URL filters"""

    def doFilter(self, url: URL) -> bool:
        """Whether a URL should be crawled"""
        ...


class DomainWhiteListURLFilter(URLFilter):
    """Filter URLs whose domain is whitelisted"""

    def __init__(self, white_list: Set[str]):
        self.white_list = white_list

    def doFilter(self, url: URL) -> bool:
        """Whether a url's domain is whitelisted

        - Support wildcards and any other Unix filename pattern.
        - Case-insensitive

        """
        domain, _ = to_host_port(url.netloc)
        match: bool = False
        for pattern in self.white_list:
            if fnmatch.fnmatch(domain, pattern):
                match = True
                break
        return match


class DomainBlackListURLFilter(URLFilter):
    """Filter URLs whose domain is blacklisted"""

    def __init__(self, blacklist: Set[str]):
        self.blacklist = blacklist

    def doFilter(self, url: URL) -> bool:
        """Whether a url's domain is blacklisted

        :return bool: True if url's domain is not in blacklist
        """
        domain, _ = to_host_port(url.netloc)
        match: bool = False
        for pattern in self.blacklist:
            if fnmatch.fnmatch(domain, pattern):
                match = True
                break
        return not match


class ChainedURLFilter(URLFilter):
    """Filter chain
    A filter chain that perform filters one by one util all filters accept the target or one filter rejects the target
    """

    def __init__(self, filters: List[URLFilter]):
        self.filter_chain = filters

    def doFilter(self, url: URL) -> bool:
        """Whether a url is acceptable"""
        accept: bool = True
        for filter in self.filter_chain:
            if filter.doFilter(url):
                continue
            else:
                accept = False
                break
        return accept
