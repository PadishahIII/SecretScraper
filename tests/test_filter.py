from typing import Set
from urllib.parse import urlparse

from secretscraper.filter import (ChainedURLFilter, DomainBlackListURLFilter,
                                  DomainWhiteListURLFilter)


def test_domain_white_list_urlfilter():
    white_list: Set[str] = {"*local.test", "*local*test"}
    filter = DomainWhiteListURLFilter(white_list)
    assert filter.doFilter(urlparse("http://local.test")) is True
    assert filter.doFilter(urlparse("http://www.local.test")) is True
    assert filter.doFilter(urlparse("http://www.local.xxxx.test")) is True
    assert filter.doFilter(urlparse("http://local.invalid")) is False
    assert filter.doFilter(urlparse("http://loopback")) is False


def test_domain_black_list_urlfilter():
    black_list: Set[str] = {"*local.test", "*local*test"}
    filter = DomainBlackListURLFilter(black_list)
    assert filter.doFilter(urlparse("http://local.test")) is False
    assert filter.doFilter(urlparse("http://www.local.test")) is False
    assert filter.doFilter(urlparse("http://www.local.xxxx.test")) is False
    assert filter.doFilter(urlparse("http://local.invalid")) is True
    assert filter.doFilter(urlparse("http://loopback")) is True


def test_chained_urlfilter():
    white_list: Set[str] = {"*local.test", "*local*test"}
    white_list_filter = DomainWhiteListURLFilter(white_list)
    black_list: Set[str] = {"*local.sensitive.test"}
    black_list_filter = DomainBlackListURLFilter(black_list)
    chained_filter = ChainedURLFilter(filters=[white_list_filter, black_list_filter])
    assert chained_filter.doFilter(urlparse("http://local.test")) is True
    assert chained_filter.doFilter(urlparse("http://www.local.test")) is True
    assert chained_filter.doFilter(urlparse("http://www.local.xxxx.test")) is True
    # in white list and in black list
    assert chained_filter.doFilter(urlparse("http://www.local.sensitive.test")) is False
