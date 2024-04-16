from typing import Set
from urllib.parse import urlparse

from secretscraper.filter import (
    ChainedURLFilter,
    DomainBlackListURLFilter,
    DomainWhiteListURLFilter,
)


def test_domain_white_list_urlfilter():
    white_list: Set[str] = {"*baidu.com", "*baidu*com"}
    filter = DomainWhiteListURLFilter(white_list)
    assert filter.doFilter(urlparse("http://baidu.com")) is True
    assert filter.doFilter(urlparse("http://www.baidu.com")) is True
    assert filter.doFilter(urlparse("http://www.baidu.xxxx.com")) is True
    assert filter.doFilter(urlparse("http://baidu.cn")) is False
    assert filter.doFilter(urlparse("http://xxx")) is False


def test_domain_black_list_urlfilter():
    black_list: Set[str] = {"*baidu.com", "*baidu*com"}
    filter = DomainBlackListURLFilter(black_list)
    assert filter.doFilter(urlparse("http://baidu.com")) is False
    assert filter.doFilter(urlparse("http://www.baidu.com")) is False
    assert filter.doFilter(urlparse("http://www.baidu.xxxx.com")) is False
    assert filter.doFilter(urlparse("http://baidu.cn")) is True
    assert filter.doFilter(urlparse("http://xxx")) is True


def test_chained_urlfilter():
    white_list: Set[str] = {"*baidu.com", "*baidu*com"}
    white_list_filter = DomainWhiteListURLFilter(white_list)
    black_list: Set[str] = {"*baidu.sensitive.com"}
    black_list_filter = DomainBlackListURLFilter(black_list)
    chained_filter = ChainedURLFilter(filters=[white_list_filter, black_list_filter])
    assert chained_filter.doFilter(urlparse("http://baidu.com")) is True
    assert chained_filter.doFilter(urlparse("http://www.baidu.com")) is True
    assert chained_filter.doFilter(urlparse("http://www.baidu.xxxx.com")) is True
    # in white list and in black list
    assert chained_filter.doFilter(urlparse("http://www.baidu.sensitive.com")) is False
