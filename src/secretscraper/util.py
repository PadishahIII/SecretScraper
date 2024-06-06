"""Common utility functions."""
import os
import re
import sys
import typing
from collections import namedtuple
from pathlib import Path
from urllib.parse import urlparse
from threading import Thread
import requests
import tldextract
from bs4 import BeautifulSoup

# from dynaconf import LazySettings

from .entity import URL
from .exception import SecretScraperException

Range = namedtuple("Range", ["start", "end"])


def read_rules_from_setting(settings) -> typing.Dict[str, str]:
    """Read rules from settings

    :param settings: Dynaconf settings
    :return typing.Dict[str, str]: key for rule name and value for regex literal
    """
    rules_dict = dict()
    try:
        rules = settings.RULES
        for rule in rules:
            name = rule.get("name")
            regex = rule.get("regex")
            loaded = rule.get("loaded")
            if loaded is True:
                rules_dict[name] = regex
    except Exception as e:
        raise SecretScraperException(
            f"Exception occur when reading rules from setting: {e}"
        ) from e
    return rules_dict


def is_static_resource(path: str) -> bool:
    """Check whether a path is a static resource"""
    exts = {'.png', '.jpg', '.jpeg', '.gif', '.css', '.ico', ".dtd", '.svg', '.scss', '.vue', '.ts'}
    for ext in exts:
        if path.endswith(ext) or path.__contains__(ext + "?"):
            return True
    return False


def to_host_port(netloc: str) -> typing.Tuple[str, str]:
    """Convert netloc to host and port"""
    r = netloc.split(":")
    if len(r) == 1:
        return r[0], ""
    if len(r) == 2:
        return r[0].strip(), r[1].strip()
    return '', ''


def get_root_domain(host: str) -> str:
    """Get the root domain"""
    domain = tldextract.extract(host)

    return domain.domain + "." + domain.suffix


def sanitize_url(url: str) -> str:
    """Remove invalid characters in url
    Return emtpy string if url is invalid
    """
    url = url.replace(" ", "") \
        .replace("\\/", "/") \
        .replace("%3A", ":") \
        .replace("%2F", "/")
    # remove url that does not contain any word
    m = re.search("[a-zA-Z0-9]+", url)
    if m is None:
        return ""
    m = re.search(
        "\\<|\\>|\\{|\\}|\\[|\\]|\\||\\^|;|/node_modules/|www\\.w3\\.org|example\\.com|jquery[-\\.\\w]*?\\.js|\\.src|\\.replace|\\.url|\\.att|\\.href|location\\.href|javascript:|location:|application/x-www-form-urlencoded|\\.createObject|:location|\\.path|\\*#__PURE__\\*|\\*\\$0\\*|\\n",
        url
    )
    if m is not None:
        return ""

    if url.strip().startswith("javascript"):
        return ""
    try:
        obj = urlparse(url)
        if obj.netloc.startswith("127.0.0.1") or obj.netloc.startswith("localhost"):
            return ""
    except:
        pass
    return url


def is_hyperscan() -> bool:
    """Check if hyperscan is usable"""
    try:
        import hyperscan
        return True
    except ImportError:
        return False


def get_response_title(response: requests.Response) -> str:
    """Get the response title"""
    bs = BeautifulSoup(response.text, "html.parser")
    titles = list()
    for t in bs.find_all('title'):
        text = t.get_text()
        titles.append(text.replace("\n", " ").replace("\r", " ").strip())
    return "|".join(titles)


import http.server


def start_local_test_http_server(host: str, port: int, server_dir: Path = None) -> tuple[
    Thread, http.server.HTTPServer]:
    """Start local test server

    """
    # if sys.platform.startswith("win"):
    #     return None, None

    if server_dir is None:
        DIR = str(
            Path(__file__).parent.parent.parent.joinpath("tests").joinpath("resources").joinpath(
                "local_server").absolute())
    else:
        DIR = str(server_dir.absolute())

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=DIR, **kwargs)

    try:
        httpd = http.server.HTTPServer((host, port), Handler)
        thread = Thread(target=httpd.serve_forever)
        thread.start()
        return thread, httpd
    except OSError:
        return None, None
